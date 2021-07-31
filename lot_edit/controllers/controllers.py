# -*- coding: utf-8 -*-
# from odoo import http


# class LotEdit(http.Controller):
#     @http.route('/lot_edit/lot_edit/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/lot_edit/lot_edit/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('lot_edit.listing', {
#             'root': '/lot_edit/lot_edit',
#             'objects': http.request.env['lot_edit.lot_edit'].search([]),
#         })

#     @http.route('/lot_edit/lot_edit/objects/<model("lot_edit.lot_edit"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('lot_edit.object', {
#             'object': obj
#         })
