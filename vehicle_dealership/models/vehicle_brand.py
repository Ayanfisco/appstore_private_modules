from odoo import models, fields, api

class VehicleBrand(models.Model):
    _name = 'vehicle.brand'
    _description = 'Vehicle Brand'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Brand Name', required=True, tracking=True)
    code = fields.Char(string='Code', tracking=True)
    country_id = fields.Many2one('res.country', string='Country of Origin', tracking=True)
    logo = fields.Binary(string='Logo')
    active = fields.Boolean(default=True, tracking=True)
    description = fields.Text(string='Description')
    model_ids = fields.One2many('vehicle.model', 'brand_id', string='Models')
    model_count = fields.Integer(string='Model Count', compute='_compute_model_count')
    vehicle_count = fields.Integer(string='Vehicle Count', compute='_compute_vehicle_count')

    @api.depends('model_ids')
    def _compute_model_count(self):
        for record in self:
            record.model_count = len(record.model_ids)

    def _compute_vehicle_count(self):
        for record in self:
            record.vehicle_count = self.env['vehicle.vehicle'].search_count([
                ('model_id.brand_id', '=', record.id)
            ])

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Brand name must be unique!')
    ]