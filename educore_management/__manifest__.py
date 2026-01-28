{
    'name': 'EduCore Management System',
    'version': '18.0.1.0.0',
    'category': 'Education',
    'summary': 'Complete School Management System for Odoo 18',
    'description': """
        EduCore Management System
        =========================
        Comprehensive school management solution including:
        * Student Management
        * Teacher Management
        * Course & Class Management
        * Enrollment & Attendance
        * Exam & Grade Management
        * Fee Management
        * Timetable Scheduling
    """,
    'author': 'Tech Joe',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'reports/report.xml',
        'reports/student_report_template.xml',
        'views/student_views.xml',
        'views/teacher_views.xml',
        'views/course_views.xml',
        'views/class_room_views.xml',
        'views/enrollment_views.xml',
        'views/attendance_views.xml',
        'views/exam_views.xml',
        'views/grade_views.xml',
        'views/fee_views.xml',
        'views/timetable_views.xml',
        'views/menu_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
