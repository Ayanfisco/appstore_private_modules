from odoo import http, fields, _
from odoo.http import request


class HotelWebsiteBooking(http.Controller):
    """Public-facing booking flow: search -> room results -> booking form ->
    confirmation. Bookings created here land as Draft reservations so hotel
    staff review and confirm them (which also assigns/locks the room and
    triggers the confirmation email) rather than being auto-confirmed from
    an unauthenticated request.
    """

    @http.route(['/hotel/rooms'], type='http', auth='public', website=True, sitemap=True)
    def hotel_rooms_search(self, **kw):
        properties = request.env['hotel.property'].sudo().search([])

        domain = []
        property_id = kw.get('property_id')
        if property_id:
            domain.append(('property_id', '=', int(property_id)))
        room_types = request.env['hotel.room.type'].sudo().search(domain)

        check_in = kw.get('check_in')
        check_out = kw.get('check_out')
        check_in_date = check_out_date = False
        if check_in and check_out:
            try:
                check_in_date = fields.Date.from_string(check_in)
                check_out_date = fields.Date.from_string(check_out)
            except ValueError:
                check_in_date = check_out_date = False

        results = []
        for rt in room_types:
            if check_in_date and check_out_date and check_out_date > check_in_date:
                free_rooms = self._free_rooms(rt, check_in_date, check_out_date)
                available = bool(free_rooms)
                total_price, avg_rate = rt.get_total_price(check_in_date, check_out_date)
            else:
                available = True
                total_price, avg_rate = 0.0, rt.list_price

            results.append({
                'room_type': rt,
                'available': available,
                'total_price': total_price,
                'avg_rate': avg_rate,
            })

        values = {
            'properties': properties,
            'results': results,
            'check_in': check_in or '',
            'check_out': check_out or '',
            'adults': kw.get('adults', '1'),
            'property_id': property_id,
            'searched': bool(check_in_date and check_out_date),
        }
        return request.render('complete_hotel_management_system.hotel_rooms_search_page', values)

    @http.route(['/hotel/book/<int:room_type_id>'], type='http', auth='public', website=True, sitemap=False)
    def hotel_book_form(self, room_type_id, **kw):
        room_type = request.env['hotel.room.type'].sudo().browse(room_type_id)
        if not room_type.exists():
            return request.redirect('/hotel/rooms')

        total_price = avg_rate = 0.0
        check_in_date = check_out_date = False
        if kw.get('check_in') and kw.get('check_out'):
            try:
                check_in_date = fields.Date.from_string(kw.get('check_in'))
                check_out_date = fields.Date.from_string(kw.get('check_out'))
                if check_out_date and check_in_date and check_out_date > check_in_date:
                    total_price, avg_rate = room_type.get_total_price(check_in_date, check_out_date)
            except ValueError:
                pass

        values = {
            'room_type': room_type,
            'check_in': kw.get('check_in', ''),
            'check_out': kw.get('check_out', ''),
            'adults': kw.get('adults', '1'),
            'total_price': total_price,
            'error': kw.get('error'),
        }
        return request.render('complete_hotel_management_system.hotel_booking_form_page', values)

    @http.route(['/hotel/book/submit'], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def hotel_book_submit(self, **post):
        room_type_id = int(post.get('room_type_id') or 0)
        room_type = request.env['hotel.room.type'].sudo().browse(room_type_id)
        if not room_type.exists():
            return request.redirect('/hotel/rooms')

        redirect_base = '/hotel/book/%s' % room_type_id
        try:
            check_in_date = fields.Date.from_string(post.get('check_in'))
            check_out_date = fields.Date.from_string(post.get('check_out'))
        except ValueError:
            return request.redirect(redirect_base + '?error=dates')

        if not check_in_date or not check_out_date or check_out_date <= check_in_date:
            return request.redirect(redirect_base + '?error=dates')

        name = (post.get('name') or '').strip()
        email = (post.get('email') or '').strip()
        phone = (post.get('phone') or '').strip()
        if not name or not email:
            return request.redirect(redirect_base + '?error=missing')

        try:
            adults = max(int(post.get('adults') or 1), 1)
            children = max(int(post.get('children') or 0), 0)
        except ValueError:
            adults, children = 1, 0

        free_rooms = self._free_rooms(room_type, check_in_date, check_out_date)
        if not free_rooms:
            return request.redirect(redirect_base + '?error=unavailable')

        guest = request.env['hotel.guest'].sudo().search([('email', '=', email)], limit=1)
        if not guest:
            guest = request.env['hotel.guest'].sudo().create({
                'name': name,
                'email': email,
                'phone': phone,
            })

        _total, avg_rate = room_type.get_total_price(check_in_date, check_out_date)

        reservation = request.env['hotel.reservation'].sudo().create({
            'guest_id': guest.id,
            'property_id': room_type.property_id.id,
            'room_type_id': room_type.id,
            'room_id': free_rooms[0].id,
            'check_in': check_in_date,
            'check_out': check_out_date,
            'adults': adults,
            'children': children,
            'room_rate': avg_rate,
            'source': 'online',
            'special_requests': post.get('special_requests'),
            'state': 'draft',
        })
        reservation._portal_ensure_token()

        self._maybe_create_crm_lead(reservation, guest, name, email, phone)

        return request.redirect('/hotel/book/thankyou/%s/%s' % (reservation.id, reservation.access_token))

    def _maybe_create_crm_lead(self, reservation, guest, name, email, phone):
        """Create a CRM lead for this booking inquiry so the sales team can
        follow up on unconfirmed requests. No-ops silently if the CRM app
        isn't installed — this integration is optional, not a hard dependency,
        so installing this module never forces buyers to install CRM too."""
        try:
            Lead = request.env['crm.lead'].sudo()
        except KeyError:
            return

        description = _(
            'Website booking inquiry\n'
            'Property: %s\nRoom Type: %s\nCheck-in: %s\nCheck-out: %s\n'
            'Adults: %s  Children: %s\nReservation: %s'
        ) % (
            reservation.property_id.name, reservation.room_type_id.name,
            reservation.check_in, reservation.check_out,
            reservation.adults, reservation.children, reservation.name,
        )
        Lead.create({
            'name': _('Hotel Booking Inquiry - %s') % reservation.name,
            'contact_name': name,
            'email_from': email,
            'phone': phone,
            'partner_id': guest.partner_id.id if guest.partner_id else False,
            'description': description,
            'type': 'lead',
        })

    @http.route(['/hotel/book/thankyou/<int:reservation_id>/<string:token>'],
                type='http', auth='public', website=True, sitemap=False)
    def hotel_book_thankyou(self, reservation_id, token, **kw):
        reservation = request.env['hotel.reservation'].sudo().browse(reservation_id)
        if not reservation.exists() or reservation.access_token != token:
            return request.redirect('/hotel/rooms')
        return request.render('complete_hotel_management_system.hotel_booking_thankyou_page', {
            'reservation': reservation,
        })

    @http.route(['/hotel/feedback/<int:reservation_id>/<string:token>/<int:rating>'],
                type='http', auth='public', website=True, sitemap=False)
    def hotel_feedback(self, reservation_id, token, rating, **kw):
        reservation = request.env['hotel.reservation'].sudo().browse(reservation_id)
        if not reservation.exists() or reservation.access_token != token:
            return request.render('complete_hotel_management_system.hotel_feedback_invalid_page', {})

        if rating in (1, 2, 3, 4, 5) and not reservation.feedback_submitted:
            reservation.write({
                'feedback_rating': str(rating),
                'feedback_submitted': True,
            })
            reservation.message_post(body=_('Guest submitted feedback rating: %s/5') % rating)

        return request.render('complete_hotel_management_system.hotel_feedback_thankyou_page', {
            'reservation': reservation,
            'rating': rating,
        })

    def _free_rooms(self, room_type, check_in_date, check_out_date):
        """Rooms of this type with no overlapping confirmed/checked-in reservation
        for the given date range."""
        busy_room_ids = request.env['hotel.reservation'].sudo().search([
            ('room_type_id', '=', room_type.id),
            ('state', 'in', ['confirmed', 'checked_in']),
            ('check_in', '<', check_out_date),
            ('check_out', '>', check_in_date),
        ]).mapped('room_id').ids
        return request.env['hotel.room'].sudo().search([
            ('room_type_id', '=', room_type.id),
            ('id', 'not in', busy_room_ids),
        ])
