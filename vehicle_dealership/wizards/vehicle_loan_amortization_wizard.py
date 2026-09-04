from odoo import models, fields, api


class VehicleLoanAmortizationWizard(models.TransientModel):
    _name = 'vehicle.loan.amortization.wizard'
    _description = 'Vehicle Loan Amortization Schedule'

    sale_id = fields.Many2one('vehicle.sale', string='Sale', required=True, readonly=True)
    currency_id = fields.Many2one(related='sale_id.currency_id', readonly=True)
    loan_amount = fields.Monetary(related='sale_id.loan_amount', readonly=True)
    interest_rate = fields.Float(related='sale_id.interest_rate', readonly=True)
    loan_term = fields.Integer(related='sale_id.loan_term', readonly=True)
    monthly_payment = fields.Monetary(related='sale_id.monthly_payment', readonly=True)
    total_interest = fields.Monetary(related='sale_id.total_interest', readonly=True)
    total_payable = fields.Monetary(related='sale_id.total_payable', readonly=True)
    line_ids = fields.One2many('vehicle.loan.amortization.line', 'wizard_id',
                               string='Schedule', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        sale_id = self.env.context.get('default_sale_id')
        if sale_id:
            sale = self.env['vehicle.sale'].browse(sale_id)
            lines = []
            balance = sale.loan_amount or 0.0
            monthly_rate = (sale.interest_rate or 0.0) / 100 / 12
            for month in range(1, (sale.loan_term or 0) + 1):
                interest = balance * monthly_rate
                principal = (sale.monthly_payment or 0.0) - interest
                balance = max(balance - principal, 0.0)
                lines.append((0, 0, {
                    'sequence': month,
                    'payment': sale.monthly_payment,
                    'principal': principal,
                    'interest': interest,
                    'balance': balance,
                }))
            res['line_ids'] = lines
        return res


class VehicleLoanAmortizationLine(models.TransientModel):
    _name = 'vehicle.loan.amortization.line'
    _description = 'Vehicle Loan Amortization Line'
    _order = 'sequence'

    wizard_id = fields.Many2one('vehicle.loan.amortization.wizard', string='Wizard',
                                ondelete='cascade')
    sequence = fields.Integer(string='Month')
    currency_id = fields.Many2one(related='wizard_id.currency_id')
    payment = fields.Monetary(string='Payment')
    principal = fields.Monetary(string='Principal')
    interest = fields.Monetary(string='Interest')
    balance = fields.Monetary(string='Remaining Balance')
