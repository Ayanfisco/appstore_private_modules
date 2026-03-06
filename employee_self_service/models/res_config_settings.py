from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ess_auto_invite_email = fields.Boolean(
        string='Send Portal Invitation Email Automatically',
        config_parameter='employee_self_service.auto_invite_email',
        help='Automatically send a welcome/invitation email when a portal '
             'user is created for an employee.',
    )
    ess_allow_expense_submission = fields.Boolean(
        string='Allow Expense Submission via Portal',
        config_parameter='employee_self_service.allow_expense',
        help='Let employees submit expense claims from the self-service portal.',
    )
    ess_allow_leave_request = fields.Boolean(
        string='Allow Leave Requests via Portal',
        config_parameter='employee_self_service.allow_leave',
        help='Let employees request time off from the self-service portal.',
    )
    ess_allow_profile_edit = fields.Boolean(
        string='Allow Employees to Edit Their Profile',
        config_parameter='employee_self_service.allow_profile_edit',
        help='Let employees update their contact info and emergency contacts '
             'from the portal.',
    )
