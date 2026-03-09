{
    'name': 'Vehicle Dealership Management',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Complete standalone vehicle dealership management - no additional modules required',
    'description': """
        Vehicle Dealership Management
        ===============================
        Complete solution for managing vehicle dealerships including:

        Features:
        ---------
        * Vehicle Inventory Management
        * Vehicle Sales & Purchase Management
        * Service & Maintenance Tracking
        * Vehicle Inspection Records
        * Customer Management & CRM Integration
        * Advanced Reporting & Analytics
        * Multi-Brand & Model Support
        * Document Management
        * Email Notifications
        * Service Appointment Scheduling
        * Vehicle History Tracking
        * Sales Commission Tracking
        * Trade-In Management
        * Finance & Loan Integration Ready
    """,
    'author': 'Tech Joe',
    'license': 'OPL-1',
    'price': 150.00,
    'currency': 'USD',
    'depends': ['base', 'mail', 'sale_management', 'purchase', 'stock', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/email_templates.xml',
        'views/actions.xml',
        'views/menu_views.xml',
        'views/vehicle_brand_views.xml',
        'views/vehicle_model_views.xml',
        'views/vehicle_views.xml',
        'views/vehicle_sale_views.xml',
        'views/vehicle_purchase_views.xml',
        'views/vehicle_service_views.xml',
        'views/vehicle_inspection_views.xml',
        'views/res_partner_views.xml',
        'report/vehicle_sale_report.xml',
        'report/vehicle_inspection_report.xml',
        'wizards/vehicle_mass_update_wizard.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}