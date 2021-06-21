# -*- coding: utf-8 -*-
# from odoo import http


# class MaintananceEdit(http.Controller):
#     @http.route('/maintanance_edit/maintanance_edit/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/maintanance_edit/maintanance_edit/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('maintanance_edit.listing', {
#             'root': '/maintanance_edit/maintanance_edit',
#             'objects': http.request.env['maintanance_edit.maintanance_edit'].search([]),
#         })

#     @http.route('/maintanance_edit/maintanance_edit/objects/<model("maintanance_edit.maintanance_edit"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('maintanance_edit.object', {
#             'object': obj
#         })
