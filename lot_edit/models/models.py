from odoo import models, fields, api


class lot_edit_inhireit(models.Model):
    _inherit = 'stock.production.lot'

    attachment_qc = fields.Many2many('ir.attachment', 'attachment_qc_lot_rel', string='Attachments QC ', )


class lot_edit(models.TransientModel):
    _name = "stock.production.lot.confirm"
    _description = "Confirm the selected plan"

    def plan_confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

