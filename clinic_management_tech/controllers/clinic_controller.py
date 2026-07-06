# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessError, MissingError, ValidationError
from datetime import datetime, date, timedelta

from odoo.addons.portal.controllers.portal import CustomerPortal


class ClinicCustomerPortal(CustomerPortal):
    """Send patients straight to their MediCore dashboard on login.

    Odoo's default portal redirects every portal user to /my after
    authentication. If the logged-in user is linked to a clinic.patient
    record we skip the generic portal home and land them on /my/health
    directly. Portal users with no linked patient (or regular, non-clinic
    portal contacts) keep seeing the normal portal home untouched.
    """

    @http.route(['/my', '/my/home'], type='http', auth='user', website=True)
    def home(self, **kw):
        patient = request.env['clinic.patient'].sudo().search(
            [('partner_id', '=', request.env.user.partner_id.id)], limit=1
        )
        if patient:
            return request.redirect('/my/health')
        return super().home(**kw)


class ClinicController(http.Controller):

    # ═══════════════════════════════════════════════════════════════════════════
    # INTERNAL JSON APIs (backend widgets)
    # ═══════════════════════════════════════════════════════════════════════════

    @http.route('/clinic/patient/search', type='json', auth='user')
    def search_patient(self, query='', limit=10):
        """Quick patient search for backend integrations."""
        patients = request.env['clinic.patient'].search([
            '|',
            ('name', 'ilike', query),
            ('patient_id', 'ilike', query),
        ], limit=limit)
        return [{
            'id': p.id,
            'patient_id': p.patient_id,
            'name': p.name,
            'age': p.age,
            'gender': p.gender,
            'blood_group': p.blood_group,
            'phone': p.phone,
            'allergies': p.allergies,
        } for p in patients]

    @http.route('/clinic/appointment/today', type='json', auth='user')
    def today_appointments(self):
        """Return today's appointments for dashboard widgets."""
        today = date.today()
        appointments = request.env['clinic.appointment'].search([
            ('appointment_date', '>=', f'{today} 00:00:00'),
            ('appointment_date', '<=', f'{today} 23:59:59'),
        ], order='appointment_date asc')
        return [{
            'id': a.id,
            'name': a.name,
            'patient': a.patient_id.name,
            'doctor': a.doctor_id.name,
            'time': str(a.appointment_date),
            'state': a.state,
            'type': a.appointment_type,
        } for a in appointments]

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC WEBSITE — Appointment Booking
    # ═══════════════════════════════════════════════════════════════════════════

    @http.route('/appointment', type='http', auth='public', website=True)
    def appointment_home(self, **kwargs):
        """Public appointment booking landing page."""
        doctors = request.env['clinic.doctor'].sudo().search([
            ('state', '=', 'active')
        ])
        return request.render('clinic_management_tech.website_appointment_home', {
            'doctors': doctors,
        })

    @http.route('/appointment/book', type='http', auth='public', website=True, methods=['GET', 'POST'])
    def appointment_book(self, **post):
        """Handle appointment booking form — GET renders form, POST saves it."""
        doctors = request.env['clinic.doctor'].sudo().search([('state', '=', 'active')])

        if request.httprequest.method == 'POST':
            error = {}
            name = post.get('name', '').strip()
            email = post.get('email', '').strip()
            phone = post.get('phone', '').strip()
            doctor_id = int(post.get('doctor_id', 0))
            appointment_date_str = post.get('appointment_date', '')
            reason = post.get('reason', '').strip()
            dob_str = post.get('date_of_birth', '').strip()
            gender = post.get('gender', '').strip()

            if not name:
                error['name'] = 'Full name is required.'
            if not email:
                error['email'] = 'Email is required.'
            if not doctor_id:
                error['doctor_id'] = 'Please select a doctor.'
            if not appointment_date_str:
                error['appointment_date'] = 'Please choose a date and time.'

            patient = request.env['clinic.patient'].sudo().search(
                [('email', '=', email)], limit=1
            )

            date_of_birth = None
            if dob_str:
                try:
                    date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
                    if date_of_birth > date.today():
                        error['date_of_birth'] = 'Date of birth cannot be in the future.'
                except ValueError:
                    error['date_of_birth'] = 'Please enter a valid date.'
            elif not patient:
                # Only require DOB for brand-new patients; returning patients
                # already have a record on file.
                error['date_of_birth'] = 'Date of birth is required.'

            if not gender and not patient:
                error['gender'] = 'Please select a gender.'

            if error:
                return request.render('clinic_management_tech.website_appointment_book', {
                    'doctors': doctors,
                    'error': error,
                    'values': post,
                })

            # Get or create patient
            if not patient:
                patient = request.env['clinic.patient'].sudo().create({
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'gender': gender or 'other',
                    'date_of_birth': date_of_birth,
                    'state': 'active',
                })

            appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%dT%H:%M')
            request.env['clinic.appointment'].sudo().create({
                'patient_id': patient.id,
                'doctor_id': doctor_id,
                'appointment_date': appointment_date,
                'appointment_type': 'new',
                'chief_complaint': reason,
                'state': 'scheduled',
            })

            return request.render('clinic_management_tech.website_appointment_confirm', {
                'patient_name': name,
                'doctor': request.env['clinic.doctor'].sudo().browse(doctor_id),
                'appointment_date': appointment_date,
            })

        return request.render('clinic_management_tech.website_appointment_book', {
            'doctors': doctors,
            'error': {},
            'values': {},
        })

    # ═══════════════════════════════════════════════════════════════════════════
    # PATIENT PORTAL — Read-only access
    # Portal users can VIEW their own records; they cannot write to the system.
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_patient_for_user(self):
        """Return the clinic.patient linked to the current portal user, or False."""
        partner = request.env.user.partner_id
        return request.env['clinic.patient'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1
        )

    def _portal_ensure_patient(self):
        """
        Return the patient, or render the 'no patient' page.
        Usage: patient = self._portal_ensure_patient()
               if isinstance(patient, werkzeug.wrappers.Response): return patient
        """
        patient = self._get_patient_for_user()
        if not patient:
            return request.render('clinic_management_tech.portal_no_patient', {})
        return patient

    @http.route('/my/health', type='http', auth='user', website=True)
    def portal_dashboard(self, **kwargs):
        """Patient portal dashboard — overview of health records (read-only)."""
        patient = self._get_patient_for_user()
        if not patient:
            return request.render('clinic_management_tech.portal_no_patient', {})

        upcoming = request.env['clinic.appointment'].sudo().search([
            ('patient_id', '=', patient.id),
            ('appointment_date', '>=', fields.Datetime.now()),
            ('state', 'not in', ['cancelled', 'no_show']),
        ], order='appointment_date asc', limit=5)

        recent_prescriptions = request.env['clinic.prescription'].sudo().search([
            ('patient_id', '=', patient.id),
        ], order='prescription_date desc', limit=5)

        lab_tests = request.env['clinic.lab.test'].sudo().search([
            ('patient_id', '=', patient.id),
        ], order='request_date desc', limit=5)

        invoices = request.env['account.move'].sudo().search([
            ('partner_id', '=', patient.partner_id.id),
            ('move_type', '=', 'out_invoice'),
        ], order='invoice_date desc', limit=5)

        return request.render('clinic_management_tech.portal_dashboard', {
            'patient': patient,
            'upcoming_appointments': upcoming,
            'recent_prescriptions': recent_prescriptions,
            'lab_tests': lab_tests,
            'invoices': invoices,
        })

    @http.route('/my/health/appointments', type='http', auth='user', website=True)
    def portal_appointments(self, **kwargs):
        """All appointments for the logged-in patient (read-only)."""
        patient = self._get_patient_for_user()
        if not patient:
            return request.render('clinic_management_tech.portal_no_patient', {})

        appointments = request.env['clinic.appointment'].sudo().search([
            ('patient_id', '=', patient.id),
        ], order='appointment_date desc')

        return request.render('clinic_management_tech.portal_appointments', {
            'patient': patient,
            'appointments': appointments,
        })

    @http.route('/my/health/prescriptions', type='http', auth='user', website=True)
    def portal_prescriptions(self, **kwargs):
        """All prescriptions for the logged-in patient (read-only)."""
        patient = self._get_patient_for_user()
        if not patient:
            return request.render('clinic_management_tech.portal_no_patient', {})

        prescriptions = request.env['clinic.prescription'].sudo().search([
            ('patient_id', '=', patient.id),
        ], order='prescription_date desc')

        return request.render('clinic_management_tech.portal_prescriptions', {
            'patient': patient,
            'prescriptions': prescriptions,
        })

    @http.route('/my/health/lab-results', type='http', auth='user', website=True)
    def portal_lab_results(self, **kwargs):
        """All lab test results for the logged-in patient (read-only)."""
        patient = self._get_patient_for_user()
        if not patient:
            return request.render('clinic_management_tech.portal_no_patient', {})

        lab_tests = request.env['clinic.lab.test'].sudo().search([
            ('patient_id', '=', patient.id),
        ], order='request_date desc')

        return request.render('clinic_management_tech.portal_lab_results', {
            'patient': patient,
            'lab_tests': lab_tests,
        })

    @http.route('/my/health/profile', type='http', auth='user', website=True)
    def portal_profile(self, **kwargs):
        """
        Patient profile — read-only view of personal information.
        Patients cannot update their own records. Contact clinic staff for changes.
        """
        patient = self._get_patient_for_user()
        if not patient:
            return request.render('clinic_management_tech.portal_no_patient', {})

        return request.render('clinic_management_tech.portal_profile', {
            'patient': patient,
        })
