# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ClinicDoctor(models.Model):
    _name = 'clinic.doctor'
    _description = 'Doctor / Medical Staff'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name asc'

    # ─── Identity ───────────────────────────────────────────────────────────────
    doctor_id = fields.Char(
        string='Doctor ID', readonly=True, copy=False, default='New')
    name = fields.Char(string='Full Name', required=True, tracking=True)
    image = fields.Binary(string='Photo', attachment=True)
    gender = fields.Selection([
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other'),
    ], string='Gender')

    # ─── Professional ────────────────────────────────────────────────────────────
    specialization = fields.Char(
        string='Specialization', required=True, tracking=True)
    qualification = fields.Char(string='Qualifications (e.g. MBBS, MD)')
    medical_council_no = fields.Char(string='Medical Council Reg. No.')
    years_of_experience = fields.Integer(string='Years of Experience')
    department = fields.Many2one('clinic.department', string='Department')

    # ─── Contact ─────────────────────────────────────────────────────────────────
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')

    # ─── Schedule ────────────────────────────────────────────────────────────────
    available_monday = fields.Boolean(string='Monday', default=True)
    available_tuesday = fields.Boolean(string='Tuesday', default=True)
    available_wednesday = fields.Boolean(string='Wednesday', default=True)
    available_thursday = fields.Boolean(string='Thursday', default=True)
    available_friday = fields.Boolean(string='Friday', default=True)
    available_saturday = fields.Boolean(string='Saturday', default=False)
    available_sunday = fields.Boolean(string='Sunday', default=False)
    start_time = fields.Float(string='Start Time', default=8.0)
    end_time = fields.Float(string='End Time', default=18.0)
    consultation_duration = fields.Integer(
        string='Consultation Duration (min)', default=20)

    # ─── Fees ────────────────────────────────────────────────────────────────────
    consultation_fee = fields.Float(string='Consultation Fee', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)

    # ─── Linked User ─────────────────────────────────────────────────────────────
    user_id = fields.Many2one('res.users', string='Linked Portal User')

    # ─── Status ──────────────────────────────────────────────────────────────────
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('active', 'Active'), ('on_leave', 'On Leave'), ('inactive', 'Inactive'),
    ], default='active', tracking=True, string='Status')

    # ─── Relational ──────────────────────────────────────────────────────────────
    appointment_ids = fields.One2many(
        'clinic.appointment', 'doctor_id', string='Appointments')
    appointment_count = fields.Integer(
        compute='_compute_appointment_count', string='Total Appointments')
    patient_count = fields.Integer(
        compute='_compute_patient_count', string='Unique Patients')

    notes = fields.Text(string='Notes / Bio')

    # ─── Compute ─────────────────────────────────────────────────────────────────
    def _compute_appointment_count(self):
        for rec in self:
            rec.appointment_count = self.env['clinic.appointment'].search_count(
                [('doctor_id', '=', rec.id)]
            )

    def _compute_patient_count(self):
        for rec in self:
            patients = self.env['clinic.appointment'].search(
                [('doctor_id', '=', rec.id)]
            ).mapped('patient_id')
            rec.patient_count = len(set(patients.ids))

    def action_view_appointments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'clinic.appointment',
            'view_mode': 'list,form,calendar',
            'domain': [('doctor_id', '=', self.id)],
            'context': {'default_doctor_id': self.id},
        }

    @api.model
    def create(self, vals):
        if vals.get('doctor_id', 'New') == 'New':
            vals['doctor_id'] = self.env['ir.sequence'].next_by_code(
                'clinic.doctor') or 'New'
        return super().create(vals)


class ClinicDepartment(models.Model):
    _name = 'clinic.department'
    _description = 'Clinical Department'
    _rec_name = 'name'

    name = fields.Char(string='Department Name', required=True)
    code = fields.Char(string='Code')
    head_doctor_id = fields.Many2one(
        'clinic.doctor', string='Head of Department')
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')
