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

        stock_moves = self.env['stock.move'].search(["|", ("location_id", "=", self.stock_location.id),
                                                     ("location_dest_id", "=", self.stock_location.id),
                                                     ("state", "=", "done"),
                                                     ("date", ">=", self.start_date), ("date", "<=", self.end_date)])

        stock_moves_groupedby_product = stock_moves.read_group(
            domain=["|", ("location_id", "=", self.stock_location.id),
                    ("location_dest_id", "=", self.stock_location.id),
                    ("state", "=", "done"),
                    ("date", "<=", self.end_date)],
            fields=['product_id', 'product_uom_qty', 'location_id', 'location_dest_id'],
            groupby=['product_id'])

        for stock_move in stock_moves_groupedby_product:
            product_id = stock_move['product_id'][0]
            product = self.env['product.product'].search([('id', '=', product_id)])
            outcome_qty_before = stock_moves.read_group(
                domain=[("location_id", "=", self.stock_location.id),
                        ("state", "=", "done"),
                        ("date", "<", self.start_date), ("product_id", "=", product_id)],
                fields=['product_id', 'product_uom_qty'],
                groupby=['product_id'])
            income_qty_before = stock_moves.read_group(
                domain=[("location_dest_id", "=", self.stock_location.id),
                        ("state", "=", "done"),
                        ("date", "<", self.start_date), ("product_id", "=", product_id)],
                fields=['product_id', 'product_uom_qty'],
                groupby=['product_id'])
            income_qty = stock_moves.read_group(
                domain=[("location_dest_id", "=", self.stock_location.id),
                        ("state", "=", "done"),
                        ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                        ("product_id", "=", product_id)],
                fields=['product_id', 'product_uom_qty'],
                groupby=['product_id'])
            outcome_qty = stock_moves.read_group(
                domain=[("location_id", "=", self.stock_location.id),
                        ("state", "=", "done"),
                        ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                        ("product_id", "=", product_id)],
                fields=['product_id', 'product_uom_qty'],
                groupby=['product_id'])
            in_qty = 0
            out_qty = 0
            outcomeblbefore = 0
            incomeblbefore = 0
            if (out_qty):
                out_qty = outcome_qty[0]['product_uom_qty']
            if (income_qty):
                in_qty = income_qty[0]['product_uom_qty']
            if outcome_qty_before:
                outcomeblbefore += outcome_qty_before[0]['product_uom_qty']
            if income_qty_before:
                incomeblbefore += income_qty_before[0]['product_uom_qty']
            startbl = incomeblbefore - outcomeblbefore
            endbl = startbl + in_qty - out_qty
            line_ids.append((0, 0, {
                'product_id': product.id,
                'start_balance': startbl,
                'income_quantity': in_qty,
                'outcome_quantity': out_qty,
                'end_balance': endbl
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


class StockProductionLotCost(models.Model):
    _inherit = 'stock.production.lot'

    cost = fields.Monetary('Unit Price', store=True, index=True)
    currency_id = fields.Many2one('res.currency', compute='_compute_value')

    @api.depends('company_id')
    def _compute_value(self):
        self.currency_id = self.env.company.currency_id
