from odoo import models, fields, api
from odoo.exceptions import ValidationError


class VehicleCommissionRule(models.Model):
    """A tiered commission rate: applies when a sale's profit margin falls
    within a range, optionally narrowed to a specific vehicle condition
    and/or a specific salesperson. Rules are evaluated in sequence order;
    the first match wins.
    """
    _name = 'vehicle.commission.rule'
    _description = 'Vehicle Commission Rule'
    _order = 'sequence, margin_from'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10,
                              help='Rules are checked in this order; the first matching rule applies.')
    active = fields.Boolean(default=True)

    salesperson_id = fields.Many2one('res.users', string='Salesperson',
                                     help='Leave empty to apply to every salesperson.')
    vehicle_condition = fields.Selection([
        ('new', 'New'),
        ('used', 'Used'),
        ('certified', 'Certified Pre-Owned'),
    ], string='Vehicle Condition', help='Leave empty to apply to every condition.')

    margin_from = fields.Float(string='Margin From (%)', required=True, default=0.0)
    margin_to = fields.Float(string='Margin To (%)', required=True, default=100.0)
    commission_rate = fields.Float(string='Commission Rate (%)', required=True)

    notes = fields.Text(string='Notes')

    @api.constrains('margin_from', 'margin_to')
    def _check_margin_range(self):
        for rule in self:
            if rule.margin_from > rule.margin_to:
                raise ValidationError(
                    "The 'Margin From' value must be lower than or equal to the 'Margin To' value.")

    @api.model
    def _find_matching_rule(self, margin_percent, salesperson=None, condition=None):
        """Return the best-matching active rule for the given margin, or an
        empty recordset if none apply. Rules are already ordered by
        sequence, so the first hit is returned.
        """
        domain = [
            ('active', '=', True),
            ('margin_from', '<=', margin_percent),
            ('margin_to', '>=', margin_percent),
        ]
        for rule in self.search(domain):
            if rule.salesperson_id and (not salesperson or rule.salesperson_id.id != salesperson.id):
                continue
            if rule.vehicle_condition and rule.vehicle_condition != condition:
                continue
            return rule
        return self.browse()
