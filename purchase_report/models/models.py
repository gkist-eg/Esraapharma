from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from itertools import groupby
from operator import itemgetter
from collections import defaultdict
import time
import datetime
from dateutil.relativedelta import relativedelta


class PRFollowup(models.TransientModel):
    _name = 'pr.followup'
    _description = 'PR Follow Up'

    choose_from = fields.Selection([('all', 'All'), ('other', 'Other')], default='all', string='Choose From',
                                   store=True)
    department = fields.Many2one('hr.department', string='Department', store=True)
    product = fields.Many2one('product.product', string='Product', store=True, domain="[('purchase_ok','=',True)]")
    choose = fields.Selection([('department', 'Department'), ('product', 'Product')], string='Choose', store=True)
    date_from = fields.Date(string="From Date", default=time.strftime('%Y-%m-01'), store=True)
    date_to = fields.Date("To Date", store=True, default=datetime.datetime.now())
    company = fields.Many2one('res.company', 'Company', required=True, index=True,
                              default=lambda self: self.env.user.company_id.id)
    line_ids = fields.One2many('pr.followup.line', 'wizard_id', required=True, ondelete='cascade', store=True)

    def print_pdf_pr_followup(self):
        line_ids = []

        # Unlink All one2many Line Ids from same wizard
        for wizard_id in self.env['pr.followup.line'].search([('wizard_id', '=', self.id)]):
            if wizard_id.wizard_id.id == self.id:
                self.write({'line_ids': [(3, wizard_id.id)]})

                # Creating Temp dictionary for Product List
        for wizard in self:
            if wizard.department:
                request = self.env['purchase.request.line'].search(
                    [('request_line_id.start_date', '>=', wizard.date_from),
                     ('request_line_id.start_date', '<=', wizard.date_to),
                     ('request_line_id.departmnt_id', '=', self.department.id),
                     ('state', 'in', ('fully_quotationed', 'request_approved'))])
                request2 = self.env['purchase.request.line'].search(
                    [('request_line_id.start_date', '>=', wizard.date_from),
                     ('request_line_id.start_date', '<=', wizard.date_to),
                     ('request_line_id.departmnt_id', '=', self.department.id),
                     ('request_line_id.state', '!=', 'request_approved')])

                for resource in request:
                    for rec in self.env['purchase.order.line'].search(
                            [('order_id.purchase_requests', '=', resource.request_line_id.id),
                             ('product_id', '=', resource.product_id.id)]):
                        for move in rec.move_ids:
                            l = None
                            s = None
                            if move.state == 'done':
                                l = move.date
                                s = move.product_uom_qty

                            if move.backorder_id:
                                for i in move.backorder_id.move_lines:
                                    line_ids.append((0, 0, {
                                        'pr_no': resource.request_line_id.name,
                                        'pr_date': resource.request_line_id.start_date,
                                        'state': resource.request_line_id.state,
                                        'product_code': resource.product_id.default_code,
                                        'product_id': resource.product_id.id,
                                        'requested_qty': resource.product_qty,
                                        'qty_received': s,
                                        'received_date': l,
                                        'backorder_id': move.backorder_id.id,
                                        'product_uom_qty': i.product_uom_qty,
                                        'po': rec.name

                                    }))
                            else:
                                line_ids.append((0, 0, {
                                    'pr_no': resource.request_line_id.name,
                                    'pr_date': resource.request_line_id.start_date,
                                    'state': resource.request_line_id.state,
                                    'product_code': resource.product_id.default_code,
                                    'product_id': resource.product_id.id,
                                    'requested_qty': resource.product_qty,
                                    'qty_received': s,
                                    'received_date': l,
                                    'po': rec.order_id.name

                                }))

                for r in request:
                    for order in self.env['purchase.order.line'].search(
                            [('order_id.purchase_requests', '=', r.request_line_id.id),
                             ('product_id', '=', r.product_id.id),
                             ('state', 'not in', ('purchase', 'done'))]):
                        line_ids.append((0, 0, {
                            'pr_no': r.request_line_id.name,
                            'pr_date': r.request_line_id.start_date,
                            'state': r.request_line_id.state,
                            'product_code': r.product_id.default_code,
                            'product_id': r.product_id.id,
                            'requested_qty': r.product_qty,
                            'po': order.order_id.name

                        }))
                for res in request2:
                    not_po = self.env['purchase.order.line'].search(
                        [('order_id.purchase_requests', '=', res.request_line_id.id),
                         ('product_id', '=', res.product_id.id), ])
                    if not not_po:
                        line_ids.append((0, 0, {
                            'pr_no': res.request_line_id.name,
                            'pr_date': res.request_line_id.start_date,
                            'state': res.request_line_id.state,
                            'product_code': res.product_id.default_code,
                            'product_id': res.product_id.id,
                            'requested_qty': res.product_qty,

                        }))

            if wizard.product:

                request = self.env['purchase.request.line'].search(
                    [('request_line_id.start_date', '>=', wizard.date_from),
                     ('request_line_id.start_date', '<=', wizard.date_to), ('product_id', '=', self.product.id),
                     ('request_line_id.state', 'in', ('fully_quotationed', 'request_approved'))])
                request2 = self.env['purchase.request.line'].search(
                    [('request_line_id.start_date', '>=', wizard.date_from),
                     ('request_line_id.start_date', '<=', wizard.date_to), ('product_id', '=', self.product.id),
                     ('request_line_id.state', '!=', 'request_approved')
                     ])
                for resource in request:
                    for rec in self.env['purchase.order.line'].search(
                            [('order_id.purchase_requests', '=', resource.request_line_id.id),
                             ('product_id', '=', resource.product_id.id)]):
                        for move in rec.move_ids:
                            l = None
                            s = None
                            if move.state == 'done':
                                l = move.date
                                s = move.product_uom_qty
                            if move.backorder_id:
                                for i in move.backorder_id.move_lines:
                                    line_ids.append((0, 0, {
                                        'pr_no': resource.request_line_id.name,
                                        'pr_date': resource.request_line_id.start_date,
                                        'state': resource.request_line_id.state,
                                        'requesting_department': resource.request_line_id.departmnt_id.id,
                                        'requested_qty': resource.product_qty,
                                        'qty_received': s,
                                        'received_date': l,
                                        'backorder_id': move.backorder_id.id,
                                        'product_uom_qty': i.product_uom_qty,
                                        'po': rec.order_id.name

                                    }))
                            else:
                                line_ids.append((0, 0, {
                                    'pr_no': resource.request_line_id.name,
                                    'pr_date': resource.request_line_id.start_date,
                                    'state': resource.request_line_id.state,
                                    'requesting_department': resource.request_line_id.departmnt_id.id,
                                    'requested_qty': resource.product_qty,
                                    'qty_received': s,
                                    'received_date': l,
                                    'po': rec.order_id.name

                                }))
                for r in request:
                    orders = self.env['purchase.order.line'].search(
                        [('order_id.purchase_requests', '=', r.request_line_id.id),
                         ('product_id', '=', r.product_id.id),
                         ('state', 'not in', ('purchase', 'done'))])
                    for order in orders:
                        line_ids.append((0, 0, {
                            'pr_no': r.request_line_id.name,
                            'pr_date': r.request_line_id.start_date,
                            'state': r.request_line_id.state,
                            'requesting_department': r.request_line_id.departmnt_id.id,
                            'requested_qty': r.product_qty,
                            'po': order.order_id.name

                        }))
                    if not orders:
                        line_ids.append((0, 0, {
                            'pr_no': r.request_line_id.name,
                            'pr_date': r.request_line_id.start_date,
                            'state': r.request_line_id.state,
                            'requesting_department': r.request_line_id.departmnt_id.id,
                            'requested_qty': r.product_qty,

                        }))
                for res in request2:
                    not_po = self.env['purchase.order.line'].search(
                        [('order_id.purchase_requests', '=', res.request_line_id.id),
                         ('product_id', '=', res.product_id.id), ])
                    if not not_po:
                        line_ids.append((0, 0, {
                            'pr_no': res.request_line_id.name,
                            'pr_date': res.request_line_id.start_date,
                            'state': res.request_line_id.state,
                            'requesting_department': res.request_line_id.departmnt_id.id,
                            'requested_qty': res.product_qty,

                        }))

            if wizard.choose_from == 'all':

                request = self.env['purchase.request.line'].search(
                    [('request_line_id.start_date', '>=', wizard.date_from),
                     ('request_line_id.start_date', '<=', wizard.date_to),
                     ('request_line_id.state', 'in', ('fully_quotationed', 'request_approved'))])
                request2 = self.env['purchase.request.line'].search(
                    [('request_line_id.start_date', '>=', wizard.date_from),
                     ('request_line_id.start_date', '<=', wizard.date_to),
                     ('request_line_id.state', '!=', 'request_approved')])

                for resource in request:
                    for rec in self.env['purchase.order.line'].search(
                            [('order_id.purchase_requests', '=', resource.request_line_id.id),
                             ('product_id', '=', resource.product_id.id)]):
                        for move in rec.move_ids:
                            l = None
                            s = None
                            if move.state == 'done':
                                l = move.date
                                s = move.product_uom_qty
                            if move.backorder_id:
                                for i in move.backorder_id.move_lines:
                                    line_ids.append((0, 0, {
                                        'pr_no': resource.request_line_id.name,
                                        'pr_date': resource.request_line_id.start_date,
                                        'state': resource.request_line_id.state,
                                        'requesting_department': resource.request_line_id.departmnt_id.id,
                                        'product_code': resource.product_id.default_code,
                                        'product_id': resource.product_id.id,
                                        'requested_qty': resource.product_qty,
                                        'qty_received': s,
                                        'received_date': l,
                                        'backorder_id': move.backorder_id.id,
                                        'product_uom_qty': i.product_uom_qty,
                                        'po': rec.order_id.name

                                    }))
                            else:
                                line_ids.append((0, 0, {
                                    'pr_no': resource.request_line_id.name,
                                    'pr_date': resource.request_line_id.start_date,
                                    'state': resource.request_line_id.state,
                                    'requesting_department': resource.request_line_id.departmnt_id.id,
                                    'product_code': resource.product_id.default_code,
                                    'product_id': resource.product_id.id,
                                    'requested_qty': resource.product_qty,
                                    'qty_received': s,
                                    'received_date': l,
                                    'po': rec.order_id.name

                                }))

                for r in request:
                    for order in self.env['purchase.order.line'].search(
                            [('order_id.purchase_requests', '=', r.request_line_id.id),
                             ('product_id', '=', r.product_id.id),
                             ('state', 'not in', ('purchase', 'done'))]):
                        line_ids.append((0, 0, {
                            'pr_no': r.request_line_id.name,
                            'pr_date': r.request_line_id.start_date,
                            'state': r.request_line_id.state,
                            'requesting_department': r.request_line_id.departmnt_id.id,
                            'product_code': r.product_id.default_code,
                            'product_id': r.product_id.id,
                            'requested_qty': r.product_qty,
                            'po': order.order_id.name

                        }))
                for res in request2:
                    not_po = self.env['purchase.order.line'].search(
                        [('order_id.purchase_requests', '=', res.request_line_id.id),
                         ('product_id', '=', res.product_id.id), ])
                    if not not_po:
                        line_ids.append((0, 0, {
                            'pr_no': res.request_line_id.name,
                            'pr_date': res.request_line_id.start_date,
                            'state': res.request_line_id.state,
                            'requesting_department': res.request_line_id.departmnt_id.id,
                            'product_code': res.product_id.default_code,
                            'product_id': res.product_id.id,
                            'requested_qty': res.product_qty,

                        }))

        # writing to One2many line_ids
        self.write({'line_ids': line_ids})
        context = {
            'lang': 'en_US',
            'active_ids': [self.id],
        }
        return {
            'context': context,
            'data': None,
            'type': 'ir.actions.report',
            'report_name': 'purchase_report.pr_followup_report',
            'report_type': 'qweb-html',
            'report_file': 'purchase_report.pr_followup_report',
            'name': 'PR Follow Up Report',
            'flags': {'action_buttons': True},
        }


