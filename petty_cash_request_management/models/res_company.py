from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    petty_cash_account_id = fields.Many2one(
        'account.account',
        string='Petty Cash Account',
        domain="[('account_type', '=', 'asset_cash'), ('company_ids', '=', id)]",
        help='Account used for petty cash payments'
    )

    default_expense_account_id = fields.Many2one(
        'account.account',
        string='Default Petty Cash Expense Account',
        domain="[('account_type', '=', 'expense'), ('company_ids', '=', id)]",
        help='Default expense account for petty cash requests'
    )

    petty_cash_journal_id = fields.Many2one(
        'account.journal',
        string='Petty Cash Journal',
        domain="[('type', '=', 'cash'), ('company_id', '=', id)]",
        help='Journal used for petty cash transactions'
    )
