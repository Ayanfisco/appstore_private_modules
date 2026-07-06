# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ClinicBilling(models.Model):
    _name = 'clinic.billing'
    _description = 'Clinic Billing Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'billing_date desc'

    name = fields.Char(string='Bill Ref', readonly=True, copy=False, default='New')
    patient_id = fields.Many2one('clinic.patient', string='Patient', required=True, index=True)
    doctor_id = fields.Many2one('clinic.doctor', string='Doctor')
    consultation_id = fields.Many2one('clinic.consultation', string='Consultation')
    billing_date = fields.Date(string='Billing Date', required=True, default=fields.Date.today)

    state = fields.Selection([
        ('draft', 'Draft'), ('confirmed', 'Confirmed'),
        ('paid', 'Paid'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    payment_method = fields.Selection([
        ('cash', 'Cash'), ('card', 'Card/POS'),
        ('transfer', 'Bank Transfer'), ('insurance', 'Insurance'),
        ('mobile', 'Mobile Money'),
    ], string='Payment Method')

    insurance_provider = fields.Char(string='Insurance Provider')
    insurance_claim_no = fields.Char(string='Claim Number')

    line_ids = fields.One2many('clinic.billing.line', 'billing_id', string='Billing Lines')

    # Tax is no longer hardcoded. It now uses real account.tax records, so it
    # adapts to whatever VAT/GST/sales-tax setup the installing company has
    # configured (Nigeria, or anywhere else) instead of assuming 7.5% VAT.
    tax_ids = fields.Many2many(
        'account.tax', string='Taxes',
        domain="[('type_tax_use', '=', 'sale'), ('company_id', '=', company_id)]",
        default=lambda self: self._default_tax_ids(),
    )
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company, required=True
    )

    subtotal = fields.Float(string='Subtotal', compute='_compute_totals', store=True)
    discount_amount = fields.Float(string='Discount')
    tax_amount = fields.Float(string='Tax', compute='_compute_totals', store=True)
    total = fields.Float(string='Total Amount', compute='_compute_totals', store=True)
    amount_paid = fields.Float(string='Amount Paid')
    balance_due = fields.Float(string='Balance Due', compute='_compute_balance', store=True)

    invoice_id = fields.Many2one('account.move', string='Odoo Invoice', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    notes = fields.Text(string='Notes')

    def _default_tax_ids(self):
        """Default to the company's configured sale taxes, if any."""
        company = self.env.company
        return company.account_sale_tax_id

    @api.depends('line_ids.total_price', 'discount_amount', 'tax_ids')
    def _compute_totals(self):
        for rec in self:
            subtotal = sum(rec.line_ids.mapped('total_price'))
            discounted_base = max(subtotal - (rec.discount_amount or 0), 0.0)
            tax = 0.0
            if rec.tax_ids:
                taxes_res = rec.tax_ids.compute_all(
                    discounted_base,
                    currency=rec.currency_id or rec.env.company.currency_id,
                    quantity=1.0,
                    product=False,
                    partner=rec.patient_id.partner_id,
                )
                tax = taxes_res['total_included'] - taxes_res['total_excluded']
            rec.subtotal = subtotal
            rec.tax_amount = tax
            rec.total = discounted_base + tax

    @api.depends('total', 'amount_paid')
    def _compute_balance(self):
        for rec in self:
            rec.balance_due = rec.total - (rec.amount_paid or 0)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('clinic.billing') or 'New'
        return super().create(vals)

    def action_confirm(self):
        self.state = 'confirmed'

    def action_pay(self):
        self.write({'state': 'paid', 'amount_paid': self.total})

    def action_cancel(self):
        self.state = 'cancelled'

    def _get_or_create_invoice_partner(self):
        """Resolve the res.partner to invoice against.

        Always prefer the patient's own linked partner_id (created/maintained
        by clinic.patient) instead of matching on the patient's display name,
        which silently merges different patients that happen to share a name.
        """
        self.ensure_one()
        patient = self.patient_id
        if patient.partner_id:
            return patient.partner_id
        # Patient has no linked contact yet (e.g. created without an email) —
        # create one now and link it back so future bills reuse it.
        partner = self.env['res.partner'].create({
            'name': patient.name,
            'email': patient.email,
            'phone': patient.phone,
        })
        patient.partner_id = partner.id
        return partner

    def action_create_invoice(self):
        self.ensure_one()
        partner = self._get_or_create_invoice_partner()
        lines = [(0, 0, {
            'name': line.service_name,
            'quantity': line.quantity,
            'price_unit': line.unit_price,
            'tax_ids': [(6, 0, self.tax_ids.ids)],
        }) for line in self.line_ids]
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'company_id': self.company_id.id,
            'invoice_line_ids': lines,
        })
        self.invoice_id = invoice.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }


class ClinicBillingLine(models.Model):
    _name = 'clinic.billing.line'
    _description = 'Billing Line Item'

    billing_id = fields.Many2one('clinic.billing', string='Billing', ondelete='cascade')
    service_name = fields.Char(string='Service / Item', required=True)
    service_type = fields.Selection([
        ('consultation', 'Consultation'),
        ('lab', 'Laboratory'),
        ('pharmacy', 'Pharmacy'),
        ('procedure', 'Procedure'),
        ('radiology', 'Radiology'),
        ('other', 'Other'),
    ], string='Type', default='consultation')
    quantity = fields.Float(string='Qty', default=1.0)
    unit_price = fields.Float(string='Unit Price')
    discount_pct = fields.Float(string='Discount (%)')
    total_price = fields.Float(string='Total', compute='_compute_total', store=True)

    @api.depends('quantity', 'unit_price', 'discount_pct')
    def _compute_total(self):
        for rec in self:
            subtotal = rec.quantity * rec.unit_price
            rec.total_price = subtotal * (1 - (rec.discount_pct or 0) / 100)
