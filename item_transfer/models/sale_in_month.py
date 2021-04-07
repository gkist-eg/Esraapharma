from datetime import datetime

from odoo import api, fields, models


class SaleInMonth(models.Model):
    _name = 'sale.in.month'
    _inherit = ['mail.thread']
    _rec_name = 'product_id'
    _description = 'Sale In Month'

    product_code = fields.Char('Product Code')
    distributor = fields.Many2one('res.partner', string='Distributors')
    quantity = fields.Float(string='Quantity')
    month = fields.Selection([('January', 'January'), ('2', 'February'),
                              ('3', 'March'), ('4', 'April'),
                              ('5', 'May'), ('6', 'June'),
                              ('7', 'July'), ('8', 'August'),
                              ('9', 'September'), ('10', 'October'),
                              ('11', 'November'), ('12', 'December')]
                             , required=True, )

    @api.onchange('product_code')
    def compute_onchange_product(self):
        for line in self:
            products = self.env['product.map.line'].search(
                [('sale_code', '=', line.product_code),
                 ('distributor', '=', line.distributor.id)
                 ])
            if products:

                line.product_id = products.product_id

            else:

                line.product_id = False

    product_id = fields.Many2one(
        'product.product', 'Product',
        track_visibility='onchange', compute='compute_onchange_product')
