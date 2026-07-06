# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta


class ClinicAppointmentWizard(models.TransientModel):
    _name = 'clinic.appointment.wizard'
    _description = 'Quick Appointment Booking Wizard'

    patient_id = fields.Many2one('clinic.patient', string='Patient', required=True)
    doctor_id = fields.Many2one('clinic.doctor', string='Doctor', required=True)
    appointment_date = fields.Datetime(string='Date & Time', required=True,
                                        default=lambda self: fields.Datetime.now() + timedelta(hours=1))
    appointment_type = fields.Selection([
        ('new', 'New Patient'),
        ('follow_up', 'Follow-Up'),
        ('emergency', 'Emergency'),
        ('routine', 'Routine Check-Up'),
        ('procedure', 'Procedure'),
    ], string='Type', default='new', required=True)
    chief_complaint = fields.Text(string='Reason / Chief Complaint')
    duration = fields.Integer(string='Duration (min)', default=20)
    notes = fields.Text(string='Additional Notes')

    def action_book(self):
        self.ensure_one()
        appointment = self.env['clinic.appointment'].create({
            'patient_id': self.patient_id.id,
            'doctor_id': self.doctor_id.id,
            'appointment_date': self.appointment_date,
            'appointment_type': self.appointment_type,
            'chief_complaint': self.chief_complaint,
            'duration': self.duration,
            'notes': self.notes,
            'state': 'scheduled',
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clinic.appointment',
            'res_id': appointment.id,
            'view_mode': 'form',
            'target': 'current',
        }
