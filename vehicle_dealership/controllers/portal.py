from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class VehiclePortal(CustomerPortal):
    """Read-only customer-facing pages: a portal user (i.e. our customer) can
    see the vehicles they bought and each sale's status, warranty, and
    service history. They cannot create, edit, or delete anything here -
    this only ever queries their own records (enforced both by the
    ir.rule on vehicle.sale and by the access check below), and it never
    touches internal-only data such as accounting or inventory records,
    in line with the Odoo Apps Store policy on portal/internal separation.
    """

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'vehicle_count' in counters:
            partner = request.env.user.partner_id
            values['vehicle_count'] = request.env['vehicle.sale'].search_count([
                ('customer_id', '=', partner.id),
            ]) if request.env['vehicle.sale'].check_access_rights('read', raise_exception=False) else 0
        return values

    def _vehicle_sale_get_page_view_values(self, sale, access_token, **kwargs):
        values = self._prepare_portal_layout_values()
        values.update({
            'sale': sale,
            'vehicle': sale.vehicle_id,
            'service_history': sale.vehicle_id.service_ids.filtered(
                lambda s: s.state == 'completed'),
            'access_token': access_token,
            'page_name': 'vehicle_sale',
        })
        return values

    @http.route(['/my/vehicles', '/my/vehicles/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_vehicles(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        VehicleSale = request.env['vehicle.sale']
        partner = request.env.user.partner_id
        domain = [('customer_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Sale Date'), 'order': 'sale_date desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
        }
        sortby = sortby or 'date'
        order = searchbar_sortings[sortby]['order']

        sale_count = VehicleSale.search_count(domain)
        pager = portal_pager(
            url='/my/vehicles',
            url_args={'sortby': sortby},
            total=sale_count,
            page=page,
            step=self._items_per_page,
        )
        sales = VehicleSale.search(domain, order=order, limit=self._items_per_page,
                                   offset=pager['offset'])

        values.update({
            'sales': sales,
            'page_name': 'vehicle_sale',
            'pager': pager,
            'default_url': '/my/vehicles',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render('vehicle_dealership.portal_my_vehicles', values)

    @http.route(['/my/vehicles/<int:sale_id>'], type='http', auth='user', website=True)
    def portal_vehicle_sale_page(self, sale_id, access_token=None, **kw):
        try:
            sale_sudo = self._document_check_access('vehicle.sale', sale_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._vehicle_sale_get_page_view_values(sale_sudo, access_token, **kw)
        return request.render('vehicle_dealership.portal_vehicle_sale_page', values)
