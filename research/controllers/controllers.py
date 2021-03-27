# -*- coding: utf-8 -*-
# from odoo import http


# class Research(http.Controller):
#     @http.route('/research/research/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/research/research/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('research.listing', {
#             'root': '/research/research',
#             'objects': http.request.env['research.research'].search([]),
#         })

#     @http.route('/research/research/objects/<model("research.research"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('research.object', {
#             'object': obj
#         })
