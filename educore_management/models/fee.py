from odoo import models, fields, api

class EducoreFee(models.Model):
    _name = 'educore.fee'
    _description = 'Student Fee'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Fee Reference', required=True, copy=False, readonly=True, default='New')
    student_id = fields.Many2one('educore.student', string='Student', required=True, tracking=True, ondelete='cascade')
    fee_type = fields.Selection([
        ('tuition', 'Tuition Fee'),
        ('admission', 'Admission Fee'),
        ('exam', 'Exam Fee'),
        ('library', 'Library Fee'),
        ('transport', 'Transport Fee'),
        ('sports', 'Sports Fee'),
        ('miscellaneous', 'Miscellaneous')
    ], string='Fee Type', required=True, tracking=True)
    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    due_date = fields.Date(string='Due Date', required=True, tracking=True)
    payment_date = fields.Date(string='Payment Date', tracking=True)
    academic_year = fields.Char(string='Academic Year', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    description = fields.Text(string='Description')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('educore.fee') or 'New'
        return super(EducoreFee, self).create(vals)

    def action_confirm(self):
        self.write({'state': 'pending'})

    def action_pay(self):
        self.write({
            'state': 'paid',
            'payment_date': fields.Date.today()
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})
