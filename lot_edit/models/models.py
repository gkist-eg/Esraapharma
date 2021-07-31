
from odoo import models, fields, api



class lot_edit_inhireit(models.Model):
    _inherit = 'stock.production.lot'

    attachment_qc = fields.Many2many('ir.attachment', string='QC Attachments', )
