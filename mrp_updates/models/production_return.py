
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round







class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'
    _description = 'Return Picking'
    production_id = fields.Many2one('mrp.production', 'Production Order')

    @api.onchange('production_id')
    def _onchange_production_id(self):
        move_dest_exists = False
        product_return_moves = [(5,)]
        # In case we want to set specific default values (e.g. 'to_refund'), we must fetch the
        # default values for creation.
        line_fields = [f for f in self.env['stock.return.picking.line']._fields.keys()]
        product_return_moves_data_tmpl = self.env['stock.return.picking.line'].default_get(line_fields)
        for move in self.production_id.move_raw_ids:
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

        if self.production_id:
            self.product_return_moves = product_return_moves
            self.move_dest_exists = move_dest_exists
            self.parent_location_id = self.production_id.picking_type_id.warehouse_id and self.production_id.picking_type_id.warehouse_id.view_location_id.id or self.production_id.location_src_id.location_id.id
            self.original_location_id = self.production_id.location_src_id.id
            location_id = self.production_id.location_src_id.id
            self.location_id = location_id

    @api.model
    def _prepare_stock_return_picking_line_vals_from_move(self, move_line):
        quantity = move_line.qty_done
        for move in move_line.move_id.move_dest_ids:
            if move.origin_returned_move_id and move.origin_returned_move_id != move_line.move_id:
                continue
            if move.state in ('partially_available', 'assigned') :
                quantity -= sum(move.move_line_ids.filtered(lambda x: x.lot_id == move_line.lot_id).mapped('product_qty'))
            elif move.state in ('partially_available', 'assigned'):
                quantity -= sum(move.move_line_ids.filtered(lambda x: x.lot_id == move_line.lot_id).mapped('qty_done'))
            elif move.state in ('done'):
                quantity -= sum(move.move_line_ids.filtered(lambda x: x.lot_id == move_line.lot_id).mapped('qty_done'))

        quantity = float_round(quantity, precision_rounding=move_line.product_uom_id.rounding)
        if quantity > 0.0:
            return {
                'product_id': move_line.product_id.id,
                'quantity': 0,
                'max_quantity': quantity,
                'move_id': move_line.move_id.id,
                'lot_id': move_line.lot_id.id,
                'uom_id': move_line.product_uom_id.id,

            }

    def _prepare_move_default_production(self, return_line):
        vals = {
            'product_id': return_line.product_id.id,
            'product_uom_qty': return_line.quantity,
            'product_uom': return_line.product_id.uom_id.id,
            'state': 'draft',
            'date': fields.Datetime.now(),
            'location_id': return_line.move_id.location_dest_id.id,
            'location_dest_id': self.location_id.id or return_line.move_id.location_id.id,
            'picking_type_id': self.production_id.picking_type_id.id,
            'warehouse_id': self.production_id.picking_type_id.warehouse_id.id,
            'origin_returned_move_id': return_line.move_id.id,
            'procure_method': 'make_to_stock',
        }
        return vals
    def _create_return_production(self):
        # TODO sle: the unreserve of the next moves could be less brutal
        for return_move in self.product_return_moves.mapped('move_id'):
            return_move.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._do_unreserve()
        if self.production_id:
            returned_lines = 0
            moves = []
            done_moves = self.env['stock.move']
            picking = self.env['stock.picking']
            done_picking = self.env['stock.picking']
            for return_line in self.product_return_moves:
                if not return_line.move_id:
                    raise UserError(_("You have manually created product lines, please delete them to proceed."))
                # TODO sle: float_is_zero?
                if return_line.quantity > 0.0:
                    if return_line.move_id not in moves:
                        moves.append(return_line.move_id)
                        returned_lines += 1
                        vals = self._prepare_move_default_production(return_line)
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
                        r = self.production_id.move_raw_ids.filtered(
                            lambda x: return_line.move_id == x.origin_returned_move_id and x.state =='draft' )
                        r.product_uom_qty += return_line.quantity
                    self.production_id.move_raw_ids.move_line_ids.create(
                        {
                            'lot_id': return_line.lot_id.id,
                            'product_id': return_line.product_id.id,
                            'qty_done': return_line.quantity,
                            'product_uom_qty': return_line.quantity,
                            'move_id': r.id,
                            'product_uom_id': return_line.uom_id.id,
                            'location_id': r.location_id.id,
                            'location_dest_id': r.location_dest_id.id,

                        }
                    )
                    done_moves |= r

                    for move in return_line.move_id.move_orig_ids:
                            done_picking |= move.picking_id
                            if picking:
                                new_picking = picking.filtered(lambda m: m.location_dest_id == move.picking_id.location_id)
                                if not new_picking:
                                    new_picking = move.picking_id.copy({'move_lines': [],
                                                                        'location_id': self.production_id.location_src_id.id,
                                                                        'location_dest_id': move.picking_id.location_id.id,
                                                                        'picking_type_id' : move.picking_id.picking_type_id.return_picking_type_id.id or move.picking_id.picking_type_id.id,
                                                                        'origin': _("Return of %s",
                                                                                    move.picking_id.name),

                                                                        })
                            else :
                                new_picking = move.picking_id.copy({'move_lines': [],
                                                                    'location_id': self.production_id.location_src_id.id,
                                                                    'location_dest_id': move.picking_id.location_id.id,
                                                                    'picking_type_id': move.picking_id.picking_type_id.return_picking_type_id.id or move.picking_id.picking_type_id.id,
                                                                    'origin': _("Return of %s",  move.picking_id.name),

                                                                    })
                            picking |= new_picking
                            new = r.copy({
                                'location_id': self.production_id.location_src_id.id,
                                'location_dest_id': move.picking_id.location_id.id,
                                'picking_id': new_picking.id,

                                'raw_material_production_id': False,
                                'move_orig_ids': [(4, m.id) for m in r]
                            })
                            r.move_dest_ids |= new

            done_moves._action_done()
            if picking:
                picking.action_assign()
            if not returned_lines:
                raise UserError(_("Please specify at least one non-zero quantity."))

    def create_returns(self):
        for wizard in self:
            if wizard.picking_id:
                new_picking_id, pick_type_id = wizard._create_returns()
            # Override the context to disable all the potential filters that could have been set previously
                ctx = dict(self.env.context)
                ctx.update({
                    'search_default_picking_type_id': pick_type_id,
                    'search_default_draft': False,
                    'search_default_assigned': False,
                    'search_default_confirmed': False,
                    'search_default_ready': False,
                    'search_default_planning_issues': False,
                    'search_default_available': False,
                })
                return {
                    'name': _('Returned Picking'),
                    'view_mode': 'form,tree,calendar',
                    'res_model': 'stock.picking',
                    'res_id': new_picking_id,
                    'type': 'ir.actions.act_window',
                    'context': ctx,
                }
            if wizard.production_id:
                wizard._create_return_production()


