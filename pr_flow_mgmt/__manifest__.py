{
    'name': 'Purchase Requisition Flow Management',
    'version': '19.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Comprehensive purchase requisition workflow with multi-level approvals',
    'description': """
Purchase Requisition Flow Management
=====================================

A comprehensive and flexible purchase requisition management system for Odoo 18.

Key Features:
-------------
* Multi-level approval workflow (configurable up to 5 levels)
* Department-based requisition management
* Product line management with detailed specifications
* Automatic purchase order creation from approved requisitions
* Email notifications at each approval stage
* Comprehensive reporting and analytics
* Budget tracking and validation
* Vendor selection and comparison
* Integration with inventory and purchase modules
* User-friendly interface with status tracking
* Requisition history and audit trail

Workflow:
---------
1. Draft - Requisition creation
2. Submitted - Awaiting department approval
3. Department Approved - Awaiting manager approval
4. Manager Approved - Awaiting final approval
5. Approved - Ready for PO creation
6. Done - Purchase orders created
7. Cancelled - Rejected or cancelled

Security:
---------
* Requisition User - Can create and submit requisitions
* Requisition Manager - Can approve department level
* Requisition Director - Can give final approval
* Requisition Admin - Full access to all features

This module is designed for Odoo 19 with modern syntax and best practices.
    """,
    'author': 'Tech Joe',
    'website': 'ayanfiscoss@gmail.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'purchase',
        'stock',
        'hr',
        'product',
    ],
    'data': [
        # Security
        'security/pr_flow_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence_data.xml',
        'data/email_template_data.xml',

        # Views (order matters - load in sequence)
        'views/purchase_requisition_line_views.xml',
        'views/purchase_requisition_views.xml',
        'views/res_config_settings_views.xml',
        'views/pr_reject_wizard_views.xml',
        'views/menu_views.xml',

        # Reports
        'report/purchase_requisition_report_template.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 122.00,
    'currency': 'USD',
}