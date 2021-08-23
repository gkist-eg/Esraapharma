from odoo import models, fields

class AccountA(models.Model):
    _inherit = "account.account"
    name_arab=fields.Char('Arabic Name')

