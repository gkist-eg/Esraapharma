# -*- coding: utf-8 -*-
# from odoo import http


# class RealCost(http.Controller):
#     @http.route('/real_cost/real_cost/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/real_cost/real_cost/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('real_cost.listing', {
#             'root': '/real_cost/real_cost',
#             'objects': http.request.env['real_cost.real_cost'].search([]),
#         })

#     @http.route('/real_cost/real_cost/objects/<model("real_cost.real_cost"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('real_cost.object', {
#             'object': obj
#         })
