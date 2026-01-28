from odoo import models, fields, api
from datetime import datetime, timedelta


class EducoreTimetable(models.Model):
    _name = 'educore.timetable'
    _description = 'Class Timetable'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    class_id = fields.Many2one('educore.class', string='Class', required=True, tracking=True)
    course_id = fields.Many2one('educore.course', string='Course', required=True, tracking=True)
    teacher_id = fields.Many2one('educore.teacher', string='Teacher', required=True, tracking=True)
    day_of_week = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday')
    ], string='Day', required=True, tracking=True)

    # Keep float fields for time input (hours format like 9.0 for 9:00 AM)
    start_time = fields.Float(string='Start Time', required=True, tracking=True)
    end_time = fields.Float(string='End Time', required=True, tracking=True)

    # Add datetime fields for calendar view
    start_datetime = fields.Datetime(string='Start DateTime', compute='_compute_datetimes', store=True)
    end_datetime = fields.Datetime(string='End DateTime', compute='_compute_datetimes', store=True)

    room_number = fields.Char(string='Room Number', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    @api.depends('class_id', 'course_id', 'day_of_week')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.class_id.name} - {record.course_id.name} - {record.day_of_week}"

    @api.depends('day_of_week', 'start_time', 'end_time')
    def _compute_datetimes(self):
        from datetime import datetime, timedelta

        # Use a fixed reference week (e.g., first week of current year)
        for record in self:
            if record.day_of_week and record.start_time and record.end_time:
                # Start from a Monday
                base_date = datetime(2026, 1, 6)  # A Monday

                day_map = {
                    'monday': 0, 'tuesday': 1, 'wednesday': 2,
                    'thursday': 3, 'friday': 4, 'saturday': 5
                }

                target_date = base_date + timedelta(days=day_map[record.day_of_week])

                # Convert float time to hours and minutes
                start_hours = int(record.start_time)
                start_minutes = int((record.start_time - start_hours) * 60)
                end_hours = int(record.end_time)
                end_minutes = int((record.end_time - end_hours) * 60)

                record.start_datetime = target_date.replace(hour=start_hours, minute=start_minutes)
                record.end_datetime = target_date.replace(hour=end_hours, minute=end_minutes)
            else:
                record.start_datetime = False
                record.end_datetime = False

    def action_activate(self):
        self.write({'state': 'active'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
