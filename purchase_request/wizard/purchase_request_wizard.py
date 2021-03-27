# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class PurchaseRequestWizard(models.TransientModel):
    _name = 'purchase.request.wizard'
    _description = 'purchase.request.wizard'


    choose=fields.Selection([
        ('product', 'Product'),
        ('department', 'Department')], string='Choose',)
    from_date=fields.Date("From Date",default=fields.Date.today)
    to_date=fields.Date("To Date",default=fields.Date.today)
    department_id = fields.Many2one('hr.department', string='Department')
    product_id = fields.Many2one(comodel_name='product.product', string="Product",)



