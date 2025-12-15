from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PrRejectWizard(models.TransientModel):
    _name = 'pr.flow.reject.wizard'
    _description = 'Purchase Requisition Rejection Wizard'

    requisition_id = fields.Many2one(
        'pr.flow.requisition',
        string='Requisition',
        required=True,
        readonly=True
    )

    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True,
        help='Please specify the reason for rejection'
    )

    def action_reject(self):
        self.ensure_one()
        if not self.rejection_reason:
            raise UserError(_('Please provide a rejection reason.'))

        self.requisition_id.with_context(skip_state_check=True).write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
        })

        # Send rejection notification
        template = self.env.ref('pr_flow_mgmt.email_template_requisition_rejected', raise_if_not_found=False)
        if template:
            template.send_mail(self.requisition_id.id, force_send=True)

        # Post message in chatter
        self.requisition_id.message_post(
            body=_('Requisition rejected by %s. Reason: %s') % (self.env.user.name, self.rejection_reason),
            message_type='notification'
        )

        return {'type': 'ir.actions.act_window_close'}
