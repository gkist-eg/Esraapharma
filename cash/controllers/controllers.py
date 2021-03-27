# -*- coding: utf-8 -*-
# from odoo import http


# class Cash(http.Controller):
#     @http.route('/cash/cash/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cash/cash/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('cash.listing', {
#             'root': '/cash/cash',
#             'objects': http.request.env['cash.cash'].search([]),
#         })

#     @http.route('/cash/cash/objects/<model("cash.cash"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cash.object', {
#             'object': obj
#         })
