import logging
import pprint
import hmac
import hashlib

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaystackController(http.Controller):
    _return_url = '/payment/paystack/return'
    _webhook_url = '/payment/paystack/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def paystack_return_from_checkout(self, **data):
        """Process the return from Paystack after payment."""
        _logger.info("Handling return from Paystack with data:\n%s", pprint.pformat(data))

        # Extract reference from the return data
        reference = data.get('reference') or data.get('trxref')

        if not reference:
            _logger.warning("Paystack return without reference: %s", data)
            return request.redirect('/payment/status')

        # Find the transaction
        try:
            tx_sudo = request.env['payment.transaction'].sudo().search([
                ('reference', '=', reference),
                ('provider_code', '=', 'paystack')
            ])

            if not tx_sudo:
                raise ValidationError(f"No transaction found for reference {reference}")

            # Process the notification data
            tx_sudo._handle_notification_data('paystack', data)

        except Exception as e:
            _logger.exception("Error processing Paystack return: %s", e)

        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='json', auth='public', methods=['POST'], csrf=False)
    def paystack_webhook(self):
        """Handle webhook notifications from Paystack."""
        data = request.jsonrequest
        _logger.info("Webhook notification from Paystack:\n%s", pprint.pformat(data))

        # Verify webhook signature
        if not self._verify_webhook_signature(data):
            _logger.warning("Invalid webhook signature from Paystack")
            return {'status': 'error', 'message': 'Invalid signature'}

        # Extract event data
        event = data.get('event')
        event_data = data.get('data', {})

        # Process different event types
        if event == 'charge.success':
            self._handle_charge_success(event_data)
        elif event == 'charge.failed':
            self._handle_charge_failed(event_data)
        else:
            _logger.info("Unhandled Paystack webhook event: %s", event)

        return {'status': 'success'}

    def _verify_webhook_signature(self, data):
        """Verify the webhook signature from Paystack."""
        # Get the signature from headers
        signature = request.httprequest.headers.get('X-Paystack-Signature')

        if not signature:
            return False

        # Get the secret key from the provider
        # Note: In production, you should get this from the provider settings
        try:
            provider_sudo = request.env['payment.provider'].sudo().search([
                ('code', '=', 'paystack'),
                ('state', 'in', ['enabled', 'test'])
            ], limit=1)

            if not provider_sudo:
                return False

            secret_key = provider_sudo.paystack_secret_key

            # Compute the hash
            computed_signature = hmac.new(
                secret_key.encode('utf-8'),
                request.httprequest.data,
                hashlib.sha512
            ).hexdigest()

            return hmac.compare_digest(computed_signature, signature)

        except Exception as e:
            _logger.exception("Error verifying webhook signature: %s", e)
            return False

    def _handle_charge_success(self, data):
        """Handle successful charge events."""
        reference = data.get('reference')

        if not reference:
            _logger.warning("Charge success event without reference")
            return

        try:
            tx_sudo = request.env['payment.transaction'].sudo().search([
                ('reference', '=', reference),
                ('provider_code', '=', 'paystack')
            ])

            if tx_sudo:
                tx_sudo._handle_notification_data('paystack', data)

        except Exception as e:
            _logger.exception("Error handling charge success: %s", e)

    def _handle_charge_failed(self, data):
        """Handle failed charge events."""
        reference = data.get('reference')

        if not reference:
            _logger.warning("Charge failed event without reference")
            return

        try:
            tx_sudo = request.env['payment.transaction'].sudo().search([
                ('reference', '=', reference),
                ('provider_code', '=', 'paystack')
            ])

            if tx_sudo:
                tx_sudo._handle_notification_data('paystack', data)

        except Exception as e:
            _logger.exception("Error handling charge failed: %s", e)