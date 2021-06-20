# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductQuantityWizard(models.TransientModel):
    _name = 'product.quantity.wizard'
    _description = 'Wizard that get the Product Quantity Input and Output by Location'

    # stock_warehouse = fields.Many2one('stock.warehouse', string='Warehouse', required=True)

    # stock_location = fields.Many2one('stock.location', string='Location', required=True)

    # @api.onchange('stock_warehouse')
    # def _get_locations_warehouse(self):
    #     stock_warehouse = self.stock_warehouse.view_location_id
    #     stock_locations = self.env["stock.location"].search([("location_id", '=', stock_warehouse.id)])
    #     return {'domain': {'stock_location': [('id', 'in', stock_locations.ids)]}}

    def _get_user_locations(self):
        user_locations = self.env.user.stock_location_ids
        return [('id', 'in', user_locations.ids)]

    stock_location = fields.Many2one('stock.location', string='Location', required=True,
                                     domain=_get_user_locations)

    start_date = fields.Date(string='From', required=True)
    end_date = fields.Date(string='To', required=True)

    line_ids = fields.One2many('product.quantity.wizard.lines', 'wizard_id', required=True)

    total_start = fields.Float()
    total_end = fields.Float()
    total_in = fields.Float()
    total_out = fields.Float()

    def get_stock_quantity(self):

        line_ids = []
        total_out = 0
        total_start = 0
        total_in = 0
        total_end = 0

        stock_moves = self.env['stock.move.line']

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
            if (outcome_qty):
                for outcome in outcome_qty:
                    out_qty += outcome['qty_done']
                total_out += out_qty
            if (income_qty):
                for income in income_qty:
                    in_qty += income['qty_done']
                total_in += in_qty
            if outcome_qty_before:
                for outcomebefore in outcome_qty_before:
                    outcomeblbefore += outcomebefore['qty_done']
            if income_qty_before:
                for incomebefore in income_qty_before:
                    incomeblbefore += incomebefore['qty_done']

            startbl = incomeblbefore - outcomeblbefore
            endbl = startbl + in_qty - out_qty
            total_start += startbl
            total_end += endbl

            line_ids.append((0, 0, {
                'product_id': product.id,
                'start_balance': startbl,
                'income_quantity': in_qty,
                'outcome_quantity': out_qty,
                'end_balance': endbl,
            }))

        self.write({'line_ids': line_ids})
        context = {
            'lang': 'en_US',
            'active_ids': [self.id],
        }

        self.total_end = total_end
        self.total_start = total_start
        self.total_in = total_in
        self.total_out = total_out

        return {
            'context': context,
            'data': None,
            'report_name': 'product_quantity_report.product_quantity_report_template',
            'report_file': 'product_quantity_report.product_quantity_report_template',
            'report_type': 'qweb-html',
            'type': 'ir.actions.report',
            'name': 'Product Quantity Report',
            'flags': {'action_buttons': True},
            'model': 'product.quantity.wizard',
        }


class ProductQuantityWizardLines(models.TransientModel):
    _name = 'product.quantity.wizard.lines'
    _description = 'Product Quantity Wizard Lines'

    wizard_id = fields.Many2one('product.quantity.wizard')
    product_id = fields.Many2one('product.product')
    start_balance = fields.Float()
    income_quantity = fields.Float()
    outcome_quantity = fields.Float()
    end_balance = fields.Float()
