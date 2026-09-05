from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


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
    season_price_ids = fields.One2many('hotel.room.type.season', 'room_type_id', string='Seasonal Rates')

    active = fields.Boolean(string='Active', default=True)

    @api.depends('max_adults', 'max_children')
    def _compute_max_capacity(self):
        for rec in self:
            rec.max_capacity = rec.max_adults + rec.max_children

    @api.depends('room_ids')
    def _compute_room_count(self):
        for rec in self:
            rec.room_count = len(rec.room_ids)

    def get_price_for_date(self, date):
        """Return the nightly rate for a single date, applying a matching seasonal
        rate if one is configured, otherwise falling back to the base list price."""
        self.ensure_one()
        season = self.season_price_ids.filtered(
            lambda s: s.date_from <= date <= s.date_to)
        return season[0].price if season else self.list_price

    def get_total_price(self, check_in, check_out):
        """Return (total_price, avg_nightly_rate) for a stay, pricing each night
        individually so seasonal rates that only cover part of the stay are
        respected. Falls back to the flat list price when there are no seasonal
        rates or the dates are invalid."""
        self.ensure_one()
        if not check_in or not check_out or check_out <= check_in:
            return 0.0, self.list_price
        nights = (check_out - check_in).days
        total = 0.0
        current = check_in
        for _i in range(nights):
            total += self.get_price_for_date(current)
            current += timedelta(days=1)
        avg_rate = total / nights if nights else self.list_price
        return total, avg_rate


class HotelRoomTypeSeason(models.Model):
    _name = 'hotel.room.type.season'
    _description = 'Hotel Room Type Seasonal Rate'
    _order = 'date_from'

    room_type_id = fields.Many2one('hotel.room.type', string='Room Type', required=True, ondelete='cascade')
    name = fields.Char(string='Season Name', required=True)
    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To', required=True)
    price = fields.Float(string='Price per Night', required=True)

    _sql_constraints = [
        ('check_season_dates', 'CHECK(date_to >= date_from)', 'End date must be on or after the start date!'),
    ]

    @api.constrains('date_from', 'date_to', 'room_type_id')
    def _check_overlap(self):
        for rec in self:
            overlapping = self.search([
                ('room_type_id', '=', rec.room_type_id.id),
                ('id', '!=', rec.id),
                ('date_from', '<=', rec.date_to),
                ('date_to', '>=', rec.date_from),
            ])
            if overlapping:
                raise ValidationError(
                    _('Seasonal rate periods cannot overlap for the same room type! '
                      '"%s" overlaps with "%s".') % (rec.name, overlapping[0].name))


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