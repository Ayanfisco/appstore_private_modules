from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


class HotelReservation(models.Model):
    _name = 'hotel.reservation'
    _description = 'Hotel Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'check_in desc, id desc'

    name = fields.Char(string='Reservation Number', required=True, copy=False, readonly=True, default='New')

    # Guest Information
    guest_id = fields.Many2one('hotel.guest', string='Guest', required=True, tracking=True)
    guest_email = fields.Char(related='guest_id.email', string='Guest Email', readonly=True)
    guest_phone = fields.Char(related='guest_id.phone', string='Guest Phone', readonly=True)
    guest_mobile = fields.Char(related='guest_id.mobile', string='Guest Mobile', readonly=True)

    # Property & Room
    property_id = fields.Many2one('hotel.property', string='Property', required=True, tracking=True)
    room_type_id = fields.Many2one('hotel.room.type', string='Room Type', required=True, tracking=True)
    room_id = fields.Many2one('hotel.room', string='Room', tracking=True,
                              domain="[('property_id', '=', property_id), ('room_type_id', '=', room_type_id)]")

    # Booking Details
    check_in = fields.Date(string='Check-in Date', required=True, tracking=True)
    check_out = fields.Date(string='Check-out Date', required=True, tracking=True)
    nights = fields.Integer(string='Nights', compute='_compute_nights', store=True)

    adults = fields.Integer(string='Adults', default=1, required=True)
    children = fields.Integer(string='Children', default=0)
    total_guests = fields.Integer(string='Total Guests', compute='_compute_total_guests', store=True)

    # Pricing
    room_rate = fields.Float(string='Room Rate per Night', required=True)
    subtotal = fields.Monetary(string='Room Subtotal', compute='_compute_amounts', store=True,
                               currency_field='currency_id')
    service_total = fields.Monetary(string='Services Total', compute='_compute_amounts', store=True,
                                    currency_field='currency_id')
    tax_amount = fields.Monetary(string='Tax Amount', compute='_compute_amounts', store=True,
                                 currency_field='currency_id')
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_amounts', store=True,
                                   currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Services
    service_line_ids = fields.One2many('hotel.service.line', 'reservation_id', string='Services')

    # Payment & Invoicing
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    invoice_status = fields.Selection([
        ('not_invoiced', 'Not Invoiced'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
    ], string='Invoice Status', default='not_invoiced', compute='_compute_invoice_status', store=True)

    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    # Additional Information
    source = fields.Selection([
        ('direct', 'Direct Booking'),
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('walk_in', 'Walk-in'),
        ('online', 'Online Portal'),
        ('ota', 'Online Travel Agency'),
    ], string='Booking Source', default='direct')

    special_requests = fields.Text(string='Special Requests')
    internal_notes = fields.Text(string='Internal Notes')

    # Dates
    booking_date = fields.Datetime(string='Booking Date', default=fields.Datetime.now, readonly=True)
    checkin_datetime = fields.Datetime(string='Actual Check-in', readonly=True)
    checkout_datetime = fields.Datetime(string='Actual Check-out', readonly=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, tracking=True)

    _sql_constraints = [
        ('check_dates', 'CHECK(check_out > check_in)', 'Check-out date must be after check-in date!'),
        ('check_guests', 'CHECK(adults > 0)', 'Number of adults must be at least 1!'),
    ]

    @api.depends('check_in', 'check_out')
    def _compute_nights(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                delta = rec.check_out - rec.check_in
                rec.nights = delta.days
            else:
                rec.nights = 0

    @api.depends('adults', 'children')
    def _compute_total_guests(self):
        for rec in self:
            rec.total_guests = rec.adults + rec.children

    @api.depends('room_rate', 'nights', 'service_line_ids.price_subtotal')
    def _compute_amounts(self):
        for rec in self:
            rec.subtotal = rec.room_rate * rec.nights
            rec.service_total = sum(rec.service_line_ids.mapped('price_subtotal'))
            total_before_tax = rec.subtotal + rec.service_total
            rec.tax_amount = total_before_tax * 0.10  # 10% tax
            rec.total_amount = total_before_tax + rec.tax_amount

    @api.depends('invoice_id', 'invoice_id.payment_state')
    def _compute_invoice_status(self):
        for rec in self:
            if not rec.invoice_id:
                rec.invoice_status = 'not_invoiced'
            elif rec.invoice_id.payment_state == 'paid':
                rec.invoice_status = 'paid'
            else:
                rec.invoice_status = 'invoiced'

    @api.onchange('room_type_id')
    def _onchange_room_type_id(self):
        if self.room_type_id:
            self.room_rate = self.room_type_id.list_price
            self.room_id = False

    @api.onchange('property_id')
    def _onchange_property_id(self):
        self.room_type_id = False
        self.room_id = False

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hotel.reservation') or 'RES'
        return super().create(vals)

    @api.constrains('check_in', 'check_out', 'room_id')
    def _check_room_availability(self):
        for rec in self:
            if rec.room_id and rec.check_in and rec.check_out:
                overlapping = self.search([
                    ('room_id', '=', rec.room_id.id),
                    ('id', '!=', rec.id),
                    ('state', 'in', ['confirmed', 'checked_in']),
                    '|',
                    '&', ('check_in', '<=', rec.check_in), ('check_out', '>', rec.check_in),
                    '&', ('check_in', '<', rec.check_out), ('check_out', '>=', rec.check_out),
                ])
                if overlapping:
                    raise ValidationError(_('Room %s is not available for the selected dates!') % rec.room_id.name)

    def action_confirm(self):
        for rec in self:
            if not rec.room_id:
                available_room = self.env['hotel.room'].search([
                    ('property_id', '=', rec.property_id.id),
                    ('room_type_id', '=', rec.room_type_id.id),
                    ('state', '=', 'available')
                ], limit=1)
                if not available_room:
                    raise UserError(_('No available rooms of type %s!') % rec.room_type_id.name)
                rec.room_id = available_room

            rec.room_id.write({'state': 'reserved'})
            rec.write({'state': 'confirmed'})
            rec.message_post(body=_('Reservation confirmed for room %s') % rec.room_id.name)

    def action_check_in(self):
        self.ensure_one()
        return {
            'name': 'Check-in',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.checkin.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_reservation_id': self.id}
        }

    def action_check_out(self):
        self.ensure_one()
        return {
            'name': 'Check-out',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.checkout.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_reservation_id': self.id}
        }

    def action_create_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            raise UserError(_('Invoice already created for this reservation!'))

        invoice_lines = [(0, 0, {
            'name': _('Room %s (%s nights)') % (self.room_id.name, self.nights),
            'quantity': self.nights,
            'price_unit': self.room_rate,
        })]

        for service_line in self.service_line_ids:
            invoice_lines.append((0, 0, {
                'name': service_line.service_id.name,
                'quantity': service_line.quantity,
                'price_unit': service_line.price_unit,
            }))

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.guest_id.partner_id.id if self.guest_id.partner_id else self.env.ref(
                'base.public_partner').id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
        })

        self.invoice_id = invoice.id
        return {
            'name': 'Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    def action_cancel(self):
        for rec in self:
            if rec.state in ['checked_in', 'done']:
                raise UserError(_('Cannot cancel a reservation that has been checked in!'))
            if rec.room_id and rec.room_id.state == 'reserved':
                rec.room_id.state = 'available'
            rec.state = 'cancelled'

    def action_done(self):
        self.write({'state': 'done'})

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f'/my/reservations/{rec.id}'