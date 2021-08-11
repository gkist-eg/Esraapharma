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
