# -*- coding: utf-8 -*-
# from odoo import http


# class PurchaseForeign(http.Controller):
#     @http.route('/purchase_foreign/purchase_foreign/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/purchase_foreign/purchase_foreign/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('purchase_foreign.listing', {
#             'root': '/purchase_foreign/purchase_foreign',
#             'objects': http.request.env['purchase_foreign.purchase_foreign'].search([]),
#         })

#     @http.route('/purchase_foreign/purchase_foreign/objects/<model("purchase_foreign.purchase_foreign"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('purchase_foreign.object', {
#             'object': obj
#         })
