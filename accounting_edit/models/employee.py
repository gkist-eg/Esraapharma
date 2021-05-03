from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class employyee_edit(models.Model):
    _inherit = 'hr.employee'
    arabic_name = fields.Char(
        string='Arabic Name',
    )