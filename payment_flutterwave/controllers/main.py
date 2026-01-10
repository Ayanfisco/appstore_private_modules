import logging
import json
import hashlib
import hmac
from werkzeug.exceptions import Forbidden
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class FlutterwaveController(http.Controller):

    @http.route('/payment/flutterwave/return', type='http', auth='public', csrf=False, save_session=False)
    def flutterwave_return(self, **data):
        """Handle customer return from Flutterwave payment page."""
        _logger.info('Flutterwave: Handling payment return with data:\n%s', data)

        # Get transaction reference
        tx_ref = data.get('tx_ref')
        transaction_id = data.get('transaction_id')
        status = data.get('status')

        if not tx_ref:
            _logger.error('Flutterwave: No transaction reference in return data')
            return request.redirect('/payment/status')

        try:
            # Find the transaction
            tx_sudo = request.env['payment.transaction'].sudo().search([
                ('reference', '=', tx_ref),
                ('provider_code', '=', 'flutterwave')
            ], limit=1)

            if not tx_sudo:
                _logger.error('Flutterwave: Transaction not found: %s', tx_ref)
                return request.redirect('/payment/status')

            # Store transaction ID if available
            if transaction_id and not tx_sudo.flutterwave_transaction_id:
                tx_sudo.flutterwave_transaction_id = transaction_id

            # Verify the transaction with Flutterwave API
            if status == 'successful' and transaction_id:
                tx_sudo._flutterwave_verify_payment()
            elif status == 'cancelled':
                tx_sudo._set_canceled('Payment was cancelled by user')
            else:
                # For any other status, we'll verify with API
                if transaction_id:
                    tx_sudo._flutterwave_verify_payment()

            # Redirect to payment status page
            return request.redirect('/payment/status')

        except Exception as e:
            _logger.exception('Flutterwave: Error processing return: %s', str(e))
            return request.redirect('/payment/status')

    @http.route('/payment/flutterwave/webhook', type='json', auth='public', csrf=False, save_session=False)
    def flutterwave_webhook(self, **kwargs):
        """Handle Flutterwave webhook notifications."""
        _logger.info('Flutterwave: Webhook received')

        try:
            # Get webhook data
            data = json.loads(request.httprequest.data)
            _logger.info('Flutterwave: Webhook data:\n%s', json.dumps(data, indent=2))

            # Verify webhook signature
            signature = request.httprequest.headers.get('verif-hash')
            if not self._verify_webhook_signature(data, signature):
                _logger.warning('Flutterwave: Invalid webhook signature')
                raise Forbidden('Invalid signature')

            # Extract transaction data
            if 'data' in data:
                notification_data = data['data']
            else:
                notification_data = data

            # Get transaction reference
            tx_ref = notification_data.get('tx_ref') or notification_data.get('txRef')

            if not tx_ref:
                _logger.error('Flutterwave: No transaction reference in webhook data')
                return {'status': 'error', 'message': 'No transaction reference'}

            # Find and process transaction
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'flutterwave', notification_data
            )

            if not tx_sudo:
                _logger.error('Flutterwave: Transaction not found: %s', tx_ref)
                return {'status': 'error', 'message': 'Transaction not found'}

            # Process the notification
            tx_sudo._process_notification_data(notification_data)

            return {'status': 'success'}

        except Forbidden:
            raise
        except Exception as e:
            _logger.exception('Flutterwave: Webhook error: %s', str(e))
            return {'status': 'error', 'message': str(e)}

    def _verify_webhook_signature(self, data, signature):
        """Verify webhook signature from Flutterwave."""
        if not signature:
            _logger.warning('Flutterwave: No signature provided in webhook')
            return True  # In test mode, Flutterwave might not send signature

        try:
            # Get all active Flutterwave providers
            providers = request.env['payment.provider'].sudo().search([
                ('code', '=', 'flutterwave'),
                ('state', 'in', ['enabled', 'test'])
            ])

            # Check if signature matches any provider's webhook secret
            for provider in providers:
                if provider.flutterwave_webhook_secret:
                    # Flutterwave sends the secret hash itself as signature
                    if signature == provider.flutterwave_webhook_secret:
                        return True

            # If no webhook secret is configured, allow in test mode
            test_providers = providers.filtered(lambda p: p.state == 'test')
            if test_providers:
                _logger.info('Flutterwave: Webhook accepted without signature (test mode)')
                return True

            return False

        except Exception as e:
            _logger.exception('Flutterwave: Error verifying webhook signature: %s', str(e))
            return False

    @http.route('/payment/flutterwave/status/<string:reference>', type='http', auth='public', website=True)
    def flutterwave_payment_status(self, reference, **kwargs):
        """Display payment status page."""
        tx_sudo = request.env['payment.transaction'].sudo().search([
            ('reference', '=', reference),
            ('provider_code', '=', 'flutterwave')
        ], limit=1)

        if not tx_sudo:
            return request.render('payment.payment_status', {
                'error_msg': 'Transaction not found'
            })

        # Render status page based on transaction state
        return request.redirect('/payment/status')
