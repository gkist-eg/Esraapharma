# -*- coding: utf-8 -*-
# from duplicity.errors import UserError
from odoo import models, fields, api, _
import math
from collections import defaultdict

from odoo.exceptions import UserError

INTEGRITY_HASH_MOVE_FIELDS = ('date', 'journal_id', 'company_id')
INTEGRITY_HASH_LINE_FIELDS = ('debit', 'credit', 'account_id', 'partner_id')


def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier + 0.5) / multiplier


class PriceList(models.Model):
    _name = 'product.pricelist'
    _inherit = 'product.pricelist'

    pharmacy_account = fields.Many2one(comodel_name="account.account", string="Pharmacy Account", )


class PartnerCategory(models.Model):
    _name = 'category.customer'
    _description = 'category customer'
    category_type = fields.Selection([
        ('store', 'Stores'), ('manufacture_for_others', 'Manufacturing for others'),
        ('pharmacy', 'Pharmacy'), ('chain_pharmacies', 'Chain Pharmacies'), ('distributor', 'Distributors'),
        ('mini_distributor', 'Mini Distributors'),
        ('tender', 'Tenders'), ('hospital', 'Hospitals'), ('foreign_customers', 'Foreign Customers'),
        ('clinic', 'Clinic'), ('str', 'str')], string='Category Type')
    name = fields.Char(string="", required=False, )
    code = fields.Char(string="", required=False, )
    customer_type = fields.Selection(string="", selection=[('customer', 'Customer Category'), ('vendor', 'Vendor '
                                                                                                         'Category'),
                                                           ], required=False, )


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    office = fields.Many2one('hr.department', store=True)

    delivery_rep = fields.Many2one(comodel_name="hr.employee", string="", )
    sales_rep = fields.Many2one(comodel_name="hr.employee", string="", )
    supervisor = fields.Many2one(comodel_name="hr.employee", string="", required=False, )
    categ_id = fields.Many2one(comodel_name="category.customer", string="Customer Category", required=True, )
    dist_discount = fields.Float(string="", required=False, )
    dist_account = fields.Many2one(comodel_name="account.account", string="", required=False, )
    cash_discount = fields.Float(string="", required=False, )
    cash_account = fields.Many2one(comodel_name="account.account", string="", required=False, )
    code = fields.Char(string="", required=False, )

    @api.constrains('name', )
    def _onchange_name(self):
        for record in self:
            if not record.code:
                code = self.env['category.customer'].search([('id', '=', self.categ_id.id)]).code
                if code:
                    self.code = code + self.env['ir.sequence'].next_by_code('res.partner') or _('New')
                if not code:
                    self.code = self.env['ir.sequence'].next_by_code('res.partner') or _('New')


