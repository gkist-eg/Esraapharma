# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    @api.model
    def _getUserGroupId(self):
        if self.user_has_groups('restrict_warehouse.group_restrict_warehouse'):
            return [('id', '=', self.env.user.stock_location_ids.ids), ('usage', 'in', ['internal', 'transit'])]
        else:
            return [('usage', 'in', ['internal', 'transit'])]

    location_ids = fields.Many2many(
        'stock.location', string='Locations',
        readonly=True, check_company=True,
        states={'draft': [('readonly', False)]}
        , domain=_getUserGroupId)

    @api.model
    def open_new_inventory(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock_barcode.stock_barcode_inventory_client_action")
        company_user = self.env.company
        warehouses = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)])
        if warehouses:
            if self.user_has_groups('restrict_warehouse.group_restrict_warehouse'):
                default_location_ids = warehouses.mapped('lot_stock_id').filtered(lambda x: x in self.env.user.stock_location_ids)

            else:
                default_location_ids = warehouses.mapped('lot_stock_id')
        else:
            raise UserError(_('You must define a warehouse for the company: %s.') % (company_user.name,))

        if self.env.ref('stock.warehouse0', raise_if_not_found=False):
            new_inv = self.env['stock.inventory'].create({
                'start_empty': True,
                'name': fields.Date.context_today(self),
                'location_ids': [(6, 0, default_location_ids.ids)],
            })
            new_inv.action_start()
            action['res_id'] = new_inv.id
            params = {
                'model': 'stock.inventory',
                'inventory_id': new_inv.id,
            }
            action['context'] = {'active_id': new_inv.id}
            action = dict(action, target='fullscreen', params=params)
        return action


