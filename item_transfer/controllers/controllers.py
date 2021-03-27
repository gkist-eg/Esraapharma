# -*- coding: utf-8 -*-
# from odoo import http


# class ItemTransfer(http.Controller):
#     @http.route('/item_transfer/item_transfer/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/item_transfer/item_transfer/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('item_transfer.listing', {
#             'root': '/item_transfer/item_transfer',
#             'objects': http.request.env['item_transfer.item_transfer'].search([]),
#         })

#     @http.route('/item_transfer/item_transfer/objects/<model("item_transfer.item_transfer"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('item_transfer.object', {
#             'object': obj
#         })
