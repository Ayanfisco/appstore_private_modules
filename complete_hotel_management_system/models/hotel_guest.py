from odoo import models, fields, api, _


class HotelGuest(models.Model):
    _name = 'hotel.guest'
    _description = 'Hotel Guest'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Guest Name', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Related Partner', ondelete='restrict')

    # Personal Information
    title = fields.Selection([
        ('mr', 'Mr.'),
        ('mrs', 'Mrs.'),
        ('miss', 'Miss'),
        ('dr', 'Dr.'),
    ], string='Title')

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')

    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age')
    nationality_id = fields.Many2one('res.country', string='Nationality')

    # Contact Information
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile', tracking=True)

    # Address
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='ZIP')
    country_id = fields.Many2one('res.country', string='Country')

    # Identification
    id_type = fields.Selection([
        ('passport', 'Passport'),
        ('national_id', 'National ID'),
        ('driving_license', 'Driving License'),
        ('other', 'Other'),
    ], string='ID Type')
    id_number = fields.Char(string='ID Number', tracking=True)
    id_expiry = fields.Date(string='ID Expiry Date')

    # Guest Preferences
    special_requests = fields.Text(string='Special Requests')
    vip = fields.Boolean(string='VIP Guest', tracking=True)
    blacklisted = fields.Boolean(string='Blacklisted', tracking=True)
    blacklist_reason = fields.Text(string='Blacklist Reason')

    # Relations
    reservation_ids = fields.One2many('hotel.reservation', 'guest_id', string='Reservations')
    reservation_count = fields.Integer(string='Total Reservations', compute='_compute_reservation_count')

    # Statistics
    total_nights = fields.Integer(string='Total Nights Stayed', compute='_compute_statistics')
    total_spent = fields.Monetary(string='Total Amount Spent', compute='_compute_statistics',
                                  currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Internal Notes')

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_of_birth:
                rec.age = today.year - rec.date_of_birth.year - (
                        (today.month, today.day) < (rec.date_of_birth.month, rec.date_of_birth.day)
                )
            else:
                rec.age = 0

    @api.depends('reservation_ids')
    def _compute_reservation_count(self):
        for rec in self:
            rec.reservation_count = len(rec.reservation_ids)

    def _compute_statistics(self):
        for rec in self:
            confirmed_reservations = rec.reservation_ids.filtered(
                lambda r: r.state in ['confirmed', 'checked_in', 'checked_out', 'done'])
            rec.total_nights = sum(confirmed_reservations.mapped('nights'))
            rec.total_spent = sum(confirmed_reservations.mapped('total_amount'))

    @api.model
    def create(self, vals):
        guest = super().create(vals)
        # Create partner if email is provided
        if guest.email and not guest.partner_id:
            partner = self.env['res.partner'].create({
                'name': guest.name,
                'email': guest.email,
                'phone': guest.phone or guest.mobile,
                'street': guest.street,
                'city': guest.city,
                'zip': guest.zip,
                'country_id': guest.country_id.id,
            })
            guest.partner_id = partner.id
        return guest

    def action_view_reservations(self):
        return {
            'name': 'Guest Reservations',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.reservation',
            'view_mode': 'list,form',
            'domain': [('guest_id', '=', self.id)],
            'context': {'default_guest_id': self.id}
        }
