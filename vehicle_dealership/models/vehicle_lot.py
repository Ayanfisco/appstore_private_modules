from odoo import models, fields, api


class VehicleLot(models.Model):
    _name = 'vehicle.lot'
    _description = 'Vehicle Lot / Showroom'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Lot/Showroom Name', required=True, tracking=True)
    code = fields.Char(string='Code', tracking=True)
    manager_id = fields.Many2one('res.users', string='Lot Manager', tracking=True)
    address = fields.Char(string='Address', tracking=True)
    city = fields.Char(string='City', tracking=True)
    state_id = fields.Many2one('res.country.state', string='State', tracking=True)
    country_id = fields.Many2one('res.country', string='Country', tracking=True)
    capacity = fields.Integer(string='Capacity', help='Maximum number of vehicles this lot can hold.')
    active = fields.Boolean(default=True, tracking=True)
    notes = fields.Text(string='Notes')

    vehicle_ids = fields.One2many('vehicle.vehicle', 'lot_id', string='Vehicles')
    vehicle_count = fields.Integer(string='Vehicle Count', compute='_compute_vehicle_count')

    @api.depends('vehicle_ids')
    def _compute_vehicle_count(self):
        for record in self:
            record.vehicle_count = len(record.vehicle_ids)

    def action_view_vehicles(self):
        self.ensure_one()
        return {
            'name': 'Vehicles',
            'type': 'ir.actions.act_window',
            'res_model': 'vehicle.vehicle',
            'view_mode': 'list,kanban,form',
            'domain': [('lot_id', '=', self.id)],
            'context': {'default_lot_id': self.id},
        }

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Lot/Showroom name must be unique!')
    ]
