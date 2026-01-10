import logging
import requests
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('flutterwave', 'Flutterwave')],
        ondelete={'flutterwave': 'set default'}
    )

    flutterwave_public_key = fields.Char(
        string='Public Key',
        required_if_provider='flutterwave',
        groups='base.group_system',
        help='Your Flutterwave Public Key (starts with FLWPUBK-)'
    )

    flutterwave_secret_key = fields.Char(
        string='Secret Key',
        required_if_provider='flutterwave',
        groups='base.group_system',
        help='Your Flutterwave Secret Key (starts with FLWSECK-)'
    )

    flutterwave_encryption_key = fields.Char(
        string='Encryption Key',
        groups='base.group_system',
        help='Optional: Encryption Key for additional security'
    )

    flutterwave_webhook_secret = fields.Char(
        string='Webhook Secret Hash',
        groups='base.group_system',
        help='Secret hash for webhook verification (found in Flutterwave dashboard)'
    )

    flutterwave_payment_methods = fields.Selection([
        ('card', 'Card'),
        ('account', 'Bank Account'),
        ('ussd', 'USSD'),
        ('mobile_money', 'Mobile Money'),
        ('all', 'All Methods'),
    ], string='Payment Methods', default='all',
        required_if_provider='flutterwave',
        help='Payment methods to offer to customers')

    flutterwave_split_payment = fields.Boolean(
        string='Enable Split Payments',
        help='Enable split payment configuration'
    )

    flutterwave_split_id = fields.Char(
        string='Split Payment ID',
        help='Your split payment configuration ID from Flutterwave'
    )

    def _flutterwave_get_api_url(self):
        """Return the appropriate API URL based on provider state."""
        self.ensure_one()
        if self.state == 'enabled':
            return 'https://api.flutterwave.com/v3'
        else:  # test mode
            return 'https://api.flutterwave.com/v3'  # Flutterwave uses same URL with test keys

    @api.model
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """Override to add Flutterwave supported currencies check."""
        providers = super()._get_compatible_providers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if not currency:
            return providers

        # Flutterwave supported currencies
        supported_currencies = [
            'NGN', 'USD', 'EUR', 'GBP', 'GHS', 'KES', 'UGX',
            'ZAR', 'TZS', 'XAF', 'XOF', 'RWF', 'ZMW', 'MAD',
            'EGP', 'CAD', 'AUD', 'JPY', 'CNY'
        ]

        return providers.filtered(
            lambda p: p.code != 'flutterwave' or currency.name in supported_currencies
        )

    def _flutterwave_make_request(self, endpoint, data=None, method='POST'):
        """Make API request to Flutterwave."""
        self.ensure_one()

        url = f"{self._flutterwave_get_api_url()}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.flutterwave_secret_key}',
            'Content-Type': 'application/json',
        }

        try:
            if method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=60)
            elif method == 'GET':
                response = requests.get(url, headers=headers, timeout=60)
            else:
                raise ValidationError(_('Unsupported HTTP method: %s', method))

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            _logger.error('Flutterwave API Error: %s', str(e))
            raise ValidationError(
                _('Unable to communicate with Flutterwave. Please try again later.\nError: %s', str(e))
            )

    def _flutterwave_verify_transaction(self, transaction_id):
        """Verify a transaction with Flutterwave."""
        self.ensure_one()
        return self._flutterwave_make_request(
            f'transactions/{transaction_id}/verify',
            method='GET'
        )

    @api.constrains('state', 'flutterwave_public_key', 'flutterwave_secret_key')
    def _check_flutterwave_credentials(self):
        """Validate Flutterwave credentials when enabling provider."""
        for provider in self:
            if provider.code != 'flutterwave':
                continue

            if provider.state == 'enabled':
                if not provider.flutterwave_public_key or not provider.flutterwave_secret_key:
                    raise ValidationError(
                        _('Flutterwave Public Key and Secret Key are required to enable the provider.')
                    )

                # Validate key format
                if not provider.flutterwave_public_key.startswith('FLWPUBK-'):
                    raise ValidationError(
                        _('Invalid Flutterwave Public Key format. It should start with FLWPUBK-')
                    )

                if not provider.flutterwave_secret_key.startswith('FLWSECK-'):
                    raise ValidationError(
                        _('Invalid Flutterwave Secret Key format. It should start with FLWSECK-')
                    )