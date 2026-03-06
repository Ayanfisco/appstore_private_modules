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

    # Payment / Deposit
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
    ], string='Payment Method')

    deposit_amount = fields.Float(string='Deposit Amount')
    post_deposit = fields.Boolean(
        string='Post Deposit to Accounting',
        default=True,
        help='Creates a real accounting payment entry for the deposit and links it to the reservation.')

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
        self.room_id.write({'state': 'occupied'})

        # ── Create deposit accounting payment ─────────────────────────────────
        if self.deposit_amount and self.deposit_amount > 0 and self.post_deposit:
            partner = (self.reservation_id.guest_id.partner_id
                       or self.env['res.partner'].search(
                        [('name', '=', self.reservation_id.guest_id.name)], limit=1)
                       or self.env.ref('base.public_partner'))

            # Find a suitable cash/bank journal based on payment method
            journal = self._get_payment_journal()

            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': partner.id,
                'amount': self.deposit_amount,
                'currency_id': self.reservation_id.currency_id.id,
                'journal_id': journal.id,
                'date': fields.Date.today(),
                'memo': _('Deposit — Reservation %s | %s') % (self.reservation_id.name,
                                                              self.reservation_id.guest_id.name),
            }
            payment = self.env['account.payment'].create(payment_vals)
            payment.action_post()

            # Link payment and deposit amount back to reservation
            self.reservation_id.write({
                'deposit_amount': self.deposit_amount,
                'deposit_payment_id': payment.id,
            })

        # Post chatter message
        msg_parts = [
            _('Guest checked in at %s.') % self.actual_checkin_date,
            _('Payment method: %s.') % (
                dict(self._fields['payment_method'].selection).get(self.payment_method, 'N/A')),
        ]
        if self.deposit_amount:
            msg_parts.append(_('Deposit posted: %s %s.') % (
                self.reservation_id.currency_id.symbol, self.deposit_amount))
        if self.notes:
            msg_parts.append(_('Notes: %s') % self.notes)

        self.reservation_id.message_post(body=' '.join(msg_parts))

        return {'type': 'ir.actions.act_window_close'}

    def _get_payment_journal(self):
        """Return appropriate journal for the deposit based on payment method."""
        journal_type = 'bank' if self.payment_method in ('card', 'bank_transfer', 'online') else 'cash'
        journal = self.env['account.journal'].search(
            [('type', '=', journal_type), ('company_id', '=', self.env.company.id)], limit=1)
        if not journal:
            journal = self.env['account.journal'].search(
                [('type', 'in', ['cash', 'bank']), ('company_id', '=', self.env.company.id)], limit=1)
        if not journal:
            raise UserError(_('No cash or bank journal found. Please configure a payment journal in Accounting.'))
        return journal
