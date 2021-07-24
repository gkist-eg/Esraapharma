from datetime import date

from odoo import api, models, _
from odoo import fields
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DT


class Moveline(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids', 'sale_type')
    def _onchange_price_subtotals(self):
        self._onchange_price_subtotal()

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'cash_discount', 'dist_discount', 'sale_type')
    def _compute_pharmacy(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            if line.product_id:
                if line.sale_type == 'sale':

                    line.pharmacy_discount = (line.p_unit * line.quantity) *((line.discount or 0.0) / 100)
                else:

                    line.pharmacy_discount = 0

    pharmacy_discount = fields.Float(string='Pharmacy Discount Amount', digits=('Discount'),
                                     compute='_compute_pharmacy', store=True)


class Move(models.Model):
    _inherit = 'account.move'

    pricelist_id = fields.Many2one(
        'product.pricelist',
        'Pricelist',
        help='Pricelist for current invoice.'
    )

    @api.depends('invoice_line_ids.pharmacy_discount', 'invoice_line_ids.cash_amount', 'invoice_line_ids.discount',
                 'invoice_line_ids.dist_amount')
    def discount_total_amount(self):
        for order in self:
            order.pharm_discount_totals = 0.00
            order.cash_discount_totals = 0.00
            order.dist_discount_totals = 0.00
            order.discount_totals = 0.00
            order.amount_totals = 0.00
            for line in order.invoice_line_ids:
                if line:

                    if line.sale_type=='sale':
                        amount_totals=line.p_unit*line.quantity
                    if line.sale_type=='bouns':
                        amount_totals=line.p_unit*line.quantity
                    pharmacy = round(line.pharmacy_discount, 3)
                    cash = round(line.cash_amount, 3)
                    dist = round(line.dist_amount, 3)
                    total_dist = round((line.dist_amount + line.pharmacy_discount + line.cash_amount), 3)

                    order.pharm_discount_totals += round(pharmacy, 3)
                    order.dist_discount_totals += round(dist, 3)
                    order.cash_discount_totals += round(cash, 3)
                    order.discount_totals += round(total_dist, 3)
                    order.amount_totals += round(total_dist, 3)
                else:
                    order.pharm_discount_totals = 0
                    order.dist_discount_totals = 0
                    order.cash_discount_totals = 0
                    order.discount_totals = 0

        return

    pharm_discount_totals = fields.Monetary(string='Total Pharmacy/Deduction Dis',
                                            compute='discount_total_amount', track_visibility='always')

    cash_discount_totals = fields.Monetary(string='Total Cash Discount',
                                           compute='discount_total_amount', track_visibility='always')

    dist_discount_totals = fields.Monetary(string='Total Distributor Discount',
                                           compute='discount_total_amount', track_visibility='always')
    discount_totals = fields.Monetary(string='Total Discount',
                                      compute='discount_total_amount', track_visibility='always')
    amount_totals = fields.Monetary(string='Total Amount',
                                      compute='discount_total_amount', track_visibility='always')

    refund_method = fields.Selection([

        ('old', 'Invoice Old')],
        store=True, track_visibility='onchange')
    invoice_number_old = fields.Char("Invoice Number (Return)")

    invoice_number = fields.Many2one('account.move', string='Invoice Number')

    dist_discount = fields.Float(string="", related="partner_id.dist_discount", store=True)
    cash_discount = fields.Float(string="", related="partner_id.cash_discount", store=True)

    @api.onchange('refund_method')
    def _onchange_ty(self):
        for record in self:
            if record.refund_method == 'old':
                record.invoice_number = False
                record.invoice_line_ids.dist_discount = record.partner_id.dist_discount
                record.invoice_line_ids.cash_discount = record.partner_id.cash_discount



    @api.onchange('pricelist_id', 'invoice_line_ids')
    def _onchange_price_list(self):

        for record in self:
            if record.move_type == 'out_refund' and record.pricelist_id:
                if record.pricelist_id:
                    for i in record.invoice_line_ids:
                        partner = record.partner_id
                        pricelist = record.pricelist_id
                        product = i.product_id
                        inv_date = record.invoice_date or date.today().strftime(DT)
                        product = product.with_context(
                            lang=partner.lang,
                            partner=partner.id,
                            quantity=i.quantity,
                            date=inv_date,
                            pricelist=pricelist.id,
                            uom=i.product_uom_id.id,
                        )
                        product_context = dict(self.env.context, partner_id=record.partner_id.id,
                                               date=record.invoice_date,
                                               uom=i.product_uom_id.id)

                        price, rule_id = pricelist.with_context(product_context).get_product_price_rule(
                            i.product_id, i.quantity or 1.0, record.partner_id)
                        new_list_price, currency_id = i.with_context(product_context)._get_real_price_currency(product,
                                                                                                               rule_id,
                                                                                                               i.quantity,
                                                                                                               i.product_uom_id,
                                                                                                               pricelist.id)
                        discount = 0
                        if new_list_price != 0:
                            if pricelist.currency_id.id != currency_id:
                                # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                                new_list_price = self.env['res.currency'].browse(currency_id).with_context(
                                    product_context).compute(
                                    new_list_price, pricelist.currency_id)
                            discount += (new_list_price - price) / new_list_price * 100
                            if discount > 0:
                                i.discount = discount

                        i.update({
                            # 'move_id': record.id,
                            'product_id': i.product_id.id,
                            #'pricelist': pricelist.id,
                            'price_unit': i.price_unit,
                            'name': i.name,
                            'discount': i.discount,
                            'account_id': i.account_id,
                            'product_uom_id': i.product_uom_id.id,
                            #'sale_type': i.sale_type,
                            #'tax_ids': [(6, 0, i.product_id.taxes_id.ids)],
                            # 'batch_num': [(6, 0, i.batch_num.ids)],
                            # 'batch_no': [(6, 0, i.batch_no.ids)],
                            'lot_id': i.lot_id.id,

                        })


