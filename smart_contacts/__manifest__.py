# -*- coding: utf-8 -*-
{
    'name': 'Smart Contacts - Organised by Role',
    'version': '18.0.1.0.0',
    'summary': 'Replace cluttered Contacts with role-based menus: Customers, Vendors, Employees & more',
    'description': """
Smart Contacts replaces the default Odoo Contacts app with an organised,
role-based contact management system. Enforces correct contact types across
Sales, Purchase, Invoices, Bills, and Payments.
    """,
    'author': 'Tech Joe',
    'category': 'Sales/CRM',
    'depends': [
        'base',
        'contacts',
        'sale_management',
        'sale',
        'purchase',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/smart_contacts_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'smart_contacts/static/src/css/smart_contacts.css',
            'smart_contacts/static/src/js/role_toggle.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
