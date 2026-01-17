from odoo import models, fields, api


class Vehicle(models.Model):
    _name = 'vehicle.vehicle'
    _description = 'Vehicle'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False,
                       readonly=True, default='New', tracking=True)
    brand_id = fields.Many2one('vehicle.brand', string='Brand',
                               required=True, tracking=True)
    model_id = fields.Many2one('vehicle.model', string='Model',
                               required=True, tracking=True,
                               domain="[('brand_id', '=', brand_id)]")
    year = fields.Integer(string='Year', required=True, tracking=True)
    vin = fields.Char(string='VIN Number', size=17, tracking=True)
    license_plate = fields.Char(string='License Plate', tracking=True)
    color_exterior = fields.Char(string='Exterior Color', tracking=True)
    color_interior = fields.Char(string='Interior Color', tracking=True)
    mileage = fields.Float(string='Mileage (km)', tracking=True)
    condition = fields.Selection([
        ('new', 'New'),
        ('used', 'Used'),
        ('certified', 'Certified Pre-Owned'),
    ], string='Condition', required=True, default='new', tracking=True)

    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('in_service', 'In Service'),
        ('unavailable', 'Unavailable'),
    ], string='Status', default='available', required=True, tracking=True)

    purchase_price = fields.Monetary(string='Purchase Price', tracking=True)
    selling_price = fields.Monetary(string='Selling Price', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Technical Specifications
    engine_number = fields.Char(string='Engine Number', tracking=True)
    fuel_type = fields.Selection(related='model_id.fuel_type', store=True)
    transmission = fields.Selection(related='model_id.transmission', store=True)
    body_type = fields.Selection(related='model_id.body_type', store=True)
    doors = fields.Integer(string='Number of Doors', default=4)

    # Dates
    purchase_date = fields.Date(string='Purchase Date', tracking=True)
    arrival_date = fields.Date(string='Arrival Date', tracking=True)
    registration_date = fields.Date(string='Registration Date', tracking=True)

    # Relations
    supplier_id = fields.Many2one('res.partner', string='Supplier',
                                  domain=[('supplier_rank', '>', 0)], tracking=True)
    location_id = fields.Many2one('stock.location', string='Location',
                                  domain=[('usage', '=', 'internal')])

    # Images and Documents
    image_1920 = fields.Binary(string='Main Image', max_width=1920, max_height=1920)
    image_128 = fields.Binary(string='Small Image', related='image_1920',
                              max_width=128, max_height=128, store=True)
    image_ids = fields.Many2many('ir.attachment', string='Additional Images')

    # Features
    features = fields.Text(string='Features')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True, tracking=True)

    # Related Records
    sale_id = fields.Many2one('vehicle.sale', string='Sale Order', readonly=True)
    purchase_id = fields.Many2one('vehicle.purchase', string='Purchase Order', readonly=True)
    service_ids = fields.One2many('vehicle.service', 'vehicle_id', string='Service Records')
    inspection_ids = fields.One2many('vehicle.inspection', 'vehicle_id', string='Inspections')

    # Computed fields
    service_count = fields.Integer(compute='_compute_service_count')
    inspection_count = fields.Integer(compute='_compute_inspection_count')
    days_in_inventory = fields.Integer(
        compute='_compute_days_in_inventory',
        store=True,
        string='Days in Inventory'
    )

    profit_margin = fields.Monetary(
        compute='_compute_profit_margin',
        store=True,
        string='Expected Profit'
    )
    vehicle_brand_id = fields.Many2one(related='model_id.brand_id',
                                       string='Vehicle Brand',
                                       store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vehicle.vehicle') or 'New'
        return super().create(vals_list)

    @api.depends('service_ids')
    def _compute_service_count(self):
        for record in self:
            record.service_count = len(record.service_ids)

    @api.depends('inspection_ids')
    def _compute_inspection_count(self):
        for record in self:
            record.inspection_count = len(record.inspection_ids)

    @api.depends('arrival_date')
    def _compute_days_in_inventory(self):
        today = fields.Date.today()
        for record in self:
            if record.arrival_date and record.state == 'available':
                delta = today - record.arrival_date
                record.days_in_inventory = delta.days
            else:
                record.days_in_inventory = 0

    @api.depends('selling_price', 'purchase_price')
    def _compute_profit_margin(self):
        for record in self:
            record.profit_margin = record.selling_price - record.purchase_price

    def action_reserve(self):
        self.write({'state': 'reserved'})

    def action_make_available(self):
        self.write({'state': 'available'})

    def action_mark_sold(self):
        self.write({'state': 'sold'})

    def action_view_services(self):
        return {
            'name': 'Service Records',
            'type': 'ir.actions.act_window',
            'res_model': 'vehicle.service',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id}
        }

    def action_view_inspections(self):
        return {
            'name': 'Inspections',
            'type': 'ir.actions.act_window',
            'res_model': 'vehicle.inspection',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id}
        }

    _sql_constraints = [
        ('vin_unique', 'unique(vin)', 'VIN Number must be unique!')
    ]
