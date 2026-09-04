from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class VehicleSale(models.Model):
    _name = 'vehicle.sale'
    _description = 'Vehicle Sale'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Sale Reference', required=True, copy=False,
                       readonly=True, default='New', tracking=True)
    vehicle_id = fields.Many2one('vehicle.vehicle', string='Vehicle',
                                 required=True, tracking=True,
                                 domain=[('state', 'in', ['available', 'reserved'])])
    customer_id = fields.Many2one('res.partner', string='Customer',
                                  required=True, tracking=True)
    salesperson_id = fields.Many2one('res.users', string='Salesperson',
                                     default=lambda self: self.env.user,
                                     tracking=True)

    sale_date = fields.Date(string='Sale Date', default=fields.Date.today,
                            required=True, tracking=True)
    delivery_date = fields.Date(string='Delivery Date', tracking=True)

    # Pricing
    list_price = fields.Monetary(string='List Price', required=True, tracking=True)
    discount_amount = fields.Monetary(string='Discount Amount', tracking=True)
    final_price = fields.Monetary(string='Final Price', compute='_compute_final_price',
                                  store=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Payment Terms
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('finance', 'Finance'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('mixed', 'Mixed'),
    ], string='Payment Method', required=True, default='cash', tracking=True)

    down_payment = fields.Monetary(string='Down Payment', tracking=True)
    finance_company = fields.Many2one('res.partner', string='Finance Company',
                                      domain=[('is_company', '=', True)])
    loan_amount = fields.Monetary(string='Loan Amount', tracking=True)
    loan_term = fields.Integer(string='Loan Term (months)', tracking=True)
    interest_rate = fields.Float(string='Interest Rate (%)', tracking=True)
    monthly_payment = fields.Monetary(string='Monthly Payment',
                                      compute='_compute_monthly_payment', store=True)
    total_payable = fields.Monetary(string='Total Payable (Loan)',
                                    compute='_compute_loan_totals', store=True)
    total_interest = fields.Monetary(string='Total Interest',
                                     compute='_compute_loan_totals', store=True)

    # Warranty
    warranty_months = fields.Integer(string='Warranty (Months)', default=12, tracking=True)
    warranty_expiry_date = fields.Date(string='Warranty Expiry Date',
                                       compute='_compute_warranty_expiry_date',
                                       store=True, tracking=True)
    warranty_reminder_sent = fields.Boolean(string='Warranty Reminder Sent',
                                            default=False, copy=False)

    # Trade-in
    has_trade_in = fields.Boolean(string='Has Trade-in', tracking=True)
    trade_in_vehicle = fields.Char(string='Trade-in Vehicle')
    trade_in_value = fields.Monetary(string='Trade-in Value', tracking=True)

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    # Commission
    commission_rate = fields.Float(string='Commission Rate (%)', default=2.5)
    commission_amount = fields.Monetary(string='Commission',
                                        compute='_compute_commission', store=True)

    # Documents
    contract_signed = fields.Boolean(string='Contract Signed', tracking=True)
    registration_transferred = fields.Boolean(string='Registration Transferred', tracking=True)

    # Additional fields
    notes = fields.Text(string='Notes')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    vehicle_brand_id = fields.Many2one(related='vehicle_id.brand_id',
                                       string='Vehicle Brand',
                                       store=True, readonly=True)
    vehicle_model_id = fields.Many2one(related='vehicle_id.model_id',
                                       string='Vehicle Model',
                                       store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vehicle.sale') or 'New'
        records = super().create(vals_list)
        for record in records:
            if record.vehicle_id:
                record.vehicle_id.write({
                    'state': 'reserved',
                    'sale_id': record.id
                })
        return records

    @api.depends('list_price', 'discount_amount', 'trade_in_value')
    def _compute_final_price(self):
        for record in self:
            record.final_price = record.list_price - record.discount_amount - record.trade_in_value

    @api.depends('loan_amount', 'loan_term', 'interest_rate')
    def _compute_monthly_payment(self):
        for record in self:
            if record.loan_amount and record.loan_term and record.interest_rate:
                monthly_rate = record.interest_rate / 100 / 12
                n = record.loan_term
                if monthly_rate > 0:
                    record.monthly_payment = record.loan_amount * (
                            monthly_rate * (1 + monthly_rate) ** n
                    ) / ((1 + monthly_rate) ** n - 1)
                else:
                    record.monthly_payment = record.loan_amount / n
            else:
                record.monthly_payment = 0

    @api.depends('final_price', 'commission_rate')
    def _compute_commission(self):
        for record in self:
            record.commission_amount = record.final_price * (record.commission_rate / 100)

    @api.depends('monthly_payment', 'loan_term', 'loan_amount')
    def _compute_loan_totals(self):
        for record in self:
            if record.monthly_payment and record.loan_term:
                record.total_payable = record.monthly_payment * record.loan_term
                record.total_interest = record.total_payable - record.loan_amount
            else:
                record.total_payable = 0
                record.total_interest = 0

    @api.depends('delivery_date', 'sale_date', 'warranty_months')
    def _compute_warranty_expiry_date(self):
        for record in self:
            start_date = record.delivery_date or record.sale_date
            if start_date and record.warranty_months:
                record.warranty_expiry_date = start_date + relativedelta(months=record.warranty_months)
            else:
                record.warranty_expiry_date = False

    @api.onchange('payment_method', 'final_price', 'down_payment')
    def _onchange_finance_loan_amount(self):
        if self.payment_method == 'finance' and self.final_price:
            self.loan_amount = self.final_price - (self.down_payment or 0)

    @api.constrains('payment_method', 'loan_amount', 'loan_term', 'down_payment', 'final_price')
    def _check_finance_details(self):
        for record in self:
            if record.payment_method == 'finance':
                if record.down_payment and record.final_price and record.down_payment > record.final_price:
                    raise ValidationError(_('Down payment cannot exceed the final price.'))
                if record.loan_amount and record.loan_amount < 0:
                    raise ValidationError(_('Loan amount cannot be negative.'))
                if record.loan_term and record.loan_term < 0:
                    raise ValidationError(_('Loan term cannot be negative.'))

    def write(self, vals):
        if 'delivery_date' in vals or 'warranty_months' in vals or 'sale_date' in vals:
            vals.setdefault('warranty_reminder_sent', False)
        return super().write(vals)

    def action_view_amortization_schedule(self):
        self.ensure_one()
        if not (self.loan_amount and self.loan_term):
            raise UserError(_('Please set the loan amount and loan term first.'))
        return {
            'name': _('Loan Amortization Schedule'),
            'type': 'ir.actions.act_window',
            'res_model': 'vehicle.loan.amortization.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_id': self.id},
        }

    @api.model
    def _cron_warranty_expiry_reminder(self, days_ahead=30):
        """Scheduled daily: flag delivered sales whose warranty is about to expire."""
        today = fields.Date.today()
        horizon = today + relativedelta(days=days_ahead)
        sales = self.search([
            ('state', '=', 'delivered'),
            ('warranty_expiry_date', '>=', today),
            ('warranty_expiry_date', '<=', horizon),
            ('warranty_reminder_sent', '=', False),
        ])
        template = self.env.ref(
            'vehicle_dealership.email_template_warranty_expiry', raise_if_not_found=False)
        for sale in sales:
            if sale.salesperson_id:
                sale.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Warranty expiring soon: %s') % sale.vehicle_id.name,
                    note=_('Warranty for %(vehicle)s (Customer: %(customer)s) expires on %(date)s.') % {
                        'vehicle': sale.vehicle_id.name,
                        'customer': sale.customer_id.name,
                        'date': sale.warranty_expiry_date,
                    },
                    user_id=sale.salesperson_id.id,
                    date_deadline=sale.warranty_expiry_date,
                )
            if template and sale.customer_id.email:
                template.send_mail(sale.id, force_send=False)
            sale.warranty_reminder_sent = True

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        self.vehicle_id.write({'state': 'sold'})

    def action_deliver(self):
        if not self.delivery_date:
            self.delivery_date = fields.Date.today()
        self.write({'state': 'delivered'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self.vehicle_id.write({'state': 'available', 'sale_id': False})

    def action_create_invoice(self):
        self.ensure_one()
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': f'Vehicle Sale - {self.vehicle_id.name}',
                'quantity': 1,
                'price_unit': self.final_price,
            })],
        })
        self.invoice_id = invoice.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
