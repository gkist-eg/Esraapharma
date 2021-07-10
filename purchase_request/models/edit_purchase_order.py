from itertools import groupby
from pytz import timezone, UTC
from werkzeug.urls import url_encode

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang


class AccountMove(models.Model):
    _inherit = "account.move"
    invoice_origin = fields.Char(string='Origin', readonly=False, tracking=True,
                                 help="The document(s) that generated the invoice.")


class EditPurchaseOrder(models.Model):
    _inherit = "purchase.order"

    request_name = fields.Char("Request Name", readonly=False)
    attachmentt_ids = fields.Many2many('ir.attachment', string='Attachments', store=True,
                                       compute="get_line_purchase_request", readonly=False)
    purchase_requests = fields.Many2one('purchase.requests', string='Purchase Request', readonly=False)
    supplier_offer = fields.Many2many('ir.attachment', 'suplier_offer', string='Supplier Offer', required=True)
    purchase_request_ids = fields.Many2many('purchase.requests', 'purchase_request', string='Purchase Requests',
                                            domain="[('request_category_id', '=',product_category_id ),('state', 'in',['request_approved', 'fully_quotationed'])]")
    product_category_id = fields.Many2one('product.category', string='Order Category', readonly=False)
    # approver_id = fields.Many2one('res.users', string='Approver', readonly=True)
    # approverrr_id = fields.Many2one('res.users', string='Final Approver', readonly=True)
    # state = fields.Selection([
    #     ('draft', 'RFQ'),
    #     ('sent', 'RFQ Sent'),
    #     ('confirm', 'confirmed'),
    #     ('leader_approved', 'Leaderteam Approved'),
    #     ('maneger_approved', 'Manager Approved'),
    #     ('purchase', 'Purchase Order'),
    #     ('done', 'Locked'),
    #     ('cancel', 'Canselled'),
    # ], default='draft', readonly=True )

    # due_term=fields.Html("body")
    notes = fields.Text("Notes")
    ship_by = fields.Selection([('by_sea', 'BY SEA'), ('by_air', 'BY AIR'), ], string=" Ship By ")
    customize_payment = fields.Boolean("Customize Payment", default=False)
    payment_terms_customized = fields.Char("Payment Terms/Customized")
    is_order_line = fields.Boolean("", )
    is_country = fields.Boolean("is country", default=False)
    is_order_categ = fields.Boolean('', default=False)

    # is_invisible=fields.Boolean("is invisible",default=False)
    # statt = fields.Selection([
    #     ('import_approval', ' Import Approval'),
    #     ('transfer_money', 'Transfer Money'),
    #     ('send_swift', 'Send Swift'),
    #     ('send_doc', 'Send Doc'),
    #     ('send_form', 'Send Form4'),
    #     ('moh', 'MOH Release'),
    #     ('clearance', 'Clearance'),
    # ], default='import_approval', readonly=True)
    # attachmenttt_id = fields.Many2many('ir.attachment','attache', string='Attachments',)
    # note = fields.Text("Note", tracking=True)
    # DateDate=fields.Date("Date" ,default=fields.Date.today,tracking=True,)
    # foreign_ids = fields.One2many('purchase.foreignn', 'foreign_id', string='foreign_ids', tracking=True)

    # @api.onchange("partner_id")
    # def get_currency_id(self):
    #     for rec in self:
    #         rec.currency_id=rec.partner_id.property_purchase_currency_id
    #         country_id=self.env.ref('base.eg').id
    #         if country_id==rec.partner_id.country_id.id or rec.partner_id.country_id.name=="Egypt":
    #             rec.is_country=True
    #         else:
    #             rec.is_country = False

    # def action_confirm_conf(self):
    #     attachmenttt_id=[]
    #     note=[]
    #     DateDate=[]
    #     for rec in self:
    #         if rec.statt=="import_approval":
    #             rec.statt="transfer_money"
    #             foriegn=self.env['purchase.foreignn'].create(
    #                 {
    #                     'foreign_id': rec.id,
    #                     'name':'Transfer Money',
    #                     'attachment_id': rec.attachmenttt_id,
    #                     'note': rec.note,
    #                     'DateDate': rec.DateDate,
    #                 })
    #         elif rec.statt=="transfer_money":
    #             rec.statt="send_swift"
    #             foriegn=self.env['purchase.foreignn'].create(
    #                 {
    #                     'foreign_id': rec.id,
    #                     'name': 'Send Swift',
    #                     'attachment_id': rec.attachmenttt_id,
    #                     'note': rec.note,
    #                     'DateDate': rec.DateDate,
    #                 })
    #         elif rec.statt=="send_swift":
    #             rec.statt="send_doc"
    #             foriegn = self.env['purchase.foreignn'].create(
    #                 {
    #                     'foreign_id': rec.id,
    #                     'name': 'Send Doc',
    #                     'attachment_id': rec.attachmenttt_id,
    #                     'note': rec.note,
    #                     'DateDate': rec.DateDate,
    #                 })
    #         elif rec.statt=="send_doc":
    #             rec.statt="send_form"
    #             foriegn = self.env['purchase.foreignn'].create(
    #                 {
    #                     'foreign_id': rec.id,
    #                     'name': 'Send Form4',
    #                     'attachment_id': rec.attachmenttt_id,
    #                     'note': rec.note,
    #                     'DateDate': rec.DateDate,
    #                 })
    #         elif rec.statt=="send_form":
    #             rec.statt="moh"
    #             foriegn = self.env['purchase.foreignn'].create(
    #                 {
    #                     'foreign_id': rec.id,
    #                     'name': 'MOH Release',
    #                     'attachment_id': rec.attachmenttt_id,
    #                     'note': rec.note,
    #                     'DateDate': rec.DateDate,
    #                 })
    #         elif rec.statt=="moh":
    #             rec.statt="clearance"
    #             rec.is_invisible=True
    #             foriegn = self.env['purchase.foreignn'].create(
    #                 {
    #                     'foreign_id': rec.id,
    #                     'name': 'Clearance',
    #                     'attachment_id': rec.attachmenttt_id,
    #                     'note': rec.note,
    #                     'DateDate': rec.DateDate,
    #                 })
    #             self._create_picking()

    @api.depends("purchase_request_ids")
    def get_line_purchase_request(self):
        order_lines = []
        if self.purchase_request_ids:
            for rec in self:
                for request in self.purchase_request_ids:
                    for line in request.request_line_ids:
                        order_lines.append((0, 0, {
                            'product_id': line.product_id.id,
                            'name': line.product_id.name,
                            'product_qty': line.product_qty,
                            'product_uom': line.product_uom_id.id,
                            'price_unit': 0,
                            'purchase_request_line': line.id,
                            'purchase_requests_id': request.id,
                            'attachmentt_ids': [a.id for a in line.attachment_ids],
                            'date_planned': line.due_date or self.date_order,
                        }))

            self.write({'order_line': False})
            self.sudo().write({'order_line': order_lines, })

    # @api.depends("purchase_request_ids")
    # def get_line_purchase_request(self):
    #     for rec in self:
    #         order_lines = []
    #         for request in self.purchase_request_ids:
    #             for line in request.request_line_ids:
    #                 if line.state!="fully_quotationed":
    #                     order_lines.append((0, 0, {
    #                         'product_id': line.product_id.id,
    #                         'name': line.name,
    #                         'product_qty': line.product_qty,
    #                         'product_uom': line.product_uom_id.id,
    #                         'price_unit': 0,
    #                         'purchase_request_line': [line.id],
    #                         'attachmentt_ids': [a.id for a in line.attachment_ids],
    #                         'date_planned': line.due_date,
    #                     }))
    #
    #     self.write({'order_line': False})
    #     self.sudo().write({'order_line': order_lines,'attachmentt_ids':self.attachmentt_ids.ids})

    # def button_confirmconfirm(self):
    #     for rec in self:
    #         rec.state="confirm"
    #         rec.approver_id=self.env.user.id
    #     if self.env.context.get('active_model',False)=="purchase.requests":
    #         return {
    #             'name': 'New Quotation',
    #             'domain': [],
    #             'res_model': 'purchase.order',
    #             'res_id': self.id,
    #             'type': 'ir.actions.act_window',
    #             'view_mode': 'form',
    #             'view_type': 'form',
    #             'context': {
    #                 'active_model':"purchase.requests",
    #             },
    #             'target': 'new',
    #         }
    #
    # def button_leaderapprove(self):
    #     for rec in self:
    #             rec.state="leader_approved"
    #     if self.env.context.get('active_model',False)=="purchase.requests":
    #         return {
    #             'name': 'New Quotation',
    #             'domain': [],
    #             'res_model': 'purchase.order',
    #             'res_id': self.id,
    #             'type': 'ir.actions.act_window',
    #             'view_mode': 'form',
    #             'view_type': 'form',
    #             'context': {
    #                 'active_model': "purchase.requests",
    #             },
    #             'target': 'new',
    #         }
    #
    #
    #
    # def button_manegerapprove(self):
    #     for rec in self:
    #             rec.state="maneger_approved"
    #     if self.env.context.get('active_model',False)=="purchase.requests":
    #         return {
    #             'name': 'New Quotation',
    #             'domain': [],
    #             'res_model': 'purchase.order',
    #             'res_id': self.id,
    #             'type': 'ir.actions.act_window',
    #             'view_mode': 'form',
    #             'view_type': 'form',
    #             'context': {
    #                 'active_model': "purchase.requests",
    #             },
    #             'target': 'new',
    #         }

    # def button_approve(self, force=False):
    #     self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
    #     self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
    #     if self.is_country:
    #         self._create_picking()
    #     return True

    @api.constrains('state')
    def _check_order_line_price(self):
        if self.state == "confirm":
            if not self.supplier_offer:
                raise ValidationError(_('you MUST INSERT Supplier Offer'))
            for rec in self:
                for line in rec.order_line:
                    if line.price_unit == 0:
                        raise ValidationError(_('PRICE UNIT MUST BE MORE THAN 0.'))
                    # or self.state == "leader_approved" or self.state == "maneger_approved"

    @api.model
    def create(self, vals):
        res = super(EditPurchaseOrder, self).create(vals)
        for rec in res:
            for line in rec.order_line:
                if line.purchase_request_line:
                    for line_rec in line.purchase_request_line:
                        line_rec.sudo().write({'state': "fully_quotationed"})
        return res


