from datetime import datetime, time

from odoo import api, fields, models, _

class RequestCategory(models.Model):
    _name = "request.category"
    _description = "Requests category"

    name = fields.Char('Request Name', readonly=True, select=True, copy=False, default='New')
    requested_category = fields.Many2one('product.category', string='Requested By')



