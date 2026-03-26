import logging
from datetime import datetime
from werkzeug import urls

from odoo import _, models
from odoo.exceptions import ValidationError
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_paystack_tech import const

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """Override to return Paystack-specific rendering values."""
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'paystack':
            return res

        # Validate required fields before hitting the API
        if not self.partner_email:
            raise ValidationError(
                "Paystack: " + _("Customer email is required to process payment.")
            )
        if self.amount <= 0:
            raise ValidationError(
                "Paystack: " + _("Payment amount must be greater than zero.")
            )
        if self.amount < 100:
            raise ValidationError(
                "Paystack: " + _("Minimum payment amount is NGN 100.")
            )

        base_url = self.provider_id.get_base_url()

        # Make reference unique per attempt to avoid Paystack duplicate reference error
        unique_reference = f"{self.reference}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        payload = {
            'email': self.partner_email,
            'amount': int(self.amount * 100),  # Convert to kobo/cents
            'currency': self.currency_id.name,
            'reference': unique_reference,
            'callback_url': urls.url_join(base_url, const.RETURN_URL),
            'metadata': {
                'transaction_id': self.id,
                'partner_id': self.partner_id.id,
                'odoo_reference': self.reference,  # Keep original for tracing
            }
        }

        # Initialize the transaction with Paystack
        response_data = self.provider_id._paystack_make_request(
            '/transaction/initialize',
            data=payload
        )

        if not response_data.get('status'):
            raise ValidationError(
                "Paystack: " + _("Unable to initialize payment.")
            )

        payment_data = response_data.get('data', {})
        api_url = payment_data.get('authorization_url')
        paystack_ref = payment_data.get('reference')

        if not api_url:
            raise ValidationError(
                "Paystack: " + _("No payment URL provided by Paystack.")
            )

        # Store Paystack's reference for verification later
        if paystack_ref:
            self.provider_reference = paystack_ref
            _logger.info(
                "Redirecting to Paystack for transaction %s (Paystack ref: %s)",
                self.reference, paystack_ref
            )

        return {
            'api_url': api_url,
            'paystack_reference': paystack_ref,
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Override to find the transaction based on Paystack data."""
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'paystack' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference')
        if not reference:
            raise ValidationError(
                "Paystack: " + _("Missing reference in notification data.")
            )

        # Search by provider_reference (Paystack's ref) first
        tx = self.search([
            ('provider_reference', '=', reference),
            ('provider_code', '=', 'paystack')
        ])

        # Fallback to Odoo reference
        if not tx:
            tx = self.search([
                ('reference', '=', reference),
                ('provider_code', '=', 'paystack')
            ])

        if not tx:
            raise ValidationError(
                "Paystack: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """Override to process the transaction based on Paystack data."""
        super()._process_notification_data(notification_data)
        if self.provider_code != 'paystack':
            return

        # Use provider_reference (Paystack's own ref) for verification
        paystack_ref = (
            self.provider_reference
            or notification_data.get('paystack_reference')
            or notification_data.get('reference')
        )

        if not paystack_ref:
            raise ValidationError(
                "Paystack: " + _("Missing Paystack reference for verification.")
            )

        # Store for future use
        self.provider_reference = paystack_ref

        # Verify transaction with Paystack
        response_data = self.provider_id._paystack_make_request(
            f'/transaction/verify/{paystack_ref}',
            method='GET'
        )

        if not response_data.get('status'):
            raise ValidationError(
                "Paystack: " + _("Unable to verify transaction.")
            )

        payment_data = response_data.get('data', {})
        status = payment_data.get('status')

        if status == 'success':
            self._set_done()
        elif status == 'failed':
            self._set_error("Paystack: " + _("Transaction failed."))
        elif status == 'abandoned':
            self._set_canceled("Paystack: " + _("Transaction was abandoned."))
        else:
            _logger.warning(
                "Received unrecognized payment status from Paystack: %s", status
            )
            self._set_pending()

    def _send_payment_request(self):
        """Override to send a payment request to Paystack."""
        if self.provider_code != 'paystack':
            return super()._send_payment_request()
        # Payment is handled via redirect — nothing to do here
        return

    def _send_refund_request(self, amount_to_refund=None):
        """Override to send a refund request to Paystack."""
        if self.provider_code != 'paystack':
            return super()._send_refund_request(amount_to_refund=amount_to_refund)

        refund_amount = amount_to_refund if amount_to_refund else self.amount

        payload = {
            'transaction': self.provider_reference,
            'amount': int(refund_amount * 100),  # Convert to kobo
        }

        response_data = self.provider_id._paystack_make_request(
            '/refund',
            data=payload
        )

        if not response_data.get('status'):
            raise ValidationError(
                "Paystack: " + _("Unable to process refund.")
            )

        refund_tx = self._create_refund_transaction(amount_to_refund=refund_amount)
        refund_tx._set_done()
        return refund_tx