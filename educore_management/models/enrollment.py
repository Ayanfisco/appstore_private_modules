from odoo import models, fields, api


class EducoreEnrollment(models.Model):
    _name = 'educore.enrollment'
    _description = 'Student Enrollment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Enrollment Reference', required=True, copy=False, readonly=True, default='New')
    student_id = fields.Many2one('educore.student', string='Student', required=True, tracking=True, ondelete='cascade')
    course_id = fields.Many2one('educore.course', string='Course', required=True, tracking=True)
    class_id = fields.Many2one('educore.class', string='Class', required=True, tracking=True)
    enrollment_date = fields.Date(string='Enrollment Date', default=fields.Date.today, required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('enrolled', 'Enrolled'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped')
    ], string='Status', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('educore.enrollment') or 'New'
        return super(EducoreEnrollment, self).create(vals)

    def action_enroll(self):
        self.write({'state': 'enrolled'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_drop(self):
        self.write({'state': 'dropped'})
