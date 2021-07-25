from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class ExpenseEdit(models.Model):
    _inherit = 'hr.expense'
    catg_id = fields.Many2one('product.category', store=True, string='Expense Category', required=True,
                              domain="[('is_expense','=',True)]", )

    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True, tracking=True,
                                 states={'draft': [('readonly', False)], 'reported': [('readonly', False)],
                                         'refused': [('readonly', False)]},
                                 domain="[('can_be_expensed', '=', True),('categ_id', 'in', [catg_id]), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                 ondelete='restrict')

    @api.onchange('catg_id')
    def _onchange_catg_id(self):
        if  self.catg_id:

            self.product_id = False





