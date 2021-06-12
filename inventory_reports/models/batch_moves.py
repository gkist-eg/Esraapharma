import base64

from datetime import datetime
from io import BytesIO
import xlsxwriter
from odoo import fields, models, api, _


class TotalInventoryWizard(models.TransientModel):
    _name = 'stock.batch.details.wizard'
    _description = 'Wizard that opens the stock Inventory by Location'

    file_name = fields.Char('File Name')
    mapping_report_file = fields.Binary('Mapping Report')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    start_date = fields.Datetime(string='From')
    end_date = fields.Datetime(string='To')
    type = fields.Selection([('sale', 'Can Be Sold'), ('purchase', 'Can Be Purchased')])

    def action_print_report(self):
        today = datetime.today().strftime('%Y-%m-%d')

        file_name = 'Batch_Details_' + self.warehouse_id.name + '_' + str(today) + '.xlsx'
        fp = BytesIO()

        workbook = xlsxwriter.Workbook(fp)
        heading_format = workbook.add_format({'align': 'center',
                                              'valign': 'vcenter',
                                              'font_color': 'blue_gray',
                                              'bold': True, 'size': 14})
        cell_text_format_n = workbook.add_format({'align': 'center', 'size': 9, 'bold': True,
                                                  'font_color': '#B22222',
                                                  })
        cell_text_format = workbook.add_format({'align': 'left',
                                                'size': 9,
                                                })

        cell_text_format.set_border()
        cell_text_format_new = workbook.add_format({'align': 'left',
                                                    'size': 9,
                                                    })
        cell_text_format_new.set_border()
        cell_number_format = workbook.add_format({'align': 'right',
                                                  'bold': False, 'size': 9,
                                                  'num_format': '#,###0.00'})
        column_heading_style2 = workbook.add_format({'font': 'right',
                                                     'bold': True, 'size': 9,
                                                     'num_format': '#,###0.00'})
        # cell_number_format.set_border()
        worksheet = workbook.add_worksheet(file_name)
        normal_num_bold = workbook.add_format({'bold': True, 'num_format': '#,###0.00', 'size': 9, })
        normal_num_bold.set_border()
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 25)
        worksheet.set_column('E:E', 25)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 20)
        worksheet.set_column('H:H', 20)
        worksheet.set_column('I:I', 20)
        worksheet.set_column('J:J', 20)
        worksheet.set_column('K:K', 20)
        worksheet.set_column('L:L', 20)
        worksheet.set_column('M:M', 20)
        worksheet.set_column('N:N', 20)
        report_head = 'Batch Details ( ' + self.warehouse_id.name + ' ' + str(self.start_date) + ' - ' + str(
            self.end_date) + ' )'
        worksheet.merge_range('A1:F1', report_head, heading_format)
        row = 2
        if self.type == 'sale':
            worksheet.write(1, 0, _('Product Code'), column_heading_style2)
            worksheet.write(1, 1, _('Product'), column_heading_style2)
            worksheet.write(1, 2, _('Batch'), column_heading_style2)
            worksheet.write(1, 3, _('Start Balance'), column_heading_style2)
            worksheet.write(1, 4, _('Production Receipts'), column_heading_style2)
            worksheet.write(1, 5, _('OutSale'), column_heading_style2)
            worksheet.write(1, 6, _('Out Transfer'), column_heading_style2)
            worksheet.write(1, 7, _('Sales Return'), column_heading_style2)
            worksheet.write(1, 8, _('Transfer Return'), column_heading_style2)
            worksheet.write(1, 9, _('out Adjust/Scrapp'), column_heading_style2)
            worksheet.write(1, 10, _('In Adjust'), column_heading_style2)
            worksheet.write(1, 11, _('End Balance'), column_heading_style2)
            stock_moves = self.env['stock.move.line']
            stock_moves_groupedby_product = stock_moves.read_group(
                domain=["|", ("location_id.warehouse_id", "=", self.warehouse_id.id),
                        ("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                        ("product_id.sale_ok", "=", True),
                        ("state", "=", "done"), ("lot_id", "!=", False), ("batch", "!=", False),
                        ("date", "<=", self.end_date)],
                fields=['batch', 'product_id'],
                groupby=['batch', 'product_id'], lazy=False)

            for stock_move in stock_moves_groupedby_product:
                lot_id = stock_move['batch']
                product = self.env['product.product'].search([('id', '=', stock_move['product_id'][0])])
                outcome_qty_before = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.warehouse_id", "!=", self.warehouse_id.id),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", "<", self.start_date), ("lot_id.ref", "=", lot_id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['batch'])
                income_qty_before = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_id.warehouse_id", "!=", self.warehouse_id.id),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", "<", self.start_date), ("lot_id.ref", "=", lot_id)],
                    fields=['lot_id', 'qty_done'],
                    groupby=['batch'])
                income_qty = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id), '|',
                            ("location_id.stock_usage", "=", 'production'), ("location_id.usage", "=", 'production'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("product_id", "=", product.id),
                            ("lot_id.ref", "=", lot_id)],
                    fields=['lot_id', 'qty_done'],
                    groupby=['batch'])
                outcome_sales = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.usage", "=", 'customer'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id.ref", "=", lot_id), ("product_id", "=", product.id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['batch'])
                outcome_adjusts = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.usage", "=", 'inventory'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id.ref", "=", lot_id), ("product_id", "=", product.id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['batch'])
                return_adjusts = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_id.usage", "=", 'inventory'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id.ref", "=", lot_id), ("product_id", "=", product.id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['batch'])
                return_sales = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_id.usage", "=", 'customer'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id.ref", "=", lot_id), ("product_id", "=", product.id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['batch'])
                outcome_transfer = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.warehouse_id", "!=", self.warehouse_id.id),
                            ("location_dest_id.usage", "=", 'internal'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id.ref", "=", lot_id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['batch'])
                return_transfers = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_id.warehouse_id", "!=", self.warehouse_id.id), '|',
                            ("location_dest_id.usage", "=", 'internal'),
                            ("location_dest_id.usage", "=", 'transit'),
                            ("location_id.usage", "=", 'internal'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id.ref", "=", lot_id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['batch'])
                outcome_transfer2 = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.usage", "=", 'transit'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id.ref", "=", lot_id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['batch'])
                in_qty = 0
                out = 0
                out_transfer = 0
                bl = 0
                return_sale = 0
                return_transfer = 0
                return_adjust = 0
                outcome_adjust = 0
                for outcome in outcome_sales:
                    out += outcome['qty_done']

                for outcome in outcome_transfer:
                    out_transfer += outcome['qty_done']
                for outcome in outcome_transfer2:
                    out_transfer += outcome['qty_done']

                for income in income_qty:
                    in_qty += income['qty_done']

                for l in outcome_adjusts:
                    outcome_adjust += l['qty_done']

                for r in return_adjusts:
                    return_adjust += r['qty_done']

                for outcomebefore in outcome_qty_before:
                    bl -= outcomebefore['qty_done']

                for incomebefore in income_qty_before:
                    bl += incomebefore['qty_done']

                for returnsale in return_sales:
                    return_sale += returnsale['qty_done']

                for returnsale in return_transfers:
                    return_transfer += returnsale['qty_done']

                endbl = bl + in_qty - out - out_transfer + return_sale + return_transfer + return_adjust - outcome_adjust

                worksheet.write(row, 0, product.default_code or '', cell_text_format_n)
                worksheet.write(row, 1, product.name or '', cell_text_format_n)
                worksheet.write(row, 2, stock_move['batch'] or '', cell_text_format)
                worksheet.write(row, 3, bl, cell_text_format)
                worksheet.write(row, 4, in_qty, cell_text_format)
                worksheet.write(row, 5, out, cell_text_format)
                worksheet.write(row, 6, out_transfer, cell_text_format)
                worksheet.write(row, 7, return_sale, cell_text_format)
                worksheet.write(row, 8, return_transfer, cell_text_format)
                worksheet.write(row, 9, outcome_adjust, cell_text_format)
                worksheet.write(row, 10, return_adjust, cell_text_format)
                worksheet.write(row, 11, endbl, cell_text_format)

                row += 1
            stock_moves_groupedby_product_list = stock_moves.read_group(
                domain=["|", ("location_id.warehouse_id", "=", self.warehouse_id.id),
                        ("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                        ("product_id.sale_ok", "=", True),
                        ("state", "=", "done"), ("lot_id", "!=", False), ("batch", "=", False),
                        ("date", "<=", self.end_date)],
                fields=['lot_id', 'product_id'],
                groupby=['lot_id', 'product_id'], lazy=False)

            for stock_move in stock_moves_groupedby_product_list:
                lot_id = stock_move['lot_id'][0]
                lot = self.env['stock.production.lot'].search([('id', '=', stock_move['lot_id'][0])])
                product = self.env['product.product'].search([('id', '=', stock_move['product_id'][0])])
                outcome_qty_before = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.warehouse_id", "!=", self.warehouse_id.id),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", "<", self.start_date), ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                income_qty_before = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_id.warehouse_id", "!=", self.warehouse_id.id),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", "<", self.start_date), ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done'],
                    groupby=['lot_id'])
                income_qty = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id), '|',
                            ("location_id.stock_usage", "=", 'production'), ("location_id.usage", "=", 'production'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("product_id", "=", product.id),
                            ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done'],
                    groupby=['lot_id'])
                outcome_sales = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.usage", "=", 'customer'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id), ("product_id", "=", product.id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                outcome_adjusts = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.usage", "=", 'inventory'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id), ("product_id", "=", product.id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                return_adjusts = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_id.usage", "=", 'inventory'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id), ("product_id", "=", product.id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                return_sales = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_id.usage", "=", 'customer'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id), ("product_id", "=", product.id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                outcome_transfer = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.warehouse_id", "!=", self.warehouse_id.id),
                            ("location_dest_id.usage", "=", 'internal'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                return_transfers = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_id.warehouse_id", "!=", self.warehouse_id.id), '|',
                            ("location_dest_id.usage", "=", 'internal'),
                            ("location_dest_id.usage", "=", 'transit'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                outcome_transfer2 = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.usage", "=", 'transit'),
                            ("state", "=", "done"), ("product_id", "=", product.id),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                in_qty = 0
                out = 0
                out_transfer = 0
                bl = 0
                return_sale = 0
                return_transfer = 0
                return_adjust = 0
                outcome_adjust = 0
                for outcome in outcome_sales:
                    out += outcome['qty_done']

                for outcome in outcome_transfer:
                    out_transfer += outcome['qty_done']
                for outcome in outcome_transfer2:
                    out_transfer += outcome['qty_done']

                for income in income_qty:
                    in_qty += income['qty_done']

                for l in outcome_adjusts:
                    outcome_adjust += l['qty_done']

                for r in return_adjusts:
                    return_adjust += r['qty_done']

                for outcomebefore in outcome_qty_before:
                    bl -= outcomebefore['qty_done']

                for incomebefore in income_qty_before:
                    bl += incomebefore['qty_done']

                for returnsale in return_sales:
                    return_sale += returnsale['qty_done']

                for returnsale in return_transfers:
                    return_transfer += returnsale['qty_done']

                endbl = bl + in_qty - out - out_transfer + return_sale + return_transfer + return_adjust - outcome_adjust

                worksheet.write(row, 0, product.default_code or '', cell_text_format_n)
                worksheet.write(row, 1, product.name or '', cell_text_format_n)
                worksheet.write(row, 2, lot.name or '', cell_text_format)
                worksheet.write(row, 3, bl, cell_text_format)
                worksheet.write(row, 4, in_qty, cell_text_format)
                worksheet.write(row, 5, out, cell_text_format)
                worksheet.write(row, 6, out_transfer, cell_text_format)
                worksheet.write(row, 7, return_sale, cell_text_format)
                worksheet.write(row, 8, return_transfer, cell_text_format)
                worksheet.write(row, 9, outcome_adjust, cell_text_format)
                worksheet.write(row, 10, return_adjust, cell_text_format)
                worksheet.write(row, 11, endbl, cell_text_format)

                row += 1
        if self.type == 'purchase':
            worksheet.write(1, 0, _('Product Code'), column_heading_style2)
            worksheet.write(1, 1, _('Product'), column_heading_style2)
            worksheet.write(1, 2, _('Lot'), column_heading_style2)
            worksheet.write(1, 3, _('Start Balance'), column_heading_style2)
            worksheet.write(1, 4, _('Receipts'), column_heading_style2)
            worksheet.write(1, 5, _('Requests'), column_heading_style2)
            worksheet.write(1, 6, _('Poduction'), column_heading_style2)
            worksheet.write(1, 8, _('Production Return'), column_heading_style2)
            worksheet.write(1, 7, _('Request Return'), column_heading_style2)
            worksheet.write(1, 9, _('In Adjustment'), column_heading_style2)
            worksheet.write(1, 10, _('Out Adjustment'), column_heading_style2)
            worksheet.write(1, 11, _('Receipts Return'), column_heading_style2)
            worksheet.write(1, 12, _('End Balance'), column_heading_style2)
            stock_moves = self.env['stock.move.line']
            stock_moves_groupedby_product = stock_moves.read_group(
                domain=["|", ("location_id.warehouse_id", "=", self.warehouse_id.id),
                        ("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                        ("product_id.purchase_ok", "=", True),
                        ("state", "=", "done"), ("lot_id", "!=", False),
                        ("date", "<=", self.end_date)],
                fields=['lot_id', 'product_id'],
                groupby=['lot_id'])

            for stock_move in stock_moves_groupedby_product:
                lot_id = stock_move['lot_id'][0]
                lot = self.env['stock.production.lot'].search([('id', '=', stock_move['lot_id'][0])])
                outcome_qty_before = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id), '|',
                            ("location_dest_id.warehouse_id", "!=", self.warehouse_id.id),
                            ("location_dest_id.usage", "in", ('customer', 'inventory')),
                            ("state", "=", "done"),
                            ("date", "<", self.start_date), ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                income_qty_before = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id), '|',
                            ("location_id.warehouse_id", "!=", self.warehouse_id.id),
                            ("location_id.usage", "in", ('vendor', 'inventory')),
                            ("state", "=", "done"),
                            ("date", "<", self.start_date), ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done'],
                    groupby=['lot_id'])
                income_qty = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_id.stock_usage", "=", 'vendor'),
                            ("state", "=", "done"),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done'],
                    groupby=['lot_id'])
                vendor_return_list = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.stock_usage", "=", 'vendor'),
                            ("state", "=", "done"),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done'],
                    groupby=['lot_id'])
                outcome_request = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.usage", "=", 'customer'),
                            ("state", "=", "done"),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id), ],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                return_request = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_id.usage", "=", 'customer'),
                            ("state", "=", "done"),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id), ],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                out_adjusts = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_id.usage", "=", 'inventory'),
                            ("state", "=", "done"),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id), ],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                in_adjusts = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.usage", "=", 'inventory'),
                            ("state", "=", "done"),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id), ],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                outcome_production = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_dest_id.usage", "=", 'production'),
                            ("state", "=", "done"),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                return_production_list = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                            ("location_id.usage", "=", 'production'),
                            ("state", "=", "done"),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done'],
                    groupby=['lot_id'])
                outcome_productions = stock_moves.read_group(
                    domain=[("location_id.warehouse_id", "=", self.warehouse_id.id), '|',
                            ("location_dest_id.usage", "=", 'internal'),
                            ("location_dest_id.stock_usage", "=", 'production'),
                            ("state", "=", "done"),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])
                return_productions = stock_moves.read_group(
                    domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id), '|',
                            ("location_id.usage", "=", 'internal'),
                            ("location_id.stock_usage", "=", 'production'),
                            ("state", "=", "done"),
                            ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                            ("lot_id", "=", lot_id)],
                    fields=['lot_id', 'qty_done', ],
                    groupby=['lot_id'])

                in_qty = 0
                out = 0
                receipt = 0
                production = 0
                bl = 0
                return_sale = 0
                return_production = 0
                in_adjust = 0
                out_adjust = 0
                vendor_return = 0
                for outcome in outcome_request:
                    out += outcome['qty_done']

                for outcome in outcome_production:
                    production += outcome['qty_done']
                for outcome in outcome_productions:
                    production += outcome['qty_done']

                for income in income_qty:
                    in_qty += income['qty_done']

                for outcomebefore in outcome_qty_before:
                    bl -= outcomebefore['qty_done']

                for incomebefore in income_qty_before:
                    bl += incomebefore['qty_done']

                for returnsale in return_request:
                    return_sale += returnsale['qty_done']
                for returnsale in return_productions:
                    return_production += returnsale['qty_done']
                for returnsale in return_production_list:
                    return_production += returnsale['qty_done']

                for in_adjus in in_adjusts:
                    in_adjust += in_adjus['qty_done']

                for in_adjus in out_adjusts:
                    out_adjust += in_adjus['qty_done']

                for vendor in vendor_return_list:
                    vendor_return += vendor['qty_done']

                endbl = bl + in_qty - out - production + return_sale + return_production  + in_adjust - out_adjust - vendor_return

                worksheet.write(row, 0, lot.product_id.default_code or '', cell_text_format_n)
                worksheet.write(row, 1, lot.product_id.name or '', cell_text_format_n)
                worksheet.write(row, 2, lot.name or '', cell_text_format)
                worksheet.write(row, 3, bl, cell_text_format)
                worksheet.write(row, 4, in_qty, cell_text_format)
                worksheet.write(row, 5, out, cell_text_format)
                worksheet.write(row, 6, production, cell_text_format)
                worksheet.write(row, 7, return_sale, cell_text_format)
                worksheet.write(row, 8, return_production, cell_text_format)
                worksheet.write(row, 9, in_adjust, cell_text_format)
                worksheet.write(row, 10, out_adjust, cell_text_format)
                worksheet.write(row, 11, vendor_return, cell_text_format)
                worksheet.write(row, 12, endbl, cell_text_format)

                row += 1
        workbook.close()
        file_download = base64.b64encode(fp.getvalue())

        fp.close()
        self.mapping_report_file = file_download
        self.file_name = file_name
        return {
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'stock.batch.details.wizard',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }
