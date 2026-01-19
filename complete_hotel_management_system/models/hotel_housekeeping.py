from odoo import models, fields, api


class HotelHousekeeping(models.Model):
    _name = 'hotel.housekeeping'
    _description = 'Hotel Housekeeping'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Task Number', required=True, copy=False, readonly=True, default='New')

    room_id = fields.Many2one('hotel.room', string='Room', required=True, tracking=True)
    property_id = fields.Many2one(related='room_id.property_id', string='Property', store=True)

    date = fields.Date(string='Scheduled Date', default=fields.Date.today, required=True, tracking=True)

    task_type = fields.Selection([
        ('cleaning', 'Regular Cleaning'),
        ('deep_cleaning', 'Deep Cleaning'),
        ('turndown', 'Turndown Service'),
        ('maintenance', 'Maintenance'),
        ('inspection', 'Inspection'),
    ], string='Task Type', required=True, default='cleaning', tracking=True)

    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)

    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', required=True, tracking=True)

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1')

    notes = fields.Text(string='Notes')
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    duration = fields.Float(string='Duration (hours)', compute='_compute_duration', store=True)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.start_time and rec.end_time:
                delta = rec.end_time - rec.start_time
                rec.duration = delta.total_seconds() / 3600
            else:
                rec.duration = 0

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hotel.housekeeping') or 'HK'
        return super().create(vals)

    def action_start(self):
        self.write({
            'state': 'in_progress',
            'start_time': fields.Datetime.now()
        })
        self.room_id.write({'state': 'cleaning'})

    def action_complete(self):
        self.write({
            'state': 'completed',
            'end_time': fields.Datetime.now()
        })
        self.room_id.write({
            'state': 'available',
            'housekeeping_status': 'clean'
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})