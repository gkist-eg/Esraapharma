from odoo import models


class PartnerXlsx(models.AbstractModel):
    _name = 'report.custom_sale.report_invoice'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        format = workbook.add_format({'font_size': 14, 'align': 'vcenter', })
        format1 = workbook.add_format({'font_size': 13, 'align': 'vcenter','font_color':'red'})
        format2 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format3 = workbook.add_format({'font_size': 9, 'align': 'vcenter','font_color':'red'})
        sheet = workbook.add_worksheet('x')
        invoice_number = 'CV' + lines.serial_name
        customer = 'Customer:' + lines.partner_id.name
        invoice_date = 'Invoice Date:' + str(lines.invoice_date)
        sheet.set_column(0, 0, 30)
        sheet.set_column(10, 2, 10)
        sheet.set_column(10, 1, 10)

        sheet.insert_image(1,0, lines.company_id.logo, {'x_offset': 15, 'y_offset': 10})
        sheet.write(2, 0, lines.company_id.name, format)
        sheet.write(3, 0, lines.company_id.street, format)
        sheet.write(5, 0, invoice_number, format)
        sheet.write(6, 0, customer, format)
        sheet.write(7, 0, invoice_date, format)
        sheet.write(10, 0, 'Description', format1)
        sheet.write(10, 1, 'Unit', format1)
        sheet.write(10, 2, 'Quantity', format1)
        sheet.write(10, 3, 'C.Price', format1)
        sheet.write(10, 4, 'B.Price', format1)
        sheet.write(10, 5, 'Amount', format1)
        sheet.write(10, 6, ' Batch No', format1)
        x = 0
        for l in lines.invoice_line_ids:
            x += 1
            sheet.write(10 + x, 0, l.name, format2)
            sheet.write(10 + x, 1, l.product_uom_id.name, format2)
            sheet.write(10 + x, 2, l.quantity, format2)
            sheet.write(10 + x, 3, l.publicprice, format2)
            if lines.partner_id.categ_id.category_type != 'store':
                sheet.write(10 + x, 4, l.price_unit, format2)
            else:
                sheet.write(10 + x, 4, l.store_price, format2)
            sheet.write(10 + x, 5, l.price_subtotal, format2)
            sheet.write(10 + x, 6, l.batch_no, format2)

            total_q = 'Total Quantity : ' + str(lines.tot_qty)
            sheet.write(11+x, 0,'', format1)
            sheet.write(12+x, 0,total_q, format1)
        sheet.write(13 + x, 0, '', format1)

        sheet.write(14 + x, 0, 'Total Amount', format3)
        sheet.write(14 + x, 1, 'SubTotal', format3)
        sheet.write(14 + x, 2, 'Taxes', format3)

        sheet.write(15 + x, 0, lines.amount_total, format2)
        sheet.write(15 + x, 1, lines.amount_untaxed, format2)
        sheet.write(15 + x, 2, lines.amount_tax, format2)

        sheet.write(16 + x, 0, 'Freight', format3)
        sheet.write(16 + x, 1, 'Items Discount Value', format3)
        sheet.write(16 + x, 2, 'Discount Invoice Value', format3)
        sheet.write(16 + x, 3, 'Distributor Discount', format3)
        sheet.write(16 + x, 4, 'Cash Discount', format3)
        sheet.write(16 + x, 5, 'Total Invoice', format3)
        sheet.write(16 + x, 5, 'Allowance Discount', format3)
        sheet.write(16 + x, 6, 'Net After Allowance Discount', format3)

        sheet.write(17 + x, 0, '0', format3)
        sheet.write(17 + x, 1, (lines.discount_amount - lines.discount_amt)/lines.tot_qty, format2)
        sheet.write(17 + x, 2, lines.discount_amount, format2)
        sheet.write(17 + x, 3, lines.distr_amount, format2)
        sheet.write(17 + x, 4, lines.cash_amount, format2)
        sheet.write(17 + x, 5, lines.discount_amount, format2)
        sheet.write(17 + x, 5, lines.discount_amt, format2)
        sheet.write(17 + x, 6, lines.discount_net, format2)
        sheet.set_column(19 + x,4, 40)
        sheet.set_column(20 + x,4, 40)
        sheet.set_column(21 + x,4, 40)
        sheet.set_column(22 + x, 4, 40)

        sheet.write(19 + x,4 , 'يستخرج الشيك باسم الاسراء فارما سيوتيكال اوبتيما الشركة تخضع لنظام الدفعات المقدمة  '
                               , format2)
        sheet.write(20 + x,4 , 'و لا يجوز الخصم عليها من المنبع بضاعة الثلاجة لا ترد ولا تستبدل يعتبر التوقيع أو ختم الفاتورة'
                               , format2)
        sheet.write(21 + x,4 , 'بمثابة ايصال استلام لمشتملات الفاتورة وتعتبر أمانة لحين سداد قيمتها بموجب  ايصال نقدية شيك مختوم ومعتمد من الشركة '
                               , format2)
        sheet.write(22 + x,4 , 'وأقر بموافقتي علي جميع بنود الفاتورة  امضاء أو ختم الفاتورة يعتبر استلاما نهائيا للبضاعة والشركة غير مسئولة عن اي عجز يتم الابلاغ عنه بعد الاستلام'
                               , format2)



