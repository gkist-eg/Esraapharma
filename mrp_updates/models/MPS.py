# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict, namedtuple
from math import log10
import math
from odoo import api, fields, models, _
from odoo.tools.date_utils import add, subtract
from odoo.tools.float_utils import float_round
from odoo.osv.expression import OR, AND
from collections import OrderedDict


class MrpProductionSchedule(models.Model):
    _inherit = 'mrp.production.schedule'
    _order = 'warehouse_id, sequence'
    _description = 'Schedule the production of Product in a warehouse'

    @api.constrains('product_id')
    def on_create_product(self):
        if self.product_id:
            bom = self.env['mrp.bom']._bom_find(
                product=self.product_id, company_id=self.company_id.id,
                bom_type='normal')
            boms, lines = bom.explode(self.product_id, 1)
            for line in lines:
                product = line[0].product_id
                exited = self.search([('product_id', '=', product.id), ('warehouse_id', '=', self.warehouse_id.id)])
                if not exited:
                    self.create({
                        'product_id': product.id,
                        'warehouse_id': self.warehouse_id.id
                    })

    def _get_incoming_qty(self, date_range):
        """ Get the incoming quantity from RFQ and existing moves.

        param: list of time slots used in order to group incoming quantity.
        return: a dict with as key a production schedule and as values a list
        of incoming quantity for each date range.
        """
        incoming_qty = defaultdict(float)
        incoming_qty_done = defaultdict(float)
        after_date = date_range[0][0]
        before_date = date_range[-1][1]
        # Get quantity in RFQ
        rfq_domain = self._get_rfq_domain(after_date, before_date)
        rfq_lines = self.env['purchase.order.line'].search(rfq_domain, order='date_planned')

        index = 0
        for line in rfq_lines:
            # Skip to the next time range if the planned date is not in the
            # current time interval.
            while not (date_range[index][0] <= line.date_planned.date() and date_range[index][1] >= line.date_planned.date()):
                index += 1
            quantity = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
            incoming_qty[date_range[index], line.product_id, line.order_id.picking_type_id.warehouse_id] += quantity

        # Get quantity on incoming moves
        # TODO: issue since it will use one search by move. Should use a
        # read_group with a group by location.
        domain_moves = self._get_moves_domain(after_date, before_date, 'incoming')
        stock_moves = self.env['stock.move'].search(domain_moves, order='date')
        index = 0
        for move in stock_moves:
            # Skip to the next time range if the planned date is not in the
            # current time interval.
            while not (date_range[index][0] <= move.date.date() and date_range[index][1] >= move.date.date()):
                index += 1
            key = (date_range[index], move.product_id, move.location_dest_id.get_warehouse())
            if move.state == 'done':
                incoming_qty_done[key] += move.product_qty
            else:
                incoming_qty[key] += move.product_qty

        return incoming_qty, incoming_qty_done

    def _get_moves_domain(self, date_start, date_stop, type):
        """ Return domain for incoming or outgoing moves """
        location = type == 'incoming' and 'location_dest_id' or 'location_id'
        location_dest = type == 'incoming' and 'location_id' or 'location_dest_id'
        return [
            (location, 'child_of', self.mapped('warehouse_id.view_location_id').ids),
            ('product_id', 'in', self.mapped('product_id').ids),
            ('state', '!=', 'cancel'),
            (location + '.usage', '!=', 'inventory'),
            '|',
            (location_dest + '.usage', 'not in', ('internal', 'inventory')),
            '&',
            (location_dest + '.usage', '=', 'internal'),
            '!',
            (location_dest, 'child_of', self.mapped('warehouse_id.view_location_id').ids),
            ('inventory_id', '=', False),
            ('date', '>=', date_start),
            ('date', '<=', date_stop)
        ]

    def _get_indirect_demand_tree(self):
        """ Get the tree architecture for all the BoM and BoM line that are
        related to production schedules in self. The purpose of the tree:
        - Easier traversal than with BoM and BoM lines.
        - Allow to determine the schedules evaluation order. (compute the
        schedule without indirect demand first)
        It also made the link between schedules even if some intermediate BoM
        levels are hidden. (e.g. B1 -1-> B2 -1-> B3, schedule for B1 and B3
        are linked even if the schedule for B2 does not exist.)
        Return a list of namedtuple that represent on top the schedules without
        indirect demand and on lowest leaves the schedules that are the most
        influenced by the others.
        """
        boms = self.env['mrp.bom'].search([
            '|',
            ('product_id', 'in', self.mapped('product_id').ids),
            '&',
            ('product_id', '=', False),
            ('product_tmpl_id', 'in', self.mapped('product_id.product_tmpl_id').ids),
            ('bom_type', '=', 'normal')
        ])
        bom_lines_by_product = defaultdict(lambda: self.env['mrp.bom'])
        bom_lines_by_product_tmpl = defaultdict(lambda: self.env['mrp.bom'])
        for bom in boms:
            if bom.product_id:
                if bom.product_id not in bom_lines_by_product:
                    bom_lines_by_product[bom.product_id] = bom
            else:
                if bom.product_tmpl_id not in bom_lines_by_product_tmpl:
                    bom_lines_by_product_tmpl[bom.product_tmpl_id] = bom

        Node = namedtuple('Node', ['product', 'ratio', 'children'])
        indirect_demand_trees = {}
        product_visited = {}

        def _get_product_tree(product, ratio):
            product_tree = product_visited.get(product)
            if product_tree:
                return Node(product_tree.product, ratio, product_tree.children)

            product_tree = Node(product, ratio, [])
            product_boms = (bom_lines_by_product[product] | bom_lines_by_product_tmpl[product.product_tmpl_id]).sorted(
                'sequence')[:1]
            if not product_boms:
                product_boms = self.env['mrp.bom']._bom_find(product=product) or self.env['mrp.bom']
            for line in product_boms.bom_line_ids:
                line_qty = line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_id)
                bom_qty = line.bom_id.product_uom_id._compute_quantity(line.bom_id.product_qty,
                                                                       line.bom_id.product_tmpl_id.uom_id)
                ratio = line_qty / bom_qty
                tree = _get_product_tree(line.product_id, ratio)
                product_tree.children.append(tree)
                if line.product_id in indirect_demand_trees:
                    del indirect_demand_trees[line.product_id]
            product_visited[product] = product_tree
            return product_tree

        for product in self.mapped('product_id'):
            if product in product_visited:
                continue
            indirect_demand_trees[product] = _get_product_tree(product, 1.0)

        return [tree for tree in indirect_demand_trees.values()]

    def _get_replenish_qty(self, after_forecast_qty):
        """ Modify the quantity to replenish depending the min/max and targeted
        quantity for safety stock.

        param after_forecast_qty: The quantity to replenish in order to reach a
        safety stock of 0.
        return: quantity to replenish
        rtype: float
        """
        bom_f = self.env['mrp.bom']._bom_find(
            product=self.product_id, company_id=self.company_id.id,
            bom_type='normal')

        optimal_qty = self.forecast_target_qty - after_forecast_qty

        if optimal_qty > self.max_to_replenish_qty:
            replenish_qty = self.max_to_replenish_qty
        elif optimal_qty < self.min_to_replenish_qty:
            replenish_qty = self.min_to_replenish_qty
        else:
            if bom_f and optimal_qty > 0:
                replenish_qty = math.ceil(optimal_qty / bom_f[0].product_qty) * bom_f[0].product_qty
            else:
                replenish_qty = optimal_qty

        return replenish_qty

    # def get_production_schedule_view_state(self):
    #     """ Prepare and returns the fields used by the MPS client action.
    #     For each schedule returns the fields on the model. And prepare the cells
    #     for each period depending the manufacturing period set on the company.
    #     The forecast cells contains the following information:
    #     - forecast_qty: Demand forecast set by the user
    #     - date_start: First day of the current period
    #     - date_stop: Last day of the current period
    #     - replenish_qty: The quantity to replenish for the current period. It
    #     could be computed or set by the user.
    #     - replenish_qty_updated: The quantity to replenish has been set manually
    #     by the user.
    #     - starting_inventory_qty: During the first period, the quantity
    #     available. After, the safety stock from previous period.
    #     - incoming_qty: The incoming moves and RFQ for the specified product and
    #     warehouse during the current period.
    #     - outgoing_qty: The outgoing moves quantity.
    #     - indirect_demand_qty: On manufacturing a quantity to replenish could
    #     require a need for a component in another schedule. e.g. 2 product A in
    #     order to create 1 product B. If the replenish quantity for product B is
    #     10, it will need 20 product A.
    #     - safety_stock_qty:
    #     starting_inventory_qty - forecast_qty - indirect_demand_qty + replenish_qty
    #     """
    #     company_id = self.env.company
    #     date_range = company_id._get_date_range()
    #
    #     # We need to get the schedule that impact the schedules in self. Since
    #     # the state is not saved, it needs to recompute the quantity to
    #     # replenish of finished products. It will modify the indirect
    #     # demand and replenish_qty of schedules in self.
    #     schedules_to_compute = self.env['mrp.production.schedule'].browse(self.get_impacted_schedule()) | self
    #
    #     # Dependencies between schedules
    #     indirect_demand_trees = schedules_to_compute._get_indirect_demand_tree()
    #
    #     indirect_ratio_mps = schedules_to_compute._get_indirect_demand_ratio_mps(indirect_demand_trees)
    #
    #     # Get the schedules that do not depends from other in first position in
    #     # order to compute the schedule state only once.
    #     indirect_demand_order = schedules_to_compute._get_indirect_demand_order(indirect_demand_trees)
    #     indirect_demand_qty = defaultdict(float)
    #     incoming_qty, incoming_qty_done = self._get_incoming_qty(date_range)
    #     outgoing_qty, outgoing_qty_done = self._get_outgoing_qty(date_range)
    #     read_fields = [
    #         'forecast_target_qty',
    #         'min_to_replenish_qty',
    #         'max_to_replenish_qty',
    #         'product_id',
    #     ]
    #     if self.env.user.has_group('stock.group_stock_multi_warehouses'):
    #         read_fields.append('warehouse_id')
    #     if self.env.user.has_group('uom.group_uom'):
    #         read_fields.append('product_uom_id')
    #     production_schedule_states = schedules_to_compute.read(read_fields)
    #     production_schedule_states_by_id = {mps['id']: mps for mps in production_schedule_states}
    #     for production_schedule in indirect_demand_order:
    #         # Bypass if the schedule is only used in order to compute indirect
    #         # demand.
    #         rounding = production_schedule.product_id.uom_id.rounding
    #         lead_time = production_schedule._get_lead_times()
    #         production_schedule_state = production_schedule_states_by_id[production_schedule['id']]
    #         if production_schedule in self:
    #             procurement_date = add(fields.Date.today(), days=lead_time)
    #             precision_digits = max(0, int(-(log10(production_schedule.product_uom_id.rounding))))
    #             production_schedule_state['precision_digits'] = precision_digits
    #             production_schedule_state['forecast_ids'] = []
    #
    #         starting_inventory_qty = production_schedule.product_id.with_context(warehouse=production_schedule.warehouse_id.id).qty_available
    #         if len(date_range):
    #             starting_inventory_qty -= incoming_qty_done.get((date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)
    #             starting_inventory_qty += outgoing_qty_done.get((date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)
    #
    #         for date_start, date_stop in date_range:
    #             forecast_values = {}
    #             key = ((date_start, date_stop), production_schedule.product_id, production_schedule.warehouse_id)
    #             existing_forecasts = production_schedule.forecast_ids.filtered(lambda p: p.date >= date_start and p.date <= date_stop)
    #             if production_schedule in self:
    #                 forecast_values['date_start'] = date_start
    #                 forecast_values['date_stop'] = date_stop
    #                 forecast_values['incoming_qty'] = float_round(incoming_qty.get(key, 0.0) + incoming_qty_done.get(key, 0.0), precision_rounding=rounding)
    #                 forecast_values['outgoing_qty'] = float_round(outgoing_qty.get(key, 0.0) + outgoing_qty_done.get(key, 0.0), precision_rounding=rounding)
    #
    #             forecast_values['indirect_demand_qty'] = float_round(indirect_demand_qty.get(key, 0.0), precision_rounding=rounding)
    #             replenish_qty_updated = False
    #             if existing_forecasts:
    #                 forecast_values['forecast_qty'] = float_round(sum(existing_forecasts.mapped('forecast_qty')), precision_rounding=rounding)
    #                 forecast_values['replenish_qty'] = float_round(sum(existing_forecasts.mapped('replenish_qty')), precision_rounding=rounding)
    #
    #                 # Check if the to replenish quantity has been manually set or
    #                 # if it needs to be computed.
    #                 replenish_qty_updated = any(existing_forecasts.mapped('replenish_qty_updated'))
    #                 forecast_values['replenish_qty_updated'] = replenish_qty_updated
    #             else:
    #                 forecast_values['forecast_qty'] = 0.0
    #
    #             if not replenish_qty_updated:
    #                 bom_f = self.env['mrp.bom']._bom_find(
    #                     product=production_schedule.product_id, company_id=production_schedule.company_id.id,
    #                     bom_type='normal')
    #                 replenish_qty = production_schedule._get_replenish_qty(
    #                     starting_inventory_qty - forecast_values['forecast_qty'] - forecast_values[
    #                         'indirect_demand_qty'])
    #                 if bom_f:
    #                     forecast_values['replenish_qty'] =float_round( math.ceil(replenish_qty / bom_f[0].product_qty) * bom_f[0].product_qty ,precision_rounding=rounding)
    #                 else:
    #                     forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
    #
    #                 forecast_values['replenish_qty_updated'] = False
    #
    #             forecast_values['starting_inventory_qty'] = float_round(starting_inventory_qty, precision_rounding=rounding)
    #             forecast_values['safety_stock_qty'] = float_round(starting_inventory_qty - forecast_values['forecast_qty'] - forecast_values['indirect_demand_qty'] + forecast_values['replenish_qty'], precision_rounding=rounding)
    #
    #             if production_schedule in self:
    #                 production_schedule_state['forecast_ids'].append(forecast_values)
    #             starting_inventory_qty = forecast_values['safety_stock_qty']
    #             if not forecast_values['replenish_qty']:
    #                 continue
    #             # Set the indirect demand qty for children schedules.
    #             for (product, ratio) in indirect_ratio_mps[(production_schedule.warehouse_id, production_schedule.product_id)].items():
    #                 related_date = max(subtract(date_start, days=lead_time), fields.Date.today())
    #                 index = next(i for i, (dstart, dstop) in enumerate(date_range) if related_date <= dstart or (related_date >= dstart and related_date <= dstop))
    #                 related_key = (date_range[index], product, production_schedule.warehouse_id)
    #                 indirect_demand_qty[related_key] += ratio * forecast_values['replenish_qty']
    #
    #         if production_schedule in self:
    #             # The state is computed after all because it needs the final
    #             # quantity to replenish.
    #             forecasts_state = production_schedule._get_forecasts_state(production_schedule_states_by_id, date_range, procurement_date)
    #             forecasts_state = forecasts_state[production_schedule.id]
    #             for index, forecast_state in enumerate(forecasts_state):
    #                 production_schedule_state['forecast_ids'][index].update(forecast_state)
    #
    #             # The purpose is to hide indirect demand row if the schedule do not
    #             # depends from another.
    #             has_indirect_demand = any(forecast['indirect_demand_qty'] != 0 for forecast in production_schedule_state['forecast_ids'])
    #             production_schedule_state['has_indirect_demand'] = has_indirect_demand
    #     return [p for p in production_schedule_states if p['id'] in self.ids]

    def action_replenish(self, based_on_lead_time=False):
        """ Run the procurement for production schedule in self. Once the
        procurements are launched, mark the forecast as launched (only used
        for state 'to_relaunch')

        :param based_on_lead_time: 2 replenishment options exists in MPS.
        based_on_lead_time means that the procurement for self will be launched
        based on lead times.
        e.g. period are daily and the product have a manufacturing period
        of 5 days, then it will try to run the procurements for the 5 first
        period of the schedule.
        If based_on_lead_time is False then it will run the procurement for the
        first period that need a replenishment
        """
        production_schedule_states = self.get_production_schedule_view_state()
        production_schedule_states = {mps['id']: mps for mps in production_schedule_states}
        procurements = []
        forecasts_values = []
        forecasts_to_set_as_launched = self.env['mrp.product.forecast']
        for production_schedule in self:
            production_schedule_state = production_schedule_states[production_schedule.id]
            # Check for kit. If a kit and its component are both in the MPS we want to skip the
            # the kit procurement but instead only refill the components not in MPS
            bom = self.env['mrp.bom']._bom_find(
                product=production_schedule.product_id, company_id=production_schedule.company_id.id,
                bom_type='phantom')
            product_ratio = []
            if bom:
                dummy, bom_lines = bom.explode(production_schedule.product_id, 1)
                product_ids = [l[0].product_id.id for l in bom_lines]
                product_ids_with_forecast = self.env['mrp.production.schedule'].search([
                    ('company_id', '=', production_schedule.company_id.id),
                    ('warehouse_id', '=', production_schedule.warehouse_id.id),
                    ('product_id', 'in', product_ids)
                ]).product_id.ids
                product_ratio += [
                    (l[0], l[0].product_qty * l[1]['qty'])
                    for l in bom_lines if l[0].product_id.id not in product_ids_with_forecast
                ]

            # Cells with values 'to_replenish' means that they are based on
            # lead times. There is at maximum one forecast by schedule with
            # 'forced_replenish', it's the cell that need a modification with
            #  the smallest start date.
            replenishment_field = based_on_lead_time and 'to_replenish' or 'forced_replenish'
            forecasts_to_replenish = filter(lambda f: f[replenishment_field], production_schedule_state['forecast_ids'])
            for forecast in forecasts_to_replenish:
                existing_forecasts = production_schedule.forecast_ids.filtered(lambda p: p.date >= forecast['date_start'] and p.date <= forecast['date_stop'])
                extra_values = production_schedule._get_procurement_extra_values(forecast)
                quantity = forecast['replenish_qty'] - forecast['incoming_qty']
                if not bom:
                    bom_f = self.env['mrp.bom']._bom_find(
                        product=production_schedule.product_id, company_id=production_schedule.company_id.id,
                        bom_type='normal')
                    if bom_f and quantity > 0:
                        for i in range(0, math.ceil(quantity / bom_f[0].product_qty)):
                            procurements.append(self.env['procurement.group'].Procurement(
                                production_schedule.product_id,
                                bom_f[0].product_qty,
                                production_schedule.product_uom_id,
                                production_schedule.warehouse_id.lot_stock_id,
                                production_schedule.product_id.name,
                                'MPS', production_schedule.company_id, extra_values
                            ))
                    else:
                        procurements.append(self.env['procurement.group'].Procurement(
                            production_schedule.product_id,
                            quantity,
                            production_schedule.product_uom_id,
                            production_schedule.warehouse_id.lot_stock_id,
                            production_schedule.product_id.name,
                            'MPS', production_schedule.company_id, extra_values
                        ))
                else:
                    for bom_line, qty_ratio in product_ratio:
                        procurements.append(self.env['procurement.group'].Procurement(
                            bom_line.product_id,
                            quantity * qty_ratio,
                            bom_line.product_uom_id,
                            production_schedule.warehouse_id.lot_stock_id,
                            bom_line.product_id.name,
                            'MPS', production_schedule.company_id, extra_values
                        ))

                if existing_forecasts:
                    forecasts_to_set_as_launched |= existing_forecasts
                else:
                    forecasts_values.append({
                        'forecast_qty': 0,
                        'date': forecast['date_stop'],
                        'procurement_launched': True,
                        'production_schedule_id': production_schedule.id
                    })
        if procurements:
            self.env['procurement.group'].with_context(skip_lead_time=True).run(procurements)

        forecasts_to_set_as_launched.write({
            'procurement_launched': True,
        })
        if forecasts_values:
            self.env['mrp.product.forecast'].create(forecasts_values)
        bom = self.env['mrp.bom']._bom_find(
            product=self.product_id, company_id=self.company_id.id,
            bom_type='normal')
        boms, lines = bom.explode(self.product_id, 1)
        for line in lines:
            product = line[0].product_id
            exited = self.search([('product_id', '=', product.id), ('warehouse_id', '=', self.warehouse_id.id)])
            exited.action_replenish()
