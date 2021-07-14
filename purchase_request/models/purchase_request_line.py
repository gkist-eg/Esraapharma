# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PurchaseRequestLine(models.Model):
    _name = "purchase.request.line"
    _description = "Purchase Request Line"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Text(string="Description", tracking=True)
    product_id = fields.Many2one('product.product', string="Product", required=True,
                                 domain="[('categ_id', '=',request_category_id)]", tracking=True)
    product_qty = fields.Float(string="Quantity", required=True, default=1, tracking=True)
    ordered_qty = fields.Float(string="Ordered Qty", tracking=True)
    m_qty = fields.Float(string="M.Qty", tracking=True)
    supply_chain_qty = fields.Float(string="Supply Chain Qty", tracking=True)
    product_uom_id = fields.Many2one("uom.uom", string="Purchase UOM", tracking=True, required=True, readonly=False,
                                     domain="[('category_id', '=',category_uom_id)]")
    category_uom_id = fields.Many2one("uom.category", string="Purchase uom category")
    request_line_id = fields.Many2one("purchase.requests", string="", tracking=True)
    request_date = fields.Date("Request Date", default=fields.Date.today, tracking=True)
    due_date = fields.Date("Due Date", tracking=True, )
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments', tracking=True)
    note = fields.Text("Note", tracking=True)
    request_category_id = fields.Many2one('product.category', string='Request Category',
                                          related='request_line_id.request_category_id', tracking=True)
    state = fields.Selection([("request_approved", "Request Approved"), ("fully_quotationed", "Fully Quotationed")],
                             readonly=True, tracking=True)
    request_state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'To Be Approved'),
        ('leader_approved', 'Leader Approved'),
        ('maneger_approved', 'Manager Approved'),
        ('request_approved', 'Request Approved'),
        ('fully_quotationed', 'Fully Quotationed'),
    ], related="request_line_id.state", readonly=False, tracking=True, store=True)
    requested_by_id = fields.Many2one(
        "res.users",
        related="request_line_id.requested_by_id",
        string="Requested by",
        store=True,
    )
    approver_id = fields.Many2one(
        "hr.employee",
        related="request_line_id.approver_id",
        string="Assigned to",
        store=True,
    )
    start_date = fields.Date(related="request_line_id.start_date", store=True)
    description = fields.Html(
        related="request_line_id.descript",
        string="PR Description",
        store=True,
        readonly=False,
    )
    origin = fields.Char(
        related="request_line_id.name", string="Source Document", store=True
    )
    nname = fields.Char(
        related="request_line_id.nname", string="Source Document", store=True
    )

    @api.onchange("product_qty", 'ordered_qty', 'm_qty')
    @api.depends("product_qty", 'ordered_qty', 'm_qty')
    def get_ordered_m_supply_chain_qty(self):
        for rec in self:
            if rec.product_qty:
                if rec.request_state == 'draft' or self.env.user.id == rec.request_line_id.requested_by_id.id:
                    rec.ordered_qty = rec.product_qty
                elif rec.request_state == 'to_be_approved' and self.env['hr.employee'].search(
                        [('user_id', '=', self.env.user.id)],
                        limit=1).id == rec.request_line_id.approver_id.id:
                    rec.m_qty = rec.ordered_qty
                elif rec.request_state == 'leader_approved' and self.env.user.id == rec.request_line_id.purchase_approver_id.id:
                    rec.supply_chain_qty = rec.m_qty

    def get_description_default(self):
        for rec in self:
            view_id = self.env.ref('purchase.purchase_order_form')
            context = dict(self._context or {})
            active_ids = context.get('active_ids', []) or []
            order_line = []
            records = self.env['purchase.request.line'].browse(active_ids)
            categorys = set(records.mapped('request_category_id').ids)
            purchase_requests = set(records.mapped('request_line_id').ids)
            if len(categorys) > 1:
                raise UserError(_('Choose Only one category'))
            category = records.mapped('request_category_id')
            purchase_request = records.mapped('request_line_id')
            for record in records:
                order_line.append((0, 0, {
                    'product_id': record.product_id.id,
                    'name': record.product_id.name,
                    'date_planned': record.due_date or datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'product_qty': record.product_qty,
                    'product_uom': record.product_uom_id.id,
                    'attachmentt_ids': [a.id for a in record.attachment_ids],
                    'purchase_request_line': record.id,

                }))

            return {
                'name': 'New Quotation',
                'domain': [],
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {
                    "default_order_line": order_line,
                    # "default_date_planned": self.due_date,
                    # "default_request_name": self.nname,
                    # "default_purchase_requests": self.id,
                    "default_product_category_id": category.id,
                    # "default_attachmentt_ids": [i.id for i in self.attachment_ids],
                    # "default_purchase_request_ids": [self.id],
                    "default_is_order_categ": True,

                },
                'target': 'new',
            }

    @api.onchange("product_id")
    def get_description_default_(self):
        for rec in self:
            rec.name = rec.product_id.name

    # @api.onchange("product_id")
    # def get_product_uom_id(self):
    #     for rec in self:
    #         rec.product_uom_id=rec.product_id.uom_id

    @api.onchange("product_id")
    def get_category_uom_id(self):
        for rec in self:
            rec.product_uom_id = rec.product_id.uom_id
            rec.category_uom_id = rec.product_uom_id.category_id
