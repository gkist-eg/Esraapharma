# -*- coding: utf-8 -*-
from odoo import models, fields, api


# class TotalInventoryWizard(models.TransientModel):
#     _name = 'total.inventory.wizard'
#
#     stock_location = fields.Many2one('stock.location', string='Stock Location')
#     start_date = fields.Datetime(string='From')
#     end_date = fields.Datetime(string='To')
#
#     def get_stock_quantity(self):
#         stock_moves = self.env['stock.move'].search(["|", ("location_id", "=", self.stock_location.id),
#                                                      ("location_dest_id", "=", self.stock_location.id),
#                                                      ("state", "=", "done"),
#                                                      ("date", ">=", self.start_date), ("date", "<=", self.end_date)])
#
#         stock_moves_groupedby_product = stock_moves.read_group(
#             domain=["|", ("location_id", "=", self.stock_location.id),
#                     ("location_dest_id", "=", self.stock_location.id),
#                     ("state", "=", "done"),
#                     ("date", "<=", self.end_date)],
#             fields=['product_id', 'product_uom_qty', 'location_id', 'location_dest_id'],
#             groupby=['product_id'])
#
#         stock_moves_list = []
#
#         for stock_move in stock_moves_groupedby_product:
#             product_id = stock_move['product_id'][0]
#             product = self.env['product.product'].search([('id', '=', product_id)])
#             outcome_qty_before = stock_moves.read_group(
#                 domain=[("location_id", "=", self.stock_location.id),
#                         ("state", "=", "done"),
#                         ("date", "<", self.start_date), ("product_id", "=", product_id)],
#                 fields=['product_id', 'product_uom_qty'],
#                 groupby=['product_id'])
#             income_qty_before = stock_moves.read_group(
#                 domain=[("location_dest_id", "=", self.stock_location.id),
#                         ("state", "=", "done"),
#                         ("date", "<", self.start_date), ("product_id", "=", product_id)],
#                 fields=['product_id', 'product_uom_qty'],
#                 groupby=['product_id'])
#             income_qty = stock_moves.read_group(
#                 domain=[("location_dest_id", "=", self.stock_location.id),
#                         ("state", "=", "done"),
#                         ("date", ">=", self.start_date), ("date", "<=", self.end_date),
#                         ("product_id", "=", product_id)],
#                 fields=['product_id', 'product_uom_qty'],
#                 groupby=['product_id'])
#             outcome_qty = stock_moves.read_group(
#                 domain=[("location_id", "=", self.stock_location.id),
#                         ("state", "=", "done"),
#                         ("date", ">=", self.start_date), ("date", "<=", self.end_date),
#                         ("product_id", "=", product_id)],
#                 fields=['product_id', 'product_uom_qty'],
#                 groupby=['product_id'])
#             in_qty = 0
#             out_qty = 0
#             outcomeblbefore = 0
#             incomeblbefore = 0
#             if (out_qty):
#                 out_qty = outcome_qty[0]['product_uom_qty']
#             if (income_qty):
#                 in_qty = income_qty[0]['product_uom_qty']
#             if outcome_qty_before:
#                 outcomeblbefore += outcome_qty_before[0]['product_uom_qty']
#             if income_qty_before:
#                 incomeblbefore += income_qty_before[0]['product_uom_qty']
#             startbl = incomeblbefore - outcomeblbefore
#             endbl = startbl + in_qty - out_qty
#             vals = {
#                 'product_id': product.default_code,
#                 'product_name': product.name,
#                 'start_balance': startbl,
#                 'income_quantity': in_qty,
#                 'outcome_quantity': out_qty,
#                 'end_balance': endbl
#             }
#             stock_moves_list.append(vals)
#             data = {
#                 'model': 'total.inventory.wizard',
#                 'form': self.read(),
#             }
#             docs = [{
#                 'stock_location': self.stock_location.display_name,
#                 'start_date': self.start_date,
#                 'end_date': self.end_date
#             }]
#             context = {
#                 'lang': 'en_US',
#                 'active_ids': [self.id],
#             }
#
#         data['stock_moves'] = stock_moves_list
#         data['values'] = docs
#         return {
#             'context': context,
#             'data': data,
#             'report_name': 'total_inventory_report.total_inventory_report_template',
#             'report_file': 'total_inventory_report.total_inventory_report_template',
#             'report_type': 'qweb-html',
#             'type': 'ir.actions.report',
#             'name': 'Total Inventory Report',
#             'flags': {'action_buttons': True},
#             'model': 'total.inventory.wizard',
#         }

