from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class PettyCashRequest(models.Model):
    _name = 'petty.cash.request'
    _description = 'Petty Cash Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Reference', required=True, copy=False,
                       readonly=True, default='New')
    requester_id = fields.Many2one('res.users', string='Requester',
                                   required=True, default=lambda self: self.env.user)
    amount = fields.Float('Amount', required=True, tracking=True)
    division_id = fields.Many2one('account.analytic.account',
                                  string='Division', required=True, tracking=True,
                                  domain="[('plan_id.name', '=', 'Division')]")
    expense_budget_code = fields.Char('Expense Budget Code', required=True)
    purpose = fields.Text('Purpose/Narration', required=True)

    # Document attachment
    attachment_ids = fields.Many2many('ir.attachment', string='Supporting Documents')

    # Approval fields
    state = fields.Selection([
        ('draft', 'Draft'),
        ('division_approval', 'Pending Division Head'),
        ('cfo_approval', 'Pending CFO'),
        ('approved', 'Approved'),
        ('payment_processing', 'Payment Processing'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    division_head_id = fields.Many2one('res.users', string='Division Head',
                                       compute='_compute_approvers', store=True)
    cfo_id = fields.Many2one('res.users', string='CFO',
                             compute='_compute_approvers', store=True)

    division_approved_date = fields.Datetime('Division Approved Date', readonly=True)
    cfo_approved_date = fields.Datetime('CFO Approved Date', readonly=True)

    # Accounting fields
    journal_entry_id = fields.Many2one('account.move', string='Journal Entry',
                                       readonly=True, copy=False)
    payment_id = fields.Many2one('account.payment', string='Payment',
                                 readonly=True, copy=False)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.request') or 'New'
        return super(PettyCashRequest, self).create(vals)

    @api.model
    def _send_approval_reminders(self):
        """Send reminder emails for pending approvals (called by cron)"""
        from datetime import datetime, timedelta

        # Reminder for Division Head (24 hours)
        division_cutoff = datetime.now() - timedelta(hours=24)
        division_requests = self.search([
            ('state', '=', 'division_approval'),
            ('create_date', '<=', division_cutoff)
        ])

        template_division = self.env.ref('petty_cash_request_management.email_template_division_reminder', False)
        if template_division:
            for request in division_requests:
                if request.division_head_id and request.division_head_id.email:
                    template_division.send_mail(request.id, force_send=True)

        # Reminder for CFO (24 hours after division approval)
        cfo_requests = self.search([
            ('state', '=', 'cfo_approval'),
            ('division_approved_date', '<=', division_cutoff)
        ])

        template_cfo = self.env.ref('petty_cash_request_management.email_template_cfo_reminder', False)
        if template_cfo:
            for request in cfo_requests:
                if request.cfo_id and request.cfo_id.email:
                    template_cfo.send_mail(request.id, force_send=True)

        # Reminder for Treasury (48 hours after CFO approval)
        payment_cutoff = datetime.now() - timedelta(hours=48)
        payment_requests = self.search([
            ('state', '=', 'payment_processing'),
            ('cfo_approved_date', '<=', payment_cutoff)
        ])

        template_payment = self.env.ref('petty_cash_request_management.email_template_payment_reminder', False)
        treasury_group = self.env.ref('petty_cash_request_management.group_petty_cash_treasury', False)

        if template_payment and treasury_group:
            for request in payment_requests:
                for user in treasury_group.users:
                    if user.email:
                        template_payment.with_context(treasury_officer=user).send_mail(request.id, force_send=True)

    @api.depends('division_id')
    def _compute_approvers(self):
        for record in self:
            # Get division head from analytic account manager or custom field
            record.division_head_id = record.division_id.manager_id if record.division_id else False
            # Get CFO from security group
            cfo_group = self.env.ref('petty_cash_request_management.group_petty_cash_cfo', False)
            record.cfo_id = cfo_group.users[0] if cfo_group and cfo_group.users else False

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError('Amount must be greater than zero.')
            if record.amount > 10000:
                raise ValidationError('Petty cash requests cannot exceed ₦10,000.')

    def action_submit(self):
        """Submit request for approval"""
        self.write({'state': 'division_approval'})
        self._send_notification('division')

    def action_division_approve(self):
        """Division Head approval"""
        if self.env.user != self.division_head_id:
            raise UserError('Only the Division Head can approve this request.')

        self.write({
            'state': 'cfo_approval',
            'division_approved_date': fields.Datetime.now()
        })
        self._send_notification('cfo')

    def action_cfo_approve(self):
        """CFO approval and automatic posting"""
        if not self.env.user.has_group('petty_cash_request_management.group_petty_cash_cfo'):
            raise UserError('Only the CFO can provide final approval.')

        self.write({
            'state': 'approved',
            'cfo_approved_date': fields.Datetime.now()
        })

        # Automatically create journal entry
        self._create_journal_entry()
        self._send_notification('approved')

    def action_reject(self):
        """Reject request"""
        self.write({'state': 'rejected'})
        self._send_notification('rejected')

    def action_cancel(self):
        """Cancel request"""
        self.write({'state': 'cancelled'})

    def _create_journal_entry(self):
        """Create journal entry for approved petty cash"""
        AccountMove = self.env['account.move']

        # Get accounts from company settings
        petty_cash_account = self.env.company.petty_cash_account_id
        default_expense_account = self.env.company.default_expense_account_id
        petty_cash_journal = self.env.company.petty_cash_journal_id

        # Validation with helpful error messages
        if not petty_cash_account:
            raise UserError(
                'Petty Cash Account not configured!\n\n'
                'Please go to Settings → Companies → Petty Cash tab '
                'and configure the Petty Cash Account.'
            )

        if not default_expense_account:
            raise UserError(
                'Default Expense Account not configured!\n\n'
                'Please go to Settings → Companies → Petty Cash tab '
                'and configure the Default Expense Account.'
            )

        if not petty_cash_journal:
            raise UserError(
                'Petty Cash Journal not configured!\n\n'
                'Please go to Settings → Companies → Petty Cash tab '
                'and configure the Petty Cash Journal.'
            )

        # Create journal entry
        move_vals = {
            'move_type': 'entry',
            'date': fields.Date.today(),
            'ref': self.name,
            'journal_id': petty_cash_journal.id,
            'line_ids': [
                (0, 0, {
                    'name': self.purpose or 'Petty Cash: ' + self.name,
                    'account_id': default_expense_account.id,
                    'analytic_distribution': {self.division_id.id: 100} if self.division_id else False,
                    'debit': self.amount,
                    'credit': 0,
                }),
                (0, 0, {
                    'name': self.purpose or 'Petty Cash: ' + self.name,
                    'account_id': petty_cash_account.id,
                    'debit': 0,
                    'credit': self.amount,
                })
            ]
        }

        move = AccountMove.create(move_vals)
        move.action_post()

        self.journal_entry_id = move.id
        self.state = 'payment_processing'

    def _send_notification(self, notification_type):
        """Send email notifications"""
        template_mapping = {
            'division': 'petty_cash_request_management.email_template_division_approval',
            'cfo': 'petty_cash_request_management.email_template_cfo_approval',
            'approved': 'petty_cash_request_management.email_template_approved',
            'rejected': 'petty_cash_request_management.email_template_rejected',
        }

        template_ref = template_mapping.get(notification_type)
        if template_ref:
            template = self.env.ref(template_ref, raise_if_not_found=False)
            if template:
                template.send_mail(self.id, force_send=True)

    def action_process_payment(self):
        """Process payment - called by Treasury/Payable officer"""
        # This would integrate with your payment processing
        # For amounts < 10,000: Treasury Officer
        # For amounts >= 10,000: Payable Officer

        self.state = 'paid'
        # Update division float balance
        self._update_division_float()

    def _update_division_float(self):
        """Update division float balance"""
        DivisionFloat = self.env['division.float']
        float_record = DivisionFloat.search([('division_id', '=', self.division_id.id)], limit=1)

        if float_record:
            float_record.balance -= self.amount
        else:
            DivisionFloat.create({
                'division_id': self.division_id.id,
                'balance': -self.amount
            })
