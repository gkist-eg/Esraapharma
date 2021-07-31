
from odoo import models, fields, api


class lot_edit(models.Model):
    _inherit = 'stock.production.lot.edit'


    qc_attach = fields.Binary()

