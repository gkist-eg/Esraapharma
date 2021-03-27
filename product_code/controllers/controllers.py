# -*- coding: utf-8 -*-
# from odoo import http


# class ProductCode(http.Controller):
#     @http.route('/product_code/product_code/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/product_code/product_code/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('product_code.listing', {
#             'root': '/product_code/product_code',
#             'objects': http.request.env['product_code.product_code'].search([]),
#         })

#     @http.route('/product_code/product_code/objects/<model("product_code.product_code"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('product_code.object', {
#             'object': obj
#         })
