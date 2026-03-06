import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # ── Portal user fields ────────────────────────────────────────────────────
    ess_portal_user_id = fields.Many2one(
        'res.users',
        string='ESS Portal User',
        domain=[('share', '=', True)],          # portal/public users only
        groups='hr.group_hr_user',
        copy=False,
        help='The portal user account linked to this employee for '
             'Employee Self-Service access.',
    )
    ess_portal_active = fields.Boolean(
        string='ESS Portal Access',
        compute='_compute_ess_portal_active',
        store=False,
        groups='hr.group_hr_user',
    )

    @api.depends('ess_portal_user_id', 'ess_portal_user_id.active')
    def _compute_ess_portal_active(self):
        for emp in self:
            emp.ess_portal_active = bool(
                emp.ess_portal_user_id and emp.ess_portal_user_id.active
            )

    # ── One-click portal user creation ───────────────────────────────────────
    def action_create_ess_portal_user(self):
        """
        Create a portal user for this employee and optionally send them
        an invitation email. Callable from the employee form button.
        """
        self.ensure_one()

        if self.ess_portal_user_id:
            raise UserError(
                _('Employee %s already has a portal user: %s')
                % (self.name, self.ess_portal_user_id.login)
            )

        work_email = self.work_email or self.private_email
        if not work_email:
            raise UserError(
                _('Please set a Work Email or Private Email on %s before '
                  'creating a portal user.') % self.name
            )

        # Check for existing user with this email
        existing = self.env['res.users'].sudo().search(
            [('login', '=', work_email)], limit=1
        )
        if existing:
            if not existing.share:
                raise UserError(
                    _('A non-portal (internal) user with email %s already '
                      'exists. Cannot create a portal user with the same '
                      'email.') % work_email
                )
            # Re-use existing portal user
            self.ess_portal_user_id = existing
            return self._notify_portal_user_linked(existing)

        portal_group = self.env.ref('base.group_portal')
        new_user = self.env['res.users'].sudo().create({
            'name': self.name,
            'login': work_email,
            'email': work_email,
            'groups_id': [(6, 0, [portal_group.id])],
            'active': True,
        })
        self.ess_portal_user_id = new_user

        # Send invitation email if template exists
        auto_invite = self.env['ir.config_parameter'].sudo().get_param(
            'employee_self_service.auto_invite_email', 'True'
        )
        if auto_invite == 'True':
            try:
                template = self.env.ref(
                    'employee_self_service.mail_template_ess_portal_invite',
                    raise_if_not_found=False,
                )
                if template:
                    template.sudo().send_mail(self.id, force_send=True)
            except Exception as e:
                _logger.warning('ESS: invitation email failed: %s', e)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Portal User Created'),
                'message': _('Portal user %s created for %s.')
                % (new_user.login, self.name),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_revoke_ess_portal_user(self):
        """Unlink (but do not delete) the portal user from this employee."""
        self.ensure_one()
        if not self.ess_portal_user_id:
            raise UserError(_('No portal user linked to %s.') % self.name)
        self.ess_portal_user_id = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Portal Access Revoked'),
                'message': _('ESS portal access removed for %s.') % self.name,
                'type': 'warning',
                'sticky': False,
            },
        }

    def _notify_portal_user_linked(self, user):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Portal User Linked'),
                'message': _('Existing portal user %s linked to %s.')
                % (user.login, self.name),
                'type': 'info',
                'sticky': False,
            },
        }

    # ── Helper: get employee for current portal user ──────────────────────────
    @api.model
    def _get_employee_for_user(self, user=None):
        """
        Return the hr.employee record linked to the given (or current) user
        via ess_portal_user_id. Returns empty recordset if not found.
        """
        if user is None:
            user = self.env.user
        return self.sudo().search(
            [('ess_portal_user_id', '=', user.id)], limit=1
        )
