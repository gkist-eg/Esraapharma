# -*- coding: utf-8 -*-
# from odoo import http


# class InventoryReturn(http.Controller):
#     @http.route('/inventory_return/inventory_return/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/inventory_return/inventory_return/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('inventory_return.listing', {
#             'root': '/inventory_return/inventory_return',
#             'objects': http.request.env['inventory_return.inventory_return'].search([]),
#         })

#     @http.route('/inventory_return/inventory_return/objects/<model("inventory_return.inventory_return"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('inventory_return.object', {
#             'object': obj
#         })
