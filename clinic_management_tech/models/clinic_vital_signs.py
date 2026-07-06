# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ClinicVitalSigns(models.Model):
    _name = 'clinic.vital.signs'
    _description = 'Vital Signs Record'
    _rec_name = 'recorded_at'
    _order = 'recorded_at desc'

    consultation_id = fields.Many2one('clinic.consultation', string='Consultation')
    recorded_by = fields.Many2one('res.users', string='Recorded By', default=lambda self: self.env.user)
    recorded_at = fields.Datetime(string='Recorded At', required=True, default=fields.Datetime.now)
    patient_id = fields.Many2one(
        related='consultation_id.patient_id',
        store=True, readonly=True,
    )

    # ─── Vitals ──────────────────────────────────────────────────────────────────
    blood_pressure_systolic = fields.Integer(string='BP Systolic (mmHg)')
    blood_pressure_diastolic = fields.Integer(string='BP Diastolic (mmHg)')
    blood_pressure_display = fields.Char(
        string='Blood Pressure', compute='_compute_bp_display', store=True
    )
    pulse_rate = fields.Integer(string='Pulse Rate (bpm)')
    respiratory_rate = fields.Integer(string='Respiratory Rate (breaths/min)')
    temperature = fields.Float(string='Temperature (°C)')
    spo2 = fields.Float(string='O₂ Saturation (%)')
    weight = fields.Float(string='Weight (kg)')
    height = fields.Float(string='Height (cm)')
    bmi = fields.Float(string='BMI', compute='_compute_bmi', store=True, digits=(5, 2))
    bmi_category = fields.Char(string='BMI Category', compute='_compute_bmi', store=True)
    blood_sugar = fields.Float(string='Blood Sugar (mg/dL)')
    blood_sugar_type = fields.Selection([
        ('fasting', 'Fasting'), ('post_prandial', 'Post-Prandial'), ('random', 'Random'),
    ], string='Blood Sugar Type')

    pain_scale = fields.Selection(
        [(str(i), str(i)) for i in range(11)],
        string='Pain Scale (0–10)'
    )
    gcs_score = fields.Integer(string='GCS Score (3–15)')
    notes = fields.Text(string='Notes / Observations')

    @api.depends('blood_pressure_systolic', 'blood_pressure_diastolic')
    def _compute_bp_display(self):
        for rec in self:
            if rec.blood_pressure_systolic and rec.blood_pressure_diastolic:
                rec.blood_pressure_display = f"{rec.blood_pressure_systolic}/{rec.blood_pressure_diastolic} mmHg"
            else:
                rec.blood_pressure_display = False

    @api.depends('weight', 'height')
    def _compute_bmi(self):
        for rec in self:
            if rec.weight and rec.height:
                h_m = rec.height / 100.0
                bmi = rec.weight / (h_m ** 2)
                rec.bmi = round(bmi, 2)
                if bmi < 18.5:
                    rec.bmi_category = 'Underweight'
                elif bmi < 25:
                    rec.bmi_category = 'Normal'
                elif bmi < 30:
                    rec.bmi_category = 'Overweight'
                else:
                    rec.bmi_category = 'Obese'
            else:
                rec.bmi = 0.0
                rec.bmi_category = ''
