{
    'name': 'Employee Self-Service Portal',
    'version': '19.0.2.0.0',
    'category': 'Human Resources/Employees',
    'summary': 'Empower your workforce with a centralized, mobile-responsive HR portal for leave requests, expense submissions, payslip downloads, and profile updates.',
    'description': """
Employee Self-Service Portal
=============================

A seamless frontend application built on native architecture that allows distributed workforces, remote employees, and deskless staff to manage routine HR requests from any browser or phone.

Optimizes internal administrative workflows by extending personal HR tracking to the secure standard web portal layer, lowering overall manual backend data entry.

What employees can do
---------------------
📋  Dashboard         — Quick overview: leave balance, pending requests, next payslip
🏖️  Time Off          — Request leave, check balances, track approval status
💰  Expenses          — Submit expense claims with description & amount, track status
🧾  Payslips          — View & download payslips (PDF) for the last 12 months
👤  My Profile        — Update phone, address, emergency contact, profile photo
📄  Documents         — View personal HR documents shared by HR

What HR / Admins can do
-----------------------
🔑  One-click "Create Portal User" button on the employee form
📧  Auto-send portal invitation email to new portal employees
✅  Approve/reject leave and expense requests as usual in the backend
🔒  Strict record-level isolation — employees can only see their own data

Technical features
------------------
* Odoo 19 compliant (uses modern views, configurations, and field structures)
* Robust security — all portal routes use auth='user' with explicit employee-ownership guards
* Comprehensive system design — fully operational with standard Community and Enterprise environments
* Fully modular design depending on core base sets: hr, hr_holidays, hr_expense, portal, mail
* Scalable QWeb layouts cleanly inheriting from portal.portal_layout
* Responsive frontend implementation utilising core Bootstrap components
    """,
    'author': 'Tech Joe',
    'website': 'https://techjoe.shop/',
    'license': 'OPL-1',
    'depends': [
        'hr',
        'hr_holidays',
        'hr_expense',
        'portal',
        'mail',
        'base_setup',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        # 'data/mail_template.xml',
        'views/hr_employee_views.xml',
        'views/portal_templates.xml',
        'views/res_config_settings_views.xml',
        # 'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'employee_self_service/static/src/css/ess_portal.css',
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 119.99,
    'currency': 'EUR',
    'support': 'ayanfiscoss@gmail.com',
}
