
from odoo import models, fields, api


class lot_edit(models.TransientModel):
    _name = 'stock.production.lot.edit'


    qc_attach = fields.Binary()

    def lot_edit(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['stock.production.lot'].browse(active_ids):

            record.button_approve_double_visit()
        return {'type': 'ir.actions.act_window_close'}
