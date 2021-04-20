from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    stock_location_ids = fields.Many2many(
        'stock.location',
        'location_security_stock_location_users',
        'user_id',
        'location_id',
        'Stock Locations')


class Locations(models.Model):
    _inherit = 'stock.location'
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', store=True)
    finish = fields.Boolean('Source Location', store=True)


class Picking(models.Model):
    _inherit = 'stock.picking'

    location = fields.Many2one('stock.location', string='Location', store=True, copy=True, readonly=True, index=True)

    def _action_done(self):
        res = super()._action_done()
        if self.origin:
            for picking2 in self:
                for item in self.env['item.transfer'].search([('name', '=', (picking2.origin)[:7])]):
                    item.line_ids._compute_qty()
                    if item.state == 'source_approved':
                        item.state = 'source_lapproved'
        return res
