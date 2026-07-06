# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta


class ClinicAppointment(models.Model):
    _name = 'clinic.appointment'
    _description = 'Patient Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'appointment_date desc'

    name = fields.Char(string='Appointment Ref', readonly=True, copy=False, default='New')
    patient_id = fields.Many2one('clinic.patient', string='Patient', required=True, tracking=True, index=True)
    doctor_id = fields.Many2one('clinic.doctor', string='Doctor', required=True, tracking=True, index=True)
    department_id = fields.Many2one('clinic.department', string='Department',
                                    related='doctor_id.department', store=True)
    appointment_date = fields.Datetime(string='Appointment Date & Time', required=True, tracking=True)
    end_date = fields.Datetime(string='End Time', compute='_compute_end_date', store=True)
    duration = fields.Integer(string='Duration (min)', default=20)

    appointment_type = fields.Selection([
        ('new', 'New Patient'),
        ('follow_up', 'Follow-Up'),
        ('emergency', 'Emergency'),
        ('routine', 'Routine Check-Up'),
        ('procedure', 'Procedure'),
    ], string='Appointment Type', default='new', required=True)

    priority = fields.Selection([
        ('0', 'Normal'), ('1', 'Urgent'), ('2', 'Critical'),
    ], string='Priority', default='0')

    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], string='Status', default='scheduled', tracking=True)

    chief_complaint = fields.Text(string='Reason / Chief Complaint')
    notes = fields.Text(string='Notes')

    consultation_id = fields.Many2one('clinic.consultation', string='Consultation', readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    invoice_state = fields.Selection(related='invoice_id.payment_state', string='Payment State', store=True)

    color = fields.Integer(compute='_compute_color', store=True)

    # ─── Compute ─────────────────────────────────────────────────────────────────
    @api.depends('appointment_date', 'duration')
    def _compute_end_date(self):
        for rec in self:
            if rec.appointment_date:
                rec.end_date = rec.appointment_date + timedelta(minutes=rec.duration or 20)
            else:
                rec.end_date = False

    @api.depends('state', 'priority')
    def _compute_color(self):
        color_map = {
            'scheduled': 1, 'confirmed': 3, 'in_progress': 4,
            'done': 10, 'cancelled': 9, 'no_show': 8,
        }
        for rec in self:
            rec.color = color_map.get(rec.state, 0)

    # ─── ORM ────────────────────────────────────────────────────────────────────
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('clinic.appointment') or 'New'
        return super().create(vals)

    @api.constrains('appointment_date')
    def _check_appointment_date(self):
        for rec in self:
            if rec.appointment_date and rec.appointment_date < fields.Datetime.now():
                if rec.state == 'scheduled':
                    pass  # Allow past dates if already saved

    # ─── Workflow ────────────────────────────────────────────────────────────────
    def action_confirm(self):
        self.state = 'confirmed'

    def action_start(self):
        self.state = 'in_progress'

    def action_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_no_show(self):
        self.state = 'no_show'

    def action_reschedule(self):
        self.state = 'scheduled'

    def action_create_consultation(self):
        self.ensure_one()
        if self.consultation_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'clinic.consultation',
                'res_id': self.consultation_id.id,
                'view_mode': 'form',
            }
        consultation = self.env['clinic.consultation'].create({
            'patient_id': self.patient_id.id,
            'doctor_id': self.doctor_id.id,
            'appointment_id': self.id,
            'consultation_date': self.appointment_date,
            'chief_complaint': self.chief_complaint,
        })
        self.consultation_id = consultation.id
        self.state = 'in_progress'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clinic.consultation',
            'res_id': consultation.id,
            'view_mode': 'form',
        }

    def action_create_invoice(self):
        self.ensure_one()
        doctor = self.doctor_id
        fee = doctor.consultation_fee or 0.0
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self._get_or_create_partner(),
            'invoice_line_ids': [(0, 0, {
                'name': f'Consultation Fee - Dr. {doctor.name} ({self.name})',
                'quantity': 1,
                'price_unit': fee,
            })],
        })
        self.invoice_id = invoice.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    def _get_or_create_partner(self):
        patient = self.patient_id
        partner = self.env['res.partner'].search([('name', '=', patient.name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': patient.name,
                'phone': patient.phone,
                'email': patient.email,
            })
        return partner.id
