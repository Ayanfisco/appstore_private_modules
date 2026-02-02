import logging
import requests
from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_paystack import const

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('paystack', 'Paystack')],
        ondelete={'paystack': 'set default'}
    )
    paystack_secret_key = fields.Char(
        string='Secret Key',
        required_if_provider='paystack',
        groups='base.group_system'
    )
    paystack_public_key = fields.Char(
        string='Public Key',
        required_if_provider='paystack'
    )

    # ==== BUSINESS METHODS ====

    def _paystack_get_api_url(self):
        """Return the API URL according to the provider state."""
        self.ensure_one()
        if self.state == 'enabled':
            return 'https://api.paystack.co'
        else:  # 'test'
            return 'https://api.paystack.co'  # Paystack uses same URL for test and live

    def _paystack_make_request(self, endpoint, data=None, method='POST'):
        """Make a request to Paystack API."""
        self.ensure_one()
        url = urls.url_join(self._paystack_get_api_url(), endpoint)
        headers = {
            'Authorization': f'Bearer {self.paystack_secret_key}',
            'Content-Type': 'application/json',
        }

        try:
            if method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                response = requests.get(url, headers=headers, timeout=10)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            # Log the exception and, if available, the HTTP response details for
            # debugging (status code and body). Do NOT include response body in
            # the UI-facing ValidationError because it may contain sensitive data.
            try:
                response = getattr(error, 'response', None)
                if response is not None:
                    _logger.error(
                        "Paystack HTTP error: status=%s, body=%s",
                        getattr(response, 'status_code', None),
                        (getattr(response, 'text', None) or '')[:1000],
                    )
                else:
                    _logger.exception("Unable to communicate with Paystack: %s", error)
            except Exception:
                # Ensure logging never raises
                _logger.exception("Unable to communicate with Paystack (and failed to log response): %s", error)

            # Return a generic, safe error to the user including the HTTP status if present.
            status_part = ''
            http_status = None
            try:
                http_status = getattr(getattr(error, 'response', None), 'status_code', None)
                if http_status:
                    status_part = f" (HTTP {http_status})"
            except Exception:
                pass

            raise ValidationError(
                "Paystack: " + _("Could not establish the connection to the API.") + status_part
            )

    @api.model
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """Override to filter Paystack provider based on supported currencies."""
        providers = super()._get_compatible_providers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name not in const.SUPPORTED_CURRENCIES:
            providers = providers.filtered(lambda p: p.code != 'paystack')

        return providers

    def _get_supported_currencies(self):
        """Override to specify supported currencies."""
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'paystack':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """Override to return the default payment method codes."""
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'paystack':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES

    def _should_build_inline(self, is_validation=False):
        """Override to force redirect flow for Paystack."""
        self.ensure_one()
        if self.code == 'paystack':
            return False
        return super()._should_build_inline(is_validation=is_validation)