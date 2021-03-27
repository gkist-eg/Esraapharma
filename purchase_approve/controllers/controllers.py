# -*- coding: utf-8 -*-
# from odoo import http


# class PurchaseApprove(http.Controller):
#     @http.route('/purchase_approve/purchase_approve/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/purchase_approve/purchase_approve/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('purchase_approve.listing', {
#             'root': '/purchase_approve/purchase_approve',
#             'objects': http.request.env['purchase_approve.purchase_approve'].search([]),
#         })

#     @http.route('/purchase_approve/purchase_approve/objects/<model("purchase_approve.purchase_approve"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('purchase_approve.object', {
#             'object': obj
#         })
