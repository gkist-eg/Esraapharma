# -*- coding: utf-8 -*-
# from odoo import http


# class CustomSale(http.Controller):
#     @http.route('/custom_sale/custom_sale/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_sale/custom_sale/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_sale.listing', {
#             'root': '/custom_sale/custom_sale',
#             'objects': http.request.env['custom_sale.custom_sale'].search([]),
#         })

#     @http.route('/custom_sale/custom_sale/objects/<model("custom_sale.custom_sale"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_sale.object', {
#             'object': obj
#         })
