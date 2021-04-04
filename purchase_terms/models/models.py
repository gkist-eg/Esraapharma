from odoo import models, fields, api


class EditPurchaseOrder(models.Model):
    _inherit = "purchase.order"
    due_term = fields.Html(string="Terms and Conditions",store=True,copy=True,index=1 )

