
from odoo import models, fields, api


class lot_edit(models.TransientModel):
    _inherit = 'stock.production.lot'


    qc_attach = fields.Binary()

    def lot_edit(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['stock.production.lot'].browse(active_ids):

            record.lot_edit()
        return {'type': 'ir.actions.act_window_close'}
