from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError



class account(models.Model):
    _inherit = 'account.account'
    account = fields.Selection(
        [('a', 'Loans'), ('b', 'Custody'), ('c', 'Cost Center'), ('d', 'Safe'), ('e', 'Bank'), ('f', 'Supplier'),
         ('discount', 'Allowance Discount')], string='Account Type')
