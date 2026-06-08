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
        already_has_user = []  # collect employees that already have portal users
        created = []  # collect successfully created ones

        for user in self:

            # collect instead of raise
            if user.ess_portal_user_id:
                already_has_user.append(user.name)
                continue  # skip, process next employee

            work_email = user.work_email or user.private_email
            if not work_email:
                already_has_user.append(
                    _('%s (no email set)') % user.name
                )
                continue  # skip, process next employee

            existing = self.env['res.users'].sudo().search(
                [('login', '=', work_email)], limit=1
            )
            if existing:
                if not existing.share:
                    already_has_user.append(
                        _('%s (internal user exists with same email)') % user.name
                    )
                    continue
                user.ess_portal_user_id = existing
                self._notify_portal_user_linked(existing)
                created.append(user.name)
                continue

            portal_group = self.env.ref('base.group_portal')

            partner = user.work_contact_id or user.address_home_id
            if not partner:
                partner = self.env['res.partner'].sudo().search([
                    ('email', '=', work_email),
                    ('user_ids', '=', False),
                ], limit=1)

            user_vals = {
                'name': user.name,
                'login': work_email,
                'email': work_email,
                'groups_id': [(6, 0, [portal_group.id])],
                'active': True,
            }
            if partner:
                user_vals['partner_id'] = partner.id

            new_user = self.env['res.users'].sudo().create(user_vals)
            user.ess_portal_user_id = new_user

            if partner and new_user.partner_id.id != partner.id:
                dupe = new_user.partner_id
                new_user.sudo().write({'partner_id': partner.id})
                dupe.sudo().write({'active': False})

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
                        template.sudo().send_mail(user.id)
                except Exception as e:
                    _logger.warning('ESS: invitation email failed: %s', e)

            created.append(user.name)

        # build feedback message
        message_parts = []
        if created:
            message_parts.append(
                _('Portal users created for: %s') % ', '.join(created)
            )
        if already_has_user:
            message_parts.append(
                _('Skipped (already have portal user or issue): %s')
                % ', '.join(already_has_user)
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Portal User Processing Complete'),
                'message': ' | '.join(message_parts) or _('Nothing to process.'),
                'type': 'success' if created else 'warning',
                'sticky': True,  # keep visible so user can read the full list
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
