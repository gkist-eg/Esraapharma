
from odoo import models, fields, _,api


class ProductUpdate(models.Model):
    _inherit = 'product.template'

    mfg = fields.Float('Pack Size', digits='Product Unit of Measure', index=True,store=True)
    pro_type = fields.Selection([('eda', 'EDA'), ('nfsa', 'NFSA'), ('nni', 'NNI')], string='Type', index=True,store=True)
