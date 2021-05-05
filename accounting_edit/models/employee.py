from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class employyee_edit(models.Model):
    _inherit = 'hr.employee'
    arabic_name = fields.Char(
        string='Arabic Name',
    )


class user_edit(models.Model):
    _inherit = 'res.users'
    employee_arabic_name = fields.Char(related='employee_id.arabic_name', string="Arabic Name", readonly=False,
                                       related_sudo=False)
