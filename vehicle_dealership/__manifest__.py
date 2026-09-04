{
    'name': 'Vehicle Dealership Management',
    'version': '18.0.1.2.0',
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
        * Sales Commission Tracking (tiered rules by margin, condition, salesperson)
        * Trade-In Management
        * Finance & Loan Integration Ready (amortization schedule included)
        * Customer Portal Access (read-only view of purchases, warranty & service history)
        * Guided Setup Wizard
        * Sample Demo Data
    """,
    'author': 'Tech Joe',
    'license': 'OPL-1',
    'price': 150.00,
    'currency': 'USD',
    'depends': ['base', 'mail', 'portal', 'sale_management', 'purchase', 'stock', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/email_templates.xml',
        'views/actions.xml',
        'views/vehicle_lot_views.xml',
        'views/vehicle_history_views.xml',
        'views/vehicle_commission_rule_views.xml',
        'wizards/vehicle_onboarding_wizard.xml',
        'views/menu_views.xml',
        'views/vehicle_brand_views.xml',
        'views/vehicle_model_views.xml',
        'views/vehicle_views.xml',
        'views/vehicle_sale_views.xml',
        'views/vehicle_purchase_views.xml',
        'views/vehicle_service_views.xml',
        'views/vehicle_inspection_views.xml',
        'views/res_partner_views.xml',
        'views/portal_templates.xml',
        'report/vehicle_sale_report.xml',
        'report/vehicle_inspection_report.xml',
        'wizards/vehicle_mass_update_wizard.xml',
        'wizards/vehicle_loan_amortization_wizard.xml',
        'data/cron.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}