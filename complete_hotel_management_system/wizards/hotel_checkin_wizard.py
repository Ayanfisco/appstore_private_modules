from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HotelCheckinWizard(models.TransientModel):
    _name = 'hotel.checkin.wizard'
    _description = 'Hotel Check-in Wizard'

    reservation_id = fields.Many2one('hotel.reservation', string='Reservation', required=True)
    guest_id = fields.Many2one(related='reservation_id.guest_id', string='Guest', readonly=True)
    room_id = fields.Many2one(related='reservation_id.room_id', string='Room', readonly=True)

    actual_checkin_date = fields.Datetime(string='Check-in Date & Time', default=fields.Datetime.now, required=True)

    # ID Verification
    id_verified = fields.Boolean(string='ID Verified', required=True)
    id_type = fields.Selection(related='guest_id.id_type', string='ID Type', readonly=True)
    id_number = fields.Char(related='guest_id.id_number', string='ID Number', readonly=True)

    # Payment
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
    ], string='Payment Method')

    deposit_amount = fields.Float(string='Deposit Amount')

    notes = fields.Text(string='Check-in Notes')

    def action_confirm_checkin(self):
        self.ensure_one()

        if not self.id_verified:
            raise UserError(_('Please verify guest identification before check-in!'))

        # Update reservation
        self.reservation_id.write({
            'state': 'checked_in',
            'checkin_datetime': self.actual_checkin_date,
        })

        # Update room status
        self.room_id.write({
            'state': 'occupied',
        })

        # Add note to reservation
        if self.notes:
            self.reservation_id.message_post(
                body=_('Check-in Notes: %s') % self.notes
            )

        # Post message
        self.reservation_id.message_post(
            body=_('Guest checked in at %s. Payment method: %s. Deposit: %s') % (
                self.actual_checkin_date,
                dict(self._fields['payment_method'].selection).get(self.payment_method, 'N/A'),
                self.deposit_amount or 0
            )
        )

        return {'type': 'ir.actions.act_window_close'}