class PRFollowUpLine(models.TransientModel):
    _name = 'pr.followup.line'

    wizard_id = fields.Many2one('pr.followup', required=True, ondelete='cascade')
    pr_no = fields.Char('Date', store=True)
    pr_date = fields.Date('Date', store=True)
    product_id = fields.Many2one('product.product', 'Product', store=True)
    product_code = fields.Char('Product Code', store=True)
    requested_qty = fields.Float('Qty', store=True)
    qty_received = fields.Float('Qty', store=True)
    requesting_department = fields.Many2one('hr.department', 'Department', store=True)
    received_date = fields.Date('Received Date', store=True)
    backorder_id = fields.Many2one('stock.picking', 'Back Order of', store=True)
    product_uom_qty = fields.Float('Back Order Qty', store=True)
    po = fields.Char('PO', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'To Be Approved'),
        ('leader_approved', 'Leader Approved'),
        ('maneger_approved', 'Manager Approved'),
        ('request_approved', 'Request Approved'),
        ('fully_quotationed', 'Fully Quotationed'),
    ], )


class POFollowup(models.TransientModel):
    _name = 'po.followup'
    _description = 'PO Follow Up'

    choose_from = fields.Selection([('all', 'All'), ('other', 'Other')], default='all', string='Choose From',
                                   store=True)
    vendor = fields.Many2one('res.partner', string='Partner', store=True)
    product = fields.Many2one('product.product', string='Product', store=True, domain="[('purchase_ok','=',True)]")
    purchase = fields.Many2one('purchase.order', string='PO', store=True, )
    choose = fields.Selection([('vendor', 'Vendor'), ('product', 'Product'), ('po', 'PO')], string='Choose', store=True)
    date_from = fields.Date(string="From Date", default=time.strftime('%Y-%m-01'), store=True)
    date_to = fields.Date("To Date", store=True, default=datetime.datetime.now())
    company = fields.Many2one('res.company', 'Company', required=True, index=True,
                              default=lambda self: self.env.user.company_id.id)
    line_ids = fields.One2many('po.followup.line', 'wizard_id', required=True, ondelete='cascade', store=True)

    def print_pdf_po_followup(self):
        line_ids = []

        # Unlink All one2many Line Ids from same wizard
        for wizard_id in self.env['po.followup.line'].search([('wizard_id', '=', self.id)]):
            if wizard_id.wizard_id.id == self.id:
                self.write({'line_ids': [(3, wizard_id.id)]})

                # Creating Temp dictionary for Product List
        for wizard in self:
            if wizard.vendor:
                request = self.env['purchase.order.line'].search(
                    [('order_id.date_order', '>=', wizard.date_from),
                     ('order_id.date_order', '<=', wizard.date_to),
                     ('order_id.partner_id', '=', self.vendor.id),
                     ])
                for resource in request:
                    for move in resource.move_ids:
                        l = None
                        s = None
                        if move.state == 'done':
                            l = move.date
                            s = move.product_uom_qty

                        if move.backorder_id:
                            for i in move.backorder_id.move_lines:
                                line_ids.append((0, 0, {
                                    'pr_no': resource.order_id.name,
                                    'pr_date': resource.order_id.date_order,
                                    'state': resource.order_id.state,
                                    'product_code': resource.product_id.default_code,
                                    'product_id': resource.product_id.id,
                                    'requested_qty': resource.product_qty,
                                    'qty_received': s,
                                    'received_date': l,
                                    'backorder_id': move.backorder_id.id,
                                    'product_uom_qty': i.product_uom_qty,

                                }))
                        else:
                            line_ids.append((0, 0, {
                                'pr_no': resource.order_id.name,
                                'pr_date': resource.order_id.start_date,
                                'state': resource.order_id.state,
                                'product_code': resource.product_id.default_code,
                                'product_id': resource.product_id.id,
                                'requested_qty': resource.product_qty,
                                'qty_received': s,
                                'received_date': l,

                            }))

            if wizard.product:
                request = self.env['purchase.order.line'].search(
                    [('order_id.date_order', '>=', wizard.date_from),
                     ('order_id.date_order', '<=', wizard.date_to),
                     ('product_id', '=', self.product_id.id),
                     ])
                for rec in request:
                        for move in rec.move_ids:
                            l = None
                            s = None
                            if move.state == 'done':
                                l = move.date
                                s = move.product_uom_qty
                            if move.backorder_id:
                                for i in move.backorder_id.move_lines:
                                    line_ids.append((0, 0, {
                                        'pr_no': rec.order_id.name,
                                        'pr_date': rec.order_id.start_date,
                                        'state': rec.order_id.state,
                                        'requesting_department': rec.order_id.departmnt_id.id,
                                        'requested_qty': rec.product_qty,
                                        'qty_received': s,
                                        'received_date': l,
                                        'backorder_id': move.backorder_id.id,
                                        'product_uom_qty': i.product_uom_qty,
                                        'po': rec.order_id.name

                                    }))
                            else:
                                line_ids.append((0, 0, {
                                    'pr_no': rec.order_id.name,
                                    'pr_date': rec.order_id.start_date,
                                    'state': rec.order_id.state,
                                    'requested_qty': rec.product_qty,
                                    'qty_received': s,
                                    'received_date': l,
                                    'po': rec.order_id.name

                                }))

            if wizard.choose_from == 'all':

                request = self.env['purchase.order.line'].search(
                    [('order_id.date_order', '>=', wizard.date_from),
                     ('order_id.date_order', '<=', wizard.date_to),

                     ])
                for resource in request:
                        for move in resource.move_ids:
                            l = None
                            s = None
                            if move.state == 'done':
                                l = move.date
                                s = move.product_uom_qty
                            if move.backorder_id:
                                for i in move.backorder_id.move_lines:
                                    line_ids.append((0, 0, {
                                        'pr_no': resource.order_id.name,
                                        'pr_date': resource.order_id.start_date,
                                        'state': resource.order_id.state,
                                        'requesting_department': resource.order_id.departmnt_id.id,
                                        'product_code': resource.product_id.default_code,
                                        'product_id': resource.product_id.id,
                                        'requested_qty': resource.product_qty,
                                        'qty_received': s,
                                        'received_date': l,
                                        'backorder_id': move.backorder_id.id,
                                        'product_uom_qty': i.product_uom_qty,

                                    }))
                            else:
                                line_ids.append((0, 0, {
                                    'pr_no': resource.order_id.name,
                                    'pr_date': resource.order_id.start_date,
                                    'state': resource.order_id.state,
                                    'requesting_department': resource.order_id.departmnt_id.id,
                                    'product_code': resource.product_id.default_code,
                                    'product_id': resource.product_id.id,
                                    'requested_qty': resource.product_qty,
                                    'qty_received': s,
                                    'received_date': l,

                                }))



        # writing to One2many line_ids
        self.write({'line_ids': line_ids})
        context = {
            'lang': 'en_US',
            'active_ids': [self.id],
        }
        return {
            'context': context,
            'data': None,
            'type': 'ir.actions.report',
            'report_name': 'purchase_report.po_followup_report',
            'report_type': 'qweb-html',
            'report_file': 'purchase_report.po_followup_report',
            'name': 'PO Follow Up Report',
            'flags': {'action_buttons': True},
        }


class POFollowUpLine(models.TransientModel):
    _name = 'po.followup.line'

    wizard_id = fields.Many2one('po.followup', required=True, ondelete='cascade')
    pr_no = fields.Char('Date', store=True)
    pr_date = fields.Date('Date', store=True)
    product_id = fields.Many2one('product.product', 'Product', store=True)
    product_code = fields.Char('Product Code', store=True)
    requested_qty = fields.Float('Qty', store=True)
    qty_received = fields.Float('Qty', store=True)
    received_date = fields.Date('Received Date', store=True)
    backorder_id = fields.Many2one('stock.picking', 'Back Order of', store=True)
    product_uom_qty = fields.Float('Back Order Qty', store=True)
    po = fields.Char('PO', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'To Be Approved'),
        ('leader_approved', 'Leader Approved'),
        ('maneger_approved', 'Manager Approved'),
        ('request_approved', 'Request Approved'),
        ('fully_quotationed', 'Fully Quotationed'),
    ], )
