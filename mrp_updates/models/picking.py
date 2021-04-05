from odoo import models, fields, _,api
from odoo.osv import expression
from odoo.exceptions import UserError
import json
from collections import defaultdict
from datetime import datetime
from itertools import groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_repr, float_round
from odoo.tools.misc import format_date, OrderedSet
import re


class PickingBatch(models.Model):
    _inherit = 'stock.picking'

    mrp_product_id = fields.Many2one('product.product',string='Product', readonly=True,index=True,copy=True)
    batch = fields.Char('Batch Number', index=True, copy=True, tracking=True,readonly=True)


    def keeper_approve(self):
        for move in self.move_lines:
            production = move.move_orig_ids.production_id.filtered(lambda p: p.state not in ('done', 'cancel'))[-1:]
            if production:
                for move_line in move.move_line_ids:
                    if not move_line.lot_id:
                        move_line._create_and_assign_production_lot()
                        production.lot_producing_id = move_line.lot_id
                        production.lot_producing_id.ref = move_line.suplier_lot
        return super(PickingBatch, self).keeper_approve()


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _set_quantity_done_prepare_vals(self, qty):
        res = []
        if self.state not in ('done' ,'cancel'):
            for ml in self.move_line_ids:
                ml_qty = ml.product_uom_qty - ml.qty_done
                if float_compare(ml_qty, 0, precision_rounding=ml.product_uom_id.rounding) <= 0:
                    continue
                # Convert move line qty into move uom
                if ml.product_uom_id != self.product_uom:
                    ml_qty = ml.product_uom_id._compute_quantity(ml_qty, self.product_uom, round=False)

                taken_qty = min(qty, ml_qty)
                # Convert taken qty into move line uom
                if ml.product_uom_id != self.product_uom:
                    taken_qty = self.product_uom._compute_quantity(ml_qty, ml.product_uom_id, round=False)

                # Assign qty_done and explicitly round to make sure there is no inconsistency between
                # ml.qty_done and qty.
                taken_qty = float_round(taken_qty, precision_rounding=ml.product_uom_id.rounding)
                res.append((1, ml.id, {'qty_done': ml.qty_done + taken_qty}))
                if ml.product_uom_id != self.product_uom:
                    taken_qty = ml.product_uom_id._compute_quantity(ml_qty, self.product_uom, round=False)
                qty -= taken_qty

                if float_compare(qty, 0.0, precision_rounding=self.product_uom.rounding) <= 0:
                    break

            for ml in self.move_line_ids:
                if float_is_zero(ml.product_uom_qty, precision_rounding=ml.product_uom_id.rounding) and float_is_zero(ml.qty_done, precision_rounding=ml.product_uom_id.rounding):
                    res.append((2, ml.id))

            if float_compare(qty, 0.0, precision_rounding=self.product_uom.rounding) > 0:
                if self.product_id.tracking != 'serial':
                    vals = self._prepare_move_line_vals(quantity=0)
                    vals['qty_done'] = qty
                    res.append((0, 0, vals))
                else:
                    uom_qty = self.product_uom._compute_quantity(qty, self.product_id.uom_id)
                    for i in range(0, int(uom_qty)):
                        vals = self._prepare_move_line_vals(quantity=0)
                        vals['qty_done'] = 1
                        vals['product_uom_id'] = self.product_id.uom_id.id
                        res.append((0, 0, vals))
            return res

    def _update_quantity_done(self, mo):
        self.ensure_one()
        if self.state not in ('done','cancel'):
            new_qty = mo.product_uom_id._compute_quantity((mo.qty_producing - mo.qty_produced) * self.unit_factor, mo.product_uom_id, rounding_method='HALF-UP')
            if not self.is_quantity_done_editable:
                self.move_line_ids.filtered(lambda ml: ml.state not in ('done', 'cancel')).qty_done = 0
                self.move_line_ids = self._set_quantity_done_prepare_vals(new_qty)
            else:
                self.quantity_done = new_qty
        return  True

    def _assign_picking(self):
        """ Try to assign the moves to an existing picking that has not been
        reserved yet and has the same procurement group, locations and picking
        type (moves should already have them identical). Otherwise, create a new
        picking to assign them to. """
        Picking = self.env['stock.picking']
        grouped_moves = groupby(sorted(self, key=lambda m: [f.id for f in m._key_assign_picking()]), key=lambda m: [m._key_assign_picking()])
        for group, moves in grouped_moves:
            moves = self.env['stock.move'].concat(*list(moves))
            new_picking = False
            # Could pass the arguments contained in group but they are the same
            # for each move that why moves[0] is acceptable
            picking = moves[0]._search_picking_for_assignation()
            if picking:
                if picking.origin == 'MPS' or picking.mrp_product_id:
                    new_picking = True
                    picking = Picking.create(moves._get_new_picking_values())
                    picking.origin = moves.created_production_id.name
                    picking.batch = moves.created_production_id.batch
                    picking.mrp_product_id = moves.created_production_id.product_id
                if any(picking.partner_id.id != m.partner_id.id or
                        picking.origin != m.origin for m in moves):
                    # If a picking is found, we'll append `move` to its move list and thus its
                    # `partner_id` and `ref` field will refer to multiple records. In this
                    # case, we chose to  wipe them.
                    picking.write({
                        'partner_id': False,
                        'origin': False,
                    })
            else:
                new_picking = True
                picking = Picking.create(moves._get_new_picking_values())

            moves.write({'picking_id': picking.id})
            moves._assign_picking_post_process(new=new_picking)
        return True

    def _key_assign_picking(self):
        self.ensure_one()
        return self.group_id, self.location_id, self.location_dest_id, self.picking_type_id,self.created_production_id




class StockProduction(models.Model):
    _inherit = 'stock.production.lot'
    ref = fields.Char(string='Batch Number', store=True)

    cost = fields.Monetary('Unit Price', store=True, index=True)
    currency_id = fields.Many2one('res.currency', compute='_compute_value')

    @api.depends('company_id')
    def _compute_value(self):
        self.currency_id = self.env.company.currency_id

    def name_get(self):
        res = []
        for asset in self:
            if asset.ref:
                res.append((asset.id,
                            asset.name + '  ' + asset.ref))
            else:
                res.append((asset.id,
                            asset.name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            products = self.env['stock.production.lot']
            if operator in positive_operators:
                products = self.search([('ref', '=', name)] + args, limit=limit)
                if not products:
                    products = self.search([('name', '=', name)] + args, limit=limit)
            if not products and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                products = self.search(args + [('ref', operator, name)], limit=limit)
                if not limit or len(products) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(products)) if limit else False
                    products += self.search(args + [('name', operator, name), ('id', 'not in', products.ids)],
                                            limit=limit2)
            elif not products and operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = expression.OR([
                    ['&', ('ref', operator, name), ('name', operator, name)],
                    ['&', ('ref', '=', False), ('name', operator, name)],
                ])
                domain = expression.AND([args, domain])
                products = self.search(domain, limit=limit)
            if not products and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    products = self.search([('ref', '=', res.group(2))] + args, limit=limit)
            # still no results, partner in context: search on supplier info as last hope to find something

        else:
            products = self.search(args, limit=limit)
        return products.name_get()

