from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EditPurchaseOrder(models.Model):
    _inherit = "purchase.order"

    product_category_id = fields.Many2one('product.category', string='Order Category', readonly=False)
    is_order_categ=fields.Boolean('',default=False)







class EditPurchaseOrderLin(models.Model):
    _inherit = "purchase.order.line"


    categ_id = fields.Many2one('product.category', string='product Category', related="order_id.product_category_id")





