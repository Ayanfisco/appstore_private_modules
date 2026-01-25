from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pr_require_dept_approval = fields.Boolean(
        string='Require Department Approval',
        config_parameter='pr_flow_mgmt.require_dept_approval',
        default=True
    )

    pr_require_manager_approval = fields.Boolean(
        string='Require Manager Approval',
        config_parameter='pr_flow_mgmt.require_manager_approval',
        default=True
    )

    pr_auto_approve_threshold = fields.Float(
        string='Auto Approve Below Amount',
        config_parameter='pr_flow_mgmt.auto_approve_threshold',
        default=0.0,
        help='Requisitions below this amount will be auto-approved (0 = disabled)'
    )
