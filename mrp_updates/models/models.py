import math
import re
from odoo import api
from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime


def increment_str(s):
    lpart = s.rstrip('Z')
    if not lpart:  # s contains only 'Z'
        new_s = 'A' * (len(s) + 1)
    else:
        num_replacements = len(s) - len(lpart)
        new_s = lpart[:-1] + increment_char(lpart[-1])
        new_s += 'A' * num_replacements
    return new_s


def increment_char(c):
    """
    Increment an uppercase character, returning 'A' if 'Z' is given
    """
    return chr(ord(c) + 1) if c != 'Z' else 'A'


class MrpUpdates(models.Model):
    _inherit = 'mrp.production'

    batch = fields.Char('Batch Number', index=True, copy=True, tracking=True, states={'draft': [('readonly', False)]},
                        readonly=True)
    name = fields.Char(
        'Reference', copy=False, readonly=True, default=lambda x: _('New'))
    check_repack = fields.Selection([
        ('normal', 'Normal'), ('repack', 'Repackaging'), ('process', 'Reprocess')
    ], string='Type ',
        copy=True, store=True, tracking=True, default='normal', states={'draft': [('readonly', False)]}, readonly=True)
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
        readonly=True, states={'draft': [('readonly', False)]},
        domain="""['&','|',('company_id', '=', False), ('company_id', '=', company_id),
                '&','|',('product_id','=',product_id), '&',
                            ('product_tmpl_id.product_variant_ids','=',product_id),
                            ('product_id','=',False),
            ('type', '=', 'normal'),
            ('bom_type', '=', check_repack)]""",
        check_company=True,
        help="Bill of Materials allow you to define the list of required components to make a finished product.")

    lot_producing_id = fields.Many2one(
        'stock.production.lot', string='Lot/Serial Number', copy=False,
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id),('ref', '=', batch),]",
        check_company=True, states={'draft': [('readonly', False)]}, readonly=True)

    user_id = fields.Many2one(
        'res.users', 'Responsible', default=lambda self: self.env.user,
        states={'draft': [('readonly', False)]}, readonly=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref('mrp.group_mrp_user').id)])

    def action_assign(self):
        for production in self:
            production.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))._action_assign()
        return True

    def post_inventory(self):
        for production in self:
            if any(production.workorder_ids.filtered(lambda mo: mo.state not in ('done', 'cancel'))):
                raise UserError (_('There is unfinished work orders please finish it first'))


            production._post_inventory()
        return True

    def _subcontracting_filter_to_done(self):
        """ Filter subcontracting production where composant is already recorded and should be consider to be validate """
        mos = self.filtered(lambda mo: mo.state not in ('done', 'cancel') and mo.bom_id.type == 'subcontract')
        return mos.filtered(lambda pro: all(
            line.lot_id for line in pro.move_raw_ids.filtered(lambda sm: sm.has_tracking != 'none').move_line_ids))

    def _post_inventory(self, cancel_backorder=False):
        for order in self:
            moves_not_to_do = order.move_raw_ids.filtered(lambda x: x.state == 'done')
            moves_to_do = order.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            for move in moves_to_do.filtered(lambda m: m.product_qty == 0.0 and m.quantity_done > 0):
                move.product_uom_qty = move.quantity_done
            # MRP do not merge move, catch the result of _action_done in order
            # to get extra moves.
            moves_to_do = moves_to_do._action_done()
            moves_to_do = order.move_raw_ids.filtered(lambda x: x.state == 'done')

            finish_moves = order.move_finished_ids.filtered(
                lambda m: m.product_id == order.product_id and m.state not in ('done', 'cancel'))
            # the finish move can already be completed by the workorder.
            if not finish_moves.quantity_done:
                finish_moves.quantity_done = float_round(order.qty_producing - order.qty_produced,
                                                         precision_rounding=order.product_uom_id.rounding,
                                                         rounding_method='HALF-UP')
                if finish_moves.quantity_done > finish_moves.product_uom_qty:
                    finish_moves.product_uom_qty = finish_moves.quantity_done
                    if len(finish_moves.move_dest_ids) == 1:
                        finish_moves.move_dest_ids.product_uom_qty = finish_moves.quantity_done
                finish_moves.move_line_ids.lot_id = order.lot_producing_id
            order._cal_price(moves_to_do)

            moves_to_finish = order.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel') and x.quantity_done >0.0)

            for move in moves_to_finish:
                for line in move.move_line_ids:
                    if line.product_id.use_expiration_date and (
                            not line.lot_id.prod_date or not line.lot_id.expiration_date):
                        raise UserError(_('Please assign Lot Production and expiration Date for lot %s')% (line.lot_id.display_name))
            moves_to_finish = moves_to_finish._action_done(cancel_backorder=cancel_backorder)
            order.action_assign()
            consume_move_lines = moves_to_do.mapped('move_line_ids')
            order.move_finished_ids.move_line_ids.consume_line_ids = [(6, 0, consume_move_lines.ids)]
            new_pickings = self.env['stock.picking']
            for picking in self.env['stock.picking'].sudo().search([('origin', '=', self.name), ('state', '=', 'assigned'),
                                                             ('location_id', '=', self.location_dest_id.id)]):
                moves = self.env['stock.move']
                for move in picking.move_lines:
                    if move.quantity_done > 0 and move.state not in ('done', 'cancel'):
                        if move.product_uom_qty > move.quantity_done > 0:
                            new_move = move.copy(
                                {'product_uom_qty': move.product_uom_qty - move.quantity_done,
                                 'quantity_done': 0,
                                 'picking_id': False, }
                            )
                            move.product_uom_qty = move.quantity_done
                            new_move.move_orig_ids = move.move_orig_ids.filtered(
                                lambda x: x.state not in ('done', 'cancel'))
                            move.move_orig_ids = move.move_orig_ids.filtered(lambda x: x.state == 'done')
                            moves |= new_move
                        elif move.product_uom_qty <= move.quantity_done:
                            move.product_uom_qty = move.quantity_done
                            picking.do_unreserve()
                            picking.action_assign()
                    if not move.quantity_done:
                        moves |= move
                if moves:
                    new_picking = picking.copy({'move_lines':[]})
                    moves.picking_id = new_picking
                    new_pickings |= new_picking
                    picking.do_unreserve()
                    picking.action_assign()
            if new_pickings:
                new_pickings.action_confirm()

        return True

    @api.depends('move_finished_ids.quantity_done','qty_producing')
    def _compute_post_visible(self):
        for order in self:
            post = any(order.move_finished_ids.filtered(
                lambda x: x.quantity_done > 0 and (x.state not in ['assigned', 'done', 'cancel'])))
            if post:
                order.post_visible = post
            elif order.qty_producing > order.qty_produced:
                order.post_visible = True
            else:
                order.post_visible = False

    post_visible = fields.Boolean(
        'Inventory Post Visible', compute='_compute_post_visible',
        help='Technical field to check when we can post')

    @api.constrains('batch')
    def _check_batch_number(self):
        if self.check_repack == 'normal' and self.batch and len(self.procurement_group_id.mrp_production_ids.ids) < 2:
            batch = self.search(
                [('batch', '=', self.batch), ('check_repack', '=', 'normal'), ('id', '!=', self.id),
                 ('state', '!=', 'cancel')])
            if batch:
                raise UserError(_('Batch AlReady exit'))

    def _set_qty_producing(self):
        if self.product_id.tracking == 'serial':
            qty_producing_uom = self.product_uom_id._compute_quantity(self.qty_producing, self.product_id.uom_id,
                                                                      rounding_method='HALF-UP')
            if qty_producing_uom != 1:
                self.qty_producing = self.product_id.uom_id._compute_quantity(1, self.product_uom_id,
                                                                              rounding_method='HALF-UP')

        for move in (self.move_raw_ids | self.move_finished_ids.filtered(
                lambda m: m.product_id != self.product_id and m.state not in ('done', 'cancel'))):
            if move._should_bypass_set_qty_producing():
                continue
            new_qty = self.product_uom_id._compute_quantity((self.qty_producing - self.qty_produced) * move.unit_factor,
                                                            self.product_uom_id, rounding_method='HALF-UP')
            move.move_line_ids.filtered(lambda ml: ml.state not in ('done', 'cancel')).qty_done = 0
            move.move_line_ids = move._set_quantity_done_prepare_vals(new_qty)
        return True

    def _update_raw_moves(self, factor):
        self.ensure_one()
        update_info = []
        move_to_unlink = self.env['stock.move']
        for move in self.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            old_qty = move.product_uom_qty
            new_qty = old_qty * factor
            if new_qty > 0:
                move.write({'product_uom_qty': new_qty})
                move._action_assign()
                update_info.append((move, old_qty, new_qty))
            else:
                if move.quantity_done > 0:
                    raise UserError(_(
                        'Lines need to be deleted, but can not as you still have some quantities to consume in them. '))
                move._action_cancel()
                move_to_unlink |= move
        move_to_unlink.unlink()
        return update_info

    def action_confirm(self):
        self._check_company()
        for production in self:
            move_to_unlink = self.env['stock.move']
            for move in self.move_raw_ids:
                if move.product_uom_qty <= 0.0:
                    move._action_cancel()
                    move_to_unlink |= move
                if move not in move_to_unlink:
                    moves = self.move_raw_ids.filtered(lambda m: m.product_id == move.product_id and m.id != move.id)
                    for m in moves:
                        move.product_uom_qty += m.product_uom_qty
                        m._action_cancel()
                        move_to_unlink |= m
            moves = self.move_byproduct_ids.filtered(lambda m: m.product_uom_qty == 0.0)
            for move in moves:
                move._action_cancel()
                move_to_unlink |= move
            move_to_unlink.unlink()
            if production.bom_id:
                production.consumption = production.bom_id.consumption
            # In case of Serial number tracking, force the UoM to the UoM of product
            if production.product_tracking == 'serial' and production.product_uom_id != production.product_id.uom_id:
                production.write({
                    'product_qty': production.product_uom_id._compute_quantity(production.product_qty,
                                                                               production.product_id.uom_id),
                    'product_uom_id': production.product_id.uom_id
                })
                for move_finish in production.move_finished_ids.filtered(
                        lambda m: m.product_id == production.product_id):
                    move_finish.write({
                        'product_uom_qty': move_finish.product_uom._compute_quantity(move_finish.product_uom_qty,
                                                                                     move_finish.product_id.uom_id),
                        'product_uom': move_finish.product_id.uom_id
                    })
            production.move_raw_ids._adjust_procure_method()
            (production.move_raw_ids | production.move_finished_ids)._action_confirm(merge=True, merge_into=False)
            production.workorder_ids._action_confirm()
            # run scheduler for moves forecasted to not have enough in stock
            production.move_raw_ids._trigger_scheduler()
            if not production.batch and production.location_src_id != production.env.company.subcontracting_location_id:
                batch = ''
                if not production.product_id.product_tmpl_id.pro_type or production.product_id.product_tmpl_id.pro_type == 'eda':
                    production.env.cr.execute(
                        "select batch from mrp_production where batch like '____'  order by batch DESC LIMIT 1")
                else:
                    production.env.cr.execute(
                        "select batch from mrp_production where batch like '____F'  order by batch DESC LIMIT 1")
                products = production.env.cr.fetchall()
                for p in products:
                    seq = int(re.search(r'\d+', p[0]).group())
                    if int(seq) < 9:
                        batch = str(int(seq) + 1)
                        prefix = p[0][:3]
                    elif int(seq) >= 9:
                        batch = '0'
                        prefix = increment_str(p[0][:3])
                    else:
                        prefix = p[0][:3]
                        batch = str(int(seq) + 1)
                    production.batch = prefix + batch

                if not products:
                    production.batch = 'AAA0'
                if not production.product_id.product_tmpl_id.pro_type or production.product_id.product_tmpl_id.pro_type == 'eda':
                    production.batch = production.batch
                else:
                    production.batch = production.batch + 'F'
            for picking in production.env['stock.picking'].search([('origin', '=', production.name)]):
                picking.batch = production.batch
                picking.mrp_product_id = production.product_id
            for move in production.move_finished_ids.filtered(lambda m: m.picking_id.origin != production.name):
                move.picking_id.origin = production.name
                move.picking_id.batch = production.batch
                move.picking_id.mrp_product_id = production.product_id
                for m in move.move_dest_ids.filtered(lambda m: m.picking_id.origin != production.name):
                    m.picking_id.origin = production.name
                    m.picking_id.batch = production.batch
                    m.picking_id.group_id = production.procurement_group_id
                    m.picking_id.mrp_product_id = production.product_id
            if not production.move_byproduct_ids:
                checks = production.workorder_ids.check_ids.filtered(
                    lambda m: m.test_type_id.technical_name == 'register_byproducts')
                if checks:
                    for check in checks:
                        for work in production.workorder_ids.search([('current_quality_check_id', '=', check.id)]):
                            work.current_quality_check_id = work.current_quality_check_id.next_check_id.id
                    checks.unlink()
            production.state = 'confirmed'
        return True

    def action_generate_serial(self):
        res = super().action_generate_serial()
        self.lot_producing_id.ref = self.batch

        for check in self.workorder_ids.check_ids.filtered(
                lambda m: m.test_type_id.technical_name == 'register_byproducts'):
            if not check.lot_id:
                check.lot_id = self.env['stock.production.lot'].create({
                    'product_id': check.component_id.id,
                    'company_id': self.company_id.id,
                    'ref': self.batch
                })
        return res

    @api.depends(
        'move_raw_ids.state', 'move_raw_ids.quantity_done', 'move_finished_ids.state',
        'workorder_ids', 'workorder_ids.state', 'product_qty', 'qty_producing')
    def _compute_state(self):
        """ Compute the production state. It use the same process than stock
        picking. It exists 3 extra steps for production:
        - progress: At least one item is produced or consumed.
        - to_close: The quantity produced is greater than the quantity to
        produce and all work orders has been finished.
        """
        # TODO: duplicated code with stock_picking.py
        for production in self:
            if all(move.state == 'draft' for move in production.move_raw_ids):
                production.state = 'draft'
            elif production.qty_producing == production.qty_produced > 0:
                production.state = 'to_close'
            elif any(wo_state in ('progress', 'done') for wo_state in production.workorder_ids.mapped('state')):
                production.state = 'progress'
            elif not float_is_zero(production.qty_producing, precision_rounding=production.product_uom_id.rounding):
                production.state = 'progress'
            elif any(not float_is_zero(move.quantity_done,
                                       precision_rounding=move.product_uom.rounding or move.product_id.uom_id.rounding)
                     for move in production.move_raw_ids):
                production.state = 'progress'
            else:
                production.state = production.state

            production.reservation_state = 'assigned'
            # Compute reservation state according to its component's moves.
            if production.state not in ('draft', 'done', 'cancel'):
                relevant_move_state = production.move_raw_ids._get_relevant_state_among_moves()
                if relevant_move_state == 'partially_available':
                    if production.bom_id.operation_ids and production.bom_id.ready_to_produce == 'asap':
                        production.reservation_state = production._get_ready_to_produce_state()
                    else:
                        production.reservation_state = 'confirmed'
                elif relevant_move_state != 'draft':
                    production.reservation_state = relevant_move_state
            elif production.state in ('draft', 'done', 'cancel'):
                production.reservation_state = False

    def action_cancel(self):
        for production in self:
            if production.state not in ('draft', 'confirmed', 'cancel'):
                raise UserError(_('You can not cancel mo unless it was draft or confirmed'))
            production.state = 'cancel'
        res = super(MrpUpdates, self).action_cancel()
        return res

    def button_mark_done(self):
        res = super(MrpUpdates, self).button_mark_done()
        self.state = 'done'
        return res

    def _cal_price(self, consumed_moves):
        """Set a price unit on the finished move according to `consumed_moves`.
        """
        super()._cal_price(consumed_moves)

        work_center_cost = 0
        finished_move = self.move_finished_ids.filtered(
            lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity_done > 0)
        for work_order in self.workorder_ids:
            time_lines = work_order.time_ids.filtered(lambda x: x.date_end and not x.cost_already_recorded)
            duration = sum(time_lines.mapped('duration'))
            time_lines.write({'cost_already_recorded': True})
            work_center_cost += (duration / 60.0) * work_order.workcenter_id.costs_hour
        extra_cost = self.extra_cost
        bom_lines = []
        for line in self.bom_id.bom_line_ids:
            bom_lines.append(line.product_id.id)

        total = sum([abs(m.stock_valuation_layer_ids.value) for m in consumed_moves.sudo()]) + work_center_cost
        bulk_cost = sum([abs(m.stock_valuation_layer_ids.value) for m in
                         consumed_moves.sudo().filtered(lambda x: x.product_id.id not in bom_lines)])
        if finished_move:
            if finished_move.product_id.cost_method != 'standard':
                qty_done = finished_move.product_uom._compute_quantity(finished_move.quantity_done,
                                                                       finished_move.product_id.uom_id)
                extra_cost = self.extra_cost * qty_done
                finished_move.price_unit = (sum([abs(m.stock_valuation_layer_ids.value) for m in
                                                 consumed_moves.sudo()]) + work_center_cost + extra_cost) / qty_done
        cost = 0
        bulks = self.bom_id.bom_line_ids.filtered(
            lambda bom_line: bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom')
        bulk = self.env['mrp.bom']
        if bulks:
            bulk = bulks[0].child_bom_id
        cost = 0
        if self.move_byproduct_ids.filtered(lambda m: not m.product_uom_qty > 0.0):

            for move in self.move_finished_ids:
                if bulk and move.product_id.mfg and self.product_id.mfg and move.product_id != self.product_id:
                    cost = ((total - bulk_cost) + ((
                                                           move.product_id.mfg * move.quantity_done) / bulk.product_qty * bulk_cost) + self.extra_cost * move.quantity_done)
                    if move.quantity_done > 0.0:
                        move.unit_price = cost / move.quantity_done
                    for m in move.move_line_ids:
                        if m.qty_done > 0.0:
                            m.lot_id.cost = cost / m.qty_done
            if self.qty_produced > 0.0:
                self.lot_producing_id.cost = ((total - bulk_cost) + (
                        (
                                self.product_id.mfg * self.qty_produced) / bulk.product_qty * bulk_cost) + self.extra_cost * self.qty_produced) / self.qty_produced

        else:
            if self.qty_produced > 0.0:
                self.lot_producing_id.cost = (total + self.extra_cost * self.qty_produced) / self.qty_produced

        return True

    def _get_moves_raw_values(self):
        moves = []
        for production in self:
            bulks = self.bom_id.bom_line_ids.filtered(
                lambda bom_line: bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom')
            bulk = self.env['mrp.bom']
            if bulks:
                bulk = bulks[0].child_bom_id
            if production.bom_id and bulk and production.product_id.mfg:
                if round(production.product_qty * production.product_id.mfg) > round(bulk.product_qty):
                    production.product_qty = production.bom_id.product_qty
            factor = production.product_uom_id._compute_quantity(production.product_qty,
                                                                 production.bom_id.product_uom_id) / production.bom_id.product_qty
            boms, lines = production.bom_id.explode(production.product_id, factor,
                                                    picking_type=production.bom_id.picking_type_id)
            for bom_line, line_data in lines:
                if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom' or \
                        bom_line.product_id.type not in ['product', 'consu']:
                    continue
                operation = bom_line.operation_id.id or line_data['parent_line'] and line_data[
                    'parent_line'].operation_id.id
                moves.append(production._get_move_raw_values(
                    bom_line.product_id,
                    line_data['qty'],
                    bom_line.product_uom_id,
                    operation,
                    bom_line
                ))
            for byproduct in production.bom_id.byproduct_ids:
                product_uom_factor = production.product_uom_id._compute_quantity(production.product_qty,
                                                                                 production.bom_id.product_uom_id)
                qty = byproduct.product_qty * (product_uom_factor / production.bom_id.product_qty)
                if production.bom_id and bulk and production.product_id.mfg and byproduct.product_id.mfg:
                    qty = round(
                        (bulk.product_qty - (
                                    production.product_qty * production.product_id.mfg)) / byproduct.product_id.mfg)
                bom = self.env['mrp.bom']._bom_find(product=byproduct.product_id,
                                                    company_id=byproduct.product_id.company_id.id,
                                                    bom_type='normal')
                if bom:
                    factor = byproduct.product_uom_id._compute_quantity(qty,
                                                                        bom.product_uom_id) / bom.product_qty
                    boms, lines = bom.explode(byproduct.product_id, factor,
                                              picking_type=production.bom_id.picking_type_id)
                    for bom_line, line_data in lines:
                        if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom' or \
                                bom_line.product_id.type not in ['product', 'consu']:
                            continue
                        if not bom.bom_line_ids.filtered(lambda line: line == bom_line):
                            continue
                        operation = bom_line.operation_id.id or line_data['parent_line'] and line_data[
                            'parent_line'].operation_id.id
                        moves.append(production._get_move_raw_values(
                            bom_line.product_id,
                            line_data['qty'],
                            bom_line.product_uom_id,
                            operation,
                            bom_line
                        ))
        return moves

    def _get_moves_finished_values(self):
        moves = []
        for production in self:
            bulks = self.bom_id.bom_line_ids.filtered(
                lambda bom_line: bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom')
            bulk = self.env['mrp.bom']
            if bulks:
                bulk = bulks[0].child_bom_id
            if production.bom_id and bulk and production.product_id.mfg:
                if round(production.product_qty * production.product_id.mfg) > round(bulk.product_qty):
                    production.product_qty = production.bom_id.product_qty
            if production.product_id in production.bom_id.byproduct_ids.mapped('product_id'):
                raise UserError(
                    _("You cannot have %s  as the finished product and in the Byproducts", production.product_id.name))
            moves.append(production._get_move_finished_values(production.product_id.id, production.product_qty,
                                                              production.product_uom_id.id))
            for byproduct in production.bom_id.byproduct_ids:
                product_uom_factor = production.product_uom_id._compute_quantity(production.product_qty,
                                                                                 production.bom_id.product_uom_id)
                qty = byproduct.product_qty * (product_uom_factor / production.bom_id.product_qty)
                if production.bom_id and bulk and production.product_id.mfg and byproduct.product_id.mfg:
                    qty = (bulk.product_qty - (
                                production.product_qty * production.product_id.mfg)) / byproduct.product_id.mfg
                moves.append(production._get_move_finished_values(
                    byproduct.product_id.id, qty, byproduct.product_uom_id.id,
                    byproduct.operation_id.id, byproduct.id))
        return moves

    @api.onchange('product_id', 'picking_type_id', 'company_id', 'check_repack')
    def onchange_product_id(self):
        """ Finds UoM of changed product. """
        if not self.product_id:
            self.bom_id = False
        elif not self.bom_id or self.bom_id.product_tmpl_id != self.product_tmpl_id or (
                self.bom_id.product_id and self.bom_id.product_id != self.product_id) or self.bom_id.bom_type != self.check_repack:
            bom = self.env['mrp.bom']._bom_find(product=self.product_id, picking_type=self.picking_type_id,
                                                company_id=self.company_id.id, bom_type='normal',
                                                type=self.check_repack)
            if bom:
                self.bom_id = bom.id
                self.product_qty = self.bom_id.product_qty
                self.product_uom_id = self.bom_id.product_uom_id.id
            else:
                self.bom_id = False
                self.product_uom_id = self.product_id.uom_id.id
    def _get_quantity_to_backorder(self):
        self.ensure_one()
        return max(self.product_qty - self.qty_producing, 1)

    def _generate_backorder_productions(self, close_mo=True):
        backorders = self.env['mrp.production']
        for production in self:
            if production.backorder_sequence == 0:  # Activate backorder naming
                production.backorder_sequence = 1
            backorder_mo = production.copy(default=production._get_backorder_mo_vals())
            if close_mo:
                production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')).write({
                    'raw_material_production_id': backorder_mo.id,
                })
                production.move_finished_ids.filtered(lambda m: m.state not in ('done', 'cancel')).write({
                    'production_id': backorder_mo.id,
                })
            else:
                new_moves_vals = []
                for move in production.move_raw_ids | production.move_finished_ids:
                    if not move.additional and not move.bom_line_id.bom_id.type == 'phantom':
                        qty_to_split = move.product_uom_qty - move.unit_factor * production.qty_producing
                        qty_to_split = move.product_uom._compute_quantity(qty_to_split, move.product_id.uom_id,
                                                                          rounding_method='HALF-UP')
                        move_vals = move._split(qty_to_split)
                        if not move_vals:
                            continue
                        if move.raw_material_production_id:
                            move_vals[0]['raw_material_production_id'] = backorder_mo.id
                        else:
                            move_vals[0]['production_id'] = backorder_mo.id
                        new_moves_vals.append(move_vals[0])
                new_moves = self.env['stock.move'].create(new_moves_vals)
            backorders |= backorder_mo
            for old_wo, wo in zip(production.workorder_ids, backorder_mo.workorder_ids):
                wo.qty_produced = max(old_wo.qty_produced - old_wo.qty_producing, 0)
                if wo.product_tracking == 'serial':
                    wo.qty_producing = 1
                else:
                    wo.qty_producing = wo.qty_remaining
                if wo.qty_producing == 0:
                    wo.action_cancel()

            production.name = self._get_name_backorder(production.name, production.backorder_sequence)

            # We need to adapt `duration_expected` on both the original workorders and their
            # backordered workorders. To do that, we use the original `duration_expected` and the
            # ratio of the quantity really produced and the quantity to produce.
            ratio = production.qty_producing / production.product_qty
            for workorder in production.workorder_ids:
                workorder.duration_expected = workorder.duration_expected * ratio
            for workorder in backorder_mo.workorder_ids:
                workorder.duration_expected = workorder.duration_expected * (1 - ratio)

        # As we have split the moves before validating them, we need to 'remove' the excess reservation
        if not close_mo:
            self.move_raw_ids.filtered(lambda m: not m.additional)._do_unreserve()
            self.move_raw_ids.filtered(lambda m: not m.additional)._action_assign()
        # Confirm only productions with remaining components
        backorders.filtered(lambda mo: mo.move_raw_ids).action_confirm()
        backorders.filtered(lambda mo: mo.move_raw_ids).action_assign()

        # Remove the serial move line without reserved quantity. Post inventory will assigned all the non done moves
        # So those move lines are duplicated.
        backorders.move_raw_ids.move_line_ids.filtered(
            lambda ml: ml.product_id.tracking == 'serial' and ml.product_qty == 0).unlink()
        backorders.move_raw_ids._recompute_state()

        return backorders
