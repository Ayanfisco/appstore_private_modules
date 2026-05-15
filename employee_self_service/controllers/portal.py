import logging
from datetime import date, datetime

from odoo import _, http
from odoo.http import request
from odoo.exceptions import ValidationError, UserError


_logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_employee_or_abort():
    """
    Resolve the hr.employee linked to the current portal user via
    ess_portal_user_id. Returns the employee (sudo) or None.
    """
    employee = request.env['hr.employee']._get_employee_for_user()
    if not employee:
        return None
    return employee


def _parse_date(date_str):
    """
    Safely parse a date string in any common format.
    Returns a datetime.date object, or None on failure.
    """
    if not date_str:
        _logger.warning('ESS _parse_date: received empty/None date string')
        return None
    date_str = date_str.strip()
    if not date_str:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
        try:
            result = datetime.strptime(date_str, fmt).date()
            _logger.info('ESS _parse_date: %r parsed as %s using fmt %s', date_str, result, fmt)
            return result
        except ValueError:
            continue
    _logger.warning('ESS _parse_date: could not parse %r with any known format', date_str)
    return None


def _is_overlap_error(msg):
    keywords = (
        'overlap',
        'already booked',
        'time off which overlaps',
        'double-book',
        'conflicting',
    )
    msg_lower = msg.lower()
    return any(kw in msg_lower for kw in keywords)


def _friendly_leave_error(msg):
    if _is_overlap_error(msg):
        return _(
            'You already have a leave request that overlaps with the selected '
            'dates. Please choose different dates or ask HR to cancel the '
            'existing request first.'
        )
    if any(kw in msg.lower() for kw in ('balance', 'allocation', 'days left')):
        return _(
            'You do not have enough leave balance for this request. '
            'Please contact HR to request an allocation.'
        )
    return msg


# ─────────────────────────────────────────────────────────────────────────────
# Controller
# ─────────────────────────────────────────────────────────────────────────────

