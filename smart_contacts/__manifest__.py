# -*- coding: utf-8 -*-
{
    'name': 'Smart Contacts — Organised by Role',
    'version': '18.0.1.0.0',
    'summary': 'Replace cluttered Contacts with role-based menus: Customers, Vendors, Employees & more',
    'description': """
Smart Contacts replaces the default Odoo Contacts app with an organised,
role-based contact management system.

Features:
- All Contacts menu listed FIRST
- Dedicated menus: Customers, Vendors, Employees, Business Partners
- Role toggle buttons on every contact form (multi-role support)
- Sales app shows only Customers; Purchase app shows only Vendors
- Hides the default Contacts app to eliminate duplication
    """,
    'author': 'Smart Contacts',
    'category': 'Sales/CRM',
    'depends': ['base', 'contacts', 'sale_management', 'sale', 'purchase'],
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
    'price': 9.99,
    'currency': 'USD',
}
