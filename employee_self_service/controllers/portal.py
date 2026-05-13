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
    Safely parse a date string in any common format:
      - yyyy-mm-dd  (HTML <input type="date"> standard output — the spec format)
      - dd/mm/yyyy  (Nigerian / European locale display)
      - mm/dd/yyyy  (US locale fallback)
      - dd-mm-yyyy  (alternate separator)
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
    """
    Detect Odoo 18 overlap error messages. Odoo 18 uses two different messages:
    - "An employee already booked time off which overlaps with this period"
    - "You've already booked time off which overlaps with this period"
    - "Attempting to double-book your time off..."
    """
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
    """
    Convert a raw Odoo leave error into a user-friendly portal message.
    Returns a translated string.
    """
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

        # Pending expenses
        pending_expenses = request.env['hr.expense.sheet'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', 'in', ('submit', 'approve')),
        ], limit=5, order='create_date desc')

        # Recent payslips
        recent_payslips = []
        if 'hr.payslip' in request.env:
            recent_payslips = request.env['hr.payslip'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ('done', 'paid')),
            ], limit=3, order='date_to desc')

        params = request.env['ir.config_parameter'].sudo()
        return request.render('employee_self_service.portal_ess_dashboard', {
            'employee': employee,
            'today': today,
            'leave_balances': leave_balances,
            'pending_leaves': pending_leaves,
            'pending_expenses': pending_expenses,
            'recent_payslips': recent_payslips,
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

        leave_types = request.env['hr.leave.type'].sudo().search([
            ('active', '=', True),
            ('requires_allocation', '=', 'no'),
        ]) | request.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
        ]).mapped('holiday_status_id')

        params = request.env['ir.config_parameter'].sudo()
        return request.render('employee_self_service.portal_ess_leaves', {
            'employee': employee,
            'leaves': leaves,
            'leave_types': leave_types,
            'today': date.today(),
            'allow_leave': params.get_param(
                'employee_self_service.allow_leave', 'True') == 'True',
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

        # Log exactly what the browser posted — critical for diagnosing date issues
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

        # ── Basic field validation ─────────────────────────────────────────────
        if not leave_type_id:
            errors.append(_('Please select a leave type.'))

        # Normalize: treat empty string same as None
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

        # ── Pre-flight overlap check using Python-side date comparison ─────────
        # IMPORTANT: hr.leave.date_from/date_to are Datetime fields stored in UTC.
        # Comparing plain date strings against them causes timezone-offset false
        # positives (e.g. WAT=UTC+1 means 08:00 local = 07:00 UTC, so a date
        # boundary query can bleed into the wrong day). We fix this by fetching
        # leaves and comparing .date() in Python, which strips the time component.
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

        # ── Create and confirm leave ───────────────────────────────────────────
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
                    # Use Odoo's built-in savepoint context manager.
                    # This is the ONLY reliable way to catch @api.constrains
                    # errors in Odoo 18 without the transaction being left in
                    # an aborted state that causes the "Oops" error page.
                    with request.env.cr.savepoint():
                        # Odoo 18 hr.leave uses request_date_from / request_date_to
                        # (pure Date fields) as the user-facing input.
                        # The ORM then computes date_from/date_to (Datetime fields)
                        # automatically based on the employee's work schedule and
                        # timezone — so we must NEVER set date_from/date_to directly
                        # as that gets overridden by the onchange computation.
                        leave_env = request.env['hr.leave'].sudo().with_context(
                            default_employee_id=employee.id,
                            allowed_company_ids=employee.company_id.ids or [1],
                        )
                        new_leave = leave_env.create({
                            'holiday_status_id': leave_type.id,
                            'employee_id': employee.id,
                            'request_date_from': date_from_norm,   # yyyy-mm-dd string
                            'request_date_to':   date_to_norm,     # yyyy-mm-dd string
                            'name': name or _('Leave Request'),
                        })
                        # Defensive check — ensure employee wasn't overridden
                        if new_leave.employee_id.id != employee.id:
                            new_leave.sudo().write({'employee_id': employee.id})
                        # Odoo 18: submit for manager approval
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

        # ── Re-render form with errors ─────────────────────────────────────────
        leave_types = request.env['hr.leave.type'].sudo().search([
            ('active', '=', True),
        ])
        return request.render('employee_self_service.portal_ess_leaves', {
            'employee': employee,
            'leaves': request.env['hr.leave'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '!=', 'refuse'),
            ], order='date_from desc', limit=50),
            'leave_types': leave_types,
            'errors': errors,
            'today': date.today(),
            'allow_leave': True,
            'page_name': 'ess_leaves',
        })

    # ── Expenses — List ───────────────────────────────────────────────────────
    @http.route('/my/ess/expenses', type='http', auth='user', website=True)
    def ess_expenses(self, **kw):
        employee = _get_employee_or_abort()
        if not employee:
            return request.redirect('/web?#action=login')

        sheets = request.env['hr.expense.sheet'].sudo().search([
            ('employee_id', '=', employee.id),
        ], order='create_date desc', limit=50)

        params = request.env['ir.config_parameter'].sudo()
        return request.render('employee_self_service.portal_ess_expenses', {
            'employee': employee,
            'expense_sheets': sheets,
            'allow_expense': params.get_param(
                'employee_self_service.allow_expense', 'True') == 'True',
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
                expense = request.env['hr.expense'].sudo().create({
                    'name': name,
                    'employee_id': employee.id,
                    'product_id': expense_product.id if expense_product else False,
                    'total_amount_currency': total_amount,
                    'date': parsed_expense_date,
                    'description': description or '',
                })
                sheet = request.env['hr.expense.sheet'].sudo().create({
                    'name': name,
                    'employee_id': employee.id,
                    'expense_line_ids': [(4, expense.id)],
                })
                sheet.sudo().action_submit_sheet()
                return request.redirect('/my/ess/expenses?success=1')

            except (ValidationError, UserError) as e:
                msg = str(e.args[0]) if e.args else str(e)
                errors.append(msg)
            except Exception as e:
                _logger.exception('ESS: expense submission failed: %s', e)
                errors.append(_('Could not submit expense. Please contact HR.'))

        sheets = request.env['hr.expense.sheet'].sudo().search([
            ('employee_id', '=', employee.id),
        ], order='create_date desc', limit=50)
        return request.render('employee_self_service.portal_ess_expenses', {
            'employee': employee,
            'expense_sheets': sheets,
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

        return request.render('employee_self_service.portal_ess_payslips', {
            'employee': employee,
            'payslips': payslips,
            'page_name': 'ess_payslips',
        })

    # ── Payslip Download ───────────────────────────────────────────────────────
    @http.route('/my/ess/payslips/<int:payslip_id>/download', type='http', auth='user', website=True)
    def ess_payslip_download(self, payslip_id, **kw):
        employee = _get_employee_or_abort()
        if not employee:
            return request.redirect('/web?#action=login')

        # Verify the payslip belongs to this employee and is confirmed
        payslip = request.env['hr.payslip'].sudo().search([
            ('id', '=', payslip_id),
            ('employee_id', '=', employee.id),
            ('state', 'in', ('done', 'paid')),
        ], limit=1)

        if not payslip:
            return request.not_found()

        # Render the standard Odoo payslip PDF report
        pdf_content, content_type = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'hr_payroll.action_report_payslip', payslip.ids
        )

        filename = 'Payslip-%s-%s.pdf' % (
            payslip.employee_id.name.replace(' ', '_'),
            payslip.date_to.strftime('%Y-%m') if payslip.date_to else 'unknown'
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