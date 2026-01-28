from odoo import models, fields, api
from odoo.exceptions import ValidationError

class EducoreGrade(models.Model):
    _name = 'educore.grade'
    _description = 'Student Grade'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    student_id = fields.Many2one('educore.student', string='Student', required=True, tracking=True, ondelete='cascade')
    exam_id = fields.Many2one('educore.exam', string='Exam', required=True, tracking=True, ondelete='cascade')
    marks_obtained = fields.Float(string='Marks Obtained', required=True, tracking=True)
    total_marks = fields.Float(string='Total Marks', related='exam_id.total_marks', store=True)
    percentage = fields.Float(string='Percentage', compute='_compute_percentage', store=True)
    grade = fields.Char(string='Grade', compute='_compute_grade', store=True)
    remarks = fields.Text(string='Remarks')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published')
    ], string='Status', default='draft', tracking=True)

    @api.depends('marks_obtained', 'total_marks')
    def _compute_percentage(self):
        for record in self:
            if record.total_marks > 0:
                record.percentage = (record.marks_obtained / record.total_marks) * 100
            else:
                record.percentage = 0

    @api.depends('percentage')
    def _compute_grade(self):
        for record in self:
            percentage = record.percentage
            if percentage >= 90:
                record.grade = 'A+'
            elif percentage >= 80:
                record.grade = 'A'
            elif percentage >= 70:
                record.grade = 'B'
            elif percentage >= 60:
                record.grade = 'C'
            elif percentage >= 50:
                record.grade = 'D'
            else:
                record.grade = 'F'

    @api.constrains('marks_obtained', 'total_marks')
    def _check_marks(self):
        for record in self:
            if record.marks_obtained > record.total_marks:
                raise ValidationError('Marks obtained cannot be greater than total marks!')

    def action_publish(self):
        self.write({'state': 'published'})
