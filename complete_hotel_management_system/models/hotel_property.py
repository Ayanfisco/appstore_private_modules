from odoo import models, fields, api


class HotelProperty(models.Model):
    _name = 'hotel.property'
    _description = 'Hotel Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Property Name', required=True, tracking=True)
    code = fields.Char(string='Property Code', copy=False, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    # Address Information
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='ZIP')
    country_id = fields.Many2one('res.country', string='Country')

    # Contact Information
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')

    # Property Details
    star_rating = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars'),
    ], string='Star Rating', tracking=True)

    check_in_time = fields.Float(string='Check-in Time', default=14.0)
    check_out_time = fields.Float(string='Check-out Time', default=12.0)

    # Relations
    room_ids = fields.One2many('hotel.room', 'property_id', string='Rooms')
    room_type_ids = fields.One2many('hotel.room.type', 'property_id', string='Room Types')

    # Statistics
    room_count = fields.Integer(string='Total Rooms', compute='_compute_room_count', store=True)
    available_room_count = fields.Integer(string='Available Rooms', compute='_compute_available_rooms')

    active = fields.Boolean(string='Active', default=True)

    @api.depends('room_ids')
    def _compute_room_count(self):
        for rec in self:
            rec.room_count = len(rec.room_ids)

    def _compute_available_rooms(self):
        for rec in self:
            available = self.env['hotel.room'].search_count([
                ('property_id', '=', rec.id),
                ('state', '=', 'available')
            ])
            rec.available_room_count = available

    @api.model
    def create(self, vals):
        if not vals.get('code'):
            vals['code'] = self.env['ir.sequence'].next_by_code('hotel.property') or 'PROP'
        return super().create(vals)

    def action_view_rooms(self):
        return {
            'name': 'Rooms',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.room',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id}
        }