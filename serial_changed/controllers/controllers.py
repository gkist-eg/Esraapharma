# -*- coding: utf-8 -*-
# from odoo import http


# class SerialChanged(http.Controller):
#     @http.route('/serial_changed/serial_changed/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/serial_changed/serial_changed/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('serial_changed.listing', {
#             'root': '/serial_changed/serial_changed',
#             'objects': http.request.env['serial_changed.serial_changed'].search([]),
#         })

#     @http.route('/serial_changed/serial_changed/objects/<model("serial_changed.serial_changed"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('serial_changed.object', {
#             'object': obj
#         })
