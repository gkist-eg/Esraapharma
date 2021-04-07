from datetime import datetime

from odoo import api, fields, models


class ProductMap(models.Model):
    _name = 'product.map'
    _inherit = ['mail.thread']
    _rec_name = 'product_id'
    _description = 'Product Mapping'

    product_id = fields.Many2one('product.product', string='Product', track_visibility='always',
                                 domain=[('sale_ok', '=', True)], required=True)
    valid = fields.Date('Valid From', default=fields.Datetime.now, track_visibility='always')
    manager_valid = fields.Date('Managers Valid From ', track_visibility='onchange')
    active = fields.Boolean("Active", default=True, track_visibility='onchange')
    line = fields.Many2many('sale.line', string='Line', track_visibility='always')
    unit_price = fields.Float('Unit Price')

    map_line = fields.One2many('product.map.line', 'map_id', string='Sales Mapping')
    tot_price = fields.Float()


class ProductMapLine(models.Model):
    _name = 'product.map.line'
    _rec_name = 'sale_code'
    _description = 'Sales Mapping'

    map_id = fields.Many2one('product.map', invisible=1)
    distributor = fields.Many2one('res.partner', string='Distributors')
    sale_code = fields.Char("Sales", required=True)
    bonus_code = fields.Char("Bonus")
    tender_code = fields.Char("Tender")
    product_id = fields.Many2one('product.product', related='map_id.product_id', string='Product')
