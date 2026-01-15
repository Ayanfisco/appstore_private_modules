from odoo import models, fields, api
from datetime import datetime, timedelta, date
from odoo.fields import Datetime


class DivisionFloat(models.Model):
    _name = 'division.float'
    _description = 'Division Float Balance Tracking'

    division_id = fields.Many2one('account.analytic.account',
                                  string='Division', required=True)
    balance = fields.Float('Float Balance', default=0.0)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    petty_cash_ids = fields.One2many('petty.cash.request',
                                     compute='_compute_petty_cash_requests')
    total_paid_requests = fields.Integer('Total Paid Requests',
                                         compute='_compute_statistics')
    total_paid_amount = fields.Float('Total Paid Amount',
                                     compute='_compute_statistics')
    average_request_amount = fields.Float('Average Request Amount',
                                          compute='_compute_statistics')
    monthly_requests = fields.Integer('This Month Requests',
                                      compute='_compute_statistics')
    monthly_amount = fields.Float('This Month Amount',
                                  compute='_compute_statistics')

    @api.depends('division_id')
    def _compute_statistics(self):
        for record in self:
            paid_requests = self.env['petty.cash.request'].search([
                ('division_id', '=', record.division_id.id),
                ('state', '=', 'paid')
            ])

            record.total_paid_requests = len(paid_requests)
            record.total_paid_amount = sum(paid_requests.mapped('amount'))
            record.average_request_amount = (
                record.total_paid_amount / record.total_paid_requests
                if record.total_paid_requests > 0 else 0
            )

            # This month statistics
            first_day = Datetime.now().replace(day=1, hour=0, minute=0, second=0)
            monthly_requests = paid_requests.filtered(
                lambda r: r.cfo_approved_date and r.cfo_approved_date >= first_day
            )

            record.monthly_requests = len(monthly_requests)
            record.monthly_amount = sum(monthly_requests.mapped('amount'))

    def action_view_petty_cash_requests(self):
        """Open petty cash requests for this division"""
        return {
            'name': 'Petty Cash Requests',
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.request',
            'view_mode': 'list,form',
            'domain': [('division_id', '=', self.division_id.id), ('state', '=', 'paid')],
            'context': {'default_division_id': self.division_id.id}
        }

    @api.depends('division_id')
    def _compute_petty_cash_requests(self):
        for record in self:
            record.petty_cash_ids = self.env['petty.cash.request'].search([
                ('division_id', '=', record.division_id.id),
                ('state', '=', 'paid')
            ])
