# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class ClinicPharmacyDispensing(models.Model):
    _name = 'clinic.pharmacy.dispensing'
    _description = 'Pharmacy Dispensing Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'dispense_date desc'

    name = fields.Char(string='Dispensing Ref', readonly=True, copy=False, default='New')
    patient_id = fields.Many2one('clinic.patient', string='Patient', required=True, index=True)
    prescription_id = fields.Many2one('clinic.prescription', string='Prescription', tracking=True)
    pharmacist_id = fields.Many2one('res.users', string='Pharmacist', default=lambda self: self.env.user)
    dispense_date = fields.Datetime(string='Dispensed On', required=True, default=fields.Datetime.now)

    state = fields.Selection([
        ('pending', 'Pending'),
        ('dispensed', 'Dispensed'),
        ('partial', 'Partially Dispensed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', tracking=True)

    line_ids = fields.One2many('clinic.pharmacy.dispensing.line', 'dispensing_id', string='Medications')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total', store=True)
    notes = fields.Text(string='Pharmacist Notes')
    stock_move_ids = fields.One2many('stock.move', 'clinic_dispensing_id', string='Stock Moves')
    stock_move_count = fields.Integer(string='Stock Move Count', compute='_compute_stock_move_count')

    @api.depends('stock_move_ids')
    def _compute_stock_move_count(self):
        for rec in self:
            rec.stock_move_count = len(rec.stock_move_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('clinic.pharmacy') or 'New'
        return super().create(vals)

    @api.depends('line_ids.total_price')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('total_price'))

    def _get_dispensing_locations(self):
        """Source = main stock location, destination = a virtual customer
        location so dispensed medication leaves stock the same way a
        regular delivery would."""
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1
        )
        src_location = warehouse.lot_stock_id if warehouse else self.env.ref('stock.stock_location_stock')
        dest_location = self.env.ref('stock.stock_location_customers')
        return src_location, dest_location

    def action_dispense(self):
        for rec in self:
            stock_lines = rec.line_ids.filtered('product_id')

            # Validate stock availability up front (kept from the original
            # behaviour) before committing to any stock movement.
            for line in stock_lines:
                stock_qty = line.product_id.with_context(
                    location=rec._get_dispensing_locations()[0].id
                ).qty_available
                if stock_qty < line.quantity:
                    raise UserError(
                        f"Insufficient stock for {line.product_id.name}. "
                        f"Available: {stock_qty}, Required: {line.quantity}"
                    )

            moves = rec.env['stock.move']
            if stock_lines:
                src_location, dest_location = rec._get_dispensing_locations()
                for line in stock_lines:
                    move = rec.env['stock.move'].create({
                        'name': f"Dispensing {rec.name or ''} - {line.product_id.display_name}",
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity,
                        'product_uom': line.product_id.uom_id.id,
                        'location_id': src_location.id,
                        'location_dest_id': dest_location.id,
                        'clinic_dispensing_id': rec.id,
                        'origin': rec.name,
                    })
                    moves |= move

                moves._action_confirm()
                moves._action_assign()
                for move in moves:
                    for move_line in move.move_line_ids:
                        move_line.quantity = move.product_uom_qty
                moves.picked = True
                moves._action_done()

            rec.state = 'dispensed'
            if rec.prescription_id:
                rec.prescription_id.action_dispense()

    def action_cancel(self):
        for rec in self:
            rec.stock_move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._action_cancel()
            rec.state = 'cancelled'

    def action_view_stock_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Moves',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('clinic_dispensing_id', '=', self.id)],
        }


class ClinicPharmacyDispensingLine(models.Model):
    _name = 'clinic.pharmacy.dispensing.line'
    _description = 'Dispensing Line'

    dispensing_id = fields.Many2one('clinic.pharmacy.dispensing', string='Dispensing', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Medication (Product)',
                                  domain=[('type', 'in', ['consu', 'product'])])
    medication_name = fields.Char(string='Medication Name', required=True)
    dosage = fields.Char(string='Dosage')
    quantity = fields.Float(string='Qty Dispensed', default=1.0)
    unit_price = fields.Float(string='Unit Price', related='product_id.lst_price', readonly=False)
    total_price = fields.Float(string='Total', compute='_compute_total', store=True)
    instructions = fields.Text(string='Dispensing Instructions')

    @api.depends('quantity', 'unit_price')
    def _compute_total(self):
        for rec in self:
            rec.total_price = rec.quantity * rec.unit_price

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.medication_name = self.product_id.name


class StockMove(models.Model):
    _inherit = 'stock.move'

    clinic_dispensing_id = fields.Many2one(
        'clinic.pharmacy.dispensing', string='Pharmacy Dispensing', index=True
    )
