# -*- coding: utf-8 -*-
from odoo import http

# class ReserveInvoices(http.Controller):
#     @http.route('/reserve_invoices/reserve_invoices/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/reserve_invoices/reserve_invoices/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('reserve_invoices.listing', {
#             'root': '/reserve_invoices/reserve_invoices',
#             'objects': http.request.env['reserve_invoices.reserve_invoices'].search([]),
#         })

#     @http.route('/reserve_invoices/reserve_invoices/objects/<model("reserve_invoices.reserve_invoices"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('reserve_invoices.object', {
#             'object': obj
#         })