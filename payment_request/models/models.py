from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PaymentRequest(models.Model):
    _name = 'payment.request'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('Name')
    origin = fields.Char('Name', related='order_id.name', store=True, tracking=True)
    partner_id = fields.Many2one('res.partner', 'Vendor', store=True,
                                 tracking=True)
    currency_id = fields.Many2one('res.currency', 'Currency', store=True,
                                  tracking=True)
    order_id = fields.Many2one('purchase.order', 'Order',
                               domain="[('state', '=','done'),('invoice_status', 'in',('to invoice','invoiced'))]",
                               required='1', store=True, tracking=True)
    picking_ids = fields.Many2many('stock.picking', string='Receptions',
                                   required='1', store=True,
                                   copy=False,
                                   tracking=True)

    line_ids = fields.One2many('payment.request.line', 'request_id', store=True, tracking=True,
                               copy=False)
    bill_ids = fields.Many2many('account.move', compute='_compute_accounting')
    coach_id = fields.Many2one('res.users')
    manager_id = fields.Many2one('res.users')
    accountant_id = fields.Many2one('res.users')
    accountant_m_id = fields.Many2one('res.users')
    bill_numbers = fields.Integer('Bill', compute='_compute_accounting')
    order_date = fields.Datetime('Order Date', related='order_id.date_order', store=True, tracking=True,
                                 copy=False)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'),
                              ('pending', 'Pending'), ('validated', 'Validated'),
                              ('done', 'Done')], 'Status', store=True, default='draft', tracking=True,
                             copy=False)
    untaxed_amount = fields.Float('Untaxed Amount', copy=False)
    taxed_amount = fields.Float('Taxed Amount', copy=False)
    total_amount = fields.Float('Total Amount', copy=False)
    create_date = fields.Datetime('Request Date')
    allowance_discount = fields.Selection([('amount', 'Amount'),
                                           ('percentage', 'Percentage')],
                                          string='Allowance Discount',
                                          tracking=True)
    discount_rate = fields.Float('Discount', tracking=True, store=True)
    discount = fields.Float('Discount', tracking=True, store=True)

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('you can delete only draft request '))
            return super(PaymentRequest, self).unlink()

    @api.constrains('picking_ids')
    def change_inspections(self):
        if not self.currency_id:
            self.currency_id = self.order_id.currency_id
        if not self.partner_id:
            self.partner_id = self.order_id.partner_id
        self.line_ids = False
        for line in self.picking_ids:
            for move in line.move_line_ids:
                done = 0
                if move.lot_id:
                    excet = self.line_ids.search(
                        [('product_id', '=', move.product_id.id), ('picking_id', '=', move.picking_id.id), ('request_id', '!=', self.id), ('request_id', '!=', False), ])
                    if not excet:
                        lines = line.move_line_ids.search(
                            [('lot_id', '=', move.lot_id.id), ('location_dest_id.stock_usage', '=', 'release'),
                             ('location_id.stock_usage', '=', 'qrtin'), ('state', '=', 'done')])
                        if not lines:
                            lines = line.move_line_ids.search(
                                [('lot_id', '=', move.lot_id.id), ('location_dest_id.stock_usage', '=', 'release'),
                                 ('state', '=', 'done')])
                        done = sum(
                            [quant.product_uom_id._compute_quantity(quant.qty_done, quant.product_id.uom_id) for quant
                             in
                             lines])
                        request = line.move_line_ids.search(
                            [('lot_id', '=', move.lot_id.id),
                             ('location_dest_id', '=', self.env.ref("item_request.emploee_location").id),
                             ('location_id.stock_usage', '=', 'qrtin'), ('state', '=', 'done')])
                        done += sum(
                            [quant.product_uom_id._compute_quantity(quant.qty_done, quant.product_id.uom_id) for quant
                             in
                             request])
                        request_return = line.move_line_ids.search(
                            [('lot_id', '=', move.lot_id.id),
                             ('location_id', '=', self.env.ref("item_request.emploee_location").id),
                             ('location_dest_id.stock_usage', '=', 'qrtin'), ('state', '=', 'done')])
                        done -= sum(
                            [quant.product_uom_id._compute_quantity(quant.qty_done, quant.product_id.uom_id) for quant
                             in
                             request_return])
                        if lines:
                            price = move.move_id.purchase_line_id.price_unit
                            taxes = move.move_id.purchase_line_id.taxes_id.compute_all(price, self.currency_id, done,
                                                                                       product=move.product_id,
                                                                                       partner=self.partner_id)

                            line1 = self.line_ids.create({
                                'product_id': move.product_id.id,
                                'request_id': self.id,
                                'uom_id': move.product_uom_id.id,
                                'lot_id': move.lot_id.id,
                                'qty': done,
                                'price_unit': price,
                                'picking_id': line.id,
                                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                                'price_total': taxes['total_included'],
                                'taxes_id': [(6, 0, move.move_id.purchase_line_id.taxes_id.ids)],
                                'total': taxes['total_excluded']

                            })
                            self.line_ids += line1
                else:
                    excet = self.line_ids.search(
                        [('product_id', '=', move.product_id.id), ('picking_id', '=', move.picking_id.id),
                         ('request_id', '!=', self.id), ('request_id', '!=', False), ])
                    if not excet:
                        price = move.move_id.purchase_line_id.price_unit
                        taxes = move.move_id.purchase_line_id.taxes_id.compute_all(price, self.currency_id, move.qty_done,
                                                                                   product=move.product_id,
                                                                                   partner=self.partner_id)
                        line1 = self.line_ids.create({
                            'product_id': move.product_id.id,
                            'request_id': self.id,
                            'uom_id': move.product_uom_id.id,
                            'qty': move.qty_done,
                            'price_unit': price,
                            'picking_id': move.picking_id.id,
                            'price_tax': taxes['total_included'] - taxes['total_excluded'],
                            'price_total': taxes['total_included'],
                            'taxes_id': [(6, 0, move.move_id.purchase_line_id.taxes_id.ids)],
                            'total': taxes['total_excluded']

                        })
                        self.line_ids += line1

    @api.constrains('line_ids')
    def change_inspections_line_ids(self):
        self.taxed_amount = 0
        self.untaxed_amount = 0
        self.total_amount = 0
        for line in self.line_ids:
            self.taxed_amount += line.price_tax
            self.untaxed_amount += line.total
            self.total_amount += line.price_total

    def action_view_picking(self):
        action = self.env.ref('account.action_invoice_tree2')
        result = action.read()[0]

        # override the context to get rid of the default filtering on picking type
        result.pop('id', None)
        result['context'] = {}
        bills = sum([order.bill_ids.ids for order in self], [])
        # choose the view_mode accordingly
        if len(bills) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, bills)) + "])]"
        elif len(bills) == 1:
            res = self.env.ref('account.invoice_supplier_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = bills and bills[0] or False
        return result

    @api.onchange('order_id')
    def _onchange_order_id(self):

        if self.order_id and not self.picking_ids:
            don_pickings = []
            pickings = []

            result = self.env['stock.picking'].search(
                [('origin', '=', self.order_id.name), ('state', '=', 'done'),
                 ('picking_type_id.code', '=', 'incoming')])
            for res in result:
                for move in res.move_line_ids:
                    if res.id not in don_pickings:
                        lines = res.move_line_ids.search(
                            [('lot_id', '=', move.lot_id.id), ('location_dest_id.stock_usage', '=', 'release'),
                             ('location_id.stock_usage', '=', 'qrtin'), ('state', '=', 'done')])
                        if lines:
                            pickings.append(res.id)
                        if not move.lot_id:
                            pickings.append(res.id)
                if not pickings:
                    for move in res.move_line_ids:
                        if res.id not in don_pickings:
                            lines = res.move_line_ids.search(
                                [('lot_id', '=', move.lot_id.id), ('location_dest_id.stock_usage', '=', 'release'),
                                 ('state', '=', 'done')])
                            if lines:
                                pickings.append(res.id)
                            if not move.lot_id:
                                pickings.append(res.id)
            domain = {'picking_ids': [('id', 'in', pickings)]}
            return {'domain': domain}

    def _compute_accounting(self):
        for order in self:
            if self.order_id and not self.line_ids:
                bills = self.env['account.move'].search([
                    ('invoice_origin', '=', self.order_id.name), ('state', '!=', 'cancel')
                ])
                order.bill_ids = bills
                order.bill_numbers = len(bills)
            else:
                bill = self.env['account.move']
                for line in self.line_ids:
                    bills = self.env['account.move.line'].search([
                        ('move_id.invoice_origin', '=', self.order_id.name), ('product_id', '=', line.product_id.id)
                    ])
                    for b in bills:
                        if b.move_id not in order.bill_ids:
                            order.bill_ids += b.move_id
                order.bill_numbers = len(order.bill_ids)

    def button_confirmed(self):
        if not self.line_ids:
            raise UserError(_('Can not Confirm Request Without Items'))
        recive = self.env['res.users'].search(
            [("groups_id", "=", self.env.ref('account.group_account_manager').id)])
        self.env['mail.message'].send("Message subject", 'Payment Request Need to be approved', self._name, self.id,
                                      self.name, recive)
        self.manager_id = self.env.user
        self.write({'state': 'pending'})

    def button_confirm(self):
        if not self.line_ids:
            raise UserError(_('Can not Confirm Request Without Items'))
        recive = self.env['res.users'].search(
            [("groups_id", "=", self.env.ref('purchase.group_purchase_manager').id)])
        self.env['mail.message'].send("Message subject", 'Payment Request Need to be confirmed', self._name, self.id,
                                      self.name, recive)
        self.coach_id = self.env.user
        self.write({'state': 'confirmed'})

    def button_valdite(self):
        self.env['mail.message'].send("Message subject", 'Payment Request Validated', self._name, self.id,
                                      self.name, self.create_uid)
        self.accountant_id = self.env.user

        self.write({'state': 'validated'})

    def button_done(self):
        self.accountant_m_id = self.env.user
        self.write({'state': 'done'})

    @api.model
    def create(self, vals):
        name = self.env['ir.sequence'].next_by_code('payment.request')
        vals['name'] = name
        res = super(PaymentRequest, self).create(vals)
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
        if employee and employee.coach_id.user_id:
            self.env['mail.message'].send("Message subject", 'Payment Request Need to be approved', res._name, res.id,
                                          res.name, employee.coach_id.user_id)
        return res


class PaymentRequestLine(models.Model):
    _name = 'payment.request.line'
    product_id = fields.Many2one('product.product', 'Item', store=True)
    request_id = fields.Many2one('payment.request', ondelete='cascade', store=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot', store=True)
    picking_id = fields.Many2one('stock.picking', 'Picking', store=True)
    uom_id = fields.Many2one('uom.uom', 'UOM', store=True)
    qty = fields.Float('Released Quantity', digits=(12, 5), store=True)
    price_unit = fields.Float('Unit Price', digits=(12, 4), store=True)
    price_tax = fields.Float('Unit Price', digits=(12, 4), store=True)
    price_total = fields.Float('Unit Price', digits=(12, 4), store=True)
    total = fields.Float('SubTotal', digits=(12, 4), store=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes',
                                domain=['|', ('active', '=', False), ('active', '=', True)], store=True)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_payment_request(self):
        self.ensure_one()
        return {
            'name': _('Payment Request'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'payment.request',
            'view_id': self.env.ref('payment_request.payment_request_form').id,
            'type': 'ir.actions.act_window',
            'context': {'default_order_id': self.id,
                        'default_currency_id': self.currency_id.id,
                        'default_partner_id': self.partner_id.id,
                        },
            'target': 'new',
        }

    def action_view_request(self):
        action = self.env.ref('payment_request.payment_request_action_form')
        result = action.read()[0]

        # override the context to get rid of the default filtering on picking type
        result.pop('id', None)
        result['context'] = {}
        bills = sum([order.request_ids.ids for order in self], [])
        # choose the view_mode accordingly
        if len(bills) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, bills)) + "])]"
        elif len(bills) == 1:
            res = self.env.ref('payment_request.payment_request_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = bills and bills[0] or False
        return result

    def _compute_accounting(self):
        for order in self:
            requests = self.env['payment.request'].search([
                ('order_id', '=', self.id)
            ])
            order.request_ids = requests
            order.request_cont = len(requests)

    request_ids = fields.Many2many('payment.request', compute='_compute_accounting')
    request_cont = fields.Integer('Payment Request', compute='_compute_accounting')
