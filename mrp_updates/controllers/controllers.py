# -*- coding: utf-8 -*-
# from odoo import http


# class MrpUpdates(http.Controller):
#     @http.route('/mrp_updates/mrp_updates/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mrp_updates/mrp_updates/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('mrp_updates.listing', {
#             'root': '/mrp_updates/mrp_updates',
#             'objects': http.request.env['mrp_updates.mrp_updates'].search([]),
#         })

#     @http.route('/mrp_updates/mrp_updates/objects/<model("mrp_updates.mrp_updates"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mrp_updates.object', {
#             'object': obj
#         })
