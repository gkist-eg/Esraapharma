from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class ExpenseEdit(models.Model):
    _inherit = 'hr.expense'
    catg_id = fields.Many2one('product.category', store=True, string='Expense Category',
                              domain="[('is_expense','=',True)]", )

    unit_amount = fields.Float("Unit Price", compute='_compute_from_product_id_company_id', store=True, required=True, copy=True,
        states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)],'approved': [('readonly', False)]}, digits='Product Price')
    product_id = fields.Many2one('product.product', string='Product', readonly=True, tracking=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'approved': [('readonly', False)], 'refused': [('readonly', False)]}, domain="[('can_be_expensed', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", ondelete='restrict')
