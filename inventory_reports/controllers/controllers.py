# -*- coding: utf-8 -*-
# from odoo import http


# class InventoryReports(http.Controller):
#     @http.route('/inventory_reports/inventory_reports/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/inventory_reports/inventory_reports/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('inventory_reports.listing', {
#             'root': '/inventory_reports/inventory_reports',
#             'objects': http.request.env['inventory_reports.inventory_reports'].search([]),
#         })

#     @http.route('/inventory_reports/inventory_reports/objects/<model("inventory_reports.inventory_reports"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('inventory_reports.object', {
#             'object': obj
#         })
