# -*- coding: utf-8 -*-
# from odoo import http


# class RestrictWarehouse(http.Controller):
#     @http.route('/restrict_warehouse/restrict_warehouse/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/restrict_warehouse/restrict_warehouse/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('restrict_warehouse.listing', {
#             'root': '/restrict_warehouse/restrict_warehouse',
#             'objects': http.request.env['restrict_warehouse.restrict_warehouse'].search([]),
#         })

#     @http.route('/restrict_warehouse/restrict_warehouse/objects/<model("restrict_warehouse.restrict_warehouse"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('restrict_warehouse.object', {
#             'object': obj
#         })
