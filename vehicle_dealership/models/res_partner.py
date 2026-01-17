from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    vehicle_sale_ids = fields.One2many('vehicle.sale', 'customer_id',
                                       string='Vehicle Purchases')
    vehicle_sale_count = fields.Integer(string='Vehicle Purchases',
                                        compute='_compute_vehicle_counts')
    vehicle_purchase_count = fields.Integer(string='Vehicles Supplied',
                                            compute='_compute_vehicle_counts')

    @api.depends('vehicle_sale_ids')
    def _compute_vehicle_counts(self):
        for partner in self:
            partner.vehicle_sale_count = len(partner.vehicle_sale_ids)
            partner.vehicle_purchase_count = self.env['vehicle.purchase'].search_count([
                ('supplier_id', '=', partner.id)
            ])