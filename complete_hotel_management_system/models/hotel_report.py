from odoo import models, fields, tools


class HotelRevenueReport(models.Model):
    """
    SQL-based read-only view that computes hotel KPIs directly from
    confirmed reservations:  ADR, RevPAR, occupancy rate, and revenue
    broken down by room type, property, booking source, and month.
    """
    _name = 'hotel.revenue.report'
    _description = 'Hotel Revenue & Occupancy Report'
    _auto = False
    _order = 'check_in desc'

    # Dimensions
    name = fields.Char(string='Reservation', readonly=True)
    property_id = fields.Many2one('hotel.property', string='Property', readonly=True)
    room_type_id = fields.Many2one('hotel.room.type', string='Room Type', readonly=True)
    guest_id = fields.Many2one('hotel.guest', string='Guest', readonly=True)
    source = fields.Selection([
        ('direct', 'Direct Booking'),
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('walk_in', 'Walk-in'),
        ('online', 'Online Portal'),
        ('ota', 'Online Travel Agency'),
    ], string='Booking Source', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', readonly=True)
    invoice_status = fields.Selection([
        ('not_invoiced', 'Not Invoiced'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
    ], string='Invoice Status', readonly=True)

    # Time
    check_in = fields.Date(string='Check-in', readonly=True)
    check_out = fields.Date(string='Check-out', readonly=True)
    month = fields.Char(string='Month', readonly=True)
    year = fields.Char(string='Year', readonly=True)

    # KPIs
    nights = fields.Integer(string='Nights', readonly=True)
    adults = fields.Integer(string='Adults', readonly=True)
    room_rate = fields.Float(string='Room Rate / Night', readonly=True)
    room_revenue = fields.Float(string='Room Revenue', readonly=True)
    service_revenue = fields.Float(string='Service Revenue', readonly=True)
    total_revenue = fields.Float(string='Total Revenue (excl. tax)', readonly=True)
    tax_amount = fields.Float(string='Tax Amount', readonly=True)
    total_amount = fields.Float(string='Total Amount (incl. tax)', readonly=True)
    deposit_amount = fields.Float(string='Deposit Received', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW hotel_revenue_report AS (
                SELECT
                    r.id                                        AS id,
                    r.name                                      AS name,
                    r.property_id                               AS property_id,
                    r.room_type_id                              AS room_type_id,
                    r.guest_id                                  AS guest_id,
                    r.source                                    AS source,
                    r.state                                     AS state,
                    r.invoice_status                            AS invoice_status,
                    r.check_in                                  AS check_in,
                    r.check_out                                 AS check_out,
                    TO_CHAR(r.check_in, 'YYYY-MM')             AS month,
                    TO_CHAR(r.check_in, 'YYYY')                AS year,
                    r.nights                                    AS nights,
                    r.adults                                    AS adults,
                    r.room_rate                                 AS room_rate,
                    (r.room_rate * r.nights)                   AS room_revenue,
                    COALESCE(svc.service_total, 0)             AS service_revenue,
                    (r.room_rate * r.nights)
                        + COALESCE(svc.service_total, 0)       AS total_revenue,
                    r.tax_amount                                AS tax_amount,
                    r.total_amount                             AS total_amount,
                    COALESCE(r.deposit_amount, 0)              AS deposit_amount
                FROM hotel_reservation r
                LEFT JOIN (
                    SELECT reservation_id,
                           SUM(price_subtotal) AS service_total
                    FROM hotel_service_line
                    GROUP BY reservation_id
                ) svc ON svc.reservation_id = r.id
                WHERE r.state NOT IN ('cancelled', 'draft')
            )
        """)


class HotelOccupancyReport(models.Model):
    """
    Aggregated monthly occupancy view.
    Shows total room-nights available vs sold per property per month.
    """
    _name = 'hotel.occupancy.report'
    _description = 'Hotel Occupancy Report'
    _auto = False
    _order = 'month desc, property_id'

    property_id = fields.Many2one('hotel.property', string='Property', readonly=True)
    month = fields.Char(string='Month', readonly=True)
    year = fields.Char(string='Year', readonly=True)
    room_type_id = fields.Many2one('hotel.room.type', string='Room Type', readonly=True)
    reservations = fields.Integer(string='Reservations', readonly=True)
    room_nights_sold = fields.Integer(string='Room Nights Sold', readonly=True)
    total_guests = fields.Integer(string='Total Guests', readonly=True)
    total_room_revenue = fields.Float(string='Room Revenue', readonly=True)
    avg_daily_rate = fields.Float(string='ADR (Avg Daily Rate)', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW hotel_occupancy_report AS (
                SELECT
                    ROW_NUMBER() OVER ()                        AS id,
                    r.property_id                               AS property_id,
                    TO_CHAR(r.check_in, 'YYYY-MM')             AS month,
                    TO_CHAR(r.check_in, 'YYYY')                AS year,
                    r.room_type_id                              AS room_type_id,
                    COUNT(r.id)                                 AS reservations,
                    SUM(r.nights)                               AS room_nights_sold,
                    SUM(r.total_guests)                         AS total_guests,
                    SUM(r.room_rate * r.nights)                 AS total_room_revenue,
                    CASE WHEN SUM(r.nights) > 0
                         THEN SUM(r.room_rate * r.nights) / SUM(r.nights)
                         ELSE 0 END                             AS avg_daily_rate
                FROM hotel_reservation r
                WHERE r.state NOT IN ('cancelled', 'draft')
                GROUP BY r.property_id, TO_CHAR(r.check_in, 'YYYY-MM'),
                         TO_CHAR(r.check_in, 'YYYY'), r.room_type_id
            )
        """)
