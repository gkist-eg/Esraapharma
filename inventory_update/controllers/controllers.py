# -*- coding: utf-8 -*-
# from odoo import http


# class InventoryUpdate(http.Controller):
#     @http.route('/inventory_update/inventory_update/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/inventory_update/inventory_update/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('inventory_update.listing', {
#             'root': '/inventory_update/inventory_update',
#             'objects': http.request.env['inventory_update.inventory_update'].search([]),
#         })

#     @http.route('/inventory_update/inventory_update/objects/<model("inventory_update.inventory_update"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('inventory_update.object', {
#             'object': obj
#         })
