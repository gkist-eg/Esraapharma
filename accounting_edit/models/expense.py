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
class ExpenseEditsheet(models.Model):
    _inherit = 'hr.expense.sheet'

    @api.model
    def _get_employee_id_domainx(self):
        res = [('id', '=', 0)]  # Nothing accepted by domain, by default
        if self.env.user.employee_ids:
            user = self.env.user
            employee = self.env.user.employee_id
            res = [
                '|', '|', '|',
                ('department_id.manager_id', '=', employee.id),
                ('parent_id', '=', employee.id),
                ('id', '=', employee.id),
                ('expense_manager_id', '=', user.id),
                '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id),
            ]
        elif self.env.user.employee_id:
            employee = self.env.user.employee_id
            res = [('id', '=', employee.id), '|', ('company_id', '=', False),
                   ('company_id', '=', employee.company_id.id)]
        return res


    @api.model
    def _default_employee_id(self):
        employee = self.env.user.employee_id
        if not employee and not self.env.user.has_group('hr_expense.group_hr_expense_team_approver'):
            raise ValidationError(_('The current user has no related employee. Please, create one.'))
        return employee

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True, tracking=True, states={'draft': [('readonly', False)]}, default=_default_employee_id, check_company=True, domain= lambda self: self.env['hr.expense']._get_employee_id_domainx())


