import logging
import json
from werkzeug import urls
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    flutterwave_transaction_id = fields.Char(
        string='Flutterwave Transaction ID',
        readonly=True,
        help='Transaction ID from Flutterwave'
    )

    flutterwave_payment_reference = fields.Char(
        string='Flutterwave Reference',
        readonly=True,
        help='Payment reference from Flutterwave'
    )

    def _get_specific_rendering_values(self, processing_values):
        """Override to return Flutterwave-specific rendering values."""
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'flutterwave':
            return res

        # Get base URL for callbacks
        base_url = self.provider_id.get_base_url()

        # Prepare payment data for Flutterwave
        rendering_values = {
            'public_key': self.provider_id.flutterwave_public_key,
            'tx_ref': self.reference,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'payment_options': self._flutterwave_get_payment_options(),
            'redirect_url': urls.url_join(base_url, '/payment/flutterwave/return'),
            'customer': {
                'email': self.partner_email or self.partner_id.email,
                'phonenumber': self.partner_phone or self.partner_id.phone or '',
                'name': self.partner_name or self.partner_id.name,
            },
            'customizations': {
                'title': self.provider_id.company_id.name or 'Payment',
                'description': self.reference,
                'logo': self.provider_id.company_id.logo_web or '',
            },
            'meta': {
                'odoo_reference': self.reference,
                'partner_id': self.partner_id.id,
            }
        }

        # Add split payment if configured
        if self.provider_id.flutterwave_split_payment and self.provider_id.flutterwave_split_id:
            rendering_values['payment_plan'] = self.provider_id.flutterwave_split_id

        return rendering_values

    def _flutterwave_get_payment_options(self):
        """Get payment methods configuration."""
        self.ensure_one()
        payment_method = self.provider_id.flutterwave_payment_methods

        if payment_method == 'all':
            return 'card,account,ussd,mobilemoney,banktransfer'
        elif payment_method == 'card':
            return 'card'
        elif payment_method == 'account':
            return 'account'
        elif payment_method == 'ussd':
            return 'ussd'
        elif payment_method == 'mobile_money':
            return 'mobilemoney'
        else:
            return 'card,account,ussd,mobilemoney'

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Override to find transaction from Flutterwave notification data."""
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'flutterwave' or len(tx) == 1:
            return tx

        # Try to find by transaction reference
        tx_ref = notification_data.get('tx_ref') or notification_data.get('txRef')
        if tx_ref:
            tx = self.search([('reference', '=', tx_ref), ('provider_code', '=', 'flutterwave')])

        # Try to find by Flutterwave transaction ID
        if not tx:
            flw_tx_id = notification_data.get('transaction_id') or notification_data.get('id')
            if flw_tx_id:
                tx = self.search([
                    ('flutterwave_transaction_id', '=', str(flw_tx_id)),
                    ('provider_code', '=', 'flutterwave')
                ])

        if not tx:
            raise ValidationError(
                _('Flutterwave: No transaction found matching reference %s', tx_ref)
            )

        return tx

    def _process_notification_data(self, notification_data):
        """Override to process Flutterwave notification data."""
        super()._process_notification_data(notification_data)
        if self.provider_code != 'flutterwave':
            return

        # Extract transaction details
        self.flutterwave_transaction_id = notification_data.get('id') or notification_data.get('transaction_id')
        self.flutterwave_payment_reference = notification_data.get('flw_ref') or notification_data.get('flwRef')

        # Get transaction status
        status = notification_data.get('status', '').lower()

        _logger.info(
            'Flutterwave: Processing transaction %s with status: %s',
            self.reference, status
        )

        # Process based on status
        if status == 'successful':
            self._set_done()
        elif status in ['failed', 'cancelled']:
            self._set_canceled(
                _('Payment failed or was cancelled. Status: %s', status)
            )
        elif status == 'pending':
            self._set_pending()
        else:
            _logger.warning(
                'Flutterwave: Unknown payment status %s for transaction %s',
                status, self.reference
            )
            self._set_error(
                _('Unknown payment status: %s', status)
            )

    def _flutterwave_verify_payment(self):
        """Verify payment with Flutterwave API."""
        self.ensure_one()

        if not self.flutterwave_transaction_id:
            raise ValidationError(
                _('Cannot verify payment: Flutterwave transaction ID is missing')
            )

        # Call Flutterwave API to verify
        try:
            response = self.provider_id._flutterwave_verify_transaction(
                self.flutterwave_transaction_id
            )

            if response.get('status') == 'success':
                data = response.get('data', {})

                # Verify amount
                paid_amount = float(data.get('amount', 0))
                expected_amount = self.amount

                if abs(paid_amount - expected_amount) > 0.01:  # Allow 0.01 difference for rounding
                    _logger.error(
                        'Flutterwave: Amount mismatch for transaction %s. Expected: %s, Got: %s',
                        self.reference, expected_amount, paid_amount
                    )
                    self._set_error(_('Payment amount mismatch'))
                    return False

                # Verify currency
                if data.get('currency') != self.currency_id.name:
                    _logger.error(
                        'Flutterwave: Currency mismatch for transaction %s',
                        self.reference
                    )
                    self._set_error(_('Payment currency mismatch'))
                    return False

                # Process the notification
                self._process_notification_data(data)
                return True
            else:
                _logger.error(
                    'Flutterwave: Verification failed for transaction %s: %s',
                    self.reference, response.get('message')
                )
                self._set_error(_('Payment verification failed'))
                return False

        except Exception as e:
            _logger.exception(
                'Flutterwave: Error verifying transaction %s: %s',
                self.reference, str(e)
            )
            self._set_error(_('Error verifying payment'))
            return False

    def action_flutterwave_verify(self):
        """Manual action to verify transaction with Flutterwave."""
        self.ensure_one()
        if self.provider_code != 'flutterwave':
            return

        if self._flutterwave_verify_payment():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Payment verified successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Payment verification failed'),
                    'type': 'danger',
                    'sticky': False,
                }
            }
