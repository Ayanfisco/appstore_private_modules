from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HotelRoomType(models.Model):
    _name = 'hotel.room.type'
    _description = 'Hotel Room Type'
    _order = 'sequence, name'

    name = fields.Char(string='Room Type', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    property_id = fields.Many2one('hotel.property', string='Property', required=True)

    # Capacity
    max_adults = fields.Integer(string='Max Adults', default=2)
    max_children = fields.Integer(string='Max Children', default=1)
    max_capacity = fields.Integer(string='Max Total Capacity', compute='_compute_max_capacity', store=True)

    # Pricing
    list_price = fields.Float(string='Base Price per Night', required=True)
    extra_bed_price = fields.Float(string='Extra Bed Price')

    # Room Details
    size = fields.Float(string='Size (sqm)')
    amenity_ids = fields.Many2many('hotel.amenity', string='Amenities')
    description = fields.Text(string='Description')

    # Accounting Integration
    product_id = fields.Many2one(
        'product.product', string='Room Product',
        help='Odoo product used on invoices. Its income account and taxes will be applied to room charge lines.',
        domain=[('type', 'in', ['service', 'consu'])])
    tax_ids = fields.Many2many(
        'account.tax', string='Customer Taxes',
        help='Taxes applied to room charges on invoices. Overrides the product taxes if set.')
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account',
        help='Analytic account for room revenue. Used in Odoo Analytic Reports.')

    # Relations
    room_ids = fields.One2many('hotel.room', 'room_type_id', string='Rooms')
    room_count = fields.Integer(string='Number of Rooms', compute='_compute_room_count', store=True)

    active = fields.Boolean(string='Active', default=True)

    @api.depends('max_adults', 'max_children')
    def _compute_max_capacity(self):
        for rec in self:
            rec.max_capacity = rec.max_adults + rec.max_children

    @api.depends('room_ids')
    def _compute_room_count(self):
        for rec in self:
            rec.room_count = len(rec.room_ids)


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Hotel Room'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'property_id, room_number'

    name = fields.Char(string='Room Name', compute='_compute_name', store=True)
    room_number = fields.Char(string='Room Number', required=True, tracking=True)
    property_id = fields.Many2one('hotel.property', string='Property', required=True, tracking=True)
    room_type_id = fields.Many2one('hotel.room.type', string='Room Type', required=True, tracking=True)

    floor = fields.Integer(string='Floor')

    # Status
    state = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Under Maintenance'),
        ('reserved', 'Reserved'),
        ('cleaning', 'Being Cleaned'),
    ], string='Status', default='available', required=True, tracking=True)

    # Housekeeping
    housekeeping_status = fields.Selection([
        ('clean', 'Clean'),
        ('dirty', 'Dirty'),
        ('inspected', 'Inspected'),
    ], string='Housekeeping Status', default='clean', tracking=True)

    # Relations
    reservation_ids = fields.One2many('hotel.reservation', 'room_id', string='Reservations')
    current_reservation_id = fields.Many2one('hotel.reservation', string='Current Reservation',
                                             compute='_compute_current_reservation')

    # Pricing from type
    list_price = fields.Float(related='room_type_id.list_price', string='Price per Night', readonly=True)

    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('room_number_property_unique', 'unique(room_number, property_id)',
         'Room number must be unique per property!')
    ]

    @api.depends('room_number', 'property_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.property_id.name} - Room {rec.room_number}" if rec.property_id and rec.room_number else 'New Room'

    def _compute_current_reservation(self):
        today = fields.Date.today()
        for rec in self:
            reservation = self.env['hotel.reservation'].search([
                ('room_id', '=', rec.id),
                ('state', 'in', ['confirmed', 'checked_in']),
                ('check_in', '<=', today),
                ('check_out', '>=', today)
            ], limit=1)
            rec.current_reservation_id = reservation

    def action_set_available(self):
        self.write({'state': 'available', 'housekeeping_status': 'clean'})

    def action_set_maintenance(self):
        self.write({'state': 'maintenance'})

    def action_set_cleaning(self):
        self.write({'state': 'cleaning', 'housekeeping_status': 'dirty'})


class HotelAmenity(models.Model):
    _name = 'hotel.amenity'
    _description = 'Hotel Amenity'
    _order = 'name'

    name = fields.Char(string='Amenity Name', required=True, translate=True)
    icon = fields.Char(string='Icon Class')
    active = fields.Boolean(string='Active', default=True)