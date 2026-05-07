# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ─── Role flags ───────────────────────────────────────────────────────────
    is_customer = fields.Boolean(
        string='Customer',
        default=False,
        help='This contact is a customer (appears in Sales contacts)',
    )
    is_vendor = fields.Boolean(
        string='Vendor',
        default=False,
        help='This contact is a vendor / supplier (appears in Purchase contacts)',
    )
    is_employee_contact = fields.Boolean(
        string='Employee',
        default=False,
        help='This contact belongs to an employee',
    )
    is_partner_contact = fields.Boolean(
        string='Business Partner',
        default=False,
        help='This contact is a generic business partner',
    )

    # ─── Derived display label ────────────────────────────────────────────────
    contact_role_label = fields.Char(
        string='Role(s)',
        compute='_compute_contact_role_label',
        store=True,
    )

    @api.depends('is_customer', 'is_vendor', 'is_employee_contact', 'is_partner_contact')
    def _compute_contact_role_label(self):
        for rec in self:
            roles = []
            if rec.is_customer:
                roles.append('Customer')
            if rec.is_vendor:
                roles.append('Vendor')
            if rec.is_employee_contact:
                roles.append('Employee')
            if rec.is_partner_contact:
                roles.append('Partner')
            rec.contact_role_label = ' · '.join(roles) if roles else 'Contact'

    # ─── onchange: instant UI feedback only ───────────────────────────────────
    @api.onchange('is_customer')
    def _onchange_is_customer(self):
        self.customer_rank = 1 if self.is_customer else 0

    @api.onchange('is_vendor')
    def _onchange_is_vendor(self):
        self.supplier_rank = 1 if self.is_vendor else 0

    # ─── write(): persist rank sync whenever role flags are saved ─────────────
    def write(self, vals):
        if 'is_customer' in vals:
            vals['customer_rank'] = 1 if vals['is_customer'] else 0
        if 'is_vendor' in vals:
            vals['supplier_rank'] = 1 if vals['is_vendor'] else 0
        return super().write(vals)

    # ─── create(): set ranks correctly from context or explicit flags ─────────
    @api.model_create_multi
    def create(self, vals_list):
        ctx = self.env.context
        for vals in vals_list:
            if ctx.get('default_is_customer'):
                vals.setdefault('is_customer', True)
            if ctx.get('default_is_vendor'):
                vals.setdefault('is_vendor', True)
            if ctx.get('default_is_employee_contact'):
                vals.setdefault('is_employee_contact', True)
            if ctx.get('default_is_partner_contact'):
                vals.setdefault('is_partner_contact', True)

            # Sync ranks — zero them out unless flag is explicitly set
            vals['customer_rank'] = 1 if vals.get('is_customer') else 0
            vals['supplier_rank'] = 1 if vals.get('is_vendor') else 0

        return super().create(vals_list)
