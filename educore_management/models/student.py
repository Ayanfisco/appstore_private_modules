from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EducoreStudent(models.Model):
    _name = 'educore.student'
    _description = 'Student Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'full_name'

    student_id = fields.Char(string='Student ID', required=True, copy=False, readonly=True, default='New')
    first_name = fields.Char(string='First Name', required=True, tracking=True)
    last_name = fields.Char(string='Last Name', required=True, tracking=True)
    full_name = fields.Char(string='Full Name', compute='_compute_full_name', store=True)
    date_of_birth = fields.Date(string='Date of Birth', required=True, tracking=True)
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender', required=True, tracking=True)
    blood_group = fields.Selection([
        ('a+', 'A+'), ('a-', 'A-'),
        ('b+', 'B+'), ('b-', 'B-'),
        ('o+', 'O+'), ('o-', 'O-'),
        ('ab+', 'AB+'), ('ab-', 'AB-')
    ], string='Blood Group')
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    address = fields.Text(string='Address', tracking=True)
    guardian_name = fields.Char(string='Guardian Name', required=True, tracking=True)
    guardian_phone = fields.Char(string='Guardian Phone', required=True, tracking=True)
    guardian_email = fields.Char(string='Guardian Email')
    admission_date = fields.Date(string='Admission Date', default=fields.Date.today, required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('graduated', 'Graduated'),
        ('withdrawn', 'Withdrawn')
    ], string='Status', default='draft', tracking=True)
    photo = fields.Image(string='Photo', max_width=256, max_height=256)
    nationality = fields.Char(string='Nationality')

    # Relations
    class_id = fields.Many2one('educore.class', string='Current Class', tracking=True)
    enrollment_ids = fields.One2many('educore.enrollment', 'student_id', string='Enrollments')
    attendance_ids = fields.One2many('educore.attendance', 'student_id', string='Attendance Records')
    grade_ids = fields.One2many('educore.grade', 'student_id', string='Grades')
    fee_ids = fields.One2many('educore.fee', 'student_id', string='Fee Records')

    # Computed fields
    total_attendance = fields.Integer(string='Total Attendance', compute='_compute_attendance_stats')
    attendance_percentage = fields.Float(string='Attendance %', compute='_compute_attendance_stats')
    total_fees = fields.Monetary(string='Total Fees', compute='_compute_fee_stats')
    paid_fees = fields.Monetary(string='Paid Fees', compute='_compute_fee_stats')
    outstanding_fees = fields.Monetary(string='Outstanding Fees', compute='_compute_fee_stats')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    _sql_constraints = [
        ('student_id_unique', 'unique(student_id)', 'Student ID must be unique!')
    ]

    @api.model
    def create(self, vals):
        if vals.get('student_id', 'New') == 'New':
            vals['student_id'] = self.env['ir.sequence'].next_by_code('educore.student') or 'New'
        return super(EducoreStudent, self).create(vals)

    @api.depends('first_name', 'last_name')
    def _compute_full_name(self):
        for record in self:
            record.full_name = f"{record.first_name} {record.last_name}"

    @api.depends('date_of_birth')
    def _compute_age(self):
        for record in self:
            if record.date_of_birth:
                today = fields.Date.today()
                record.age = today.year - record.date_of_birth.year - (
                            (today.month, today.day) < (record.date_of_birth.month, record.date_of_birth.day))
            else:
                record.age = 0

    @api.depends('attendance_ids')
    def _compute_attendance_stats(self):
        for record in self:
            total = len(record.attendance_ids)
            present = len(record.attendance_ids.filtered(lambda a: a.status == 'present'))
            record.total_attendance = total
            record.attendance_percentage = (present / total * 100) if total > 0 else 0

    @api.depends('fee_ids')
    def _compute_fee_stats(self):
        for record in self:
            record.total_fees = sum(record.fee_ids.mapped('amount'))
            record.paid_fees = sum(record.fee_ids.filtered(lambda f: f.state == 'paid').mapped('amount'))
            record.outstanding_fees = record.total_fees - record.paid_fees

    def action_activate(self):
        self.write({'state': 'active'})

    def action_suspend(self):
        self.write({'state': 'suspended'})

    def action_graduate(self):
        self.write({'state': 'graduated'})

    def action_withdraw(self):
        self.write({'state': 'withdrawn'})
