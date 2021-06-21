# -*- coding: utf-8 -*-

from collections import Counter
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockLot(models.Model):
    _inherit = 'stock.production.lot'

    cost = fields.Monetary('Unit Price', store=True, index=True)
    currency_id = fields.Many2one('res.currency', compute='_compute_value')

    @api.depends('company_id')
    def _compute_value(self):
        self.currency_id = self.env.company.currency_id


class StockInventory(models.Model):
    _inherit = 'stock.inventory'
    def _get_inventory_lines_values(self):
        """Return the values of the inventory lines to create for this inventory.

        :return: a list containing the `stock.inventory.line` values to create
        :rtype: list
        """
        self.ensure_one()
        quants_groups = self._get_quantities()
        vals = []
        for (product_id, location_id, lot_id, package_id, owner_id), quantity in quants_groups.items():
            line_values = {
                'inventory_id': self.id,
                'product_qty': 0 if self.prefill_counted_quantity == "zero" else quantity,
                'theoretical_qty': quantity,
                'prod_lot_id': lot_id,
                'price_unit': self.env['stock.production.lot'].browse(lot_id).cost,
                'partner_id': owner_id,
                'product_id': product_id,
                'location_id': location_id,
                'package_id': package_id
            }
            line_values['product_uom_id'] = self.env['product.product'].browse(product_id).uom_id.id
            vals.append(line_values)
        if self.exhausted:
            vals += self._get_exhausted_inventory_lines_vals({(l['product_id'], l['location_id']) for l in vals})
        return vals

class StockInventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    @api.onchange('product_id', 'location_id', 'product_uom_id', 'prod_lot_id', 'partner_id', 'package_id')
    def _onchange_quantity_context(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
        if self.product_id and self.location_id and self.product_id.uom_id.category_id == self.product_uom_id.category_id:  # TDE FIXME: last part added because crash
            theoretical_qty = self.product_id.get_theoretical_quantity(
                self.product_id.id,
                self.location_id.id,
                lot_id=self.prod_lot_id.id,
                package_id=self.package_id.id,
                owner_id=self.partner_id.id,
                to_uom=self.product_uom_id.id,
            )
        else:
            theoretical_qty = 0
        # Sanity check on the lot.
        if self.prod_lot_id:
            if self.product_id.tracking == 'none' or self.product_id != self.prod_lot_id.product_id:
                self.prod_lot_id = False

        if self.prod_lot_id and self.product_id.tracking == 'serial':
            # We force `product_qty` to 1 for SN tracked product because it's
            # the only relevant value aside 0 for this kind of product.
            self.product_qty = 1
        elif self.product_id and float_compare(self.product_qty, self.theoretical_qty,
                                               precision_rounding=self.product_uom_id.rounding) == 0:
            # We update `product_qty` only if it equals to `theoretical_qty` to
            # avoid to reset quantity when user manually set it.
            self.product_qty = theoretical_qty
        self.theoretical_qty = theoretical_qty
        self.price_unit = self.prod_lot_id.cost

    price_unit = fields.Float(
        'Unit Price',
        help="Technical field used to record the product cost set by the user during a picking confirmation (when costing "
             "method used is 'average price' or 'real'). Value given in company currency and in product uom.",
        copy=True)  # as it's a technical field, we intentionally don't provide the digits attribute

    @api.depends('company_id')
    def _compute_value(self):
        self.currency_id = self.env.company.currency_id

    def _get_move_values(self, qty, location_id, location_dest_id, out):
        if self.price_unit and self.prod_lot_id:
            self.prod_lot_id.cost = self.price_unit
        self.ensure_one()
        return {
            'name': _('INV:') + (self.inventory_id.name or ''),
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': qty,
            'date': self.inventory_id.date,
            'company_id': self.inventory_id.company_id.id,
            'inventory_id': self.inventory_id.id,
            'state': 'confirmed',
            'price_unit': self.price_unit,
            'restrict_partner_id': self.partner_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'lot_id': self.prod_lot_id.id,
                'product_uom_qty': 0,  # bypass reservation here
                'product_uom_id': self.product_uom_id.id,
                'qty_done': qty,
                'package_id': out and self.package_id.id or False,
                'result_package_id': (not out) and self.package_id.id or False,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'owner_id': self.partner_id.id,
            })]
        }


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    cost = fields.Monetary('Unit Price', store=True, index=True, groups='stock.group_stock_manager')

    @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity')
    def _compute_value(self):
        """ For standard and AVCO valuation, compute the current accounting
        valuation of the quants by multiplying the quantity by
        the standard price. Instead for FIFO, use the quantity times the
        average cost (valuation layers are not manage by location so the
        average cost is the same for all location and the valuation field is
        a estimation more than a real value).
        """
        self.currency_id = self.env.company.currency_id
        for quant in self:
            # If the user didn't enter a location yet while enconding a quant.
            if not quant.location_id:
                quant.value = 0
                return

            if not quant.location_id._should_be_valued() or \
                    (quant.owner_id and quant.owner_id != quant.company_id.partner_id):
                quant.value = 0
                continue
            if quant.product_id.cost_method == 'fifo':
                quantity = quant.product_id.quantity_svl
                if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
                    quant.value = 0.0
                    continue
                average_cost = quant.product_id.value_svl / quantity
                quant.value = quant.quantity * average_cost
            elif quant.product_id.cost_method == 'real':
                quant.value = quant.quantity * quant.lot_id.cost
            else:
                quant.value = quant.quantity * quant.product_id.standard_price



class StockMove(models.Model):
    _inherit = 'stock.move'

    price_unit = fields.Float(
        'Unit Price',
        help="Technical field used to record the product cost set by the user during a picking confirmation (when costing "
             "method used is 'average price' or 'real'). Value given in company currency and in product uom.",
        copy=True)  # as it's a technical field, we intentionally don't provide the digits attribute

    def _create_in_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_in_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done,
                                                                                     move.product_id.uom_id)
            unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).
            if move.product_id.cost_method == 'standard':
                unit_cost = move.product_id.standard_price
            svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
            svl_vals.update(move._prepare_common_svl_vals())
            if move.product_id.cost_method == 'real':
                cost = 0
                qty = 0
                for line in move.move_line_ids:
                    if line.lot_id:
                        cost += line.lot_id.cost * line.qty_done
                        qty += line.qty_done
                if qty > 0.0:
                    svl_vals.update({'unit_cost': cost/qty,
                                     'value': cost})
            if forced_quantity:
                svl_vals[
                    'description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)


    def _create_out_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_out_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                continue

            svl_vals = move.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity, move.company_id)
            svl_vals.update(move._prepare_common_svl_vals())
            if move.product_id.cost_method == 'real':
                cost = 0
                qty = 0
                for line in move.move_line_ids:
                    if line.lot_id:
                        cost += line.lot_id.cost * line.qty_done
                        qty += line.qty_done
                if qty > 0.0:
                    svl_vals.update({'unit_cost': cost/qty,
                                     'value': cost * -1})
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _create_and_assign_production_lot(self):
        if not self.lot_id:
            """ Creates and assign new production lots for move lines."""
            lot_vals = [{
                'company_id': ml.move_id.company_id.id,
                'name': ml.lot_name,
                'product_id': ml.product_id.id,
                'cost': ml.move_id._get_price_unit(),
            } for ml in self]
            lots = self.env['stock.production.lot'].create(lot_vals)
            for ml, lot in zip(self, lots):
                ml._assign_production_lot(lot)
