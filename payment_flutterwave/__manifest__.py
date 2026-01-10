{
    'name': 'Flutterwave Payment Gateway',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': 'Payment Provider: Flutterwave - Accept payments via Cards, Bank Transfer, USSD & Mobile Money',
    'description': """
Flutterwave Payment Gateway Integration for Odoo 18
====================================================

Accept payments across Africa and globally using Flutterwave's payment infrastructure.

Features:
---------
* Support for multiple payment methods (Cards, Bank Transfer, USSD, Mobile Money)
* Multi-currency support (NGN, USD, GHS, KES, ZAR, etc.)
* Secure webhook integration for real-time payment verification
* Test and Live mode support
* Transaction management and logging
* Refund support
* Split payment support
* Recurring payment support
* Multi-company compatible
* Mobile responsive payment form

Supported Payment Methods:
- Credit/Debit Cards (Visa, Mastercard, Verve)
- Bank Transfer
- USSD
- Mobile Money (MTN, Vodafone, etc.)
- Bank Account
- MPESA, Ghana Mobile Money, Rwanda Mobile Money, etc.

Supported Countries & Currencies:
- Nigeria (NGN)
- Ghana (GHS)
- Kenya (KES)
- South Africa (ZAR)
- Uganda (UGX)
- Tanzania (TZS)
- And many more...
""",
    'author': 'Tech Joe',
    'website': 'ayanfiscoss@gmail.com',
    'license': 'OPL-1',
    'category': 'Accounting/Payment Acquirers',
    'version': '18.0.1.0.0',
    'depends': ['payment'],
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_flutterwave_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_flutterwave/static/src/js/payment_form.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 99.00,
    'currency': 'USD',
    'support': 'ayanfiscoss@gmail.com',
    # 'live_test_url': '',
}