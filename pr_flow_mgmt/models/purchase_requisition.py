from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class PurchaseRequisition(models.Model):
    _name = 'pr.flow.requisition'
    _description = 'Purchase Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_required desc, id desc'

    # Basic Information
    name = fields.Char(
        string='Requisition Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('dept_approved', 'Department Approved'),
        ('manager_approved', 'Manager Approved'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, required=True)

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Very Urgent'),
    ], string='Priority', default='0', tracking=True)

    # Dates
    date_request = fields.Date(
        string='Request Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )

    date_required = fields.Date(
        string='Required Date',
        required=True,
        tracking=True
    )

    date_approved = fields.Datetime(
        string='Approved Date',
        readonly=True,
        tracking=True
    )

    # Related Users
    user_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        required=True,
        tracking=True
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        tracking=True
    )

    dept_manager_id = fields.Many2one(
        'res.users',
        string='Department Manager',
        tracking=True
    )

    manager_id = fields.Many2one(
        'res.users',
        string='Approval Manager',
        tracking=True
    )

    approved_by_id = fields.Many2one(
        'res.users',
        string='Final Approved By',
        readonly=True,
        tracking=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    # Requisition Lines
    line_ids = fields.One2many(
        'pr.flow.requisition.line',
        'requisition_id',
        string='Requisition Lines',
        copy=True
    )

    # Budget and Amounts
    estimated_amount = fields.Monetary(
        string='Estimated Amount',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True
    )

    # Description and Notes
    description = fields.Text(string='Description')
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True)
    notes = fields.Text(string='Internal Notes')

    # Purchase Orders
    purchase_order_ids = fields.One2many(
        'purchase.order',
        'requisition_id',
        string='Purchase Orders'
    )

    purchase_count = fields.Integer(
        string='Purchase Order Count',
        compute='_compute_purchase_count'
    )

    # Computed Fields
    line_count = fields.Integer(
        string='Line Count',
        compute='_compute_line_count'
    )

    is_editable = fields.Boolean(
        string='Is Editable',
        compute='_compute_is_editable'
    )

    # Approval Configuration
    require_dept_approval = fields.Boolean(
        string='Require Department Approval',
        default=True
    )

    require_manager_approval = fields.Boolean(
        string='Require Manager Approval',
        default=True
    )

    @api.depends('line_ids', 'line_ids.estimated_price', 'line_ids.quantity')
    def _compute_amounts(self):
        for rec in self:
            rec.estimated_amount = sum(rec.line_ids.mapped('subtotal'))

    @api.depends('purchase_order_ids')
    def _compute_purchase_count(self):
        for rec in self:
            rec.purchase_count = len(rec.purchase_order_ids)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends('state')
    def _compute_is_editable(self):
        for rec in self:
            rec.is_editable = rec.state in ['draft', 'rejected']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('pr.flow.requisition') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        # Prevent editing if not in editable state
        if not self.env.context.get('skip_state_check'):
            # Allow state changes and approval-related fields
            allowed_fields = ['state', 'rejection_reason', 'purchase_order_ids',
                              'dept_manager_id', 'manager_id', 'approved_by_id', 'date_approved']
            for rec in self:
                if not rec.is_editable and any(key not in allowed_fields for key in vals.keys()):
                    raise UserError(_('You cannot edit a requisition that is not in Draft or Rejected state.'))
        return super().write(vals)

    @api.constrains('date_required', 'date_request')
    def _check_dates(self):
        for rec in self:
            if rec.date_required < rec.date_request:
                raise ValidationError(_('Required date cannot be earlier than request date.'))

    @api.constrains('line_ids')
    def _check_lines(self):
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(_('Please add at least one requisition line.'))

    # State Change Methods
    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Cannot submit requisition without lines.'))

        self.write({
            'state': 'submitted',
        })
        self._send_approval_notification('dept_manager_id')
        return True

    def action_dept_approve(self):
        self.ensure_one()
        next_state = 'manager_approved' if self.require_manager_approval else 'approved'

        self.write({
            'state': 'dept_approved',
            'dept_manager_id': self.env.user.id,
        })

        if self.require_manager_approval:
            self._send_approval_notification('manager_id')
        else:
            self.action_manager_approve()

        return True

    def action_manager_approve(self):
        self.ensure_one()
        self.write({
            'state': 'approved',
            'manager_id': self.env.user.id,
            'approved_by_id': self.env.user.id,
            'date_approved': fields.Datetime.now(),
        })
        self._send_approval_notification('user_id')
        return True

    def action_reject(self):
        self.ensure_one()
        return {
            'name': _('Rejection Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'pr.flow.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_requisition_id': self.id},
        }

    def action_cancel(self):
        self.ensure_one()
        if self.purchase_order_ids.filtered(lambda po: po.state not in ['draft', 'cancel']):
            raise UserError(_('Cannot cancel requisition with confirmed purchase orders.'))

        self.write({'state': 'cancelled'})
        return True

    def action_draft(self):
        self.ensure_one()
        self.write({
            'state': 'draft',
            'rejection_reason': False,
        })
        return True

    def action_create_purchase_order(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved requisitions can create purchase orders.'))

        # Group lines by vendor
        lines_by_vendor = {}
        for line in self.line_ids:
            if not line.vendor_id:
                raise UserError(_('Please set vendor for all lines before creating purchase orders.'))

            if line.vendor_id not in lines_by_vendor:
                lines_by_vendor[line.vendor_id] = []
            lines_by_vendor[line.vendor_id].append(line)

        # Create purchase orders
        purchase_orders = self.env['purchase.order']
        for vendor, lines in lines_by_vendor.items():
            po_lines = []
            for line in lines:
                po_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.description or line.product_id.name,
                    'product_qty': line.quantity,
                    'product_uom': line.uom_id.id,
                    'price_unit': line.estimated_price,
                    'date_planned': self.date_required,
                }))

            po_vals = {
                'partner_id': vendor.id,
                'requisition_id': self.id,
                'date_order': fields.Datetime.now(),
                'order_line': po_lines,
                'origin': self.name,
            }

            purchase_orders |= self.env['purchase.order'].create(po_vals)

        self.write({'state': 'done'})

        return {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', purchase_orders.ids)],
        }

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('requisition_id', '=', self.id)],
            'context': {'default_requisition_id': self.id},
        }

    def _send_approval_notification(self, user_field):
        """Send email notification to the next approver"""
        template = self.env.ref('pr_flow_mgmt.email_template_requisition_approval', raise_if_not_found=False)
        if template:
            for rec in self:
                if user_field and rec[user_field]:
                    template.send_mail(rec.id, force_send=True)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    requisition_id = fields.Many2one(
        'pr.flow.requisition',
        string='Source Requisition',
        readonly=True
    )

