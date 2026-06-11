{
    'name': 'Employee Self-Service Portal',
    'version': '18.0.3.0.0',
    'category': 'Human Resources/Employees',
    'summary': 'Give every employee a self-service portal — leave requests, '
               'expense submissions, payslip downloads, profile updates, and '
               'personal documents, all from any browser or phone.',
    'description': """
Employee Self-Service Portal
=============================

A complete self-service portal that lets your employees manage their own HR
activities from any browser or phone, no extra apps, no extra logins to
remember.

Perfect for companies who want to reduce HR admin overhead and give staff
direct, secure access to their own HR information through Odoo's portal.

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
* Odoo 18 v18 compliant (no attrs, list not tree, app/block/setting in config)
* All portal routes use auth='user' with employee-ownership guard
* Works with Odoo Community AND Enterprise
* Depends only on: hr, hr_holidays, hr_expense, portal, mail
* Clean QWeb portal templates extending portal.portal_layout
* Responsive design with Bootstrap 5 (already in Odoo 18)

Note on user licensing
-----------------------
This module uses Odoo's standard portal access groups. Whether portal-based
employee accounts count toward your Odoo subscription's user count depends
on your subscription terms; we recommend confirming with Odoo or your Odoo
partner for deployments with a large number of employees.
    """,
    'author': 'Tech Joe',
    'website': '',
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