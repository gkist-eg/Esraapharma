# -*- coding: utf-8 -*-
# from odoo import http


# class AddProductCategory(http.Controller):
#     @http.route('/add_product_category/add_product_category/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/add_product_category/add_product_category/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('add_product_category.listing', {
#             'root': '/add_product_category/add_product_category',
#             'objects': http.request.env['add_product_category.add_product_category'].search([]),
#         })

#     @http.route('/add_product_category/add_product_category/objects/<model("add_product_category.add_product_category"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('add_product_category.object', {
#             'object': obj
#         })
