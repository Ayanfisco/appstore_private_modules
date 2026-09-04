from odoo import models, fields, api


class VehicleOnboardingWizard(models.TransientModel):
    """A short guided setup: create your first lot, your first brand/model,
    and an optional starter commission rule. Built as a classic multi-step
    wizard (a state field switching which group is shown) rather than
    hooking into Odoo's internal onboarding-banner framework, which is
    JS-heavy and not a stable, documented extension point for third-party
    modules.
    """
    _name = 'vehicle.onboarding.wizard'
    _description = 'Vehicle Dealership Setup Wizard'

    state = fields.Selection([
        ('lot', 'Lot / Showroom'),
        ('brand', 'Brand & Model'),
        ('commission', 'Commission Rule'),
        ('done', 'All Set'),
    ], default='lot', required=True)

    # Step 1: Lot / Showroom
    lot_name = fields.Char(string='Lot/Showroom Name', default='Main Showroom')
    lot_city = fields.Char(string='City')
    lot_capacity = fields.Integer(string='Capacity', default=20)

    # Step 2: Brand & Model
    brand_name = fields.Char(string='Brand Name', default='Toyota')
    model_name = fields.Char(string='Model Name', default='Camry')
    model_body_type = fields.Selection([
        ('sedan', 'Sedan'),
        ('suv', 'SUV'),
        ('truck', 'Truck'),
        ('coupe', 'Coupe'),
        ('convertible', 'Convertible'),
        ('hatchback', 'Hatchback'),
        ('wagon', 'Wagon'),
        ('van', 'Van'),
        ('minivan', 'Minivan'),
    ], string='Body Type', default='sedan')

    # Step 3: Commission Rule
    create_commission_rule = fields.Boolean(string='Create a starter commission rule', default=True)
    commission_rate = fields.Float(string='Commission Rate (%)', default=2.5)

    # Results, shown on the final step
    created_lot_id = fields.Many2one('vehicle.lot', readonly=True)
    created_brand_id = fields.Many2one('vehicle.brand', readonly=True)
    created_model_id = fields.Many2one('vehicle.model', readonly=True)

    def _reopen(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vehicle.onboarding.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_next(self):
        self.ensure_one()
        if self.state == 'lot':
            self.state = 'brand'
        elif self.state == 'brand':
            self.state = 'commission'
        elif self.state == 'commission':
            self._create_records()
            self.state = 'done'
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        order = ['lot', 'brand', 'commission', 'done']
        idx = order.index(self.state)
        if idx > 0:
            self.state = order[idx - 1]
        return self._reopen()

    def _create_records(self):
        self.ensure_one()
        if self.lot_name and not self.created_lot_id:
            self.created_lot_id = self.env['vehicle.lot'].create({
                'name': self.lot_name,
                'city': self.lot_city,
                'capacity': self.lot_capacity,
            })
        if self.brand_name and not self.created_brand_id:
            self.created_brand_id = self.env['vehicle.brand'].create({
                'name': self.brand_name,
            })
        if self.model_name and self.created_brand_id and not self.created_model_id:
            self.created_model_id = self.env['vehicle.model'].create({
                'name': self.model_name,
                'brand_id': self.created_brand_id.id,
                'body_type': self.model_body_type,
            })
        if self.create_commission_rule:
            self.env['vehicle.commission.rule'].create({
                'name': 'Starter Commission Rule',
                'margin_from': 0,
                'margin_to': 100,
                'commission_rate': self.commission_rate,
            })

    def action_finish(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}

    def action_go_to_vehicles(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicles',
            'res_model': 'vehicle.vehicle',
            'view_mode': 'list,kanban,form',
        }
