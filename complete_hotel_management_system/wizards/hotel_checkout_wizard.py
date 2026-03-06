from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HotelCheckoutWizard(models.TransientModel):
    _name = 'hotel.checkout.wizard'
    _description = 'Hotel Check-out Wizard'

    reservation_id = fields.Many2one('hotel.reservation', string='Reservation', required=True)
    guest_id = fields.Many2one(related='reservation_id.guest_id', string='Guest', readonly=True)
    room_id = fields.Many2one(related='reservation_id.room_id', string='Room', readonly=True)

    actual_checkout_date = fields.Datetime(string='Check-out Date & Time', default=fields.Datetime.now, required=True)

    # Charges Summary
    room_charges = fields.Monetary(related='reservation_id.subtotal', string='Room Charges', readonly=True,
                                   currency_field='currency_id')
    service_charges = fields.Monetary(related='reservation_id.service_total', string='Service Charges', readonly=True,
                                      currency_field='currency_id')
    deposit_amount = fields.Monetary(related='reservation_id.deposit_amount', string='Deposit Paid', readonly=True,
                                     currency_field='currency_id')
    total_amount = fields.Monetary(related='reservation_id.total_amount', string='Total Amount', readonly=True,
                                   currency_field='currency_id')
    currency_id = fields.Many2one(related='reservation_id.currency_id')

    # Balance due (total minus deposit already paid)
    balance_due = fields.Monetary(string='Balance Due', compute='_compute_balance_due',
                                  currency_field='currency_id')

    # Invoice & Payment
    create_invoice = fields.Boolean(string='Create Invoice', default=True)
    register_payment = fields.Boolean(
        string='Register Balance Payment',
        default=False,
        help='Register the balance payment immediately after creating the invoice.')
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
    ], string='Payment Method', default='cash')

    # Room Condition
    room_condition = fields.Selection([
        ('good', 'Good Condition'),
        ('minor_issues', 'Minor Issues'),
        ('damaged', 'Damaged'),
    ], string='Room Condition', default='good', required=True)

    damage_notes = fields.Text(string='Damage Notes')
    notes = fields.Text(string='Check-out Notes')

    @api.depends('total_amount', 'deposit_amount')
    def _compute_balance_due(self):
        for rec in self:
            rec.balance_due = max(rec.total_amount - rec.deposit_amount, 0.0)

    def action_confirm_checkout(self):
        self.ensure_one()

        # Update reservation
        self.reservation_id.write({
            'state': 'checked_out',
            'checkout_datetime': self.actual_checkout_date,
        })

        # Update room status — mark for cleaning
        self.room_id.write({
            'state': 'cleaning',
            'housekeeping_status': 'dirty',
        })

        # Create housekeeping task
        self.env['hotel.housekeeping'].create({
            'room_id': self.room_id.id,
            'date': fields.Date.today(),
            'task_type': 'cleaning',
            'priority': '1',
            'notes': 'Post check-out cleaning required',
        })

        # Create invoice if requested
        if self.create_invoice and not self.reservation_id.invoice_id:
            self.reservation_id.action_create_invoice()

        # Register balance payment if requested
        if self.register_payment and self.reservation_id.invoice_id and self.balance_due > 0:
            invoice = self.reservation_id.invoice_id

            # Post invoice first if still draft
            if invoice.state == 'draft':
                invoice.action_post()

            journal = self._get_payment_journal()
            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': invoice.partner_id.id,
                'amount': self.balance_due,
                'currency_id': self.reservation_id.currency_id.id,
                'journal_id': journal.id,
                'date': fields.Date.today(),
                'memo': _('Balance payment — %s') % self.reservation_id.name,
            }
            payment = self.env['account.payment'].create(payment_vals)
            payment.action_post()

            # Reconcile payment with invoice
            credit_lines = payment.move_id.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )
            debit_lines = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )
            if credit_lines and debit_lines:
                (credit_lines | debit_lines).reconcile()

        # Chatter message
        checkout_message = _('Guest checked out at %s. Room condition: %s.') % (
            self.actual_checkout_date,
            dict(self._fields['room_condition'].selection).get(self.room_condition)
        )
        if self.damage_notes:
            checkout_message += _(' Damage notes: %s') % self.damage_notes
        if self.notes:
            checkout_message += _(' Additional notes: %s') % self.notes

        self.reservation_id.message_post(body=checkout_message)

        return {'type': 'ir.actions.act_window_close'}

    def _get_payment_journal(self):
        journal_type = 'bank' if self.payment_method in ('card', 'bank_transfer', 'online') else 'cash'
        journal = self.env['account.journal'].search(
            [('type', '=', journal_type), ('company_id', '=', self.env.company.id)], limit=1)
        if not journal:
            journal = self.env['account.journal'].search(
                [('type', 'in', ['cash', 'bank']), ('company_id', '=', self.env.company.id)], limit=1)
        if not journal:
            raise UserError(_('No cash or bank journal found. Please configure one in Accounting.'))
        return journal
