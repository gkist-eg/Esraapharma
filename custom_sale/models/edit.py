from datetime import date
from odoo import api, models, _
from odoo import fields



class ResUser(models.Model):
    _inherit = 'res.users'

    multi_warehouse = fields.Many2many(
        'stock.warehouse', string='Warehouse',
    )


class Partner(models.Model):
    _inherit = 'res.partner'

    limit_credit = fields.Float(string='Limit Of Credit', store=True)

class MOvex(models.Model):
    _inherit = 'account.move'

    def compute_cash(self):
        cash = 0

        order = self.env['sale.order'].search([('name', '=', self.invoice_origin)])
        if order:
            for x in order:
                cash = x.cash_discount_sale

        return cash


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    _sql_constraints = [
        ('name', 'UNIQUE (name,company_id)',
         'Sales Order Number is unique')]

    credit = fields.Monetary(string='Total Receivable', help="Total amount this customer owes you.",
                             compute='get_credit')

    @api.onchange('partner_id')
    def get_credit(self):
        for order in self:
            if order.partner_id:
                order.credit = order.partner_id.credit
            else:
                order.credit = 0

    # @api.model
    # def get_warehouse(self):
    #     for record in self:
    #         w = []
    #         for ware in self.env.user.multi_warehouse:
    #                 w.append(ware.id)
    #         return {('id', 'in', w)}

    @api.model
    def _getUserwarehous(self):
        return [('id', 'in', self.env.user.multi_warehouse.ids),
                ]

    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        required=True, domain=_getUserwarehous)
    warehouse = fields.Many2one(
        'stock.warehouse', string='no',
        domain=_getUserwarehous)

    @api.onchange('partner_id')
    def onchange_partner_id_warning(self):
        res = super(SaleOrder, self).onchange_partner_id_warning()
        for record in self:
            warning = {}
            title = False
            message = False
            partner = record.partner_id
            if partner.limit_credit != 0.0:
                if partner.limit_credit == partner.credit:
                    title = ("Warning: %s") % ("The Limit for %s") % partner.name
                    message = partner.limit_credit
                    warning = {
                        'title': title,
                        'message': message,
                    }
                if partner.limit_credit < partner.credit:
                    title = ("Block: %s") % ("The Limit for %s") % partner.name
                    message = partner.limit_credit
                    warning = {
                        'title': title,
                        'message': message,
                    }
                    self.update({'partner_id': False, 'partner_invoice_id': False, 'partner_shipping_id': False,
                                 'pricelist_id': False, 'delivery_rep': False, 'sales_rep': False, 'office': False,
                                 'cash_discount': False, 'dist_discount': False,
                                 'payment_term_id': False})
                    return {'warning': warning}
            if warning:
                return {'warning': warning}
        return res

    # name = fields.Char(string='Order Reference', required=True, copy=False,
    #              index=True, default=lambda self: _(''),
    #              states={'draft': [('readonly', False)], 'sent': [('readonly', False)],
    #                     'approve': [('readonly', False)]})


class Warehouses(models.Model):
    _inherit = 'stock.warehouse'

    sale_store = fields.Boolean(
        string="On Sale Store",
        store=True)
