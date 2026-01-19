from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HotelCheckoutWizard(models.TransientModel):
    _name = 'hotel.checkout.wizard'
    _description = 'Hotel Check-out Wizard'

    reservation_id = fields.Many2one('hotel.reservation', string='Reservation', required=True)
    guest_id = fields.Many2one(related='reservation_id.guest_id', string='Guest', readonly=True)
    room_id = fields.Many2one(related='reservation_id.room_id', string='Room', readonly=True)

    actual_checkout_date = fields.Datetime(string='Check-out Date & Time', default=fields.Datetime.now, required=True)

    # Charges Summary
    room_charges = fields.Monetary(related='reservation_id.subtotal', string='Room Charges', readonly=True,
                                   currency_field='currency_id')
    service_charges = fields.Monetary(related='reservation_id.service_total', string='Service Charges', readonly=True,
                                      currency_field='currency_id')
    total_amount = fields.Monetary(related='reservation_id.total_amount', string='Total Amount', readonly=True,
                                   currency_field='currency_id')
    currency_id = fields.Many2one(related='reservation_id.currency_id')

    # Payment
    create_invoice = fields.Boolean(string='Create Invoice', default=True)
    payment_received = fields.Boolean(string='Payment Received')

    # Room Condition
    room_condition = fields.Selection([
        ('good', 'Good Condition'),
        ('minor_issues', 'Minor Issues'),
        ('damaged', 'Damaged'),
    ], string='Room Condition', default='good', required=True)

    damage_notes = fields.Text(string='Damage Notes')

    notes = fields.Text(string='Check-out Notes')

    def action_confirm_checkout(self):
        self.ensure_one()

        # Update reservation
        self.reservation_id.write({
            'state': 'checked_out',
            'checkout_datetime': self.actual_checkout_date,
        })

        # Update room status - mark for cleaning
        self.room_id.write({
            'state': 'cleaning',
            'housekeeping_status': 'dirty',
        })

        # Create housekeeping task
        self.env['hotel.housekeeping'].create({
            'room_id': self.room_id.id,
            'date': fields.Date.today(),
            'task_type': 'cleaning',
            'priority': '1',
            'notes': 'Post check-out cleaning required',
        })

        # Create invoice if requested
        if self.create_invoice and not self.reservation_id.invoice_id:
            self.reservation_id.action_create_invoice()

        # Add notes
        checkout_message = _('Guest checked out at %s. Room condition: %s.') % (
            self.actual_checkout_date,
            dict(self._fields['room_condition'].selection).get(self.room_condition)
        )

        if self.damage_notes:
            checkout_message += _(' Damage notes: %s') % self.damage_notes

        if self.notes:
            checkout_message += _(' Additional notes: %s') % self.notes

        self.reservation_id.message_post(body=checkout_message)

        return {'type': 'ir.actions.act_window_close'}