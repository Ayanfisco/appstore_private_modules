from odoo import models, fields, tools


class VehicleHistory(models.Model):
    """Read-only aggregated timeline of everything that happened to a vehicle:
    acquisition, sale, service visits and inspections, newest first.
    Backed by a SQL view instead of a table, so it always reflects the
    underlying records with no extra data to maintain.
    """
    _name = 'vehicle.history'
    _description = 'Vehicle History Timeline'
    _auto = False
    _order = 'event_date desc, id desc'

    vehicle_id = fields.Many2one('vehicle.vehicle', string='Vehicle', readonly=True)
    event_date = fields.Date(string='Date', readonly=True)
    event_type = fields.Selection([
        ('purchase', 'Acquisition'),
        ('sale', 'Sale'),
        ('service', 'Service'),
        ('inspection', 'Inspection'),
    ], string='Event Type', readonly=True)
    title = fields.Char(string='Event', readonly=True)
    description = fields.Char(string='Reference', readonly=True)
    amount = fields.Monetary(string='Amount', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    state = fields.Char(string='Status', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %(table)s AS (
                SELECT
                    (1000000000 + p.id) AS id,
                    p.vehicle_id AS vehicle_id,
                    p.actual_arrival AS event_date,
                    'purchase' AS event_type,
                    CONCAT('Acquired from ', COALESCE(sp.name, 'supplier')) AS title,
                    p.name AS description,
                    p.total_cost AS amount,
                    p.currency_id AS currency_id,
                    p.state AS state
                FROM vehicle_purchase p
                LEFT JOIN res_partner sp ON sp.id = p.supplier_id
                WHERE p.vehicle_id IS NOT NULL

                UNION ALL

                SELECT
                    (2000000000 + s.id) AS id,
                    s.vehicle_id AS vehicle_id,
                    s.sale_date AS event_date,
                    'sale' AS event_type,
                    CONCAT('Sold to ', COALESCE(cp.name, 'customer')) AS title,
                    s.name AS description,
                    s.final_price AS amount,
                    s.currency_id AS currency_id,
                    s.state AS state
                FROM vehicle_sale s
                LEFT JOIN res_partner cp ON cp.id = s.customer_id
                WHERE s.vehicle_id IS NOT NULL

                UNION ALL

                SELECT
                    (3000000000 + sv.id) AS id,
                    sv.vehicle_id AS vehicle_id,
                    sv.service_date AS event_date,
                    'service' AS event_type,
                    CONCAT('Service: ', COALESCE(sv.service_type, 'general')) AS title,
                    sv.name AS description,
                    sv.total_cost AS amount,
                    sv.currency_id AS currency_id,
                    sv.state AS state
                FROM vehicle_service sv
                WHERE sv.vehicle_id IS NOT NULL

                UNION ALL

                SELECT
                    (4000000000 + i.id) AS id,
                    i.vehicle_id AS vehicle_id,
                    i.inspection_date AS event_date,
                    'inspection' AS event_type,
                    CONCAT('Inspection: ', COALESCE(i.inspection_type, 'general')) AS title,
                    i.name AS description,
                    i.estimated_repair_cost AS amount,
                    i.currency_id AS currency_id,
                    CASE WHEN i.passed THEN 'passed' ELSE 'pending' END AS state
                FROM vehicle_inspection i
                WHERE i.vehicle_id IS NOT NULL
            )
        """ % {'table': self._table})
