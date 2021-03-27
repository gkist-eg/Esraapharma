from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class ProductExpense(models.Model):
    _inherit = 'product.category'
    is_expense = fields.Boolean(string='Is Expense', store=True)
