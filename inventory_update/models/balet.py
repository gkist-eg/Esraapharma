from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BaletLocation(models.Model):
    _name = 'balet.location'

    name = fields.Char('Name', required=True, store=True)

    _sql_constraints = [('name_unique', 'unique(name)', 'name already exists!')]