# -*- coding: utf-8 -*-
# from odoo import http


# class MrpItemRequest(http.Controller):
#     @http.route('/mrp_item_request/mrp_item_request/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mrp_item_request/mrp_item_request/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('mrp_item_request.listing', {
#             'root': '/mrp_item_request/mrp_item_request',
#             'objects': http.request.env['mrp_item_request.mrp_item_request'].search([]),
#         })

#     @http.route('/mrp_item_request/mrp_item_request/objects/<model("mrp_item_request.mrp_item_request"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mrp_item_request.object', {
#             'object': obj
#         })
