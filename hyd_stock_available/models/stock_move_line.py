from odoo import api, fields, models


class StockMoveLine(models.Model):

    _inherit = "stock.move.line"
    _name = "stock.move.line"

    not_reserved = fields.Float(
        string="Available Quantity",
        compute="_compute_available_qty",
        store=True,
        readonly=True,
    )

    @api.depends("product_id", "product_uom_qty", "lot_id")
    def _compute_available_qty(self):
        for record in self:
            if record.product_id and record.move_id.state != "done" and record.location_id.usage in ('internal', 'transit'):
                if record.lot_id:
                    quants = sum(x.available_quantity for x in record.lot_id.quant_ids.filtered(lambda quant: quant.location_id == record.location_id))
                    actual_qty = quants + record.product_uom_id._compute_quantity(record.product_uom_qty, record.product_id.uom_id, rounding_method='HALF-UP')
                    record.not_reserved = actual_qty
                else:
                    record.not_reserved = 0.0
            else:
                record.not_reserved = 0.0

