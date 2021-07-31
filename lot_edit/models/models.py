
from odoo import models, fields, api


class lot_edit(models.TransientModel):
    _name = 'stock.production.lot.edit'


    qc_attach = fields.Binary()

