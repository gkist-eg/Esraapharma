# -*- coding: utf-8 -*-
# from odoo import http


# class AccountingEdit(http.Controller):
#     @http.route('/accounting_edit/accounting_edit/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/accounting_edit/accounting_edit/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('accounting_edit.listing', {
#             'root': '/accounting_edit/accounting_edit',
#             'objects': http.request.env['accounting_edit.accounting_edit'].search([]),
#         })

#     @http.route('/accounting_edit/accounting_edit/objects/<model("accounting_edit.accounting_edit"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('accounting_edit.object', {
#             'object': obj
#         })
