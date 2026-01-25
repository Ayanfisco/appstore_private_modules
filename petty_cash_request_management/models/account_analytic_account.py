from odoo import models, fields, api, _


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    manager_id = fields.Many2one('res.users', string='Manager', help='Manager responsible for this analytic account')