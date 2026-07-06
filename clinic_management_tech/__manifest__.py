# -*- coding: utf-8 -*-
{
    'name': 'MediCore — Clinic & Healthcare Management',
    'version': '18.0.1.0.0',
    'category': 'Healthcare',
    'summary': 'Complete clinic management: patient portal, online appointment booking, consultations, prescriptions, lab tests, billing & pharmacy.',
    'description': """
MediCore — Clinic & Healthcare Management
==========================================

A full-featured healthcare module for clinics, hospitals, and private practices.
Includes a **patient-facing website portal** for online appointment booking, medical history access, and invoice tracking.

Key Features
------------
* **Patient Portal** — Patients log in via Odoo portal to view appointments, prescriptions, lab results, and invoices.
* **Online Appointment Booking** — Public-facing booking form with doctor and time-slot selection.
* **Patient Management** — Full patient profile: demographics, blood group, allergies, chronic conditions, insurance info, and unique patient ID.
* **Appointments** — Calendar-based scheduling with doctor availability and status workflow.
* **Consultations** — Detailed clinical notes (Chief Complaint, History, Examination, Diagnosis, ICD-10, Treatment Plan).
* **Prescriptions** — Medication prescriptions linked to consultations with printable PDF.
* **Lab Tests** — Request, track, and record lab investigations. Link results to consultations.
* **Vital Signs** — Record BP, pulse, temperature, weight, height, BMI, O2 saturation per visit.
* **Billing & Invoicing** — Auto-generate invoices. Integrates with Odoo Accounting.
* **Pharmacy** — Dispensing linked to prescriptions with stock deduction.
* **Doctor Management** — Profiles with specializations, qualifications, and schedules.
* **Security** — Role-based access: Administrator, Doctor, Nurse/Receptionist, Lab Technician, Pharmacist.
* **Demo Data** — Pre-loaded sample patients, doctors, and appointments.
    """,
    'author': 'Tech Joe',
    'license': 'OPL-1',
    'price': 149.99,
    'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'product',
        'account',
        'stock',
        'calendar',
        'web',
        'portal',
        'website',
        'auth_signup',
    ],
    'data': [
        # Security
        'security/clinic_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/clinic_sequence_data.xml',
        'data/clinic_data.xml',

        # Backend Views
        'views/clinic_patient_views.xml',
        'views/clinic_doctor_views.xml',
        'views/clinic_appointment_views.xml',
        'views/clinic_consultation_views.xml',
        'views/clinic_prescription_views.xml',
        'views/clinic_lab_test_views.xml',
        'views/clinic_vital_signs_views.xml',
        'views/clinic_billing_views.xml',
        'views/clinic_pharmacy_views.xml',
        'views/clinic_menu_views.xml',

        # Website / Portal Views
        'views/website/portal_templates.xml',
        'views/website/website_appointment_templates.xml',

        # Reports
        'reports/clinic_patient_report.xml',
        'reports/clinic_prescription_report.xml',
        'reports/clinic_lab_report.xml',
        'reports/clinic_invoice_report.xml',
    ],
    'demo': [
        'demo/clinic_demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'clinic_management_tech/static/src/css/clinic_style.css',
        ],
        'web.assets_frontend': [
            'clinic_management_tech/static/src/css/clinic_portal.css',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
