# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class ClinicPatient(models.Model):
    _name = 'clinic.patient'
    _description = 'Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name asc'

    # ─── Identity ───────────────────────────────────────────────────────────────
    patient_id = fields.Char(
        string='Patient ID', readonly=True, copy=False,
        default='New', tracking=True
    )
    name = fields.Char(string='Full Name', required=True, tracking=True)
    image = fields.Binary(string='Photo', attachment=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender', required=True, tracking=True)
    date_of_birth = fields.Date(string='Date of Birth', required=True)
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A−'),
        ('b+', 'B+'), ('b-', 'B−'),
        ('ab+', 'AB+'), ('ab-', 'AB−'),
        ('o+', 'O+'), ('o-', 'O−'),
    ], string='Blood Group')
    marital_status = fields.Selection([
        ('single', 'Single'), ('married', 'Married'),
        ('divorced', 'Divorced'), ('widowed', 'Widowed'),
    ], string='Marital Status')
    nationality = fields.Many2one('res.country', string='Nationality')

    # ─── Portal / Partner Link ───────────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Related Contact',
        help='Linked res.partner used for portal login and invoicing.',
        tracking=True
    )

    # ─── Contact ─────────────────────────────────────────────────────────────────
    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile / WhatsApp')
    email = fields.Char(string='Email')
    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    zip = fields.Char(string='ZIP')

    # ─── Emergency Contact ───────────────────────────────────────────────────────
    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone')
    emergency_contact_relation = fields.Char(string='Relationship')

    # ─── Medical Info ────────────────────────────────────────────────────────────
    allergies = fields.Text(string='Known Allergies')
    chronic_conditions = fields.Text(string='Chronic Conditions')
    current_medications = fields.Text(string='Current Medications')
    surgical_history = fields.Text(string='Surgical History')
    family_history = fields.Text(string='Family Medical History')

    # ─── Insurance ───────────────────────────────────────────────────────────────
    insurance_provider = fields.Char(string='Insurance Provider')
    insurance_policy_no = fields.Char(string='Policy Number')
    insurance_valid_to = fields.Date(string='Valid Until')

    # ─── Primary Doctor ──────────────────────────────────────────────────────────
    primary_doctor_id = fields.Many2one('clinic.doctor', string='Primary Doctor')

    # ─── Status ──────────────────────────────────────────────────────────────────
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deceased', 'Deceased'),
    ], string='Status', default='active', tracking=True)

    # ─── Relational ──────────────────────────────────────────────────────────────
    appointment_ids = fields.One2many('clinic.appointment', 'patient_id', string='Appointments')
    appointment_count = fields.Integer(compute='_compute_appointment_count', string='Appointments')
    consultation_ids = fields.One2many('clinic.consultation', 'patient_id', string='Consultations')
    consultation_count = fields.Integer(compute='_compute_consultation_count', string='Consultations')
    prescription_ids = fields.One2many('clinic.prescription', 'patient_id', string='Prescriptions')
    lab_test_ids = fields.One2many('clinic.lab.test', 'patient_id', string='Lab Tests')

    # ─── Notes ───────────────────────────────────────────────────────────────────
    notes = fields.Text(string='Internal Notes')

    # ─── Compute ─────────────────────────────────────────────────────────────────
    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.date_of_birth:
                dob = rec.date_of_birth
                rec.age = today.year - dob.year - (
                    (today.month, today.day) < (dob.month, dob.day)
                )
            else:
                rec.age = 0

    def _compute_appointment_count(self):
        for rec in self:
            rec.appointment_count = self.env['clinic.appointment'].search_count(
                [('patient_id', '=', rec.id)]
            )

    def _compute_consultation_count(self):
        for rec in self:
            rec.consultation_count = self.env['clinic.consultation'].search_count(
                [('patient_id', '=', rec.id)]
            )

    # ─── ORM ────────────────────────────────────────────────────────────────────
    @api.model
    def create(self, vals):
        if vals.get('patient_id', 'New') == 'New':
            vals['patient_id'] = self.env['ir.sequence'].next_by_code('clinic.patient') or 'New'
        # Auto-create / link a res.partner for portal access
        if not vals.get('partner_id') and vals.get('email'):
            partner = self.env['res.partner'].search(
                [('email', '=', vals['email'])], limit=1
            )
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': vals.get('name', ''),
                    'email': vals.get('email', ''),
                    'phone': vals.get('phone', ''),
                })
            vals['partner_id'] = partner.id
        return super().create(vals)

    @api.constrains('date_of_birth')
    def _check_dob(self):
        for rec in self:
            if rec.date_of_birth and rec.date_of_birth > date.today():
                raise ValidationError("Date of birth cannot be in the future.")

    # ─── Actions ─────────────────────────────────────────────────────────────────
    def action_view_appointments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,form,calendar',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }

    def action_view_consultations(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Consultations',
            'res_model': 'clinic.consultation',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }

    def action_new_appointment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Appointment',
            'res_model': 'clinic.appointment',
            'view_mode': 'form',
            'context': {'default_patient_id': self.id},
            'target': 'new',
        }

    def action_grant_portal_access(self):
        """Grant portal access to the linked partner."""
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError("No linked contact found. Please set an email for this patient first.")
        portal_group = self.env.ref('base.group_portal')
        self.partner_id.write({'groups_id': [(4, portal_group.id)]})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Portal Access Granted',
                'message': f'{self.name} can now log into the patient portal.',
                'type': 'success',
            }
        }
