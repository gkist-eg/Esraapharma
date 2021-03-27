from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round, float_compare
from datetime import date

from odoo import fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DT, itemgetter, groupby


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    allow_return = fields.Boolean(
        string="Return Operation",
    )


class PickingModule(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()
        self.create_invoice()
        return res

    def create_invoice(self):
        """This is the function for creating customer invoice
        from the picking"""
        for picking_id in self:
            current_user = self.env.uid

            if picking_id.picking_type_id.code == 'incoming' and picking_id.picking_type_id.allow_return:
                invoice_line_list = []
                for move in picking_id.move_line_ids:
                    vals = (0, 0, {
                        'name': move.description_picking,
                        'product_id': move.product_id.id,
                        'price_unit': move.product_id.lst_price,
                        'lot_id': move.lot_id.id,
                        'account_id': move.product_id.property_account_income_id.id if move.product_id.property_account_income_id
                        else move.product_id.categ_id.property_account_income_categ_id.id,
                        'tax_ids': [(6, 0, [tax.id for tax in move.product_id.taxes_id])],
                        'quantity': move.qty_done,
                    })
                    invoice_line_list.append(vals)
                invoice = picking_id.sudo().env['account.move'].create({
                        'move_type': 'out_refund',
                        'invoice_origin': picking_id.name,
                        'invoice_user_id': current_user,
                        'narration': picking_id.name,
                        'partner_id': picking_id.partner_id.id,
                        'currency_id': picking_id.env.user.company_id.currency_id.id,
                        'payment_reference': picking_id.name,
                        'picking_id': picking_id.id,
                        'invoice_line_ids': invoice_line_list
                    })


class AccountInvoiceRefund(models.Model):
    _inherit = 'account.move'

    picking_id = fields.Many2one('stock.picking', string='Picking')


class AcountInvoiceLine(models.Model):
    _inherit = 'account.move.line'
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        domain="[('product_id', '=', product_id)]", check_company=True)
