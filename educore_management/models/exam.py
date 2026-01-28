from odoo import models, fields, api


class EducoreExam(models.Model):
    _name = 'educore.exam'
    _description = 'Examination'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Exam Name', required=True, tracking=True)
    course_id = fields.Many2one('educore.course', string='Course', required=True, tracking=True)
    exam_date = fields.Date(string='Exam Date', required=True, tracking=True)
    exam_time = fields.Float(string='Exam Time', tracking=True)
    duration = fields.Float(string='Duration (Hours)', tracking=True)
    total_marks = fields.Float(string='Total Marks', required=True, tracking=True)
    passing_marks = fields.Float(string='Passing Marks', required=True, tracking=True)
    exam_type = fields.Selection([
        ('midterm', 'Midterm'),
        ('final', 'Final'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment')
    ], string='Exam Type', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('conducted', 'Conducted'),
        ('graded', 'Graded')
    ], string='Status', default='draft', tracking=True)

    # Relations
    grade_ids = fields.One2many('educore.grade', 'exam_id', string='Grades')

    def action_schedule(self):
        self.write({'state': 'scheduled'})

    def action_conduct(self):
        self.write({'state': 'conducted'})

    def action_grade(self):
        self.write({'state': 'graded'})