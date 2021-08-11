from datetime import datetime, time

from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = "product.template"

    purchase_request = fields.Boolean(
        help="Check this box to generate Purchase Request instead of "
        "generating Requests For Quotation from procurement."
    )



