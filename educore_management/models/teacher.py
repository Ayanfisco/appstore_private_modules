from odoo import models, fields, api


class EducoreTeacher(models.Model):
    _name = 'educore.teacher'
    _description = 'Teacher Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'full_name'

    teacher_id = fields.Char(string='Teacher ID', required=True, copy=False, readonly=True, default='New')
    first_name = fields.Char(string='First Name', required=True, tracking=True)
    last_name = fields.Char(string='Last Name', required=True, tracking=True)
    full_name = fields.Char(string='Full Name', compute='_compute_full_name', store=True)
    date_of_birth = fields.Date(string='Date of Birth', tracking=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender', required=True, tracking=True)
    email = fields.Char(string='Email', required=True, tracking=True)
    phone = fields.Char(string='Phone', required=True, tracking=True)
    address = fields.Text(string='Address', tracking=True)
    joining_date = fields.Date(string='Joining Date', default=fields.Date.today, required=True, tracking=True)
    qualification = fields.Char(string='Qualification', tracking=True)
    specialization = fields.Char(string='Specialization', tracking=True)
    experience_years = fields.Integer(string='Years of Experience', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('resigned', 'Resigned')
    ], string='Status', default='draft', tracking=True)
    photo = fields.Image(string='Photo', max_width=256, max_height=256)
    salary = fields.Monetary(string='Salary', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Relations
    course_ids = fields.One2many('educore.course', 'teacher_id', string='Courses')
    class_ids = fields.One2many('educore.class', 'class_teacher_id', string='Classes (Class Teacher)')
    timetable_ids = fields.One2many('educore.timetable', 'teacher_id', string='Timetable')

    _sql_constraints = [
        ('teacher_id_unique', 'unique(teacher_id)', 'Teacher ID must be unique!'),
        ('email_unique', 'unique(email)', 'Email must be unique!')
    ]

    @api.model
    def create(self, vals):
        if vals.get('teacher_id', 'New') == 'New':
            vals['teacher_id'] = self.env['ir.sequence'].next_by_code('educore.teacher') or 'New'
        return super(EducoreTeacher, self).create(vals)

    @api.depends('first_name', 'last_name')
    def _compute_full_name(self):
        for record in self:
            record.full_name = f"{record.first_name} {record.last_name}"

    def action_activate(self):
        self.write({'state': 'active'})

    def action_set_on_leave(self):
        self.write({'state': 'on_leave'})

    def action_resign(self):
        self.write({'state': 'resigned'})
