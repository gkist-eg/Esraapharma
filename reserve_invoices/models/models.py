# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from lib2to3.fixes.fix_input import context

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    serial_changed = fields.Boolean()

    @api.onchange('cust_categ_id')
    def serial(self):
        for record in self:
            if record.cust_categ_id:
                if record.cust_categ_id.name == 'distributor':
                    record.serial_changed = False
                else:
                    record.serial_changed = True


class ReserveInvoices(models.Model):
    _name = 'reserve.invoices'
    _description = 'Reserve Invoices'
    _rec_name = 'display_name'
    _order = 'customer'

    order_number = fields.Char('Order Number')
    old_order_number = fields.Char('Old Order Number')
    customer = fields.Many2one('res.partner')
    customer_name = fields.Char('res.partner', related='customer.name')
    inv_number = fields.Char('Invoice Number')
    old_inv_number = fields.Char('Old Invoice Number')
    date = fields.Datetime('Date', default=fields.Datetime.now)
    changing_date = fields.Datetime()
    employee = fields.Many2one('res.users')
    changed = fields.Boolean()
    display_name = fields.Char(compute='get_display_name')

    def get_display_name(self):
        for record in self:
            record.display_name = record.customer.name + '[' + record.order_number + ']' + '[' + record.inv_number + ']'


class ChangeInvoicesRequest(models.Model):
    _name = 'change.invoices.request'
    _description = 'Change Invoices Requests'

    order_ids = fields.Many2many('sale.order', 'sale_order_reserve_rel', 'reserve_id', 'order_id', string="Reserves",
                                 copy=False, readonly=True)
    order_number = fields.Char()
    orders = fields.Many2one('sale.order', required=True, readonly=True)
    partner = fields.Many2one('res.partner', required=True)
    reserves = fields.Many2one('reserve.invoices', required=True)

    @api.model
    def default_get(self, fields):
        rec = super(ChangeInvoicesRequest, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        if not active_model or not active_ids:
            raise UserError(
                _("Programmation error: wizard action executed without active_model or active_ids in context."))
        if active_model != 'sale.order':
            raise UserError(_(
                "Programmation error: the expected model for this action is 'account.invoice'. The provided one is '%d'.") % active_model)

        invoices = self.env[active_model].browse(active_ids)
        order_num = ' '.join([ref for ref in invoices.mapped('name') if ref])
        rec.update({
            'order_number': order_num,
            'orders': invoices.id,
            'partner': invoices.partner_id.id,
        })
        return rec

    def change(self):
        for record in self:
            if record.reserves:
                old_num = ''
                record.reserves.old_order_number = record.orders.name
                for s_order in self.env['sale.order'].search([('id', '=', record.orders.id)]):

                    old_num += s_order.name
                    s_order.write({'date_order': record.reserves.date,
                                   'name': record.reserves.order_number,
                                   })
                    if record.orders.invoice_status == 'invoiced':
                        s_order.update({'serial_changed': True})

                # if record.orders.invoice_status == 'invoiced':
                invoices = self.env['account.move'].search([('invoice_origin', '=', record.reserves.old_order_number)])
                if invoices:
                    for invoice in invoices:
                        if invoice:
                            if invoice.state == 'posted':
                                record.reserves.old_inv_number = invoice.name
                                invoice.write({
                                    'date': record.reserves.date,
                                    'name': record.reserves.inv_number,
                                    'invoice_origin': record.reserves.order_number})
                            else:
                                raise UserError(_(
                                    "Must Validate Invoice"))
                        if invoice.line_ids:
                            move_line = self.env['account.move.line'].search(
                                [('name', '=', record.reserves.old_order_number)])

                            if move_line:
                                record.reserves.old_inv_number = invoice.name
                                invoice.write({
                                    'date': record.reserves.date,
                                    'name': record.reserves.inv_number,
                                })

                else:
                    raise UserError(_(
                        "Must Create Invoice"))
                record.reserves.changed = True
                record.reserves.changing_date = datetime.today()


class ReserveInvoicesRequest(models.Model):
    _name = 'reserve.invoices.request'
    _description = 'Reserve Invoices Requests'

    reserve_change = fields.Selection([('reserve', 'Reserve')], string='Type')
    n = fields.Char()
    c = fields.Char()
    customer = fields.Many2many('res.partner', string='Order Customer', domain="[('change_serial','=',False)]")
    date_reserve = fields.Datetime('Reserving Date', default=fields.Datetime.now)

    reserves_line_ids = fields.One2many('reserve.invoices.request.line', 'reserve_line')

    @api.onchange('reserve_change')
    def onchange_reserve_change(self):
        for record in self:
            if record.reserve_change == 'change':
                record.order_number = False
                record.inv_number = False
                record.order_customer = False
                record.inv_customer = False

    def request(self):
        for record in self:
            if record.reserve_change == "reserve":
                if record.customer:
                    for cust in record.customer:
                        order_num = ''
                        inv_num = ''
                        for seq in self:
                            order_num += self.env['ir.sequence'].next_by_code('sale.order.quot')
                        for seq in self:
                            inv_num += self.env['ir.sequence'].next_by_code('customer_invoice')

                        self.env['reserve.invoices'].create({
                            'order_number': order_num,
                            'inv_number': inv_num,
                            'customer': cust.id,
                            'date': record.date_reserve
                        })
                else:
                    for line in record.reserves_line_ids:
                        for i in range(1, line.reserve_num + 1):
                            order_num = ''
                            inv_num = ''
                            for seq in self:
                                order_num += self.env['ir.sequence'].next_by_code('sale.order.quot')
                            for seq in self:
                                inv_num += self.env['ir.sequence'].next_by_code('customer_invoice')

                            self.env['reserve.invoices'].create({
                                'order_number': order_num,
                                'inv_number': inv_num,
                                'customer': line.customer.id,
                                'date': record.date_reserve
                            })

    @api.onchange('reserve_change')
    def get_products(self):
        lines = []
        if self.reserve_change == 'reserve':
            customers = self.env['res.partner'].search(
                [('categ_id.name', '=', 'distributor')])
            for customer in customers:
                lines.append((0, 0, {
                    'customer': customer.id,
                }))
            self.reserves_line_ids = lines


class ReserveInvoicesRequestLine(models.Model):
    _name = 'reserve.invoices.request.line'
    _description = 'Reserve Invoices Requests'

    reserve_line = fields.Many2one('reserve.invoices.request')
    customer = fields.Many2one('res.partner', string='Order Customer', required=True)
    reserve_num = fields.Integer()
