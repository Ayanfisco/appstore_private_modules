# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ClinicConsultation(models.Model):
    _name = 'clinic.consultation'
    _description = 'Medical Consultation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'consultation_date desc'

    name = fields.Char(string='Consultation Ref', readonly=True, copy=False, default='New')
    patient_id = fields.Many2one('clinic.patient', string='Patient', required=True, tracking=True, index=True)
    doctor_id = fields.Many2one('clinic.doctor', string='Doctor', required=True, tracking=True)
    appointment_id = fields.Many2one('clinic.appointment', string='Appointment')
    consultation_date = fields.Datetime(string='Consultation Date', required=True, default=fields.Datetime.now)

    # ─── Clinical Notes ──────────────────────────────────────────────────────────
    chief_complaint = fields.Text(string='Chief Complaint', required=True)
    history_of_illness = fields.Text(string='History of Present Illness')
    past_medical_history = fields.Text(string='Past Medical History')
    physical_examination = fields.Text(string='Physical Examination Findings')
    systems_review = fields.Text(string='Systems Review')

    # ─── Diagnosis ───────────────────────────────────────────────────────────────
    provisional_diagnosis = fields.Char(string='Provisional Diagnosis')
    final_diagnosis = fields.Char(string='Final Diagnosis', tracking=True)
    icd10_code = fields.Char(string='ICD-10 Code')
    severity = fields.Selection([
        ('mild', 'Mild'), ('moderate', 'Moderate'), ('severe', 'Severe'), ('critical', 'Critical'),
    ], string='Severity')

    # ─── Plan ────────────────────────────────────────────────────────────────────
    treatment_plan = fields.Text(string='Treatment Plan')
    clinical_notes = fields.Text(string='Additional Clinical Notes')
    follow_up_date = fields.Date(string='Next Follow-Up Date')
    follow_up_notes = fields.Text(string='Follow-Up Instructions')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # ─── Relational ──────────────────────────────────────────────────────────────
    vital_ids = fields.One2many('clinic.vital.signs', 'consultation_id', string='Vital Signs')
    prescription_ids = fields.One2many('clinic.prescription', 'consultation_id', string='Prescriptions')
    prescription_count = fields.Integer(compute='_compute_prescription_count')
    lab_test_ids = fields.One2many('clinic.lab.test', 'consultation_id', string='Lab Tests')
    lab_test_count = fields.Integer(compute='_compute_lab_count')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('clinic.consultation') or 'New'
        return super().create(vals)

    def _compute_prescription_count(self):
        for rec in self:
            rec.prescription_count = len(rec.prescription_ids)

    def _compute_lab_count(self):
        for rec in self:
            rec.lab_test_count = len(rec.lab_test_ids)

    def action_start(self):
        self.state = 'in_progress'

    def action_done(self):
        self.state = 'done'
        if self.appointment_id:
            self.appointment_id.state = 'done'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_create_prescription(self):
        prescription = self.env['clinic.prescription'].create({
            'patient_id': self.patient_id.id,
            'doctor_id': self.doctor_id.id,
            'consultation_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clinic.prescription',
            'res_id': prescription.id,
            'view_mode': 'form',
        }

    def action_create_lab_request(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Request Lab Test',
            'res_model': 'clinic.lab.test',
            'view_mode': 'form',
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_doctor_id': self.doctor_id.id,
                'default_consultation_id': self.id,
            },
            'target': 'new',
        }
