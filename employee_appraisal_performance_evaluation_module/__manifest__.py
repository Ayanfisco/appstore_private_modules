{
    'name': 'Employee Appraisal Management',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Complete Employee Performance Appraisal System',
    'description': """
        Employee Appraisal Management System
        ====================================
        * Create and manage employee appraisals
        * Define appraisal templates with competencies
        * Set goals and track performance
        * Generate appraisal reports
        * Multi-level approval workflow
        * Email notifications
        * Dashboard and analytics
    """,
    'author': 'Tech Joe',
    'website': 'ayanfiscoss@gmail.com',
    'license': 'LGPL-3',
    'depends': ['hr', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/appraisal_data.xml',
        'views/employee_appraisal_views.xml',
        'views/appraisal_template_views.xml',
        'views/appraisal_competency_views.xml',
        'report/appraisal_report_template.xml',
        'views/appraisal_menu.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 99.00,
    'currency': 'USD',
}
