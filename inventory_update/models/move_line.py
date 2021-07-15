from odoo import models, fields, api
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_repr, float_round
from odoo.tools.misc import format_date
from re import findall as regex_findall


class StockInventoryLine(models.Model):
    _inherit = 'stock.inventory.line'
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        required=True, readonly=False)


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    def action_validate(self):
        if not self.exists():
            return
        self.ensure_one()
        if self.state != 'confirm':
            raise UserError(_(
                "You can't validate the inventory '%s', maybe this inventory "
                "has been already validated or isn't ready.", self.name))
        inventory_lines = self.line_ids.filtered(lambda l: l.product_id.tracking in ['lot',
                                                                                     'serial'] and not l.prod_lot_id and l.theoretical_qty != l.product_qty)
        lines = self.line_ids.filtered(lambda l: float_compare(l.product_qty, 1,
                                                               precision_rounding=l.product_uom_id.rounding) > 0 and l.product_id.tracking == 'serial' and l.prod_lot_id)
        if inventory_lines and not lines:
            wiz_lines = [(0, 0, {'product_id': product.id, 'tracking': product.tracking}) for product in
                         inventory_lines.mapped('product_id')]
            wiz = self.env['stock.track.confirmation'].create({'inventory_id': self.id, 'tracking_line_ids': wiz_lines})
            return {
                'name': _('Tracked Products in Inventory Adjustment'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_model': 'stock.track.confirmation',
                'target': 'new',
                'res_id': wiz.id,
            }
        self._action_done()
        self.line_ids._check_company()
        self._check_company()
        return True


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    _order = 'product_id,id'
    batch = fields.Char('Batch Number', store=True, related='lot_id.ref', index=True)
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True, index=True)

    @api.onchange('product_id', 'product_uom_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.id and self.user_has_groups('stock.group_stock_multi_locations'):
                self.location_dest_id = self.location_dest_id._get_putaway_strategy \
                                            (self.product_id) or self.location_dest_id
            if self.picking_id:
                product = self.product_id.with_context(lang=self.picking_id.partner_id.lang or self.env.user.lang)
                self.description_picking = product._get_description(self.picking_id.picking_type_id)
            self.lots_visible = self.product_id.tracking != 'none'
            if not self.product_uom_id or self.product_uom_id.category_id != self.product_id.uom_id.category_id:
                if self.move_id.product_uom:
                    self.product_uom_id = self.move_id.product_uom.id
                else:
                    self.product_uom_id = self.product_id.uom_id.id

    @api.onchange('lot_id', 'lot_id.expiration_date', 'qty_done')
    def _onchange_lot_id(self):
        if not self.picking_type_use_existing_lots or not self.product_id.use_expiration_date:
            return
        if self.lot_id:
            self.expiration_date = self.lot_id.expiration_date
        else:
            self.expiration_date = False

    @api.onchange('product_id', 'location_id', 'lot_id')
    def _onchange_domain_id(self):
        products = []

        if self.location_id.usage == 'transit':
            domain = {'product_id': [('id', '=', False)]}
            return {'domain': domain}
        elif self.picking_id:
            for line in self.picking_id.move_ids_without_package:
                products.append(line.product_id.id)
            if self.location_id.usage == 'internal':
                domain = {'product_id': [('id', 'in', products)],
                          'lot_id': [('quant_ids.location_id', '=', self.location_id.id),
                                     ('product_id', '=', self.product_id.id), ('quant_ids.quantity', '>', 0.0)]}
                return {'domain': domain}
            else:
                domain = {'product_id': [('id', 'in', products)]}
                return {'domain': domain}

    @api.depends('product_id', 'product_uom_id', 'product_uom_qty')
    @api.onchange('product_id', 'product_uom_id', 'product_uom_qty')
    def _compute_product_qty(self):
        for line in self:
            line.product_qty = line.product_uom_id._compute_quantity(line.product_uom_qty, line.product_id.uom_id,
                                                                     rounding_method='HALF-UP')

    @api.constrains('qty_done')
    def qty_done_reservation(self):
        for ml in self:
            if (ml.qty_done - ml.product_uom_qty != 0.0) and ml.state == 'assigned' and ml.location_id.usage in ('internal', 'transit') and ml.lot_id:
                Quant = self.env['stock.quant']
                quants = sum(x.available_quantity for x in
                             ml.lot_id.quant_ids.filtered(lambda quant: quant.location_id == ml.location_id))
                done_qty = ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id,
                                                      rounding_method='HALF-UP')
                actual_qty = quants + ml.product_uom_id._compute_quantity(ml.product_uom_qty, ml.product_id.uom_id, rounding_method='HALF-UP')
                if round(done_qty, 5) > round(actual_qty, 5):
                    ml.qty_done = actual_qty
                    qty = actual_qty - ml.product_uom_id._compute_quantity(ml.product_uom_qty, ml.product_id.uom_id, rounding_method='HALF-UP')
                else:
                    qty = done_qty - ml.product_uom_id._compute_quantity(ml.product_uom_qty, ml.product_id.uom_id, rounding_method='HALF-UP')

                q = Quant._update_reserved_quantity(ml.product_id, ml.location_id, qty,
                                                    lot_id=ml.lot_id,
                                                    package_id=ml.package_id,
                                                    owner_id=ml.owner_id, strict=True)
                reserved_qty = sum([x[1] for x in q])
                new_product_uom_qty = ml.product_id.uom_id._compute_quantity(reserved_qty, ml.product_uom_id, rounding_method='HALF-UP')
                ml.with_context(bypass_reservation_update=True).product_uom_qty += new_product_uom_qty
