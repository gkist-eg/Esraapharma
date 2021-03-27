# -*- coding: utf-8 -*-
# from odoo import http


# class SendNotification(http.Controller):
#     @http.route('/send_notification/send_notification/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/send_notification/send_notification/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('send_notification.listing', {
#             'root': '/send_notification/send_notification',
#             'objects': http.request.env['send_notification.send_notification'].search([]),
#         })

#     @http.route('/send_notification/send_notification/objects/<model("send_notification.send_notification"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('send_notification.object', {
#             'object': obj
#         })
