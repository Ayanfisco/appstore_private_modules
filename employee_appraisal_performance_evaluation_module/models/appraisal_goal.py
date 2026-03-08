# -*- coding: utf-8 -*-
from odoo import models, fields


class AppraisalGoalLine(models.Model):
    _name = 'appraisal.goal.line'
    _inherit = ["mail.thread"]
    _description = 'Appraisal Goal Line'

    appraisal_id = fields.Many2one(
        'employee.appraisal',
        string='Appraisal',
        ondelete='cascade'
    )
    name = fields.Char(string='Goal', required=True)
    description = fields.Text(string='Description')
    target_date = fields.Date(string='Target Date')
    achievement_percentage = fields.Float(
        string='Achievement %',
        digits=(5, 2)
    )
    status = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='not_started')
    comments = fields.Text(string='Comments')