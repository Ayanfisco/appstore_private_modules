from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VehicleService(models.Model):
    _name = 'vehicle.service'
    _description = 'Vehicle Service Record'
    _order = 'service_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Service Reference', required=True, copy=False,
                       readonly=True, default='New', tracking=True)
    vehicle_id = fields.Many2one('vehicle.vehicle', string='Vehicle',
                                 required=True, tracking=True)
    service_date = fields.Date(string='Service Date', default=fields.Date.today,
                               required=True, tracking=True)
    next_service_date = fields.Date(string='Next Service Date', tracking=True)

    service_type = fields.Selection([
        ('routine', 'Routine Maintenance'),
        ('repair', 'Repair'),
        ('inspection', 'Inspection'),
        ('warranty', 'Warranty Work'),
        ('recall', 'Recall'),
        ('upgrade', 'Upgrade'),
    ], string='Service Type', required=True, default='routine', tracking=True)

    technician_id = fields.Many2one('res.users', string='Technician', tracking=True)
    workshop = fields.Char(string='Workshop/Service Center', tracking=True)

    # Service Details
    current_mileage = fields.Float(string='Current Mileage', tracking=True)
    description = fields.Text(string='Service Description', required=True)
    parts_replaced = fields.Text(string='Parts Replaced')

    # Costs
    labor_cost = fields.Monetary(string='Labor Cost', tracking=True)
    parts_cost = fields.Monetary(string='Parts Cost', tracking=True)
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_total_cost',
                                 store=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    color = fields.Char(string='Color', tracking=True)

    # State
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled', required=True, tracking=True)

    warranty_covered = fields.Boolean(string='Warranty Covered', tracking=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('vehicle.service') or 'New'
        return super().create(vals_list)

    @api.depends('labor_cost', 'parts_cost')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = record.labor_cost + record.parts_cost

    def action_start(self):
        self.write({'state': 'in_progress'})
        self.vehicle_id.write({'state': 'in_service'})

    def action_complete(self):
        self.write({'state': 'completed'})
        if self.vehicle_id.state == 'in_service':
            self.vehicle_id.write({'state': 'available'})
        if self.current_mileage:
            self.vehicle_id.write({'mileage': self.current_mileage})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        if self.vehicle_id.state == 'in_service':
            self.vehicle_id.write({'state': 'available'})