class EditPurchaseOrderLin(models.Model):
    _inherit = "purchase.order.line"

    attachmentt_ids = fields.Many2many('ir.attachment', "attachmen", string='Attachments')
    # purchase_requests = fields.Char(string='PR.NO', readonly=True,store=True)
    purchase_requests_id = fields.Many2one('purchase.requests', string='Purchase Request', store=True)
    last_price_purchase = fields.Float("Last Price Purchase", compute="get_last_purchase_price", store=True)
    last_date_purchase = fields.Date("Last Date Purchase", compute="get_last_purchase_price", store=True)
    # purchase_request_line = fields.Many2one("purchase.request.line", "purchase request line")
    categ_id = fields.Many2one('product.category', string='product Category', related="order_id.product_category_id")
    purchase_request_line = fields.Many2one("purchase.request.line", string="Purchase Requast Line", )

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        if not self.product_id or self.state != 'draft':
            return
        params = {'order_id': self.order_id}
        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order.date(),
            uom_id=self.product_uom,
            params=params)

        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # If not seller, use the standard price. It needs a proper currency conversion.
        if not seller:
            po_line_uom = self.product_uom or self.product_id.uom_po_id
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                self.product_id.uom_id._compute_price(self.product_id.standard_price, po_line_uom),
                self.product_id.supplier_taxes_id,
                self.taxes_id,
                self.company_id,
            )
            if price_unit and self.order_id.currency_id and self.order_id.company_id.currency_id != self.order_id.currency_id:
                price_unit = self.order_id.company_id.currency_id._convert(
                    price_unit,
                    self.order_id.currency_id,
                    self.order_id.company_id,
                    self.date_order or fields.Date.today(),
                )

            self.price_unit = price_unit
            return

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,
                                                                             self.product_id.supplier_taxes_id,
                                                                             self.taxes_id,
                                                                             self.company_id) if seller else 0.0
        if price_unit and seller and self.order_id.currency_id and seller.currency_id != self.order_id.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, self.order_id.currency_id, self.order_id.company_id, self.date_order or fields.Date.today())

        if seller and self.product_uom and seller.product_uom != self.product_uom:
            price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)

        self.price_unit = price_unit

    @api.depends('product_id')
    def get_last_purchase_price(self):
        for rec in self:
            if rec.product_id:
                lastprice = self.env['account.move.line'].search(
                    [('product_id', '=', rec.product_id.id), ('move_id.move_type', 'in', ('in_invoice', 'in_refund'))],
                    limit=1)
                rec.last_price_purchase = lastprice.price_unit
                rec.last_date_purchase = lastprice.date
            else:
                rec.last_price_purchase = False
                rec.last_date_purchase = False

# class PurchaseOrderForeign(models.Model):
#     _name = "purchase.foreignn"
#     _description = "Purchase Foreign"
#
#     name=fields.Char("state")
#     attachment_id = fields.Many2many('ir.attachment', string='Attachments', )
#     note = fields.Text("Note", tracking=True)
#     DateDate = fields.Date("Date", default=fields.Date.today, tracking=True, )
#     foreign_id=fields.Many2one('purchase.order', string='Purchase foreign',)
