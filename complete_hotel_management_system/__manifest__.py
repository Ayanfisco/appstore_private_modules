{
    'name': 'Complete Hotel Management System',
    'version': '18.0.3.0.0',
    'category': 'Services/Hotel',
    'summary': 'Complete Hotel Management - Rooms, Reservations, Guests, Housekeeping, Website Booking & PMS',
    'description': """
        Complete Hotel Management System
        =================================

        Professional all-in-one hotel management solution with:

        **Core Features:**
        * Advanced Room Management (Types, Categories, Amenities)
        * Complete Guest Profile Management with History
        * Smart Reservation & Booking System
        * Streamlined Check-in / Check-out Wizards
        * Housekeeping Task Management & Tracking
        * Service Management (Room Service, Laundry, Spa, etc.)
        * Integrated Invoicing & Payment Processing
        * Comprehensive Reports & Analytics
        * Automated Reservation Confirmation Emails
        * Multi-property Support

        **Advanced Capabilities:**
        * Website Self-Service Room Search & Booking Requests
        * Seasonal / Date-Range Pricing per Room Type
        * Automated Post-Stay Guest Feedback Emails
        * Real-time Room Availability Tracking
        * Guest History & Preferences
        * VIP Guest Management
        * Damage Tracking & Room Inspection
        * Calendar View for Reservations
        * Portal Access for Guests
        * Multi-currency Support
        * Activity & Task Management

        **Perfect For:**
        Hotels, Resorts, Hostels, Vacation Rentals, B&Bs, Boutique Hotels

        **Integrations:**
        Seamlessly integrates with Odoo Accounting, Sales, and CRM modules.
    """,
    'author': 'Tech Joe',
    'website': 'https://techjoe.shop/',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'account',
        'portal',
        'website',
    ],
    'data': [
        # Security
        'security/hotel_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/hotel_sequence.xml',
        'data/hotel_data.xml',
        'data/mail_template.xml',

        # Views
        'views/hotel_property_views.xml',
        'views/hotel_room_type_views.xml',
        'views/hotel_room_views.xml',
        'views/hotel_amenity_views.xml',
        'views/hotel_guest_views.xml',
        'views/hotel_reservation_views.xml',
        'views/hotel_service_views.xml',
        'views/hotel_service_line_views.xml',
        'views/hotel_housekeeping_views.xml',
        'views/hotel_report_views.xml',
        'views/website_templates.xml',

        # Reports
        'reports/hotel_reports.xml',
        'reports/reservation_report_template.xml',

        # Wizards
        'wizards/hotel_checkin_wizard_views.xml',
        'wizards/hotel_checkout_wizard_views.xml',
        'views/hotel_menus.xml',
    ],
    'demo': [
        'demo/hotel_demo.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 199.00,
    'currency': 'USD',
}
