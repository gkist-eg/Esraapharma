# -*- coding: utf-8 -*-
# from odoo import http


# class PurchaseTerms(http.Controller):
#     @http.route('/purchase_terms/purchase_terms/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/purchase_terms/purchase_terms/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('purchase_terms.listing', {
#             'root': '/purchase_terms/purchase_terms',
#             'objects': http.request.env['purchase_terms.purchase_terms'].search([]),
#         })

#     @http.route('/purchase_terms/purchase_terms/objects/<model("purchase_terms.purchase_terms"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('purchase_terms.object', {
#             'object': obj
#         })
