from collections import defaultdict

from odoo import models
import json
from collections import defaultdict
from datetime import datetime
from itertools import groupby
from operator import itemgetter
from re import findall as regex_findall
from re import split as regex_split

from dateutil import relativedelta

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_repr, float_round
from odoo.tools.misc import format_date, OrderedSet


class StockMove(models.Model):
    _inherit = "stock.move"
    restrict_lot_id = fields.Many2one(
        'stock.production.lot', string='Restricted Lot Numbers', readonly=False)

    @api.onchange('restrict_lot_id', 'product_id', 'location_id')
    def _onchange_lot_domain_id(self):
        if self.product_id:
            domain = {'restrict_lot_id': [('product_id', '=', self.product_id.id),
                                          ('quant_ids.location_id', '=', self.location_id.id)]}
            return {'domain': domain}

        if self.restrict_lot_id and not self.product_id:
            self.product_id = self.restrict_lot_id.product_id.id
            self.product_uom_qty = sum(self.restrict_lot_id.quant_ids.filtered(
                lambda quant: quant.location_id.id == self.location_id.id).mapped('quantity'))

        if self.location_id and not self.product_id:
            domain = {'restrict_lot_id': [('quant_ids.location_id', '=', self.location_id.id)]}
            return {'domain': domain}

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
        distinct_fields += ['restrict_lot_id']
        return distinct_fields

    def _action_confirm(self, merge=True, merge_into=False):
        moves = super(StockMove, self)._action_confirm(merge=merge, merge_into=merge_into)
        moves._create_quality_checks()
        return moves

    def _create_quality_checks(self):
        # Groupby move by picking. Use it in order to generate missing quality checks.
        res = super(StockMove, self)._create_quality_checks()
        pick_moves = defaultdict(lambda: self.env['stock.move'])
        check_vals_list = []
        for move in self:
            quality_points_domain = self.env['quality.point']._get_domain(move.product_id,
                                                                          move.picking_id.picking_type_id)
            quality_points = self.env['quality.point'].sudo().search(quality_points_domain)

            if quality_points:
                picking_check_vals_list = quality_points._get_checks_values(move.product_id,
                                                                            move.picking_id.company_id.id,
                                                                            existing_checks=move.picking_id.sudo().check_ids)
                for check_value in picking_check_vals_list:
                    check_value.update({
                        'picking_id': move.picking_id.id,
                        'lot_id': move.restrict_lot_id.id,
                    })
                check_vals_list += picking_check_vals_list
            if move.location_id.stock_usage == 'qrtin':
                quality_checks = self.env['quality.check'].sudo().search(
                    [('product_id', '=', move.product_id.id), ('picking_id', '=', False),
                     ('team_id.read_users_ids', 'in', self.env.user.id),
                     ('finished_lot_id', '=', move.restrict_lot_id.id)])
                quality_checks.sudo().write({'picking_id': move.picking_id.id, })
            if check_vals_list:
                self.env['quality.check'].sudo().create(check_vals_list)
        return True
