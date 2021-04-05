# -*- coding: utf-8 -*-
# from odoo import http


# class PurchaseReport(http.Controller):
#     @http.route('/purchase_report/purchase_report/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/purchase_report/purchase_report/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('purchase_report.listing', {
#             'root': '/purchase_report/purchase_report',
#             'objects': http.request.env['purchase_report.purchase_report'].search([]),
#         })

#     @http.route('/purchase_report/purchase_report/objects/<model("purchase_report.purchase_report"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('purchase_report.object', {
#             'object': obj
#         })
