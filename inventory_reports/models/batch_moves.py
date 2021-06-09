import base64
import os
from datetime import datetime
from io import BytesIO
from odoo.tools.misc import xlwt
import xlsxwriter
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from xlsxwriter.utility import xl_rowcol_to_cell


class TotalInventoryWizard(models.TransientModel):
    _name = 'stock.batch.details.wizard'
    _description = 'Wizard that opens the stock Inventory by Location'

    file_name = fields.Char('File Name')
    mapping_report_file = fields.Binary('Mapping Report')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    start_date = fields.Datetime(string='From')
    end_date = fields.Datetime(string='To')

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
        worksheet.write(1, 0, _('Product Code'), column_heading_style2)
        worksheet.write(1, 1, _('Product'), column_heading_style2)
        worksheet.write(1, 2, _('Batch'), column_heading_style2)
        worksheet.write(1, 3, _('Start Balance'), column_heading_style2)
        worksheet.write(1, 4, _('Income'), column_heading_style2)
        worksheet.write(1, 5, _('OutSale'), column_heading_style2)
        worksheet.write(1, 6, _('Out Transfer'), column_heading_style2)
        worksheet.write(1, 7, _('End Balace'), column_heading_style2)
        stock_moves = self.env['stock.move.line']
        stock_moves_groupedby_product = stock_moves.read_group(
            domain=["|", ("location_id.warehouse_id", "=", self.warehouse_id.id),
                    ("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                    ("state", "=", "done"), ("lot_id", "!=", False),
                    ("date", "<=", self.end_date)],
            fields=['batch', 'product_id'],
            groupby=['batch', 'product_id'], lazy=False)

        for stock_move in stock_moves_groupedby_product:
            lot_id = stock_move['batch']
            product = self.env['product.product'].search([('id', '=',  stock_move['product_id'][0])])
            outcome_qty_before = stock_moves.read_group(
                domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                        ("state", "=", "done"), ("product_id", "=", product.id),
                        ("date", "<", self.start_date), ("lot_id.ref", "=", lot_id)],
                fields=['lot_id', 'qty_done', ],
                groupby=['batch'])
            income_qty_before = stock_moves.read_group(
                domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                        ("state", "=", "done"), ("product_id", "=", product.id),
                        ("date", "<", self.start_date), ("lot_id.ref", "=", lot_id)],
                fields=['lot_id', 'qty_done'],
                groupby=['batch'])
            income_qty = stock_moves.read_group(
                domain=[("location_dest_id.warehouse_id", "=", self.warehouse_id.id),
                        ("state", "=", "done"), ("product_id", "=", product.id),
                        ("date", ">=", self.start_date), ("date", "<=", self.end_date), ("product_id", "=", product.id),
                        ("lot_id.ref", "=", lot_id)],
                fields=['lot_id', 'qty_done'],
                groupby=['batch'])
            outcome_sales = stock_moves.read_group(
                domain=[("location_id.warehouse_id", "=", self.warehouse_id.id),
                        ("location_dest_id.usage", "=", 'customer'),
                        ("state", "=", "done"), ("product_id", "=", product.id),
                        ("date", ">=", self.start_date), ("date", "<=", self.end_date),
                        ("lot_id.ref", "=", lot_id),("product_id", "=", product.id)],
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
            in_qty = 0
            out = 0
            out_transfer = 0
            bl = 0
            production_in = 0
            for outcome in outcome_sales:
                out += outcome['qty_done']

            for outcome in outcome_transfer:
                out_transfer += outcome['qty_done']

            for income in income_qty:
                in_qty += income['qty_done']

            for outcomebefore in outcome_qty_before:
                bl -= outcomebefore['qty_done']

            for incomebefore in income_qty_before:
                bl += incomebefore['qty_done']

            endbl = bl + in_qty - out

            worksheet.write(row, 0, product.default_code or '', cell_text_format_n)
            worksheet.write(row, 1, product.name or '', cell_text_format_n)
            worksheet.write(row, 2, stock_move['batch'] or '', cell_text_format)
            worksheet.write(row, 3, bl or '', cell_text_format)
            worksheet.write(row, 4, in_qty or '', cell_text_format)
            worksheet.write(row, 5, out or '', cell_text_format)
            worksheet.write(row, 6, out_transfer or '', cell_text_format)
            worksheet.write(row, 7, endbl or '', cell_text_format)
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
