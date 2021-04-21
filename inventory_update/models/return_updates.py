
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round




class ReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"
    _rec_name = 'product_id'

    max_quantity = fields.Float("Available Quantity", digits='Product Unit of Measure')

    lot_id = fields.Many2one('stock.production.lot', "Lot/Serial")

    @api.onchange('quantity')
    def on_change_quantity_value(self):
        if self.quantity > self.max_quantity:
            self.quantity = self.max_quantity


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'
    _description = 'Return Picking'


    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        move_dest_exists = False
        product_return_moves = [(5,)]
        if self.picking_id and self.picking_id.state != 'done':
            raise UserError(_("You may only return Done pickings."))
        # In case we want to set specific default values (e.g. 'to_refund'), we must fetch the
        # default values for creation.
        line_fields = [f for f in self.env['stock.return.picking.line']._fields.keys()]
        product_return_moves_data_tmpl = self.env['stock.return.picking.line'].default_get(line_fields)
        for move in self.picking_id.move_lines:
            if move.state == 'cancel':
                continue
            if move.scrapped:
                continue
            if move.move_dest_ids:
                move_dest_exists = True
            for move_line in move.move_line_ids:
                product_return_moves_data = dict(product_return_moves_data_tmpl)
                return_lines = self._prepare_stock_return_picking_line_vals_from_move(move_line)
                if return_lines:
                    product_return_moves_data.update(return_lines)
                    product_return_moves.append((0, 0, product_return_moves_data))
        if self.picking_id and len(product_return_moves) < 1:
            raise UserError(_("No products to return (only lines in Done state and not fully returned yet can be returned)."))
        if self.picking_id:
            self.product_return_moves = product_return_moves
            self.move_dest_exists = move_dest_exists
            self.parent_location_id = self.picking_id.picking_type_id.warehouse_id and self.picking_id.picking_type_id.warehouse_id.view_location_id.id or self.picking_id.location_id.location_id.id
            self.original_location_id = self.picking_id.location_id.id
            location_id = self.picking_id.location_id.id
            if self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
                location_id = self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.id
            self.location_id = location_id

    @api.model
    def _prepare_stock_return_picking_line_vals_from_move(self, move_line):
        quantity = move_line.qty_done
        for move in move_line.move_id.move_dest_ids:
            if move.origin_returned_move_id and move.origin_returned_move_id != move_line.move_id:
                continue
            if move.state in ('partially_available', 'assigned') and move.location_dest_id.usage != 'production':
                quantity -= sum(move.move_line_ids.filtered(lambda x: x.lot_id == move_line.lot_id).mapped('product_qty'))
            elif move.state in ('partially_available', 'assigned') and move.location_dest_id.usage == 'production':
                quantity -= sum(move.move_line_ids.filtered(lambda x: x.lot_id == move_line.lot_id).mapped('qty_done'))
            elif move.state in ('done'):
                quantity -= sum(move.move_line_ids.filtered(lambda x: x.lot_id == move_line.lot_id).mapped('qty_done'))

        quantity = float_round(quantity, precision_rounding=move_line.product_uom_id.rounding)
        if quantity > 0.0:
            return {
                'product_id': move_line.product_id.id,
                'quantity': quantity,
                'max_quantity': quantity,
                'move_id': move_line.move_id.id,
                'lot_id': move_line.lot_id.id,
                'uom_id': move_line.product_uom_id.id,

            }

    def _prepare_move_default_values(self, return_line, new_picking):
        vals = {
            'product_id': return_line.product_id.id,
            'product_uom_qty': return_line.quantity,
            'product_uom': return_line.uom_id.id,
            'picking_id': new_picking.id,
            'state': 'draft',
            'date': fields.Datetime.now(),
            'location_id': return_line.move_id.location_dest_id.id,
            'location_dest_id': self.location_id.id or return_line.move_id.location_id.id,
            'picking_type_id': new_picking.picking_type_id.id,
            'warehouse_id': self.picking_id.picking_type_id.warehouse_id.id,
            'origin_returned_move_id': return_line.move_id.id,
            'procure_method': 'make_to_stock',
        }
        return vals

    def _create_returns(self):
        # TODO sle: the unreserve of the next moves could be less brutal
        for return_move in self.product_return_moves.mapped('move_id'):
            return_move.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._do_unreserve()

        # create new picking for returned products
        picking_type_id = self.picking_id.picking_type_id.return_picking_type_id.id or self.picking_id.picking_type_id.id
        new_picking = self.picking_id.copy({
            'move_lines': [],
            'picking_type_id': picking_type_id,
            'state': 'draft',
            'origin': _("Return of %s", self.picking_id.name),
            'location_id': self.picking_id.location_dest_id.id,
            'location_dest_id': self.location_id.id})
        new_picking.message_post_with_view('mail.message_origin_link',
            values={'self': new_picking, 'origin': self.picking_id},
            subtype_id=self.env.ref('mail.mt_note').id)
        returned_lines = 0
        moves=[]
        for return_line in self.product_return_moves:
            if not return_line.move_id:
                raise UserError(_("You have manually created product lines, please delete them to proceed."))
            # TODO sle: float_is_zero?
            if return_line.quantity > 0.0:
                if return_line.move_id not in moves:
                    moves.append(return_line.move_id)
                    returned_lines += 1
                    vals = self._prepare_move_default_values(return_line, new_picking)
                    r = return_line.move_id.copy(vals)
                    vals = {}

                    # +--------------------------------------------------------------------------------------------------------+
                    # |       picking_pick     <--Move Orig--    picking_pack     --Move Dest-->   picking_ship
                    # |              | returned_move_ids              ↑                                  | returned_move_ids
                    # |              ↓                                | return_line.move_id              ↓
                    # |       return pick(Add as dest)          return toLink                    return ship(Add as orig)
                    # +--------------------------------------------------------------------------------------------------------+
                    move_orig_to_link = return_line.move_id.move_dest_ids.mapped('returned_move_ids')
                    # link to original move
                    move_orig_to_link |= return_line.move_id
                    # link to siblings of original move, if any
                    move_orig_to_link |= return_line.move_id \
                        .mapped('move_dest_ids').filtered(lambda m: m.state not in ('cancel')) \
                        .mapped('move_orig_ids').filtered(lambda m: m.state not in ('cancel'))
                    move_dest_to_link = return_line.move_id.move_orig_ids.mapped('returned_move_ids')
                    # link to children of originally returned moves, if any. Note that the use of
                    # 'return_line.move_id.move_orig_ids.returned_move_ids.move_orig_ids.move_dest_ids'
                    # instead of 'return_line.move_id.move_orig_ids.move_dest_ids' prevents linking a
                    # return directly to the destination moves of its parents. However, the return of
                    # the return will be linked to the destination moves.
                    move_dest_to_link |= return_line.move_id.move_orig_ids.mapped('returned_move_ids') \
                        .mapped('move_orig_ids').filtered(lambda m: m.state not in ('cancel')) \
                        .mapped('move_dest_ids').filtered(lambda m: m.state not in ('cancel'))
                    vals['move_orig_ids'] = [(4, m.id) for m in move_orig_to_link]
                    vals['move_dest_ids'] = [(4, m.id) for m in move_dest_to_link]
                    r.write(vals)
                else:
                    r = new_picking.move_lines.filtered(
                        lambda r: return_line.move_id == r.origin_returned_move_id)
                    r.product_uom_qty += return_line.quantity
                new_picking.move_line_ids.create(
                    {
                        'lot_id': return_line.lot_id.id,
                        'product_id': return_line.product_id.id,
                        'qty_done': return_line.quantity,
                        'product_uom_qty': return_line.quantity,
                        'move_id': r.id,
                        'picking_id': new_picking.id,
                        'product_uom_id': return_line.uom_id.id,
                        'location_id': r.location_id.id,
                        'location_dest_id': r.location_dest_id.id,

                    }
                )

        if not returned_lines:
            raise UserError(_("Please specify at least one non-zero quantity."))

        new_picking.action_confirm()
        new_picking.do_unreserve()
        new_picking.action_assign()
        for move in new_picking.move_lines:
            return_picking_lines = self.product_return_moves.filtered(
                lambda r: r.move_id == move.origin_returned_move_id)
            for return_picking_line in return_picking_lines:
                if return_picking_line and return_picking_line.to_refund:
                    move.to_refund = True
        # for move in new_picking.move_line_ids:
        #     if move.product_id.tracking != 'none' and not move.lot_id:
        #         move.unlink()

        return new_picking.id, picking_type_id

