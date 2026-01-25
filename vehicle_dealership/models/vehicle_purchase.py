from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VehiclePurchase(models.Model):
    _name = 'vehicle.purchase'
    _description = 'Vehicle Purchase'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Purchase Reference', required=True, copy=False,
                       readonly=True, default='New', tracking=True)
    supplier_id = fields.Many2one('res.partner', string='Supplier',
                                  required=True, tracking=True,
                                  domain=[('supplier_rank', '>', 0)])
    purchase_date = fields.Date(string='Purchase Date', default=fields.Date.today,
                                required=True, tracking=True)
    expected_arrival = fields.Date(string='Expected Arrival', tracking=True)
    actual_arrival = fields.Date(string='Actual Arrival', tracking=True)

    # Vehicle Details (before creating vehicle record)
    brand_id = fields.Many2one('vehicle.brand', string='Brand', required=True, tracking=True)
    model_id = fields.Many2one('vehicle.model', string='Model', required=True, tracking=True,
                               domain="[('brand_id', '=', brand_id)]")
    year = fields.Integer(string='Year', required=True, tracking=True)
    vin = fields.Char(string='VIN Number', size=17, tracking=True)
    color = fields.Char(string='Color', tracking=True)
    mileage = fields.Float(string='Mileage (km)', tracking=True)

    # Pricing
    purchase_price = fields.Monetary(string='Purchase Price', required=True, tracking=True)
    shipping_cost = fields.Monetary(string='Shipping Cost', tracking=True)
    import_duty = fields.Monetary(string='Import Duty/Tax', tracking=True)
    other_costs = fields.Monetary(string='Other Costs', tracking=True)
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_total_cost',
                                 store=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ordered', 'Ordered'),
        ('in_transit', 'In Transit'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    # Relations
    vehicle_id = fields.Many2one('vehicle.vehicle', string='Vehicle Record',
                                 readonly=True, tracking=True)
    bill_id = fields.Many2one('account.move', string='Vendor Bill', readonly=True)

    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vehicle.purchase') or 'New'
        return super().create(vals_list)

    @api.depends('purchase_price', 'shipping_cost', 'import_duty', 'other_costs')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = (record.purchase_price + record.shipping_cost +
                                 record.import_duty + record.other_costs)

    def action_order(self):
        self.write({'state': 'ordered'})

    def action_in_transit(self):
        self.write({'state': 'in_transit'})

    def action_receive(self):
        # Create vehicle record when received
        vehicle = self.env['vehicle.vehicle'].create({
            'brand_id': self.brand_id.id,
            'model_id': self.model_id.id,
            'year': self.year,
            'vin': self.vin,
            'color_exterior': self.color,
            'mileage': self.mileage,
            'purchase_price': self.total_cost,
            'purchase_date': self.purchase_date,
            'arrival_date': fields.Date.today(),
            'supplier_id': self.supplier_id.id,
            'condition': 'used' if self.mileage > 0 else 'new',
            'state': 'available',
            'purchase_id': self.id,
        })
        self.write({
            'state': 'received',
            'vehicle_id': vehicle.id,
            'actual_arrival': fields.Date.today()
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})