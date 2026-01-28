from odoo import models, fields, api


class EducoreClass(models.Model):
    _name = 'educore.class'
    _description = 'Class Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Class Name', required=True, tracking=True)
    code = fields.Char(string='Class Code', required=True, tracking=True)
    section = fields.Char(string='Section', tracking=True)
    academic_year = fields.Char(string='Academic Year', required=True, tracking=True)
    class_teacher_id = fields.Many2one('educore.teacher', string='Class Teacher', tracking=True)
    room_number = fields.Char(string='Room Number', tracking=True)
    capacity = fields.Integer(string='Capacity', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed')
    ], string='Status', default='draft', tracking=True)

    # Relations
    student_ids = fields.One2many('educore.student', 'class_id', string='Students')
    enrollment_ids = fields.One2many('educore.enrollment', 'class_id', string='Enrollments')
    timetable_ids = fields.One2many('educore.timetable', 'class_id', string='Timetable')

    # Computed
    student_count = fields.Integer(string='Student Count', compute='_compute_student_count', store=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Class Code must be unique!')
    ]

    @api.depends('student_ids')
    def _compute_student_count(self):
        for record in self:
            record.student_count = len(record.student_ids)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_close(self):
        self.write({'state': 'closed'})
