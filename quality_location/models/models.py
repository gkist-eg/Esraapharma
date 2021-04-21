# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    release_date = fields.Datetime('Release Date',compute='_compute_release_date')
    release_state = fields.Boolean('Check Release',compute='_compute_release_date')

    def _compute_release_date(self):
        for lot in self:
            stock_moves = self.env['stock.move.line'].sudo().search([
                        ('lot_id', '=', lot.id),
                        ('state', '=', 'done'), ('location_id.stock_usage', '=', 'qrtin'),
                        ('location_dest_id.usage', '=', 'internal'),
                    ])

            stock_moves = stock_moves.filtered(
                    lambda move: move.picking_id.location_id.usage == 'internal' and move.state == 'done')
            if stock_moves:
                lot.release_date = stock_moves[0].picking_id.date_done
            else:
                lot.release_date = False

            if any(stock_moves.search([('id', 'in', stock_moves.ids)]).filtered(
                    lambda move: move.picking_id.location_dest_id.stock_usage == 'release' and move.state == 'done')):
                lot.release_state = True
            elif any (stock_moves.search([('id', 'in', stock_moves.ids)]).filtered(
                    lambda move: move.picking_id.location_dest_id.stock_usage == 'reject' and move.state == 'done')):
                lot.release_state = False
            else:
                lot.release_state = False


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _getUserGroupId(self):
            if self.env.user.has_group('quality_location.group_stock_approve'):
                return [('id', '=', self.env.user.stock_location_ids.ids), ('stock_usage', '!=', 'production')]
            elif self.env.user.has_group('stock.group_stock_user'):
                return [('id', '=', self.env.user.stock_location_ids.ids), ('stock_usage', 'not in', ('production', 'qrtin'))]

    @api.depends('state')
    def _compute_show_validate(self):
        for picking in self:
            if picking.state == 'assigned' and picking.approve and self.location_id in self.env.user.stock_location_ids and self.location_dest_id in self.env.user.stock_location_ids:
                if(self.location_id.stock_usage == 'qrtin' or self.location_dest_id.stock_usage == 'qrtin' ) and self.env.user.has_group('quality_location.group_stock_approve') and not picking.batch and self.picking_type_id.code == 'internal':
                    picking.show_validate = True
                elif(self.location_id.stock_usage == 'qrtin' or self.location_dest_id.stock_usage == 'qrtin' ) and self.env.user.has_group('stock.group_stock_manager') and not self.env.user.has_group('quality_location.group_stock_approve') and not picking.batch and self.picking_type_id.code != 'internal':
                    picking.show_validate = True
                elif (self.location_id.stock_usage == 'qrtin' or self.location_dest_id.stock_usage == 'qrtin' ) and self.env.user.has_group('stock.group_stock_manager') and not self.env.user.has_group('quality_location.group_stock_approve') and picking.batch:
                    picking.show_validate = True

                elif self.location_dest_id.stock_usage != 'qrtin' and self.location_id.stock_usage != 'qrtin' and self.env.user.has_group('stock.group_stock_manager') :
                    picking.show_validate = True
                else:
                    picking.show_validate = False
            else:
                picking.show_validate = False

    @api.depends('state')
    def compute_show_confirm(self):
        for picking in self:
            if picking.state == 'assigned' and not picking.approve and self.location_id in self.env.user.stock_location_ids and self.location_dest_id in self.env.user.stock_location_ids:
                if(self.location_id.stock_usage == 'qrtin' or self.location_dest_id.stock_usage == 'qrtin' ) and self.env.user.has_group('quality_location.group_stock_approve') and not picking.batch and self.picking_type_id.code  == 'internal':
                    picking.show_cofirm = True
                elif (self.location_id.stock_usage == 'qrtin' or self.location_dest_id.stock_usage == 'qrtin') and self.env.user.has_group('stock.group_stock_user') and not self.env.user.has_group('quality_location.group_stock_approve') and picking.batch:
                    picking.show_cofirm = True

                elif (self.location_id.stock_usage == 'qrtin' or self.location_dest_id.stock_usage == 'qrtin' ) and self.env.user.has_group('stock.group_stock_user') and not self.env.user.has_group('quality_location.group_stock_approve') and not picking.batch and self.picking_type_id.code != 'internal':
                    picking.show_cofirm = True

                elif self.location_dest_id.stock_usage != 'qrtin' and self.location_id.stock_usage != 'qrtin' and self.env.user.has_group('stock.group_stock_user'):
                    picking.show_cofirm = True
                else:
                    picking.show_cofirm = False
            else:
                picking.show_cofirm = False

