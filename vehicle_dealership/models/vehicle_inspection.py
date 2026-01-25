from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VehicleInspection(models.Model):
    _name = 'vehicle.inspection'
    _description = 'Vehicle Inspection'
    _order = 'inspection_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Inspection Reference', required=True, copy=False,
                       readonly=True, default='New', tracking=True)
    vehicle_id = fields.Many2one('vehicle.vehicle', string='Vehicle',
                                 required=True, tracking=True)
    inspection_date = fields.Date(string='Inspection Date', default=fields.Date.today,
                                  required=True, tracking=True)
    inspector_id = fields.Many2one('res.users', string='Inspector',
                                   default=lambda self: self.env.user, tracking=True)

    inspection_type = fields.Selection([
        ('pre_purchase', 'Pre-Purchase'),
        ('pre_sale', 'Pre-Sale'),
        ('routine', 'Routine'),
        ('accident', 'Accident Assessment'),
        ('insurance', 'Insurance'),
    ], string='Type', required=True, default='pre_sale', tracking=True)

    # Inspection Items
    exterior_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], string='Exterior Condition', tracking=True)

    interior_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], string='Interior Condition', tracking=True)

    engine_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], string='Engine Condition', tracking=True)

    transmission_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], string='Transmission Condition', tracking=True)

    tire_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], string='Tire Condition', tracking=True)

    brake_condition = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ], string='Brake Condition', tracking=True)

    # Overall Assessment
    overall_rating = fields.Integer(string='Overall Rating (1-10)', tracking=True)
    passed = fields.Boolean(string='Passed Inspection', tracking=True)
    issues_found = fields.Text(string='Issues Found')
    recommendations = fields.Text(string='Recommendations')
    estimated_repair_cost = fields.Monetary(string='Estimated Repair Cost')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Attachments
    report_file = fields.Binary(string='Inspection Report')
    report_filename = fields.Char(string='Filename')
    photo_ids = fields.Many2many('ir.attachment', string='Photos')

    notes = fields.Text(string='Additional Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vehicle.inspection') or 'New'
        return super().create(vals_list)