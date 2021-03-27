# -*- coding: utf-8 -*-
# from odoo import http


# class ItemRequest(http.Controller):
#     @http.route('/item_request/item_request/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/item_request/item_request/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('item_request.listing', {
#             'root': '/item_request/item_request',
#             'objects': http.request.env['item_request.item_request'].search([]),
#         })

#     @http.route('/item_request/item_request/objects/<model("item_request.item_request"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('item_request.object', {
#             'object': obj
#         })
