# -*- coding: utf-8 -*-
# from odoo import http


# class Report(http.Controller):
#     @http.route('/report/report/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/report/report/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('report.listing', {
#             'root': '/report/report',
#             'objects': http.request.env['report.report'].search([]),
#         })

#     @http.route('/report/report/objects/<model("report.report"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('report.object', {
#             'object': obj
#         })
