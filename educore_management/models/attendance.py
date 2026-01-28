from odoo import models, fields, api

class EducoreAttendance(models.Model):
    _name = 'educore.attendance'
    _description = 'Student Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    student_id = fields.Many2one('educore.student', string='Student', required=True, tracking=True, ondelete='cascade')
    class_id = fields.Many2one('educore.class', string='Class', required=True, tracking=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today, tracking=True)
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused')
    ], string='Status', required=True, default='present', tracking=True)
    remarks = fields.Text(string='Remarks')

    _sql_constraints = [
        ('unique_attendance', 'unique(student_id, date)', 'Attendance already marked for this student on this date!')
    ]