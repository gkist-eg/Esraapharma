# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AddManufact(models.Model):
    _inherit = 'product.product'
    man_for = fields.Boolean('Manufacturing For Others', related='product_tmpl_id.man_for', store=True)


class AddFixAssset(models.Model):
    _inherit = 'product.template'
    man_for = fields.Boolean('Manufacturing For Others', store=True)


class EditPurchaseOrder(models.Model):
    _inherit = "purchase.order"

    check_sample = fields.Selection([
        ('normal', 'Normal'), ('plan', 'Sample'),
    ], string='Type ', copy=True, store=True, track_visibility='onchange', default='normal', )
    mfo = fields.Boolean('Manfacturing For Others', store=True)
    name_update = fields.Boolean('Manfacturing For Others', compute="compute_name_update")

    @api.model
    def create(self, vals):
        res = super(EditPurchaseOrder, self).create(vals)
        for rec in res:
            if rec.mfo:
                rec.name = self.env['ir.sequence'].next_by_code('purchase.order.toll') or 'New'

        return res

    @api.onchange('order_line')
    def _onchange_order_lines(self):
        if self.order_line:
            for j in self.order_line:
                if j.product_id.man_for or j.product_id.bom_ids.type == 'subcontract':
                    self.mfo = True

    @api.onchange('mfo')
    def compute_name_update(self):
        for record in self:
            done = False
            if record.mfo and record.state == 'draft':
                done = True
            record.name_update = done

    def _get_destination_location(self):
        self.ensure_one()
        if self.check_sample == 'plan':
            location = self.env['stock.location'].search([('type', '=', 'plan')])
            if location:
                return location[0].id

        return self.picking_type_id.default_location_dest_id.id

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('confirm', 'confirmed'),
        ('leader_approved', 'Leaderteam Approved'),
        ('maneger_approved', 'Manager Approved'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Canselled'),
    ], default='draft', readonly=True)
    approver_id = fields.Many2one('res.users', string='Approver', readonly=True)
    approverrr_id = fields.Many2one('res.users', string='Final Approver', readonly=True)
    note = fields.Text("Note", )

    def button_confirmconfirm(self):
        for rec in self:
            rec.state = "confirm"
            rec.approver_id = self.env.user.id
        if self.env.context.get('active_model', False) == "purchase.requests":
            return {
                'name': 'New Quotation',
                'domain': [],
                'res_model': 'purchase.order',
                'res_id': self.id,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {
                    'active_model': "purchase.requests",
                },
                'target': 'new',
            }

    def button_leaderapprove(self):
        for rec in self:
            rec.state = "leader_approved"
        if self.env.context.get('active_model', False) == "purchase.requests":
            return {
                'name': 'New Quotation',
                'domain': [],
                'res_model': 'purchase.order',
                'res_id': self.id,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {
                    'active_model': "purchase.requests",
                },
                'target': 'new',
            }

    def button_manegerapprove(self):
        for rec in self:
            rec.state = "maneger_approved"
        if self.env.context.get('active_model', False) == "purchase.requests":
            return {
                'name': 'New Quotation',
                'domain': [],
                'res_model': 'purchase.order',
                'res_id': self.id,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {
                    'active_model': "purchase.requests",
                },
                'target': 'new',
            }

    def button_confirm(self):
        for order in self:
            order.state = "sent"
            if not order.mfo:
                order.name = self.env['ir.sequence'].next_by_code('purchase.order.name') or 'New'
            order.approverrr_id = self.env.user.id
        res = super(EditPurchaseOrder, self).button_confirm()
        return res

    @api.constrains('state')
    def _check_order_line_price(self):
        if self.state == "confirm" or self.state == "leader_approved" or self.state == "maneger_approved":
            if not self.supplier_offer:
                raise ValidationError(_('you MUST INSERT Supplier Offer'))
        if self.check_sample != 'sample':
            for rec in self:
                for line in rec.order_line:
                    if line.price_unit == 0:
                        raise ValidationError(_('PRICE UNIT MUST BE MORE THAN 0.'))

    receipt_reminder_email = fields.Boolean('Receipt Reminder Email', related=False,
                                            readonly=False)
    reminder_date_before_receipt = fields.Integer('Days Before Receipt',
                                                  related=False, readonly=False)

    @api.onchange('partner_id')
    @api.depends('partner_id')
    def partner_id_onchange(self):
        for record in self:
            if record.partner_id:
                record.receipt_reminder_email = record.partner_id.receipt_reminder_email
                record.reminder_date_before_receipt = record.partner_id.reminder_date_before_receipt


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    product_id = fields.Many2one('product.product', string='Product', change_default=True)

    @api.onchange('product_id')
    def onchange_value_product(self):
        if self.env.user.has_group('purchase_approve.group_mfo_user'):
            domain = {'product_id': [('purchase_ok', '=', True), '|', ('bom_ids.type', '=', 'subcontract'),
                                     ('man_for', '=', True), ]}
            return {'domain': domain}

    partner_id = fields.Many2one('res.partner', related=False, compute="partner_id_onchange", string='Partner')

    @api.onchange('order_id.partner_id', "product_id")
    def partner_id_onchange(self):
        for record in self:
            record.partner_id = record.order_id.partner_id
