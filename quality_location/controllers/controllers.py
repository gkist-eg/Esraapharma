# -*- coding: utf-8 -*-
# from odoo import http


# class QualityLocation(http.Controller):
#     @http.route('/quality_location/quality_location/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/quality_location/quality_location/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('quality_location.listing', {
#             'root': '/quality_location/quality_location',
#             'objects': http.request.env['quality_location.quality_location'].search([]),
#         })

#     @http.route('/quality_location/quality_location/objects/<model("quality_location.quality_location"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('quality_location.object', {
#             'object': obj
#         })
