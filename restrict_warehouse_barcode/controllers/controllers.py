# -*- coding: utf-8 -*-
# from odoo import http


# class RestrictWarehouseBarcode(http.Controller):
#     @http.route('/restrict_warehouse_barcode/restrict_warehouse_barcode/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/restrict_warehouse_barcode/restrict_warehouse_barcode/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('restrict_warehouse_barcode.listing', {
#             'root': '/restrict_warehouse_barcode/restrict_warehouse_barcode',
#             'objects': http.request.env['restrict_warehouse_barcode.restrict_warehouse_barcode'].search([]),
#         })

#     @http.route('/restrict_warehouse_barcode/restrict_warehouse_barcode/objects/<model("restrict_warehouse_barcode.restrict_warehouse_barcode"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('restrict_warehouse_barcode.object', {
#             'object': obj
#         })