class EmployeeSelfServicePortal(http.Controller):

    # ── Dashboard ─────────────────────────────────────────────────────────────
    @http.route('/my/ess', type='http', auth='user', website=True)
    def ess_dashboard(self, **kw):
        employee = _get_employee_or_abort()
        if not employee:
            return request.redirect('/web?#action=login')

        today = date.today()

        # Leave balances
        leave_allocations = request.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('holiday_status_id.active', '=', True),
        ])
        leave_balances = []
        for alloc in leave_allocations:
            lt = alloc.holiday_status_id
            leave_balances.append({
                'type': lt.name,
                'allocated': alloc.number_of_days,
                'taken': alloc.leaves_taken,
                'remaining': alloc.number_of_days - alloc.leaves_taken,
            })

        # Pending leave requests
        pending_leaves = request.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', 'in', ('confirm', 'validate1')),
        ], limit=5, order='date_from desc')

        # Pending expenses — Odoo 19: hr.expense.sheet removed; use hr.expense directly
        # State 'reported' = submitted for approval; 'approved' = manager approved
        pending_expenses = request.env['hr.expense'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', 'in', ('reported', 'approved')),
        ], limit=5, order='create_date desc')

        # Recent payslips
        recent_payslips = []
        if 'hr.payslip' in request.env:
            recent_payslips = request.env['hr.payslip'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ('done', 'paid')),
            ], limit=3, order='date_to desc')

        def fmt_date(d, fmt):
            try:
                return d.strftime(fmt) if d else ''
            except Exception:
                return ''

        leave_state_labels = {
            'confirm': 'Pending',
            'validate1': 'Part. Approved',
            'validate': 'Approved',
        }
        expense_state_labels = {
            'draft': 'Draft',
            'reported': 'Submitted',
            'approved': 'Approved',
            'done': 'Paid',
            'refused': 'Refused',
        }

        pending_leaves_fmt = [{
            'name': lv.holiday_status_id.name or '',
            'date_from': fmt_date(lv.date_from, '%d %b') if lv.date_from else '',
            'date_to': fmt_date(lv.date_to, '%d %b %Y') if lv.date_to else '',
            'state_label': leave_state_labels.get(lv.state, lv.state),
        } for lv in pending_leaves]

        pending_expenses_fmt = [{
            'name': exp.name or '',
            'create_date': fmt_date(exp.create_date, '%d %b %Y') if exp.create_date else '',
            'state_label': expense_state_labels.get(exp.state, exp.state),
        } for exp in pending_expenses]

        recent_payslips_fmt = [{
            'name': ps.name or '',
            'date_from': fmt_date(ps.date_from, '%d %b') if ps.date_from else '',
            'date_to': fmt_date(ps.date_to, '%d %b %Y') if ps.date_to else '',
        } for ps in recent_payslips]

        params = request.env['ir.config_parameter'].sudo()
        return request.render('employee_self_service.portal_ess_dashboard', {
            'employee': employee,
            'employee_first_name': (employee.name or '').split(' ')[0],
            'today_fmt': fmt_date(today, '%A, %d %B %Y'),
            'today': today,
            'leave_balances': leave_balances,
            'pending_leaves_fmt': pending_leaves_fmt,
            'pending_expenses_fmt': pending_expenses_fmt,
            'recent_payslips_fmt': recent_payslips_fmt,
            'allow_leave': params.get_param(
                'employee_self_service.allow_leave', 'True') == 'True',
            'allow_expense': params.get_param(
                'employee_self_service.allow_expense', 'True') == 'True',
            'allow_profile_edit': params.get_param(
                'employee_self_service.allow_profile_edit', 'True') == 'True',
            'page_name': 'ess_dashboard',
        })

    # ── Time Off — List ───────────────────────────────────────────────────────
    @http.route('/my/ess/leaves', type='http', auth='user', website=True)
    def ess_leaves(self, **kw):
        employee = _get_employee_or_abort()
        if not employee:
            return request.redirect('/web?#action=login')

        leaves = request.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '!=', 'refuse'),
        ], order='date_from desc', limit=50)

        # Odoo 19: requires_allocation is now a Boolean field (was selection 'yes'/'no')
        leave_types = request.env['hr.leave.type'].sudo().search([
            ('active', '=', True),
            ('requires_allocation', '=', False),
        ]) | request.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
        ]).mapped('holiday_status_id')

        def fmt_date(d, fmt):
            try:
                return d.strftime(fmt) if d else '-'
            except Exception:
                return '-'

        leave_state_labels = {
            'draft': 'Draft',
            'confirm': 'Pending',
            'validate1': 'Approved (L1)',
            'validate': 'Approved',
            'refuse': 'Refused',
        }

        leaves_fmt = [{
            'holiday_status_name': lv.holiday_status_id.name or '',
            'date_from': fmt_date(lv.date_from, '%d %b %Y'),
            'date_to': fmt_date(lv.date_to, '%d %b %Y'),
            'number_of_days': lv.number_of_days,
            'state_label': leave_state_labels.get(lv.state, lv.state),
            'state': lv.state,
        } for lv in leaves]

        params = request.env['ir.config_parameter'].sudo()
        return request.render('employee_self_service.portal_ess_leaves', {
            'employee': employee,
            'leaves_fmt': leaves_fmt,
            'leave_types': leave_types,
            'today': date.today(),
            'today_fmt': date.today().strftime('%Y-%m-%d'),
            'allow_leave': params.get_param(
                'employee_self_service.allow_leave', 'True') == 'True',
            'success': request.params.get('success'),
            'page_name': 'ess_leaves',
        })

    # ── Time Off — Submit new request ─────────────────────────────────────────
    @http.route('/my/ess/leaves/new', type='http', auth='user', website=True,
                methods=['POST'])
    def ess_leave_new(self, leave_type_id=None, date_from=None, date_to=None,
                      name=None, **kw):
        employee = _get_employee_or_abort()
        if not employee:
            return request.redirect('/web?#action=login')

        params = request.env['ir.config_parameter'].sudo()
        if params.get_param('employee_self_service.allow_leave', 'True') != 'True':
            return request.redirect('/my/ess/leaves')

        _logger.warning(
            'ESS leave_new RAW POST: leave_type_id=%r date_from=%r date_to=%r name=%r',
            leave_type_id, date_from, date_to, name,
        )
        _logger.info(
            'ESS leave_new: portal_user=%s (uid=%s) -> employee=%s (id=%s)',
            request.env.user.login, request.env.user.id,
            employee.name, employee.id,
        )

        errors = []

        if not leave_type_id:
            errors.append(_('Please select a leave type.'))

        date_from = (date_from or '').strip() or None
        date_to   = (date_to   or '').strip() or None

        if not date_from:
            errors.append(_('Please select a start date.'))
        if not date_to:
            errors.append(_('Please select an end date.'))

        parsed_from = _parse_date(date_from) if date_from else None
        parsed_to   = _parse_date(date_to)   if date_to   else None

        if date_from and not parsed_from:
            errors.append(_(
                'Invalid start date format "%s". Expected yyyy-mm-dd from the date picker.'
            ) % date_from)
        if date_to and not parsed_to:
            errors.append(_(
                'Invalid end date format "%s". Expected yyyy-mm-dd from the date picker.'
            ) % date_to)
        if parsed_from and parsed_to and parsed_from > parsed_to:
            errors.append(_('End date must be on or after the start date.'))

        if parsed_from and parsed_to and not errors:
            existing_leaves = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', 'not in', ('refuse', 'draft')),
            ], order='date_from desc', limit=100)

            overlap = None
            for lv in existing_leaves:
                if not lv.date_from or not lv.date_to:
                    continue
                lv_from = lv.date_from.date()
                lv_to   = lv.date_to.date()
                if lv_from <= parsed_to and lv_to >= parsed_from:
                    overlap = lv
                    break

            if overlap:
                errors.append(_(
                    'You already have a "%s" request from %s to %s '
                    '(status: %s). Please choose different dates or ask HR '
                    'to cancel the existing request first.'
                ) % (
                    overlap.holiday_status_id.name,
                    overlap.date_from.date().strftime('%d/%m/%Y') if overlap.date_from else '-',
                    overlap.date_to.date().strftime('%d/%m/%Y')   if overlap.date_to   else '-',
                    dict(
                        confirm='Pending',
                        validate1='Partially Approved',
                        validate='Approved',
                    ).get(overlap.state, overlap.state),
                ))

        if not errors and parsed_from and parsed_to:
            date_from_norm = parsed_from.strftime('%Y-%m-%d')
            date_to_norm   = parsed_to.strftime('%Y-%m-%d')

            try:
                leave_type = request.env['hr.leave.type'].sudo().browse(
                    int(leave_type_id)
                )
                if not leave_type.exists():
                    errors.append(_('Invalid leave type selected.'))
                else:
                    with request.env.cr.savepoint():
                        leave_env = request.env['hr.leave'].sudo().with_context(
                            default_employee_id=employee.id,
                            allowed_company_ids=employee.company_id.ids or [1],
                        )
                        new_leave = leave_env.create({
                            'holiday_status_id': leave_type.id,
                            'employee_id': employee.id,
                            'request_date_from': date_from_norm,
                            'request_date_to':   date_to_norm,
                            'name': name or _('Leave Request'),
                        })
                        if new_leave.employee_id.id != employee.id:
                            new_leave.sudo().write({'employee_id': employee.id})
                        new_leave.sudo().write({'state': 'confirm'})
                    return request.redirect('/my/ess/leaves?success=1')

            except (ValidationError, UserError) as e:
                msg = str(e.args[0]) if e.args else str(e)
                _logger.warning('ESS leave blocked: %s', msg)
                errors.append(_friendly_leave_error(msg))

            except Exception as e:
                _logger.exception('ESS: leave creation failed unexpectedly: %s', e)
                msg = str(e)
                if _is_overlap_error(msg):
                    errors.append(_friendly_leave_error(msg))
                else:
                    errors.append(_('An unexpected error occurred. Please contact HR.'))

        leave_types = request.env['hr.leave.type'].sudo().search([
            ('active', '=', True),
        ])
        raw_leaves = request.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '!=', 'refuse'),
        ], order='date_from desc', limit=50)
        leave_state_labels2 = {
            'draft': 'Draft', 'confirm': 'Pending',
            'validate1': 'Approved (L1)', 'validate': 'Approved', 'refuse': 'Refused',
        }
        leaves_fmt2 = [{
            'holiday_status_name': lv.holiday_status_id.name or '',
            'date_from': lv.date_from.strftime('%d %b %Y') if lv.date_from else '-',
            'date_to': lv.date_to.strftime('%d %b %Y') if lv.date_to else '-',
            'number_of_days': lv.number_of_days,
            'state_label': leave_state_labels2.get(lv.state, lv.state),
            'state': lv.state,
        } for lv in raw_leaves]
        return request.render('employee_self_service.portal_ess_leaves', {
            'employee': employee,
            'leaves_fmt': leaves_fmt2,
            'leave_types': leave_types,
            'errors': errors,
            'today': date.today(),
            'today_fmt': date.today().strftime('%Y-%m-%d'),
            'allow_leave': True,
            'page_name': 'ess_leaves',
        })

    # ── Expenses — List ───────────────────────────────────────────────────────
    # Odoo 19: hr.expense.sheet REMOVED — expenses managed directly on hr.expense
    @http.route('/my/ess/expenses', type='http', auth='user', website=True)
    def ess_expenses(self, **kw):
        employee = _get_employee_or_abort()
        if not employee:
            return request.redirect('/web?#action=login')

        expenses = request.env['hr.expense'].sudo().search([
            ('employee_id', '=', employee.id),
        ], order='create_date desc', limit=50)

        expense_state_labels = {
            'draft': 'Draft', 'reported': 'Submitted',
            'approved': 'Approved', 'done': 'Paid', 'refused': 'Refused',
        }
        expenses_fmt = [{
            'name': exp.name or '',
            'create_date': exp.create_date.strftime('%d %b %Y') if exp.create_date else '-',
            'total_amount': '%.2f' % (exp.total_amount_currency or 0.0),
            'state_label': expense_state_labels.get(exp.state, exp.state),
            'state': exp.state,
        } for exp in expenses]

        params = request.env['ir.config_parameter'].sudo()
        return request.render('employee_self_service.portal_ess_expenses', {
            'employee': employee,
            'expenses_fmt': expenses_fmt,
            'allow_expense': params.get_param(
                'employee_self_service.allow_expense', 'True') == 'True',
            'success': request.params.get('success'),
            'page_name': 'ess_expenses',
        })

    # ── Expenses — Submit new ─────────────────────────────────────────────────
    @http.route('/my/ess/expenses/new', type='http', auth='user', website=True,
                methods=['POST'])
    def ess_expense_new(self, name=None, total_amount=None, expense_date=None,
                        description=None, **kw):
        employee = _get_employee_or_abort()
        if not employee:
            return request.redirect('/web?#action=login')

        params = request.env['ir.config_parameter'].sudo()
        if params.get_param('employee_self_service.allow_expense', 'True') != 'True':
            return request.redirect('/my/ess/expenses')

        errors = []
        if not name:
            errors.append(_('Please enter an expense name.'))
        if not total_amount:
            errors.append(_('Please enter the amount.'))
        else:
            try:
                total_amount = float(total_amount)
                if total_amount <= 0:
                    errors.append(_('Amount must be greater than zero.'))
            except ValueError:
                errors.append(_('Invalid amount entered.'))

        parsed_expense_date = _parse_date(expense_date) if expense_date else date.today()
        if not parsed_expense_date:
            parsed_expense_date = date.today()

        if not errors:
            try:
                expense_product = request.env.ref(
                    'hr_expense.product_product_fixed_cost',
                    raise_if_not_found=False,
                )
                # Odoo 19: create hr.expense directly — no sheet wrapper
                expense = request.env['hr.expense'].sudo().create({
                    'name': name,
                    'employee_id': employee.id,
                    'product_id': expense_product.id if expense_product else False,
                    'total_amount_currency': total_amount,
                    'date': parsed_expense_date,
                    'description': description or '',
                })
                # Odoo 19: action_submit() replaces action_submit_sheet()
                expense.sudo().action_submit()
                return request.redirect('/my/ess/expenses?success=1')

            except (ValidationError, UserError) as e:
                msg = str(e.args[0]) if e.args else str(e)
                errors.append(msg)
            except Exception as e:
                _logger.exception('ESS: expense submission failed: %s', e)
                errors.append(_('Could not submit expense. Please contact HR.'))

        raw_expenses = request.env['hr.expense'].sudo().search([
            ('employee_id', '=', employee.id),
        ], order='create_date desc', limit=50)
        exp_state_labels2 = {
            'draft': 'Draft', 'reported': 'Submitted',
            'approved': 'Approved', 'done': 'Paid', 'refused': 'Refused',
        }
        expenses_fmt2 = [{
            'name': exp.name or '',
            'create_date': exp.create_date.strftime('%d %b %Y') if exp.create_date else '-',
            'total_amount': '%.2f' % (exp.total_amount_currency or 0.0),
            'state_label': exp_state_labels2.get(exp.state, exp.state),
            'state': exp.state,
        } for exp in raw_expenses]
        return request.render('employee_self_service.portal_ess_expenses', {
            'employee': employee,
            'expenses_fmt': expenses_fmt2,
            'errors': errors,
            'allow_expense': True,
            'page_name': 'ess_expenses',
        })

    # ── Payslips ──────────────────────────────────────────────────────────────
    @http.route('/my/ess/payslips', type='http', auth='user', website=True)
    def ess_payslips(self, **kw):
        employee = _get_employee_or_abort()
        if not employee:
            return request.redirect('/web?#action=login')

        payslips = []
        if 'hr.payslip' in request.env:
            payslips = request.env['hr.payslip'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ('done', 'paid')),
            ], order='date_to desc', limit=24)

        payslips_fmt = [{
            'id': ps.id,
            'date_from': ps.date_from.strftime('%b %Y') if ps.date_from else '-',
            'name': ps.name or '-',
            'net_wage': '%.2f' % (ps.net_wage or 0.0),
            'state_label': 'Paid' if ps.state == 'paid' else 'Done',
            'state': ps.state,
        } for ps in payslips]

        return request.render('employee_self_service.portal_ess_payslips', {
            'employee': employee,
            'payslips_fmt': payslips_fmt,
            'page_name': 'ess_payslips',
        })


    # ── Payslip — Download PDF ────────────────────────────────────────────────
    @http.route('/my/ess/payslips/<int:payslip_id>/download', type='http',
                auth='user', website=True)
    def ess_payslip_download(self, payslip_id, **kw):
        """
        Secure payslip PDF download.
        Verifies the payslip belongs to the current portal user's employee,
        then streams the PDF rendered by Odoo's report engine.
        Odoo 19: use request.env['ir.actions.report']._render_qweb_pdf()
        and return a Response with the PDF bytes.
        """
        employee = _get_employee_or_abort()
        if not employee:
            return request.redirect('/web?#action=login')

        payslip = request.env['hr.payslip'].sudo().browse(payslip_id)
        if not payslip.exists() or payslip.employee_id.id != employee.id:
            return request.not_found()

        # Render the standard Odoo payslip report
        report_ref = 'hr_payroll.action_report_payslip'
        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            report_ref, [payslip_id]
        )

        filename = '{}-{}.pdf'.format(
            payslip.employee_id.name.replace(' ', '_'),
            payslip.date_to.strftime('%Y-%m') if payslip.date_to else 'payslip',
        )

        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'attachment; filename="%s"' % filename),
                ('Content-Length', len(pdf_content)),
            ]
        )

    # ── Profile — View ────────────────────────────────────────────────────────
    @http.route('/my/ess/profile', type='http', auth='user', website=True,
                methods=['GET'])
    def ess_profile(self, **kw):
        employee = _get_employee_or_abort()
        if not employee:
            return request.redirect('/web?#action=login')

        params = request.env['ir.config_parameter'].sudo()
        return request.render('employee_self_service.portal_ess_profile', {
            'employee': employee,
            'allow_profile_edit': params.get_param(
                'employee_self_service.allow_profile_edit', 'True') == 'True',
            'page_name': 'ess_profile',
            'success': kw.get('success'),
        })

    # ── Profile — Save ────────────────────────────────────────────────────────
    @http.route('/my/ess/profile/save', type='http', auth='user', website=True,
                methods=['POST'])
    def ess_profile_save(self, mobile_phone=None, work_phone=None,
                         private_email=None, emergency_contact=None,
                         emergency_phone=None, **kw):
        employee = _get_employee_or_abort()
        if not employee:
            return request.redirect('/web?#action=login')

        params = request.env['ir.config_parameter'].sudo()
        if params.get_param('employee_self_service.allow_profile_edit', 'True') != 'True':
            return request.redirect('/my/ess/profile')

        vals = {}
        if mobile_phone is not None:
            vals['mobile_phone'] = mobile_phone.strip()
        if work_phone is not None:
            vals['work_phone'] = work_phone.strip()
        if private_email is not None:
            vals['private_email'] = private_email.strip()
        if emergency_contact is not None:
            vals['emergency_contact'] = emergency_contact.strip()
        if emergency_phone is not None:
            vals['emergency_phone'] = emergency_phone.strip()

        if vals:
            try:
                employee.sudo().write(vals)
            except Exception as e:
                _logger.exception('ESS: profile save failed: %s', e)

        return request.redirect('/my/ess/profile?success=1')
