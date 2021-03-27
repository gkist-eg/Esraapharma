
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from email.mime.text import MIMEText as text
import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_round
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ItemRequest(models.Model):
    _inherit = 'item.request'
    production_id = fields.Many2one('mrp.production', 'Production Order')

    def _compute_can_manager_approved(self):
        current_user = self.env.user
        if self.state == 'leader_approved' and current_user.has_group(
                'item_request.item_request_manager') and self.location_id in current_user.multi_locations and not self.production_id:
            self.can_manager_approved = True
        elif self.state == 'leader_approved' and current_user.has_group('mrp.group_mrp_manager') or current_user.has_group('research.group_research_manager') and self.location_id in current_user.multi_locations and self.production_id:
            self.can_manager_approved = True
        else:
            self.can_manager_approved = False

    def button_manager_approved(self):

        copy_record = self.env['stock.picking'].sudo()
        for record in self:
            item = self.env['stock.picking'].search([('origin', '=', self.name)])
            if item:
                raise UserError(_('AlReady Issued '))
            order_lines = []
            if not self.production_id:
                for line in record.line_ids:
                    if line.qty > 0.0:
                        order_lines.append((0, 0, {
                            'name': line.product_id.display_name,
                            'product_id': line.product_id.id,
                            'product_uom': line.product_uom_id.id,
                            'date': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                            'picking_type_id': self.location_id.warehouse_id.out_type_id.id,
                            'restrict_lot_id': line.lot_id.id,
                            'origin': self.name,
                            'product_uom_qty': line.qty,
                        }))

                dest_location = self.env.ref("item_request.emploee_location").id
                copy_record.create({
                    'origin': self.name,
                    'picking_type_id': self.location_id.warehouse_id.out_type_id.id,
                    'move_ids_without_package': order_lines,
                    'location_id': self.location_id.id,
                    'location_dest_id': dest_location,
                    'partner_id': self.requested_by.partner_id.id,
                }).action_confirm()
            else:
                location = self.env['stock.location'].search([('usage', '=', 'production')])
                picking = copy_record.create({
                    'origin': self.name,
                    'batch': self.production_id.batch,
                    'group_id': self.production_id.procurement_group_id.id,
                    'mrp_product_id': self.production_id.product_id.id,
                    'picking_type_id': self.location_id.warehouse_id.pbm_type_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.location_id.warehouse_id.pbm_loc_id.id,
                })
                for line in self.line_ids:
                    if line.qty > 0.0:
                        moves = self.env['stock.move'].sudo().create({
                                'name': line.product_id.display_name,
                                'product_id': line.product_id.id,
                                'product_uom': line.product_uom_id.id,
                                'date': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                'picking_type_id': self.location_id.warehouse_id.manu_type_id.id,
                                'restrict_lot_id': line.lot_id.id,
                                'group_id': self.production_id.procurement_group_id.id,
                                'raw_material_production_id': self.production_id.id,
                                'origin': self.name,
                                'location_id': self.location_id.warehouse_id.pbm_loc_id.id,
                                'location_dest_id': location.id,
                                'product_uom_qty': line.qty,

                            })
                        move = self.env['stock.move'].create({
                                'name': line.product_id.display_name,
                                'product_id': line.product_id.id,
                                'product_uom': line.product_uom_id.id,
                                'date': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                'picking_type_id': self.location_id.warehouse_id.pbm_type_id.id,
                                'restrict_lot_id': line.lot_id.id,
                                'origin': self.name,
                                'picking_id': picking.id,
                                'product_uom_qty': line.qty,
                                'move_dest_ids': [(4, x.id) for x in moves],
                                'location_id': self.location_id.id,
                                'location_dest_id': self.location_id.warehouse_id.pbm_loc_id.id,

                            })
                        moves.move_orig_ids += move
                        moves._action_confirm()

                picking.action_confirm()

        self.line_ids._compute_qty()
        self.state = 'approved'


class MrpItemRequest(models.Model):
    _inherit = 'mrp.production'
    request_count = fields.Integer(compute='_compute_request', string='Requests', default=0)

    requests = fields.Many2many('item.request', compute='_compute_request', string='Requests', copy=False)

    def action_see_request(self):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        When only one found, show the picking immediately.
        '''
        action = self.env.ref('item_request.item_request_form_action')
        result = action.read()[0]

        # override the context to get rid of the default filtering on picking type
        result.pop('id', None)
        result['context'] = {}
        pick_ids = sum([order.requests.ids for order in self], [])
        # choose the view_mode accordingly
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('item_request.view_item_request_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result

    def _compute_request(self):
        for order in self:
            requests = self.env['item.request'].search([('production_id', '=', self.id)])
            order.requests = requests
            order.request_count = len(requests)

    def button_adding(self):
        self.ensure_one()
        return {
            'name': _('Adding Material'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'item.request',
            'view_id': self.env.ref('item_request.view_item_request_form').id,
            'type': 'ir.actions.act_window',
            'context': {'default_production_id': self.id,
                        'default_origin': self.batch,

                        },
            'target': 'new',
        }