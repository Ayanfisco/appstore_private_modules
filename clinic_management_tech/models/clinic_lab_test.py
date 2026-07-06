# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ClinicLabTest(models.Model):
    _name = 'clinic.lab.test'
    _description = 'Laboratory Test'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'request_date desc'

    name = fields.Char(string='Lab Request Ref', readonly=True, copy=False, default='New')
    patient_id = fields.Many2one('clinic.patient', string='Patient', required=True, tracking=True, index=True)
    doctor_id = fields.Many2one('clinic.doctor', string='Requesting Doctor', required=True)
    consultation_id = fields.Many2one('clinic.consultation', string='Consultation')
    lab_technician_id = fields.Many2one('res.users', string='Lab Technician')

    request_date = fields.Datetime(string='Requested On', default=fields.Datetime.now)
    sample_date = fields.Datetime(string='Sample Collected On', tracking=True)
    result_date = fields.Datetime(string='Results Ready On', tracking=True)

    state = fields.Selection([
        ('requested', 'Requested'),
        ('sample_collected', 'Sample Collected'),
        ('in_progress', 'In Progress'),
        ('done', 'Results Ready'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='requested', tracking=True)

    urgency = fields.Selection([
        ('routine', 'Routine'), ('urgent', 'Urgent'), ('stat', 'STAT (Emergency)'),
    ], string='Urgency', default='routine')

    clinical_notes = fields.Text(string='Clinical Information / Reason')
    result_summary = fields.Text(string='Result Summary / Impression')
    attachment_ids = fields.Many2many('ir.attachment', string='Result Attachments')

    line_ids = fields.One2many('clinic.lab.test.line', 'lab_test_id', string='Tests Requested')

    invoice_id = fields.Many2one('account.move', string='Invoice')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('clinic.lab.test') or 'New'
        return super().create(vals)

    def action_collect_sample(self):
        self.write({'state': 'sample_collected', 'sample_date': fields.Datetime.now()})

    def action_start_processing(self):
        self.state = 'in_progress'

    def action_done(self):
        self.write({'state': 'done', 'result_date': fields.Datetime.now()})

    def action_cancel(self):
        self.state = 'cancelled'

    def action_print_report(self):
        return self.env.ref('clinic_management_tech.action_report_lab').report_action(self)


class ClinicLabTestLine(models.Model):
    _name = 'clinic.lab.test.line'
    _description = 'Individual Lab Test'
    _rec_name = 'test_name'

    lab_test_id = fields.Many2one('clinic.lab.test', string='Lab Request', ondelete='cascade')
    test_name = fields.Char(string='Test Name', required=True)
    test_category = fields.Selection([
        ('hematology', 'Hematology'), ('biochemistry', 'Biochemistry'),
        ('microbiology', 'Microbiology'), ('immunology', 'Immunology'),
        ('urinalysis', 'Urinalysis'), ('radiology', 'Radiology'),
        ('pathology', 'Pathology'), ('other', 'Other'),
    ], string='Category', default='biochemistry')
    result_value = fields.Char(string='Result')
    unit = fields.Char(string='Unit (e.g. mg/dL)')
    reference_range = fields.Char(string='Reference Range')
    flag = fields.Selection([
        ('normal', 'Normal'), ('low', 'Low'), ('high', 'High'), ('critical', 'Critical'),
    ], string='Flag')
    price = fields.Float(string='Price')
    notes = fields.Text(string='Notes')


class ClinicLabTestCatalog(models.Model):
    """Pre-defined test catalog for quick selection."""
    _name = 'clinic.lab.test.catalog'
    _description = 'Lab Test Catalog'
    _rec_name = 'name'

    name = fields.Char(string='Test Name', required=True)
    code = fields.Char(string='Test Code')
    category = fields.Selection([
        ('hematology', 'Hematology'), ('biochemistry', 'Biochemistry'),
        ('microbiology', 'Microbiology'), ('immunology', 'Immunology'),
        ('urinalysis', 'Urinalysis'), ('radiology', 'Radiology'),
        ('pathology', 'Pathology'), ('other', 'Other'),
    ], string='Category', required=True, default='biochemistry')
    unit = fields.Char(string='Default Unit')
    reference_range = fields.Char(string='Reference Range')
    price = fields.Float(string='Standard Price')
    turnaround_time = fields.Char(string='Turnaround Time')
    active = fields.Boolean(default=True)
