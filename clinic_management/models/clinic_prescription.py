# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ClinicPrescription(models.Model):
    _name = 'clinic.prescription'
    _description = 'Medical Prescription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'prescription_date desc'

    name = fields.Char(string='Prescription Ref', readonly=True, copy=False, default='New')
    patient_id = fields.Many2one('clinic.patient', string='Patient', required=True, tracking=True, index=True)
    doctor_id = fields.Many2one('clinic.doctor', string='Prescribing Doctor', required=True, tracking=True)
    consultation_id = fields.Many2one('clinic.consultation', string='Consultation')
    prescription_date = fields.Date(string='Prescription Date', required=True, default=fields.Date.today)
    valid_until = fields.Date(string='Valid Until')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('dispensed', 'Dispensed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    diagnosis = fields.Char(string='Diagnosis / Indication')
    notes = fields.Text(string='Instructions to Patient')

    line_ids = fields.One2many('clinic.prescription.line', 'prescription_id', string='Medications')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('clinic.prescription') or 'New'
        return super().create(vals)

    def action_issue(self):
        self.state = 'issued'

    def action_dispense(self):
        self.state = 'dispensed'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_print(self):
        return self.env.ref('clinic_management.action_report_prescription').report_action(self)


class ClinicPrescriptionLine(models.Model):
    _name = 'clinic.prescription.line'
    _description = 'Prescription Line (Medication)'
    _rec_name = 'medication_name'

    prescription_id = fields.Many2one('clinic.prescription', string='Prescription', ondelete='cascade')
    medication_name = fields.Char(string='Medication / Drug Name', required=True)
    dosage = fields.Char(string='Dosage (e.g. 500mg)')
    route = fields.Selection([
        ('oral', 'Oral'), ('iv', 'Intravenous'), ('im', 'Intramuscular'),
        ('topical', 'Topical'), ('sublingual', 'Sublingual'), ('inhaled', 'Inhaled'),
        ('rectal', 'Rectal'), ('other', 'Other'),
    ], string='Route', default='oral')
    frequency = fields.Char(string='Frequency (e.g. twice daily)')
    duration = fields.Char(string='Duration (e.g. 7 days)')
    quantity = fields.Float(string='Quantity', default=1.0)
    refills = fields.Integer(string='Refills Allowed', default=0)
    instructions = fields.Text(string='Special Instructions')
    product_id = fields.Many2one('product.product', string='Linked Product (Pharmacy)', domain=[('type', '=', 'consu')])
