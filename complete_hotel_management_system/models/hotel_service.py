from odoo import models, fields, api


class HotelService(models.Model):
    _name = 'hotel.service'
    _description = 'Hotel Service'
    _order = 'sequence, name'

    name = fields.Char(string='Service Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)

    category = fields.Selection([
        ('room_service', 'Room Service'),
        ('laundry', 'Laundry'),
        ('spa', 'Spa & Wellness'),
        ('restaurant', 'Restaurant'),
        ('transport', 'Transport'),
        ('other', 'Other'),
    ], string='Category', required=True, default='other')

    price = fields.Float(string='Price', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    # Product integration (optional)
    product_id = fields.Many2one('product.product', string='Related Product')


class HotelServiceLine(models.Model):
    _name = 'hotel.service.line'
    _description = 'Hotel Service Line'
    _order = 'date desc, id desc'

    reservation_id = fields.Many2one('hotel.reservation', string='Reservation', required=True, ondelete='cascade')
    service_id = fields.Many2one('hotel.service', string='Service', required=True)

    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    price_unit = fields.Float(string='Unit Price', required=True)

    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_price_subtotal', store=True,
                                     currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', related='reservation_id.currency_id')

    description = fields.Text(string='Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.quantity * rec.price_unit

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            self.price_unit = self.service_id.price
            self.description = self.service_id.description