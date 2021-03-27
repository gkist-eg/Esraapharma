from odoo import models, fields, api, _, tools
import datetime
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_repr, float_round


class Locations(models.Model):
    _inherit = 'stock.location'
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', store=True)


class StockMove(models.Model):
    _inherit = 'stock.move'

    restrict_lot_id = fields.Many2one(
        'stock.production.lot', string='Restricted Lot Numbers', readonly=False)

    def _get_accounting_data_for_valuation(self):
        """ Return the accounts and journal to use to post Journal Entries for
        the real-time valuation of the quant. """
        self.ensure_one()
        self = self.with_company(self.company_id)
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()

        if self.location_id.valuation_out_account_id:
            acc_src = self.location_id.valuation_out_account_id.id
        else:
            acc_src = accounts_data['stock_input'].id

        if self.location_dest_id.valuation_in_account_id:
            acc_dest = self.location_dest_id.valuation_in_account_id.id
        else:
            acc_dest = accounts_data['stock_output'].id
        if self.picking_id:
            if self.picking_id.partner_id:
                for employee in self.env['hr.employee'].search(
                        [('user_id.partner_id', '=', self.picking_id.partner_id.id)]):
                    if employee.department_id and employee.department_id.account_id and self.picking_id.picking_type_id.code == 'outgoing':
                        acc_dest = employee.department_id.account_id.id
                    if employee.department_id and employee.department_id.account_id and self.picking_id.picking_type_id.code == 'incoming':
                        acc_src = employee.department_id.account_id.id
        acc_valuation = accounts_data.get('stock_valuation', False)
        if acc_valuation:
            acc_valuation = acc_valuation.id
        if not accounts_data.get('stock_journal', False):
            raise UserError(_(
                'You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts.'))
        if not acc_src:
            raise UserError(_(
                'Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (
                                self.product_id.display_name))
        if not acc_dest:
            raise UserError(_(
                'Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (
                                self.product_id.display_name))
        if not acc_valuation:
            raise UserError(_(
                'You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
        journal_id = accounts_data['stock_journal'].id
        return journal_id, acc_src, acc_dest, acc_valuation


class ResUsers(models.Model):
    _inherit = 'res.users'
    multi_locations = fields.Many2many('stock.location',
                                       'location_item_request',
                                       'user_id',
                                       'location_id', string='Item Request Location')


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        res = super()._action_done()
        for picking2 in self:
            for item in self.env['item.request'].search([('name', '=', picking2.origin)]):
                item.line_ids._compute_qty()
                item.state = 'done'
        return res


class Department(models.Model):
    _inherit = "hr.department"

    account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account (Outgoing)',
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
        help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products being moved out of this location "
             "and into an internal location, instead of the generic Stock Output Account set on the product. "
             "This has no effect for internal locations.")
