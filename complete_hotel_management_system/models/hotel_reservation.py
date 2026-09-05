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

    # Deposit tracking
    deposit_amount = fields.Monetary(string='Deposit Received', default=0.0, currency_field='currency_id')
    deposit_payment_id = fields.Many2one('account.payment', string='Deposit Payment', readonly=True, copy=False)

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

    # Post-stay guest feedback
    feedback_rating = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Fair'),
        ('3', '3 - Good'),
        ('4', '4 - Very Good'),
        ('5', '5 - Excellent'),
    ], string='Guest Feedback Rating', copy=False)
    feedback_comment = fields.Text(string='Guest Feedback Comment', copy=False)
    feedback_submitted = fields.Boolean(string='Feedback Submitted', default=False, copy=False)

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

    @api.depends('room_rate', 'nights', 'room_type_id.tax_ids', 'room_type_id.product_id.taxes_id',
                 'service_line_ids.price_subtotal', 'service_line_ids.quantity', 'service_line_ids.price_unit',
                 'service_line_ids.service_id.tax_ids', 'service_line_ids.service_id.product_id.taxes_id',
                 'currency_id')
    def _compute_amounts(self):
        for rec in self:
            rec.subtotal = rec.room_rate * rec.nights
            rec.service_total = sum(rec.service_line_ids.mapped('price_subtotal'))

            currency = rec.currency_id or rec.company_id.currency_id
            tax_total = 0.0

            # Room charge tax: room type's own taxes, falling back to its linked product's taxes
            room_taxes = rec.room_type_id.tax_ids or (
                rec.room_type_id.product_id.taxes_id if rec.room_type_id.product_id else self.env['account.tax'])
            if room_taxes and rec.nights:
                res = room_taxes.compute_all(
                    rec.room_rate, currency=currency, quantity=rec.nights,
                    product=rec.room_type_id.product_id)
                tax_total += res['total_included'] - res['total_excluded']

            # Service charge tax, computed per line since services can have different taxes
            for sl in rec.service_line_ids:
                svc = sl.service_id
                svc_taxes = svc.tax_ids or (
                    svc.product_id.taxes_id if svc.product_id else self.env['account.tax'])
                if svc_taxes and sl.quantity:
                    res = svc_taxes.compute_all(
                        sl.price_unit, currency=currency, quantity=sl.quantity, product=svc.product_id)
                    tax_total += res['total_included'] - res['total_excluded']

            rec.tax_amount = tax_total
            rec.total_amount = rec.subtotal + rec.service_total + tax_total

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
            self.room_id = False
            self._update_room_rate()

    @api.onchange('property_id')
    def _onchange_property_id(self):
        self.room_type_id = False
        self.room_id = False

    @api.onchange('check_in', 'check_out')
    def _onchange_dates_pricing(self):
        self._update_room_rate()

    def _update_room_rate(self):
        """Set room_rate to the blended average nightly rate for the current
        stay, applying any seasonal rates that cover part of it. Kept as a
        single editable Float field so staff can still override it manually."""
        if self.room_type_id and self.check_in and self.check_out and self.check_out > self.check_in:
            _total, avg_rate = self.room_type_id.get_total_price(self.check_in, self.check_out)
            self.room_rate = avg_rate
        elif self.room_type_id:
            self.room_rate = self.room_type_id.list_price

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
        template = self.env.ref(
            'complete_hotel_management_system.email_template_reservation_confirmation',
            raise_if_not_found=False)
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

            # Automatically queue the confirmation email (queued, not force-sent,
            # so a missing/unconfigured outgoing mail server never blocks confirmation).
            if template and rec.guest_email:
                template.send_mail(rec.id, force_send=False)

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

        # Determine journal: use property journal if set, else Odoo default
        journal = self.property_id.journal_id or self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.company_id.id)], limit=1)

        invoice_lines = []

        # ── Room charge line ─────────────────────────────────────────────────
        room_type = self.room_type_id
        room_line_vals = {
            'name': _('Room %s — %s (%s nights @ %s)') % (
                self.room_id.name, room_type.name, self.nights, self.room_rate),
            'quantity': self.nights,
            'price_unit': self.room_rate,
        }
        # Link product so Odoo resolves income account automatically
        if room_type.product_id:
            room_line_vals['product_id'] = room_type.product_id.id
        # Taxes: prefer room type taxes, fall back to product taxes
        if room_type.tax_ids:
            room_line_vals['tax_ids'] = [(6, 0, room_type.tax_ids.ids)]
        elif room_type.product_id and room_type.product_id.taxes_id:
            room_line_vals['tax_ids'] = [(6, 0, room_type.product_id.taxes_id.ids)]
        # Analytic distribution
        if room_type.analytic_account_id:
            room_line_vals['analytic_distribution'] = {
                str(room_type.analytic_account_id.id): 100
            }
        invoice_lines.append((0, 0, room_line_vals))

        # ── Service charge lines ─────────────────────────────────────────────
        for sl in self.service_line_ids:
            svc = sl.service_id
            svc_line_vals = {
                'name': sl.description or svc.name,
                'quantity': sl.quantity,
                'price_unit': sl.price_unit,
            }
            if svc.product_id:
                svc_line_vals['product_id'] = svc.product_id.id
            if svc.tax_ids:
                svc_line_vals['tax_ids'] = [(6, 0, svc.tax_ids.ids)]
            elif svc.product_id and svc.product_id.taxes_id:
                svc_line_vals['tax_ids'] = [(6, 0, svc.product_id.taxes_id.ids)]
            if svc.analytic_account_id:
                svc_line_vals['analytic_distribution'] = {
                    str(svc.analytic_account_id.id): 100
                }
            invoice_lines.append((0, 0, svc_line_vals))

        # ── Resolve partner ───────────────────────────────────────────────────
        partner = (self.guest_id.partner_id
                   or self.env['res.partner'].search([('name', '=', self.guest_id.name)], limit=1)
                   or self.env.ref('base.public_partner'))

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'narration': _('Reservation: %s | Check-in: %s | Check-out: %s') % (
                self.name, self.check_in, self.check_out),
        }
        if journal:
            invoice_vals['journal_id'] = journal.id

        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id

        # ── Apply deposit as outstanding credit if deposit was paid ──────────
        if self.deposit_payment_id and self.deposit_payment_id.state == 'posted':
            invoice.action_post()
            credit_lines = self.deposit_payment_id.move_id.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )
            debit_lines = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )
            if credit_lines and debit_lines:
                (credit_lines | debit_lines).reconcile()

        return {
            'name': 'Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'name': 'Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
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

    def action_send_feedback_email(self):
        """Queue the post-stay feedback request email. Called automatically
        from the check-out wizard; safe to call manually too."""
        template = self.env.ref(
            'complete_hotel_management_system.email_template_guest_feedback',
            raise_if_not_found=False)
        for rec in self:
            if template and rec.guest_email:
                rec._portal_ensure_token()
                template.send_mail(rec.id, force_send=False)

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f'/my/reservations/{rec.id}'
