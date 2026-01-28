from odoo import models, fields, api


class EducoreCourse(models.Model):
    _name = 'educore.course'
    _description = 'Course Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Course Name', required=True, tracking=True)
    code = fields.Char(string='Course Code', required=True, tracking=True)
    description = fields.Text(string='Description')
    credits = fields.Integer(string='Credits', tracking=True)
    duration_hours = fields.Integer(string='Duration (Hours)', tracking=True)
    teacher_id = fields.Many2one('educore.teacher', string='Teacher', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived')
    ], string='Status', default='draft', tracking=True)

    # Relations
    enrollment_ids = fields.One2many('educore.enrollment', 'course_id', string='Enrollments')
    exam_ids = fields.One2many('educore.exam', 'course_id', string='Exams')
    timetable_ids = fields.One2many('educore.timetable', 'course_id', string='Timetable')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Course Code must be unique!')
    ]

    def action_activate(self):
        self.write({'state': 'active'})

    def action_archive(self):
        self.write({'state': 'archived'})
