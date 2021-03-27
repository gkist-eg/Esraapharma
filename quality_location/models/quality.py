import ast
from datetime import datetime
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.osv.expression import OR


class QualityPoint(models.Model):
    _inherit = "quality.point"

