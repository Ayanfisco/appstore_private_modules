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

    @http.route(
        _return_url, type='http', auth='public',
        methods=['GET', 'POST'], csrf=False
    )
    def paystack_return_from_checkout(self, **data):
        """Process the return from Paystack after payment."""
        _logger.info(
            "Handling return from Paystack with data:\n%s",
            pprint.pformat(data)
        )

        reference = data.get('reference') or data.get('trxref')

        if not reference:
            _logger.warning("Paystack return without reference: %s", data)
            return request.redirect('/payment/status')

        try:
            tx_sudo = request.env['payment.transaction'].sudo().search([
                ('provider_reference', '=', reference),
                ('provider_code', '=', 'paystack')
            ], limit=1)

            # Fallback to Odoo reference
            if not tx_sudo:
                tx_sudo = request.env['payment.transaction'].sudo().search([
                    ('reference', '=', reference),
                    ('provider_code', '=', 'paystack')
                ], limit=1)

            if not tx_sudo:
                raise ValidationError(
                    f"No transaction found for reference {reference}"
                )

            tx_sudo._handle_notification_data('paystack', data)

        except Exception as e:
            _logger.exception("Error processing Paystack return: %s", e)

        return request.redirect('/payment/status')

    @http.route(
        _webhook_url, type='json', auth='public',
        methods=['POST'], csrf=False
    )
    def paystack_webhook(self):
        """Handle webhook notifications from Paystack."""
        data = request.jsonrequest
        _logger.info(
            "Webhook notification from Paystack:\n%s",
            pprint.pformat(data)
        )

        if not self._verify_webhook_signature():
            _logger.warning("Invalid webhook signature from Paystack")
            return {'status': 'error', 'message': 'Invalid signature'}

        event = data.get('event')
        event_data = data.get('data', {})

        if event == 'charge.success':
            self._handle_charge_success(event_data)
        elif event == 'charge.failed':
            self._handle_charge_failed(event_data)
        else:
            _logger.info("Unhandled Paystack webhook event: %s", event)

        return {'status': 'success'}

    def _verify_webhook_signature(self):
        """Verify the webhook signature from Paystack."""
        signature = request.httprequest.headers.get('X-Paystack-Signature')
        if not signature:
            return False

        try:
            provider_sudo = request.env['payment.provider'].sudo().search([
                ('code', '=', 'paystack'),
                ('state', 'in', ['enabled', 'test'])
            ], limit=1)

            if not provider_sudo or not provider_sudo.paystack_secret_key:
                return False

            computed_signature = hmac.new(
                key=provider_sudo.paystack_secret_key.encode('utf-8'),
                msg=request.httprequest.data,
                digestmod=hashlib.sha512
            ).hexdigest()

            return hmac.compare_digest(computed_signature, signature)

        except Exception as e:
            _logger.exception("Error verifying webhook signature: %s", e)
            return False

    def _handle_charge_success(self, data):
        """Handle successful charge webhook events."""
        reference = data.get('reference')
        if not reference:
            _logger.warning("Charge success event without reference")
            return
        try:
            tx_sudo = request.env['payment.transaction'].sudo().search([
                ('provider_reference', '=', reference),
                ('provider_code', '=', 'paystack')
            ], limit=1)
            if tx_sudo:
                tx_sudo._handle_notification_data('paystack', data)
        except Exception as e:
            _logger.exception("Error handling charge success: %s", e)

    def _handle_charge_failed(self, data):
        """Handle failed charge webhook events."""
        reference = data.get('reference')
        if not reference:
            _logger.warning("Charge failed event without reference")
            return
        try:
            tx_sudo = request.env['payment.transaction'].sudo().search([
                ('provider_reference', '=', reference),
                ('provider_code', '=', 'paystack')
            ], limit=1)
            if tx_sudo:
                tx_sudo._handle_notification_data('paystack', data)
        except Exception as e:
            _logger.exception("Error handling charge failed: %s", e)