class TotalInventoryWizard(models.TransientModel):
    _name = 'total.inventory.wizard'
    _description = 'Wizard that opens the stock Inventory by Location'

    stock_location = fields.Many2one('stock.location', string='Stock Location')
    start_date = fields.Datetime(string='From')
    end_date = fields.Datetime(string='To')

    line_ids = fields.One2many('total.inventory.wizard.lines', 'wizard_id', required=True, ondelete='cascade')

    def get_stock_quantity(self):

        line_ids = []

        stock_moves = self.env['stock.move.line'].search(["|", ("location_id", "=", self.stock_location.id),
                                                          ("location_dest_id", "=", self.stock_location.id),
                                                          ("state", "=", "done"),
                                                          ("date", ">=", self.start_date),
                                                          ("date", "<=", self.end_date)])

        stock_moves_groupedby_product = stock_moves.read_group(
            domain=["|", ("location_id", "=", self.stock_location.id),
                    ("location_dest_id", "=", self.stock_location.id),
                    ("state", "=", "done"),
                    ("date", "<=", self.end_date)],
            fields=['product_id', 'qty_done', 'location_id', 'location_dest_id'],
            groupby=['product_id'])

        for stock_move in stock_moves_groupedby_product:
            product_id = stock_move['product_id'][0]
            product = self.env['product.product'].search([('id', '=', product_id)])
            outcome_qty_before = stock_moves.read_group(
                domain=[("location_id", "=", self.stock_location.id),
                        ("state", "=", "done"),
                        ("date", "<", self.start_date), ("product_id", "=", product_id)],
                fields=['product_id', 'qty_done', ],
                groupby=['lot_id'])
            income_qty_before = stock_moves.read_group(
                domain=[("location_dest_id", "=", self.stock_location.id),
                        ("state", "=", "done"),
                        ("date", "<", self.start_date), ("product_id", "=", product_id)],
                fields=['product_id', 'qty_done', 'lot_id'],
                groupby=['lot_id'])
            income_qty = stock_moves.read_group(
                domain=[("location_dest_id", "=", self.stock_location.id),
                        ("state", "=", "done"),
                        ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                        ("product_id", "=", product_id)],
                fields=['product_id', 'lot_id', 'qty_done'],
                groupby=['lot_id'])
            outcome_qty = stock_moves.read_group(
                domain=[("location_id", "=", self.stock_location.id),
                        ("state", "=", "done"),
                        ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                        ("product_id", "=", product_id)],
                fields=['lot_id', 'product_id', 'qty_done', ],
                groupby=['lot_id'])
            in_qty = 0
            out_qty = 0
            outcomeblbefore = 0
            incomeblbefore = 0
            start_val = 0
            in_val = 0
            out_val = 0
            end_val = 0
            if (outcome_qty):
                for outcome in outcome_qty:
                    out_qty += outcome['qty_done']
                    if outcome['lot_id']:
                        lot = self.env['stock.production.lot'].search([('id', '=', outcome['lot_id'][0])])
                        out_val += outcome['qty_done'] * lot.cost
                        print(len(outcome))
                        print(outcome)
                    # else:
                    #     out_val += ['qty_done']
            if (income_qty):
                for income in income_qty:
                    in_qty += income['qty_done']
                    if income['lot_id']:
                        lot = self.env['stock.production.lot'].search([('id', '=', income['lot_id'][0])])
                        in_val += income['qty_done'] * lot.cost
                    # else:
                    #     in_val += ['qty_done'] * product.standard_price
            if outcome_qty_before:
                for outcomebefore in outcome_qty_before:
                    outcomeblbefore += outcomebefore['qty_done']
                    if outcomebefore['lot_id']:
                        lot = self.env['stock.production.lot'].search([('id', '=', outcomebefore['lot_id'])])
                        outcomeblbefore += outcomebefore['qty_done'] * lot.cost
                    # else:
                    #     outcomeblbefore += ['qty_done'] * product.standard_price
            if income_qty_before:
                for incomebefore in income_qty_before:
                    incomeblbefore += incomebefore['qty_done']
                    if incomebefore['lot_id']:
                        lot = self.env['stock.production.lot'].search([('id', '=', incomeblbefore['lot_id'][0])])
                        incomeblbefore += incomeblbefore['qty_done'] * lot.cost
                    # else:
                    #     incomeblbefore += ['qty_done'] * product.standard_price
            startbl = incomeblbefore - outcomeblbefore
            endbl = startbl + in_qty - out_qty
            line_ids.append((0, 0, {
                'product_id': product.id,
                'start_balance': startbl,
                'income_quantity': in_qty,
                'outcome_quantity': out_qty,
                'end_balance': endbl,
                'start_val': start_val,
                'in_val': in_val,
                'out_val': out_val,
                'end_val': end_val
            }))
        self.write({'line_ids': line_ids})
        context = {
            'lang': 'en_US',
            'active_ids': [self.id],
        }

        return {
            'context': context,
            'data': None,
            'report_name': 'total_inventory_report.total_inventory_report_template',
            'report_file': 'total_inventory_report.total_inventory_report_template',
            'report_type': 'qweb-html',
            'type': 'ir.actions.report',
            'name': 'Total Inventory Report',
            'flags': {'action_buttons': True},
            'model': 'total.inventory.wizard',
        }


class TotalInventoryWizardLines(models.TransientModel):
    _name = 'total.inventory.wizard.lines'

    wizard_id = fields.Many2one('total.inventory.wizard')
    product_id = fields.Many2one('product.product')
    start_balance = fields.Float()
    income_quantity = fields.Float()
    outcome_quantity = fields.Float()
    end_balance = fields.Float()
    start_val = fields.Float()
    in_val = fields.Float()
    out_val = fields.Float()
    end_val = fields.Float()


class StockProductionLotCost(models.Model):
    _inherit = 'stock.production.lot'

    cost = fields.Monetary('Unit Price', store=True, index=True)
    currency_id = fields.Many2one('res.currency', compute='_compute_value')

    @api.depends('company_id')
    def _compute_value(self):
        self.currency_id = self.env.company.currency_id
