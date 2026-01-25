from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseRequisitionLine(models.Model):
    _name = 'pr.flow.requisition.line'
    _description = 'Purchase Requisition Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)

    requisition_id = fields.Many2one(
        'pr.flow.requisition',
        string='Requisition',
        required=True,
        ondelete='cascade',
        index=True
    )

    state = fields.Selection(
        related='requisition_id.state',
        string='Status',
        readonly=True,
        store=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('purchase_ok', '=', True)]
    )

    product_category_id = fields.Many2one(
        'product.category',
        related='product_id.categ_id',
        string='Product Category',
        readonly=True
    )

    description = fields.Text(string='Description')

    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure'
    )

    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
        domain="[('name', '=', product_uom_category_id)]"
    )

    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id',
        readonly=True
    )

    estimated_price = fields.Float(
        string='Estimated Price',
        digits='Product Price',
        default=0.0
    )

    subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        related='requisition_id.currency_id',
        string='Currency',
        readonly=True
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string='Preferred Vendor',
        domain="[('is_company', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )

    company_id = fields.Many2one(
        related='requisition_id.company_id',
        string='Company',
        readonly=True,
        store=True
    )

    date_required = fields.Date(
        related='requisition_id.date_required',
        string='Required Date',
        readonly=True,
        store=True
    )

    notes = fields.Text(string='Notes')

    # Inventory Related
    stock_available = fields.Float(
        string='Available Stock',
        compute='_compute_stock_available'
    )

    @api.depends('quantity', 'estimated_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.estimated_price

    def _compute_stock_available(self):
        for line in self:
            if line.product_id:
                line.stock_available = line.product_id.with_context(
                    company_id=line.company_id.id
                ).qty_available
            else:
                line.stock_available = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            self.description = self.product_id.name

            # Get last purchase price
            last_po_line = self.env['purchase.order.line'].search([
                ('product_id', '=', self.product_id.id),
                ('state', 'in', ['purchase', 'done'])
            ], order='date_order desc', limit=1)

            if last_po_line:
                self.estimated_price = last_po_line.price_unit
            else:
                self.estimated_price = self.product_id.standard_price

            # Set preferred vendor
            if self.product_id.seller_ids:
                self.vendor_id = self.product_id.seller_ids[0].partner_id

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))

