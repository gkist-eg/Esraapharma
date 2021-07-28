# -*- coding: utf-8 -*-
from odoo import http

# class UsersSignature(http.Controller):
#     @http.route('/users_signature/users_signature/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/users_signature/users_signature/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('users_signature.listing', {
#             'root': '/users_signature/users_signature',
#             'objects': http.request.env['users_signature.users_signature'].search([]),
#         })

#     @http.route('/users_signature/users_signature/objects/<model("users_signature.users_signature"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('users_signature.object', {
#             'object': obj
#         })