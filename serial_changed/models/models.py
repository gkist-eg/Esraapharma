# -*- coding: utf-8 -*-
from odoo import models, fields, api
import re
from collections import defaultdict
from odoo.tools import float_is_zero


class Partner(models.Model):
    _inherit = 'res.partner'

    change_serial = fields.Boolean(string="Change")


class Move(models.Model):
    _inherit = 'account.move'
    name = fields.Char(string='Number', copy=False, readonly=False, store=True, index=True,
                       tracking=True, )

    @api.depends('name')
    def compute_serial(self):
        for record in self:
            if record.name:
                seq = record.name[2:]
                record.serial_name = seq
            else:
                record.serial_name = ''

    serial_name = fields.Char(string='Number', copy=False,  store=True, index=True,
                              tracking=True,compute='compute_serial')
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', readonly=True, store=True, states={'draft': [('readonly', False)]},
    )


    def action_post(self):
        for invoice in self:
            if self.move_type != 'entry':
                if invoice.partner_id.change_serial and invoice.move_type == 'out_invoice' and invoice.move_type != 'entry':
                    invoice.name = self.env['ir.sequence'].next_by_code('customer_invoice')
                if invoice.warehouse_id.sale_store and invoice.move_type == 'out_invoice' and invoice.move_type != 'entry':
                    invoice.name = self.env['ir.sequence'].next_by_code('customer_invoice_distributor')
                else:
                    if invoice.move_type == 'out_invoice' and not invoice.partner_id.change_serial:
                        invoice.name = self.env['ir.sequence'].next_by_code('draft_invoice')
                if invoice.move_type == 'out_refund' and invoice.move_type != 'entry':
                    invoice.name = self.env['ir.sequence'].next_by_code('refund_invoice')
                if invoice.move_type == 'in_refund' and invoice.move_type != 'entry':
                    invoice.name = self.env['ir.sequence'].next_by_code('refund_bill')

        return super().action_post()
