from odoo import models, fields, api

class VehicleModel(models.Model):
    _name = 'vehicle.model'
    _description = 'Vehicle Model'
    _order = 'brand_id, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Model Name', required=True, tracking=True)
    brand_id = fields.Many2one('vehicle.brand', string='Brand', required=True, tracking=True)
    year = fields.Integer(string='Year', tracking=True)
    body_type = fields.Selection([
        ('sedan', 'Sedan'),
        ('suv', 'SUV'),
        ('truck', 'Truck'),
        ('coupe', 'Coupe'),
        ('convertible', 'Convertible'),
        ('hatchback', 'Hatchback'),
        ('wagon', 'Wagon'),
        ('van', 'Van'),
        ('minivan', 'Minivan'),
    ], string='Body Type', tracking=True)
    fuel_type = fields.Selection([
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
        ('plugin_hybrid', 'Plug-in Hybrid'),
    ], string='Fuel Type', tracking=True)
    transmission = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('cvt', 'CVT'),
        ('semi_automatic', 'Semi-Automatic'),
    ], string='Transmission', tracking=True)
    engine_capacity = fields.Float(string='Engine Capacity (L)', tracking=True)
    horsepower = fields.Integer(string='Horsepower', tracking=True)
    seating_capacity = fields.Integer(string='Seating Capacity', default=5)
    image = fields.Binary(string='Image')
    active = fields.Boolean(default=True, tracking=True)
    description = fields.Text(string='Description')
    vehicle_count = fields.Integer(string='Vehicle Count', compute='_compute_vehicle_count')

    def _compute_vehicle_count(self):
        for record in self:
            record.vehicle_count = self.env['vehicle.vehicle'].search_count([
                ('model_id', '=', record.id)
            ])

    _sql_constraints = [
        ('name_brand_year_unique', 'unique(name, brand_id, year)',
         'Model name, brand and year combination must be unique!')
    ]