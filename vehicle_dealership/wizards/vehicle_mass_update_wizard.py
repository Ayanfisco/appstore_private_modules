from odoo import models, fields, api
from odoo.exceptions import UserError


class VehicleMassUpdateWizard(models.TransientModel):
    _name = 'vehicle.mass.update.wizard'
    _description = 'Mass Update Vehicles Wizard'

    vehicle_ids = fields.Many2many('vehicle.vehicle', string='Vehicles')

    # Location Update
    update_location = fields.Boolean(string='Update Location')
    location_id = fields.Many2one('stock.location', string='New Location',
                                  domain=[('usage', '=', 'internal')])

    # State Update
    update_state = fields.Boolean(string='Update Status')
    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('in_service', 'In Service'),
        ('unavailable', 'Unavailable'),
    ], string='New Status')

    # Price Update
    update_selling_price = fields.Boolean(string='Update Selling Price')
    selling_price = fields.Monetary(string='New Selling Price')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Discount
    apply_discount = fields.Boolean(string='Apply Discount')
    discount_percentage = fields.Float(string='Discount %', default=0.0)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            res['vehicle_ids'] = [(6, 0, active_ids)]
        return res

    def action_apply(self):
        self.ensure_one()
        if not self.vehicle_ids:
            raise UserError('No vehicles selected!')

        update_vals = {}

        if self.update_location and self.location_id:
            update_vals['location_id'] = self.location_id.id

        if self.update_state and self.state:
            # Check if vehicles can be updated to sold/reserved
            if self.state in ['sold', 'reserved']:
                for vehicle in self.vehicle_ids:
                    if vehicle.state == 'sold':
                        raise UserError(f'Vehicle {vehicle.name} is already sold and cannot be updated!')
            update_vals['state'] = self.state

        if self.update_selling_price and self.selling_price:
            update_vals['selling_price'] = self.selling_price

        if self.apply_discount and self.discount_percentage:
            for vehicle in self.vehicle_ids:
                if vehicle.selling_price:
                    discount_amount = vehicle.selling_price * (self.discount_percentage / 100)
                    new_price = vehicle.selling_price - discount_amount
                    vehicle.selling_price = new_price

        if update_vals:
            self.vehicle_ids.write(update_vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'{len(self.vehicle_ids)} vehicle(s) updated successfully!',
                'type': 'success',
                'sticky': False,
            }
        }