class Sale(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'
    cash_discount_sale = fields.Float('Cash Discount', store=True)
    dis_discount_sale = fields.Float('Distributor Discount', store=True)
    return_order = fields.Boolean(string='Returned Order',
                                  compute='_compute_return_order', search='_search_return_order')

    def _search_return_order(self, operator, value):
        if operator != '=':
            if operator == '!=' and isinstance(value, bool):
                value = not value
            else:
                raise NotImplementedError()
        lines = self.search([('invoice_status', '=', "to invoice")])
        line_ids = lines.filtered(lambda line: line.return_order == value).ids
        return [('id', 'in', line_ids)]

    def _compute_return_order(self):
        for record in self:
            lines = record.order_line.filtered(lambda line: line.qty_invoiced > line.qty_delivered)
            if lines:
                record.return_order = True
            else:
                record.return_order = False

    @api.onchange('partner_id')
    def _onchange_ty(self):
        for record in self:
            if self.partner_id:
                record.dis_discount_sale = record.partner_id.dist_discount
                record.cash_discount_sale = record.partner_id.cash_discount

    office = fields.Many2one('hr.department', store=True)

    cust_categ_id = fields.Many2one(comodel_name="category.customer", string="", required=True, )
    delivery_rep = fields.Many2one(comodel_name="hr.employee", string="", )
    sales_rep = fields.Many2one(comodel_name="hr.employee", string="", )
    supervisor = fields.Many2one(comodel_name="hr.employee", string="", required=False, )

    @api.onchange('cust_categ_id')
    def _onchange_cust_categ_id(self):
        if self.state in ['draft', 'sent']:
            self.order_line = False
            self.partner_id = False
        return {'domain': {'partner_id': [('categ_id', '=', self.cust_categ_id.id)]}}

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(Sale, self).onchange_partner_id()
        if self.state in ['draft', 'sent']:
            self.order_line = False

    def pharm_discount_total_amount(self):
        for order in self:
            order.pharm_discount_total = 0.00
            order.cash_discount_total = 0.00
            order.dist_discount_total = 0.00
            order.discount_total = 0.00
            for line in order.order_line:
                if line:
                    if order.partner_id.categ_id.category_type == 'store' or order.partner_id.categ_id.category_type == 'tender':

                        pharmacy = 0
                        cash = 0
                        dist = 0
                        total_dist = 0

                    else:
                        pharmacy = round(line.pharmacy_discount, 2)
                        cash = round(line.cash_amount, 2)
                        dist = round(line.dist_amount, 2)
                        total_dist = round((line.dist_amount + line.pharmacy_discount + line.cash_amount), 2)
                    order.pharm_discount_total += round(pharmacy, 2)
                    order.dist_discount_total += round(dist, 2)
                    order.cash_discount_total += round(cash, 2)
                    order.discount_total += round(total_dist, 2)
                else:

                    pharmacy = 0
                    cash = 0
                    dist = 0
                    total_dist = 0

        return

    pharm_discount_total = fields.Monetary(string='Total Pharmacy/Deduction Dis',
                                           compute='pharm_discount_total_amount', track_visibility='always')

    cash_discount_total = fields.Monetary(string='Total Cash Discount',
                                          compute='pharm_discount_total_amount', track_visibility='always')

    dist_discount_total = fields.Monetary(string='Total Distributor Discount',
                                          compute='pharm_discount_total_amount', track_visibility='always')
    discount_total = fields.Monetary(string='Total Discount',
                                     compute='pharm_discount_total_amount', track_visibility='always')

    def _prepare_invoice(self):
        self.ensure_one()
        invoice_vals = super(Sale, self)._prepare_invoice()
        invoice_vals.update({'delivery_rep': self.delivery_rep and self.delivery_rep.id,
                             'sales_rep': self.sales_rep.id,
                             'supervisor': self.supervisor.id,
                             'warehouse_id': self.warehouse_id.id,
                             'discount_amount': self.discount_total,
                             'pharm_amount': self.pharm_discount_total,
                             'distr_amount': self.dist_discount_total,
                             'cash_amount': self.cash_discount_total,
                             'cust_categ_id': self.cust_categ_id,
                             'cash_discount_sale': self.cash_discount_sale,
                             'dis_discount_sale': self.dis_discount_sale,
                             })
        return invoice_vals


class ORder(models.Model):
    _name = 'sale.order.line'
    _inherit = 'sale.order.line'
    cash_discount_sale = fields.Float('Cash Dis%', related='order_id.cash_discount_sale', store=True)
    dis_discount_sale = fields.Float('Dist Dis%', related='order_id.dis_discount_sale', store=True)

    sale_type = fields.Selection(string="Product Type", selection=[('sale', 'Sale'), ('bouns', 'Bouns')],
                                 required=False, default='sale')
    dist_discount = fields.Float(string="", related="order_id.partner_id.dist_discount", store=True)
    cash_discount = fields.Float(string="", related="order_id.partner_id.cash_discount", store=True)
    real_price = fields.Float(string="Real Priice", related="product_id.list_price", store=True)
    dist_amount = fields.Float(string="", compute='_compute_amount')
    cash_amount = fields.Float(string="", compute='_compute_amount')
    batch_no = fields.Char(string="Batch Number", required=False, )
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    publicprice = fields.Float("Public Price", digits=('Product Price'), store=True)

    @api.onchange('product_id')
    def onchange_public_price(self):
        for line in self:
            if line.product_id:
                line.publicprice = line.product_id.pubprice

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'sale_type')
    def _compute_pharmacy(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            if line.product_id:
                if line.sale_type == 'sale':
                    price3 = line.product_uom_qty * line.price_unit * ((line.discount or 0.0) / 100)

                    line.pharmacy_discount = price3
                else:
                    line.pharmacy_discount = 0

    pharmacy_discount = fields.Float(string='price list Discount Amount', digits=('Discount'),
                                     compute='_compute_pharmacy', store=True)

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'sale_type')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            if line.order_id.partner_id.categ_id.category_type == 'store' or line.order_id.partner_id.categ_id.category_type == 'tender':

                price1 = line.store_price

                price2 = price1 * (1.0 - (line.dist_discount or 0.0) / 100.0)
                price = price2 * (1.0 - (line.cash_discount or 0.0) / 100.0)
                ##print(line.price_unit, price1, price2, price)

                if line.sale_type == 'bouns':

                    taxes = line.tax_id.compute_all(price2, line.order_id.currency_id, line.product_uom_qty,
                                                    product=line.product_id, partner=line.order_id.partner_shipping_id)

                    line.update({
                        'dist_amount': 0.0,
                        'cash_amount': 0.0,
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_subtotal': 0.0,
                    })
                else:

                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                    product=line.product_id, partner=line.order_id.partner_shipping_id)
                    line.update({
                        'dist_amount': price1 * ((line.order_id.dis_discount_sale or 0.0) / 100) * line.product_uom_qty,
                        'cash_amount': price2 * (
                                (line.order_id.cash_discount_sale or 0.0) / 100) * line.product_uom_qty,
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': taxes['total_included'],
                        'price_subtotal': taxes['total_excluded'],
                    })

                if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                        'account.group_account_manager'):
                    line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])
            else:
                price1 = (line.price_unit * (1.0 - (line.discount or 0.0) / 100.0))
                price2 = price1 * (1.0 - (line.dist_discount or 0.0) / 100.0)
                price = price2 * (1.0 - (line.cash_discount or 0.0) / 100.0)
                # print(line.price_unit, price1, price2, price)

                if line.sale_type == 'bouns':

                    taxes = line.tax_id.compute_all(price1, line.order_id.currency_id, line.product_uom_qty,
                                                    product=line.product_id, partner=line.order_id.partner_shipping_id)

                    line.update({
                        'dist_amount': 0.0,
                        'cash_amount': 0.0,
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_subtotal': 0.0,
                    })
                else:

                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                    product=line.product_id, partner=line.order_id.partner_shipping_id)
                    line.update({
                        'dist_amount': price1 * ((line.dist_discount or 0.0) / 100) * line.product_uom_qty,
                        'cash_amount': price2 * ((line.cash_discount or 0.0) / 100) * line.product_uom_qty,
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': taxes['total_included'],
                        'price_subtotal': taxes['total_excluded'],
                    })

                if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                        'account.group_account_manager'):
                    line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

    def _prepare_invoice_line(self, **optional_values):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        :param optional_values: any parameter that should be added to the returned invoice line
        """
        self.ensure_one()
        res = {
            'display_type': self.display_type,
            'sale_type': self.sale_type,
            'batch_no': self.batch_no,
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'discount': self.discount,
            'cash_discount_sale': self.cash_discount_sale,
            'dis_discount_sale': self.dis_discount_sale,
            'store_price': self.store_price,
            'publicprice': self.publicprice,
            'price_unit': self.price_unit,
            'tax_ids': [(6, 0, self.tax_id.ids)],
            'analytic_account_id': self.order_id.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'sale_line_ids': [(4, self.id)],
        }
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res

    @api.depends('price_unit', 'product_id', 'discount')
    def compute_store_price(self):
        for line in self:
            if line.order_id.partner_id.categ_id.category_type == 'store' or line.order_id.partner_id.categ_id.category_type == 'tender':
                if line.discount:
                    line.store_price = round((line.price_unit * (1.0 - line.discount / 100.0)), 3)
                else:
                    line.store_price = line.price_unit
        return

    store_price = fields.Float(string='Store/Tender Price', digits=(12, 2), store=True, compute='compute_store_price')


class Invoceder(models.Model):
    _name = 'account.move.line'
    _inherit = 'account.move.line'
    cash_discount_sale = fields.Float('Cash Discount', store=True, index=True)
    dis_discount_sale = fields.Float('Distributor Discount', store=True, index=True)
    publicprice = fields.Float("Public Price", store=True, digits=('Product Price'))

    @api.onchange('product_id')
    def onchange_public_price(self):
        for line in self:
            if line.product_id:
                line.publicprice = line.product_id.pubprice

    @api.depends('price_unit', 'product_id', 'discount')
    def onchange_p_price(self):
        for line in self:
            if line.product_id:
                line.p_unit = line.product_id.lst_price
        return

    p_unit = fields.Float("Price Unit", store=True, digits=('Product Price'), compute='onchange_p_price')

    @api.depends('price_unit', 'product_id', 'discount')
    def compute_store_price(self):
        for line in self:
            if line.move_id.partner_id.categ_id.category_type == 'store' or line.move_id.partner_id.categ_id.category_type == 'tender':
                if line.discount:
                    line.store_price = round((line.p_unit * (1.0 - line.discount / 100.0)), 3)
                else:
                    line.store_price = line.p_unit
        return

    store_price = fields.Float(string='Store/Tender Price', digits=(12, 2), store=True, compute='compute_store_price')

    sale_type = fields.Selection(string="Product Type", selection=[('bouns', 'Bouns'), ('sale', 'Sale'), ],
                                 required=False, )
    dist_discount = fields.Float(string="", related="move_id.partner_id.dist_discount", store=True)
    cash_discount = fields.Float(string="", related="move_id.partner_id.cash_discount", store=True)
    dist_account = fields.Many2one(comodel_name="account.account", related="move_id.partner_id.dist_account", string="",
                                   store=True)
    cash_account = fields.Many2one(comodel_name="account.account", related="move_id.partner_id.cash_account", string="",
                                   store=True)
    tax_name = fields.Char('tax_name', compute='_compute_func_tax', )
    dist_amount = fields.Float(string="", compute='_compute_discount')
    cash_amount = fields.Float(string="", compute='_compute_discount')
    pre_amount = fields.Float(string="Pre Amount", compute='_compute_discount')
    move_type = fields.Selection(string="move type", related="move_id.move_type")
    batch_no = fields.Char(string="Batch Number", required=False, )
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    list_price = fields.Float(string='Unit Price', digits='Product Price')

    @api.onchange('price_unit')
    def _onchange_price(self):
        for rec in self:
            if rec.price_unit != 0:
                rec.list_price = rec.price_unit

    def write(self, vals):
        # OVERRIDE
        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')
        PROTECTED_FIELDS_TAX_LOCK_DATE = ['debit', 'credit', 'tax_line_id', 'tax_ids', 'tax_tag_ids']
        PROTECTED_FIELDS_LOCK_DATE = PROTECTED_FIELDS_TAX_LOCK_DATE + ['account_id', 'journal_id', 'amount_currency',
                                                                       'currency_id', 'partner_id']
        PROTECTED_FIELDS_RECONCILIATION = ('account_id', 'date', 'debit', 'credit', 'amount_currency', 'currency_id')

        account_to_write = self.env['account.account'].browse(vals['account_id']) if 'account_id' in vals else None

        # Check writing a deprecated account.
        if account_to_write and account_to_write.deprecated:
            raise UserError(_('You cannot use a deprecated account.'))

        for line in self:
            if line.parent_state == 'posted':
                if line.move_id.restrict_mode_hash_table and set(vals).intersection(INTEGRITY_HASH_LINE_FIELDS):
                    raise UserError(_(
                        "You cannot edit the following fields due to restrict mode being activated on the journal: %s.") % ', '.join(
                        INTEGRITY_HASH_LINE_FIELDS))
                if any(key in vals for key in ('tax_ids', 'tax_line_ids')):
                    if line.move_id.discount_flag == False:
                        raise UserError(_(
                            'You cannot modify the taxes related to a posted journal item, you should reset the journal entry to draft to do so.'))

            # Check the lock date.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in
                   PROTECTED_FIELDS_LOCK_DATE):
                line.move_id._check_fiscalyear_lock_date()

            # Check the tax lock date.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in
                   PROTECTED_FIELDS_TAX_LOCK_DATE):
                line._check_tax_lock_date()

            # Check the reconciliation.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in
                   PROTECTED_FIELDS_RECONCILIATION):
                line._check_reconciliation()

            # Check switching receivable / payable accounts.
            if account_to_write:
                account_type = line.account_id.user_type_id.type
                if line.move_id.is_sale_document(include_receipts=True):
                    if (account_type == 'receivable' and account_to_write.user_type_id.type != account_type) \
                            or (account_type != 'receivable' and account_to_write.user_type_id.type == 'receivable'):
                        raise UserError(_(
                            "You can only set an account having the receivable type on payment terms lines for customer invoice."))
                if line.move_id.is_purchase_document(include_receipts=True):
                    if (account_type == 'payable' and account_to_write.user_type_id.type != account_type) \
                            or (account_type != 'payable' and account_to_write.user_type_id.type == 'payable'):
                        raise UserError(_(
                            "You can only set an account having the payable type on payment terms lines for vendor bill."))

        # Get all tracked fields (without related fields because these fields must be manage on their own model)
        tracking_fields = []
        for value in vals:
            field = self._fields[value]
            if hasattr(field, 'related') and field.related:
                continue  # We don't want to track related field.
            if hasattr(field, 'tracking') and field.tracking:
                tracking_fields.append(value)
        ref_fields = self.env['account.move.line'].fields_get(tracking_fields)

        # Get initial values for each line
        move_initial_values = {}
        for line in self.filtered(lambda l: l.move_id.posted_before):  # Only lines with posted once move.
            for field in tracking_fields:
                # Group initial values by move_id
                if line.move_id.id not in move_initial_values:
                    move_initial_values[line.move_id.id] = {}
                move_initial_values[line.move_id.id].update({field: line[field]})

        # Create the dict for the message post
        tracking_values = {}  # Tracking values to write in the message post
        for move_id, modified_lines in move_initial_values.items():
            tmp_move = {move_id: []}
            for line in self.filtered(lambda l: l.move_id.id == move_id):
                changes, tracking_value_ids = line._mail_track(ref_fields,
                                                               modified_lines)  # Return a tuple like (changed field, ORM command)
                tmp = {'line_id': line.id}
                if tracking_value_ids:
                    selected_field = tracking_value_ids[0][
                        2]  # Get the last element of the tuple in the list of ORM command. (changed, [(0, 0, THIS)])
                    tmp.update({
                        **{'field_name': selected_field.get('field_desc')},
                        **self._get_formated_values(selected_field)
                    })
                elif changes:
                    field_name = line._fields[changes.pop()].string  # Get the field name
                    tmp.update({
                        'error': True,
                        'field_error': field_name
                    })
                else:
                    continue
                tmp_move[move_id].append(tmp)
            if len(tmp_move[move_id]) > 0:
                tracking_values.update(tmp_move)

        # Write in the chatter.
        for move in self.mapped('move_id'):
            fields = tracking_values.get(move.id, [])
            if len(fields) > 0:
                msg = self._get_tracking_field_string(tracking_values.get(move.id))
                move.message_post(body=msg)  # Write for each concerned move the message in the chatter

        result = True
        for line in self:
            cleaned_vals = line.move_id._cleanup_write_orm_values(line, vals)
            if not cleaned_vals:
                continue

            # Auto-fill amount_currency if working in single-currency.
            if 'currency_id' not in cleaned_vals \
                    and line.currency_id == line.company_currency_id \
                    and any(field_name in cleaned_vals for field_name in ('debit', 'credit')):
                cleaned_vals.update({
                    'amount_currency': vals.get('debit', 0.0) - vals.get('credit', 0.0),
                })

            result |= super(Invoceder, line).write(cleaned_vals)

            if not line.move_id.is_invoice(include_receipts=True):
                continue

            # Ensure consistency between accounting & business fields.
            # As we can't express such synchronization as computed fields without cycling, we need to do it both
            # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
            # business [resp. accounting] fields are recomputed.
            if any(field in cleaned_vals for field in ACCOUNTING_FIELDS):
                price_subtotal = line._get_price_total_and_subtotal().get('price_subtotal', 0.0)
                to_write = line._get_fields_onchange_balance(price_subtotal=price_subtotal)
                to_write.update(line._get_price_total_and_subtotal(
                    price_unit=to_write.get('price_unit', line.price_unit),
                    quantity=to_write.get('quantity', line.quantity),
                    discount=to_write.get('discount', line.discount),
                ))
                result |= super(Invoceder, line).write(to_write)
            elif any(field in cleaned_vals for field in BUSINESS_FIELDS):
                to_write = line._get_price_total_and_subtotal()
                to_write.update(line._get_fields_onchange_subtotal(
                    price_subtotal=to_write['price_subtotal'],
                ))
                result |= super(Invoceder, line).write(to_write)

        # Check total_debit == total_credit in the related moves.
        if self._context.get('check_move_validity', True):
            self.mapped('move_id')._check_balanced()

        self.mapped('move_id')._synchronize_business_models({'line_ids'})

        return result

    @api.depends('cash_discount', 'dist_discount', 'sale_type')
    def _compute_discount(self):
        for rec in self:
            if rec.sale_type != 'bouns':
                price = rec.p_unit
                price1 = (price * (1.0 - (rec.discount or 0.0) / 100.0))
                price2 = price1 * (1.0 - (rec.dist_discount or 0.0) / 100.0)
                rec.pre_amount = price * ((rec.discount or 0.0) / 100.0) * rec.quantity
                rec.dist_amount = price1 * ((rec.dist_discount or 0.0) / 100.0) * rec.quantity
                rec.cash_amount = price2 * ((rec.cash_discount or 0.0) / 100.0) * rec.quantity
            else:
                rec.dist_amount = 0.0
                rec.cash_amount = 0.0
                rec.pre_amount = 0.0

    @api.depends('tax_ids')
    def _compute_func_tax(self):
        for rec in self:
            if rec.tax_ids:
                tax = ''
                for tx in rec.tax_ids:
                    tax += ' ' + tx.name
                rec.tax_name = tax
            else:
                rec.tax_name = ''

    def compute_dist(self):
        dist = 0
        for r in self:
            order = self.env['sale.order'].search([('name', '=', r.move_id.invoice_origin)])
            if order:
                for x in order:
                    dist = x.dis_discount_sale
            else:

                dist = r.move_id.partner_id.dist_discount

            return dist

    def compute_cash(self):
        cash = 0
        for r in self:
            order = self.env['sale.order'].search([('name', '=', r.move_id.invoice_origin)])
            if order:
                for x in order:
                    cash = x.cash_discount_sale
            else:

                cash = r.move_id.partner_id.cash_discount

            return cash

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount,
                                            currency, product, partner, taxes,
                                            move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.e3 ``

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}

        # Compute 'price_subtotal'.
        price_unit = self.p_unit

        if partner.categ_id.category_type == 'store' or partner.categ_id.category_type == 'tender':
            if product:
                x = round((price_unit * (1.0 - discount / 100.0)), 3)
                price_unit_wo_discount1 = round_half_up(x, 2)
                price_unit_wo_discount2 = price_unit_wo_discount1 * (1 - (self.compute_dist() or 0.0) / 100.0)
                price_unit_wo_discount = price_unit_wo_discount2 * (1 - (self.compute_cash() or 0.0) / 100.0)
            else:
                price_unit_wo_discount = price_unit

            subtotal = quantity * price_unit_wo_discount

            # Compute 'price_total'.
            if taxes:

                if self.sale_type == 'bouns':

                    taxes_res = taxes._origin.compute_all(price_unit_wo_discount,
                                                          quantity=quantity, currency=currency, product=product,
                                                          partner=partner,
                                                          is_refund=move_type in ('out_refund', 'in_refund'))
                    # print(price_unit_wo_discount, taxes_res)
                    res['price_subtotal'] = 0.00
                    res['price_total'] = taxes_res['total_included'] - taxes_res['total_excluded']
                elif self.sale_type == 'sale':
                    taxes_res = taxes._origin.compute_all(price_unit_wo_discount,
                                                          quantity=quantity, currency=currency, product=product,
                                                          partner=partner,
                                                          is_refund=move_type in ('out_refund', 'in_refund'))
                    res['price_subtotal'] = taxes_res['total_excluded']
                    res['price_total'] = taxes_res['total_included']
                elif not self.sale_type:
                    taxes_res = taxes._origin.compute_all(price_unit_wo_discount,
                                                          quantity=quantity, currency=currency, product=product,
                                                          partner=partner,
                                                          is_refund=move_type in ('out_refund', 'in_refund'))
                    res['price_subtotal'] = taxes_res['total_excluded']
                    res['price_total'] = taxes_res['total_included']

            else:
                if self.sale_type == 'bouns':
                    res['price_total'] = res['price_subtotal'] = 0.00

                else:
                    res['price_total'] = res['price_subtotal'] = subtotal

            # In case of multi currency, round before it's use for computing debit credit
            if currency:
                res = {k: currency.round(v) for k, v in res.items()}
            return res
        else:
            if product:

                price_unit_wo_discount1 = (price_unit * (1 - ((discount or 0.0) / 100.0)))
                price_unit_wo_discount2 = price_unit_wo_discount1 * (1 - (self.compute_dist() or 0.0) / 100.0)
                price_unit_wo_discount = price_unit_wo_discount2 * (1 - ((self.compute_cash() or 0.0)) / 100.0)
            else:
                price_unit_wo_discount = price_unit

            subtotal = quantity * price_unit_wo_discount

            # Compute 'price_total'.
            if taxes:

                if self.sale_type == 'bouns':
                    price_unit_wo_discount1 = (price_unit * (1.0 - (discount / 100.0)))
                    taxes_res = taxes._origin.compute_all(price_unit_wo_discount1,
                                                          quantity=quantity, currency=currency, product=product,
                                                          partner=partner,
                                                          is_refund=move_type in ('out_refund', 'in_refund'))
                    # print(price_unit_wo_discount, taxes_res)
                    res['price_subtotal'] = 0.00
                    res['price_total'] = taxes_res['total_included'] - taxes_res['total_excluded']
                elif self.sale_type == 'sale':
                    taxes_res = taxes._origin.compute_all(price_unit_wo_discount,
                                                          quantity=quantity, currency=currency, product=product,
                                                          partner=partner,
                                                          is_refund=move_type in ('out_refund', 'in_refund'))
                    res['price_subtotal'] = taxes_res['total_excluded']
                    res['price_total'] = taxes_res['total_included']
                elif not self.sale_type:
                    taxes_res = taxes._origin.compute_all(price_unit_wo_discount,
                                                          quantity=quantity, currency=currency, product=product,
                                                          partner=partner,
                                                          is_refund=move_type in ('out_refund', 'in_refund'))
                    res['price_subtotal'] = taxes_res['total_excluded']
                    res['price_total'] = taxes_res['total_included']

            else:
                if self.sale_type == 'bouns':
                    res['price_total'] = res['price_subtotal'] = 0.00

                else:
                    res['price_total'] = res['price_subtotal'] = subtotal

            # In case of multi currency, round before it's use for computing debit credit
            if currency:
                res = {k: currency.round(v) for k, v in res.items()}
            return res

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency', 'sale_type')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids', 'sale_type')
        print(vals_list)
        for val in vals_list:
            try:
                if val['sale_type'] == 'bouns':
                    price = val['price_unit']
                    val['price_unit'] = 0.0
                    val['list_price'] = price
            except:
                print(vals_list)

        lines = super(Invoceder, self).create(vals_list)

        return lines


class Move(models.Model):
    _name = 'account.move'
    _inherit = 'account.move'

    @api.depends('posted_before', 'state', 'journal_id', 'date')
    def _compute_name(self):
        for invoice in self:
            if not self.name:
                if self.move_type != 'entry' and invoice.move_type == 'out_invoice' and invoice.warehouse_id.sale_store == False:
                    invoice.name = self.env['ir.sequence'].next_by_code('customer_invoice')
                elif self.move_type != 'entry' and invoice.move_type == 'out_invoice' and invoice.warehouse_id.sale_store == True:
                    invoice.name = self.env['ir.sequence'].next_by_code('customer_invoice_distributor')
                elif self.move_type != 'entry' and invoice.move_type == 'out_refund':
                    invoice.name = self.env['ir.sequence'].next_by_code('refund_invoice')
                elif self.move_type != 'entry' and invoice.move_type == 'in_refund':
                    invoice.name = self.env['ir.sequence'].next_by_code('refund_bill')
                elif self.move_type != 'entry' and invoice.move_type == 'in_invoice':
                    invoice.name = self.env['ir.sequence'].next_by_code('in_invoice')

                elif self.move_type == 'entry':

                    def journal_key(move):
                        return (move.journal_id, move.journal_id.refund_sequence and move.move_type)

                    def date_key(move):
                        return (move.date.year, move.date.month)

                    grouped = defaultdict(  # key: journal_id, move_type
                        lambda: defaultdict(  # key: first adjacent (date.year, date.month)
                            lambda: {
                                'records': self.env['account.move'],
                                'format': False,
                                'format_values': False,
                                'reset': False
                            }
                        )
                    )
                    self = self.sorted(lambda m: (m.date, m.ref or '', m.id))
                    highest_name = self[0]._get_last_sequence() if self else False

                    # Group the moves by journal and month
                    for move in self:
                        if not highest_name and move == self[0] and not move.posted_before:
                            # In the form view, we need to compute a default sequence so that the user can edit
                            # it. We only check the first move as an approximation (enough for new in form view)
                            pass
                        elif (move.name and move.name != '/') or move.state != 'posted':
                            # Has already a name or is not posted, we don't add to a batch
                            continue
                        group = grouped[journal_key(move)][date_key(move)]
                        if not group['records']:
                            # Compute all the values needed to sequence this whole group
                            move._set_next_sequence()
                            group['format'], group['format_values'] = move._get_sequence_format_param(move.name)
                            group['reset'] = move._deduce_sequence_number_reset(move.name)
                        group['records'] += move

                    # Fusion the groups depending on the sequence reset and the format used because `seq` is
                    # the same counter for multiple groups that might be spread in multiple months.
                    final_batches = []
                    for journal_group in grouped.values():
                        for date_group in journal_group.values():
                            if not final_batches or final_batches[-1]['format'] != date_group['format']:
                                final_batches += [date_group]
                            elif date_group['reset'] == 'never':
                                final_batches[-1]['records'] += date_group['records']
                            elif (
                                    date_group['reset'] == 'year'
                                    and final_batches[-1]['records'][0].date.year == date_group['records'][0].date.year
                            ):
                                final_batches[-1]['records'] += date_group['records']
                            else:
                                final_batches += [date_group]

                    # Give the name based on previously computed values
                    for batch in final_batches:
                        for move in batch['records']:
                            move.name = batch['format'].format(**batch['format_values'])
                            batch['format_values']['seq'] += 1
                        batch['records']._compute_split_sequence()

                    self.filtered(lambda m: not m.name).name = '/'

    name = fields.Char(string='Number', copy=False, default=False, compute='_compute_name', store=True, index=True,
                       tracking=True)

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids2(self):
        for m in self:
            domain = [('company_id', '=', m.company_id.id)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)

    suitable_journal_ids = fields.Many2many('account.journal', compute='_compute_suitable_journal_ids2')

    @api.depends('invoice_origin')
    def _compute_invoice_return(self):
        for m in self:
            if m.invoice_origin:
                x = self.env['account.move'].search([('invoice_origin', '=', m.invoice_origin)])
                t = []
                if x:
                    for l in x:
                        m.return_source = l.name
                else:

                    m.return_source = False
            else:
                m.return_source = False

    return_source = fields.Char('Return Source', compute='_compute_invoice_return')
    cash_discount_sale = fields.Float('Cash Discount', store=True, index=True)
    dis_discount_sale = fields.Float('Distributor Discount', store=True, index=True)
    cust_categ_id = fields.Many2one(string="Customer Category", related="partner_id.categ_id")

    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', readonly=True, store=True, states={'draft': [('readonly', False)]},
    )
    delivery_rep = fields.Many2one(comodel_name="hr.employee", string="", )
    sales_rep = fields.Many2one(comodel_name="hr.employee", string="", )
    supervisor = fields.Many2one(comodel_name="hr.employee", string="", required=False, )
    account_allowence = fields.Many2one(comodel_name="account.account", string="Account Allowance", required=False, )
    discount_type = fields.Selection(string="Allowance Discount",
                                     selection=[('fixed', 'Fixed'), ('percent', 'Percent'), ],
                                     required=False, default='fixed')
    discount_rate = fields.Float(string="Discount", required=False, digits='Product Price')
    discount_flag = fields.Boolean(string="Discount", )
    discount_val = fields.Float(string="", required=False, digits='Product Price')
    tot_qty = fields.Float(string='Total Quantity', compute='_compute_sum_quantity', digits='Product Price')

    def action_post(self):
        rec = 0

        for line in self.invoice_line_ids:
            if line.product_id:
                rec = line.account_id.id

        lines_list = []

        dic_disc_amount = self.dist_discount_totals
        cash_disc_amount = self.cash_discount_totals
        pharma_discount = self.pharm_discount_totals
        total = dic_disc_amount + cash_disc_amount + pharma_discount
        ##print(total)
        if total != 0 and self.move_type == 'out_invoice':

            # lines_list.append((0, 0, {
            #     'name': 'Total Discount',
            #     'display_type': False,
            #     'exclude_from_invoice_tab': True,
            #     'account_id': rec,
            #     'debit': 0.0,
            #     'credit': round(dic_disc_amount, 2) + round(cash_disc_amount, 2) + round(pharma_discount, 2),
            # }))
            if self.partner_id.dist_account.id:
                lines_list.append((0, 0, {
                    'name': 'Dist Discount',
                    'display_type': False,
                    'exclude_from_invoice_tab': True,
                    'account_id': self.partner_id.dist_account.id,
                    'debit': round(dic_disc_amount, 2),
                    'credit': 0.0
                }))
            if self.partner_id.cash_account.id:
                lines_list.append((0, 0, {
                    'name': 'Cash Discount',
                    'display_type': False,
                    'exclude_from_invoice_tab': True,
                    'account_id': self.partner_id.cash_account.id,
                    'credit': 0.0,
                    'debit': round(cash_disc_amount, 2),

                }))

            if self.partner_id.property_product_pricelist.pharmacy_account:
                lines_list.append((0, 0, {
                    'name': 'Pharmacy Discount',
                    'display_type': False,
                    'exclude_from_invoice_tab': True,
                    'account_id': self.partner_id.property_product_pricelist.pharmacy_account.id,
                    'credit': 0.0,
                    'debit': round(pharma_discount, 2),

                }))

            self.update({'line_ids': lines_list,
                         })
        if total != 0 and self.move_type == 'out_refund':

            # lines_list.append((0, 0, {
            #     'name': 'Total Discount',
            #     'display_type': False,
            #     'exclude_from_invoice_tab': True,
            #     'account_id': rec,
            #     'debit': round(dic_disc_amount, 2) + round(cash_disc_amount, 2) + round(pharma_discount, 2),
            #     'credit':0.0 ,
            # }))
            if self.partner_id.dist_account.id:
                lines_list.append((0, 0, {
                    'name': 'Dist Discount',
                    'display_type': False,
                    'exclude_from_invoice_tab': True,
                    'account_id': self.partner_id.dist_account.id,
                    'credit': round(dic_disc_amount, 2),
                    'debit': 0.0
                }))
            if self.partner_id.cash_account.id:
                lines_list.append((0, 0, {
                    'name': 'Cash Discount',
                    'display_type': False,
                    'exclude_from_invoice_tab': True,
                    'account_id': self.partner_id.cash_account.id,
                    'debit': 0.0,
                    'credit': round(cash_disc_amount, 2),

                }))

            if self.partner_id.property_product_pricelist.pharmacy_account.id:
                lines_list.append((0, 0, {
                    'name': 'Pharmacy Discount',
                    'display_type': False,
                    'exclude_from_invoice_tab': True,
                    'account_id': self.partner_id.property_product_pricelist.pharmacy_account.id,
                    'debit': 0.0,
                    'credit': round(pharma_discount, 2),

                }))

            self.update({'line_ids': lines_list,
                         })
        return super(Move, self).action_post()

    @api.depends('invoice_line_ids.quantity')
    def _compute_sum_quantity(self):
        for invoice in self:
            tot_qty = 0
            for line in invoice.invoice_line_ids:
                tot_qty += line.quantity
            invoice.tot_qty = tot_qty

    def submit_discount(self):
        for rec in self:
            rec.discount_val = rec.discount_amt
            rec.discount_flag = True
            for invoice in self:
                debit = credit = invoice.discount_amt
                if invoice.move_type == 'out_invoice':
                    move = {
                        'journal_id': invoice.journal_id.id,
                        'name': self.env['ir.sequence'].next_by_code('customer_invoice_dis'),
                        'date': invoice.invoice_date,
                        'ref': invoice.name,
                        'move_type': 'entry',
                        'line_ids': [(0, 0, {
                            'name': '/',
                            'debit': debit,
                            'account_id': invoice.account_allowence.id,
                            'partner_id': rec.partner_id.id,
                        }), (0, 0, {
                            'name': "/",
                            'credit': credit,
                            'account_id': rec.partner_id.property_account_receivable_id.id,
                            'partner_id': invoice.partner_id.id,

                        })]
                    }
                    move_id = self.env['account.move'].create(move)
                    move_id.post()
                if invoice.move_type == 'out_refund':
                    move = {
                        'journal_id': invoice.journal_id.id,
                        'date': invoice.invoice_date,
                        'ref': invoice.name,
                        'move_type': 'entry',
                        'line_ids': [(0, 0, {
                            'name': '/',
                            'debit': debit,
                            'account_id': rec.partner_id.property_account_receivable_id.id,
                            'partner_id': rec.partner_id.id,
                        }), (0, 0, {
                            'name': "/",
                            'credit': credit,
                            'account_id': rec.account_allowence.id,
                            'partner_id': rec.partner_id.id,

                        })]
                    }
                    move_id = self.env['account.move'].create(move)

                    move_id.post()

    @api.depends('discount_rate', 'discount_type', 'amount_total')
    def _compute_func_net(self):
        for rec in self:
            if rec.discount_rate and not rec.discount_flag:
                if rec.discount_type == 'fixed':
                    rec.discount_net = rec.amount_total - rec.discount_rate
                    rec.discount_amt = rec.discount_rate
                else:
                    rec.discount_amt = rec.amount_total * (rec.discount_rate / 100)
                    rec.discount_net = rec.amount_total - rec.discount_amt
            elif rec.discount_rate and rec.discount_flag:
                if rec.discount_type == 'fixed':
                    rec.discount_amt = rec.discount_rate
                else:
                    rec.discount_amt = rec.amount_total * (rec.discount_rate / 100)
                rec.discount_net = rec.amount_total

            else:
                rec.discount_net = rec.amount_total
                rec.discount_amt = 0

    @api.depends('invoice_line_ids')
    def _compute_func_discount(self):
        for order in self:
            order.distr_amount = 0.00
            order.cash_amount = 0.00
            order.discount_amount = 00
            order.pharm_amount = 0.00
            for line in order.invoice_line_ids:

                if line.product_id and line.sale_type != 'bouns' and line.sale_type == 'sale':
                    cash = line.cash_amount
                    dist = line.dist_amount
                    total_dist = cash + dist

                    order.distr_amount += dist
                    order.cash_amount += cash
                    order.discount_amount = +total_dist
                else:
                    order.distr_amount = 0.0
                    order.cash_amount = 0.0
                    order.discount_amount = 0.0

    discount_amount = fields.Float('Total Discount Amount', store=True)
    cash_amount = fields.Float('Cash Discount Amount', store=True)
    pharm_amount = fields.Float('Pharmacy Discount Amount', store=True)
    distr_amount = fields.Float('dist Discount Amount', store=True)
    discount_net = fields.Float('Net After Allowance Discount', store=True, compute='_compute_func_net',
                                digits='Product Price')
    discount_amt = fields.Float('Net Discount Value', store=True, compute='_compute_func_net', digits='Product Price')

    def compute_dist(self):
        dist = 0
        for r in self:
            order = self.env['sale.order'].search([('name', '=', r.invoice_origin)])
            if order:
                for x in order:
                    dist = x.dis_discount_sale
            else:

                dist = r.partner_id.dist_discount

            return dist

    def compute_cash(self):
        cash = 0
        for r in self:
            order = self.env['sale.order'].search([('name', '=', r.invoice_origin)])
            if order:
                for x in order:
                    cash = x.cash_discount_sale
            else:

                cash = r.partner_id.cash_discount

            return cash

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        ''' Compute the dynamic tax lines of the journal entry.

        :param lines_map: The line_ids dispatched by type containing:
            * base_lines: The lines having a tax_ids set.
            * tax_lines: The lines having a tax_line_id set.
            * terms_lines: The lines generated by the payment terms of the invoice.
            * rounding_lines: The cash rounding lines of the invoice.
        '''
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''

            move = base_line.move_id
            if move.is_invoice(include_receipts=True):

                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                is_refund = move.move_type in ('out_refund', 'in_refund')
                if move.partner_id.categ_id.category_type == 'store' or move.partner_id.categ_id.category_type == 'tender':
                    if base_line.product_id and base_line.sale_type == 'sale':
                        x = round((base_line.p_unit * (1.0 - base_line.discount / 100.0)), 3)
                        discount_pharm = round_half_up(x, 2)
                        discount_dist = discount_pharm * (1.0 - (move.compute_dist() / 100.0))
                        discount_cash = discount_dist * (1.0 - (move.compute_cash() / 100.0))
                        price_unit_wo_discount = sign * discount_cash
                    elif base_line.product_id and base_line.sale_type == 'bouns':
                        x = round((base_line.p_unit * (1.0 - base_line.discount / 100.0)), 3)
                        discount_pharm = round_half_up(x, 2)
                        discount_dist = discount_pharm * (1.0 - (move.compute_dist() / 100.0))
                        discount_cash = discount_dist * (1.0 - (move.compute_cash() / 100.0))
                        price_unit_wo_discount = sign * discount_cash

                    else:
                        price_unit_wo_discount = sign * base_line.p_unit
                else:
                    if base_line.product_id and base_line.sale_type == 'sale':
                        discount_pharm = ((base_line.p_unit * (1.0 - (base_line.discount / 100.0))))
                        discount_dist = discount_pharm * (1.0 - (move.compute_dist() / 100.0))
                        discount_cash = discount_dist * (1.0 - (move.compute_cash() / 100.0))
                        price_unit_wo_discount = sign * discount_cash
                    elif base_line.product_id and base_line.sale_type == 'bouns':
                        discount_pharm = (base_line.p_unit * (1.0 - (base_line.discount / 100.0)))
                        discount_dist = discount_pharm * (1.0 - (move.compute_dist() / 100.0))
                        discount_cash = discount_dist * (1.0 - (move.compute_cash() / 100.0))
                        price_unit_wo_discount = sign * discount_pharm

                    else:
                        price_unit_wo_discount = sign * base_line.p_unit



            else:

                handle_price_include = False
                quantity = 1.00
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (
                        tax_type == 'purchase' and base_line.credit)
                price_unit_wo_discount = base_line.balance
                # print(base_line.balance, 'balance')

            balance_taxes_res = base_line.tax_ids._origin.compute_all(
                price_unit_wo_discount,
                currency=base_line.currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
            )

            if move.move_type == 'entry':
                repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
                repartition_tags = base_line.tax_ids.mapped(repartition_field).filtered(
                    lambda x: x.repartition_type == 'base').tag_ids
                tags_need_inversion = (tax_type == 'sale' and not is_refund) or (
                        tax_type == 'purchase' and is_refund)
                if tags_need_inversion:
                    balance_taxes_res['base_tags'] = base_line._revert_signed_tags(repartition_tags).ids
                    for tax_res in balance_taxes_res['taxes']:
                        tax_res['tag_ids'] = base_line._revert_signed_tags(
                            self.env['account.account.tag'].browse(tax_res['tag_ids'])).ids

            return balance_taxes_res

            taxes_map = {}

            # ==== Add tax lines ====
            to_remove = self.env['account.move.line']
            for line in self.line_ids.filtered('tax_repartition_line_id'):
                grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)
                if grouping_key in taxes_map:
                    # A line with the same key does already exist, we only need one
                    # to modify it; we have to drop this one.
                    to_remove += line
                else:
                    taxes_map[grouping_key] = {
                        'tax_line': line,
                        'amount': 0.0,
                        'tax_base_amount': 0.0,
                        'grouping_dict': False,
                    }
            self.line_ids -= to_remove

            # ==== Mount base lines ====
            for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
                # Don't call compute_all if there is no tax.
                if not line.tax_ids:
                    line.tax_tag_ids = [(5, 0, 0)]
                    continue

                compute_all_vals = _compute_base_line_taxes(line)

                # Assign tags on base line
                line.tax_tag_ids = compute_all_vals['base_tags']

                tax_exigible = True
                for tax_vals in compute_all_vals['taxes']:
                    grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                    grouping_key = _serialize_tax_grouping_key(grouping_dict)

                    tax_repartition_line = self.env['account.tax.repartition.line'].browse(
                        tax_vals['tax_repartition_line_id'])
                    tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                    if tax.tax_exigibility == 'on_payment':
                        tax_exigible = False

                    taxes_map_entry = taxes_map.setdefault(grouping_key, {
                        'tax_line': None,
                        'amount': 0.0,
                        'tax_base_amount': 0.0,
                        'grouping_dict': False,
                    })
                    taxes_map_entry['amount'] += tax_vals['amount']
                    taxes_map_entry['tax_base_amount'] += tax_vals['base']
                    taxes_map_entry['grouping_dict'] = grouping_dict
                line.tax_exigible = tax_exigible

            # ==== Process taxes_map ====
            for taxes_map_entry in taxes_map.values():
                # The tax line is no longer used in any base lines, drop it.
                if taxes_map_entry['tax_line'] and not taxes_map_entry['grouping_dict']:
                    self.line_ids -= taxes_map_entry['tax_line']
                    continue

                currency = self.env['res.currency'].browse(taxes_map_entry['grouping_dict']['currency_id'])

                # Don't create tax lines with zero balance.
                if currency.is_zero(taxes_map_entry['amount']):
                    if taxes_map_entry['tax_line']:
                        self.line_ids -= taxes_map_entry['tax_line']
                    continue

                tax_base_amount = (-1 if self.is_inbound() else 1) * taxes_map_entry['tax_base_amount']
                # tax_base_amount field is expressed using the company currency.
                tax_base_amount = currency._convert(tax_base_amount, self.company_currency_id, self.company_id,
                                                    self.date or fields.Date.context_today(self))

                # Recompute only the tax_base_amount.
                if taxes_map_entry['tax_line'] and recompute_tax_base_amount:
                    taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                    continue

                balance = currency._convert(
                    taxes_map_entry['amount'],
                    self.journal_id.company_id.currency_id,
                    self.journal_id.company_id,
                    self.date or fields.Date.context_today(self),
                )
                to_write_on_line = {
                    'amount_currency': taxes_map_entry['amount'],
                    'currency_id': taxes_map_entry['grouping_dict']['currency_id'],
                    'debit': balance > 0.0 and balance or 0.0,
                    'credit': balance < 0.0 and -balance or 0.0,
                    'tax_base_amount': tax_base_amount,
                }

                if taxes_map_entry['tax_line']:
                    # Update an existing tax line.
                    taxes_map_entry['tax_line'].update(to_write_on_line)
                else:
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                        'account.move.line'].create
                    tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                    tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
                    tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                    taxes_map_entry['tax_line'] = create_method({
                        **to_write_on_line,
                        'name': tax.name,
                        'move_id': self.id,
                        'partner_id': line.partner_id.id,
                        'company_id': line.company_id.id,
                        'company_currency_id': line.company_currency_id.id,
                        'tax_base_amount': tax_base_amount,
                        'exclude_from_invoice_tab': True,
                        'tax_exigible': tax.tax_exigibility == 'on_invoice',
                        **taxes_map_entry['grouping_dict'],
                    })

                if in_draft_mode:
                    taxes_map_entry['tax_line'].update(taxes_map_entry['tax_line']._get_fields_onchange_balance())
