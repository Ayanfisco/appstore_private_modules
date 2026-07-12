{
    'name': 'Paystack Payment Provider',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Payment Provider: Paystack Implementation for African Markets',
    'description': """
    Paystack Payment Provider for Odoo 18
    =====================================
    Accept payments via Paystack - Africa's leading payment gateway

    Features:
    * Support for Nigerian Naira (NGN), Ghanaian Cedi (GHS), South African Rand (ZAR), Kenyan Shilling (KES)
    * Card payments (Visa, Mastercard, Verve)
    * Bank transfers and USSD payments
    * Mobile money integration
    * Instant settlement options
    * PCI-DSS Level 1 compliant
    * Webhook support for real-time payment notifications
    """,
    'author': 'Tech Joe',
    'depends': ['payment'],
    'data': [
        'views/payment_paystack_templates.xml',
        'views/payment_provider_views.xml',
        'data/payment_provider_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_paystack_tech/static/src/js/**/*',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'price': 13.00,
    'currency': 'usd',
    'license': 'LGPL-3',
}