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
    user_id = fields.Many2one('res.users', 'Manager', compute='_compute_from_employee_id', store=True, readonly=True, copy=False, states={'draft': [('readonly', True)]}, tracking=True, domain=lambda self: [('groups_id', 'in', self.env.ref('hr_expense.group_hr_expense_team_approver').id)])



    def _get_employee_id_domain(self):
        res = [('id', '=', 0)] # Nothing accepted by domain, by default
        if self.user_has_groups('hr_expense.group_hr_expense_user') or self.user_has_groups('account.group_account_user'):
            res = "['|', ('company_id', '=', False), ('company_id', '=', company_id)]"  # Then, domain accepts everything
        elif self.user_has_groups('hr_expense.group_hr_expense_team_approver') and self.env.user.employee_ids:
            user = self.env.user
            employee = self.env.user.employee_id
            res = [
                '|', '|', '|','|',
                ('department_id.manager_id', '=', employee.id),
                ('parent_id', '=', employee.id),
                ('id', '=', employee.id),
                ('parent_id.user_id', '=', employee.id),

                ('expense_manager_id', '=', user.id),
                '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id),
            ]
        elif self.env.user.employee_id:
            employee = self.env.user.employee_id
            res = [('id', '=', employee.id), '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id)]
        return res




