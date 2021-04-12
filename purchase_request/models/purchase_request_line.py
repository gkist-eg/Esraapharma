# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError




class PurchaseRequestLine(models.Model):
    _name = "purchase.request.line"
    _description = "Purchase Request Line"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']



    name = fields.Text(string="Description",tracking=True)
    product_id = fields.Many2one(comodel_name='product.product',string="Product",required=True, domain="[('categ_id', '=',request_category_id)]",tracking=True)
    product_qty = fields.Float(string="Quantity",required=True,default=1,tracking=True)
    ordered_qty = fields.Float(string="Ordered Qty",tracking=True)
    m_qty= fields.Float(string="M.Qty",tracking=True)
    supply_chain_qty=fields.Float(string="Supply Chain Qty",tracking=True)
    product_uom_id = fields.Many2one(comodel_name="uom.uom",string="Purchase UOM",tracking=True,required=True,readonly=False,domain="[('category_id', '=',category_uom_id)]")
    category_uom_id = fields.Many2one(comodel_name="uom.category", string="Purchase uom category")
    request_line_id = fields.Many2one(comodel_name="purchase.requests",string="",tracking=True)
    request_date = fields.Date("Request Date", default=fields.Date.today,tracking=True)
    due_date = fields.Date("Due Date",tracking=True, )
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments',tracking=True)
    note=fields.Text("Note",tracking=True)
    request_category_id = fields.Many2one('product.category', string='Request Category',related='request_line_id.request_category_id',tracking=True)
    state=fields.Selection([("request_approved","Request Approved"),("fully_quotationed","Fully Quotationed")],readonly=True,tracking=True)


    @api.onchange("product_qty")
    def get_ordered_m_supply_chain_qty(self):
        for rec in self:
            if rec.product_qty :
                if  int(rec.ordered_qty)==0 or self.env.user.id == rec.request_line_id.requested_by_id.id:
                    rec.ordered_qty=rec.product_qty
                elif self.env['hr.employee'].search([('user_id','=',self.env.user.id)],limit=1).id == rec.request_line_id.approver_id.id:
                    rec.m_qty = rec.product_qty
                elif self.env.user.id==rec.request_line_id.purchase_approver_id.id:
                    rec.supply_chain_qty=rec.product_qty

    @api.onchange("product_id")
    def get_description_default(self):
        for rec in self:
            rec.name=rec.product_id.name


    # @api.onchange("product_id")
    # def get_product_uom_id(self):
    #     for rec in self:
    #         rec.product_uom_id=rec.product_id.uom_id



    @api.onchange("product_id")
    def get_category_uom_id(self):
        for rec in self:
            rec.product_uom_id = rec.product_id.uom_id
            rec.category_uom_id=rec.product_uom_id.category_id



