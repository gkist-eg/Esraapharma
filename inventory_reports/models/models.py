from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import base64
from io import BytesIO
import xlsxwriter
from odoo import fields, models, api, _


class ProductStockBalance(models.TransientModel):
    _name = 'stock.wizerd.quantity.line'
    _order = 'date asc'
    wizerd_id = fields.Many2one('stock.wizerd.quantity', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    picking_id = fields.Many2one('stock.picking')
    partner_id = fields.Many2one('res.partner')
    picking_type_id = fields.Many2one('stock.picking.type')
    location_id = fields.Many2one('stock.location', string="Location Name")
    dest_location = fields.Many2one('stock.location', string="Location Name")
    lot_id = fields.Many2one('stock.production.lot')
    batch_no = fields.Char('Batch No')
    name = fields.Char('Batch No')
    in_qty = fields.Float(digits='Product Unit of Measure')
    out_qty = fields.Float(digits='Product Unit of Measure')
    balance = fields.Float(digits='Product Unit of Measure')
    date = fields.Datetime()


class ProductTemplate(models.TransientModel):
    _name = 'stock.wizerd.quantity'

    file_name = fields.Char('File Name')
    mapping_report_file = fields.Binary('Mapping Report')
    line_ids = fields.One2many(
        'stock.wizerd.quantity.line', 'wizerd_id', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product Name')

    @api.model
    def _getUserGroupId(self):
        return [('id', '=', self.env.user.stock_location_ids.ids), ('usage', '=', 'internal')]

    location_id = fields.Many2one('stock.location', string='Location', domain=_getUserGroupId)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
                                   )
    lot_id = fields.Many2many('stock.production.lot', string='Serial /lOT',
                              domain="[('product_id', 'in', [product_id])]")

    qty = fields.Float('Quantity', digits='Product Unit of Measure')
    end_qty = fields.Float('Quantity', digits='Product Unit of Measure')

    @api.model
    def _get_from_date(self):
        company = self.env.user.company_id
        current_date = datetime.today()
        from_date = company.compute_fiscalyear_dates(current_date)['date_from']
        return from_date

    date_from = fields.Date("Start Date", default=_get_from_date)
    date_to = fields.Date("End Date", default=datetime.today())
    date_from2 = fields.Date("Start Date", compute='compute_date_to2')
    date_to2 = fields.Date("End Date", compute='compute_date_to2')

    def compute_date_to2(self):
        for record in self:
            record.date_to2 = record.date_to - relativedelta(days=1)
            record.date_from2 = record.data_from + relativedelta(days=1)

    # @api.constrains('location_id')
    # def check_user_location_rights(self):
    #     user_locations = self.env.user.stock_location_ids
    #     if self.env.user.restrict_locations:
    #         message = _(
    #             'Invalid Location. You cannot process this move since you do '
    #             'not control the location "%s". '
    #             'Please contact your Adminstrator.')
    #         if self.location_id not in user_locations:
    #             raise Warning(message % self.location_id.name)

    def print_pdf_stock(self):
        is_excel = self.env.context.get('is_excel', False)
        line_ids = []
        for wizard_id in self.env['stock.wizerd.quantity.line'].search([('wizerd_id', '=', self.id)]):
            if wizard_id.wizard_id.id == self.id:
                self.write({'line_ids': [(3, wizard_id.id)]})
        date_from = self.date_from - relativedelta(days=1)
        date_to = self.date_to + relativedelta(days=1)
        qty = 0
        lb = 0
        if is_excel:
            today = datetime.today().strftime('%Y-%m-%d')

            file_name = 'Item Sheet ' + '_' + str(today) + '.xlsx'
            fp = BytesIO()

            workbook = xlsxwriter.Workbook(fp)
            heading_format = workbook.add_format({'align': 'center',
                                                  'valign': 'vcenter',
                                                  'font_color': 'blue_gray',
                                                  'bold': True, 'size': 14})
            cell_text_format_n = workbook.add_format({'align': 'center', 'size': 9,
                                                      })
            cell_text_format = workbook.add_format({'align': 'left',
                                                    'size': 9,
                                                    })

            formatdict = {'num_format': 'dd/mm/yyyy hh:mm:ss'}
            fmt = workbook.add_format(formatdict)
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
            report_head = 'Item sheet quantity ( ' + str(self.date_from) + ' - ' + str(
                self.date_to) + ' )'
            worksheet.merge_range('A1:F1', report_head, heading_format)
            worksheet.write(1, 0, _('Product:'), heading_format)
            worksheet.merge_range('B2:C2', self.product_id.display_name, heading_format)
            worksheet.write(1, 3, 'Location :', heading_format)
            worksheet.merge_range('E2:F2', self.location_id.display_name, heading_format)

            row = 3
            worksheet.write(row, 0, _('Referance'), column_heading_style2)
            worksheet.write(row, 1, _('Date'), column_heading_style2)
            worksheet.write(row, 2, _('Lot'), column_heading_style2)
            worksheet.write(row, 3, _('Batch'), column_heading_style2)
            worksheet.write(row, 4, _('Income Qty'), column_heading_style2)
            worksheet.write(row, 5, _('Outgoing Qty'), column_heading_style2)
            worksheet.write(row, 6, _('Balance'), column_heading_style2)
            worksheet.write(row, 7, _('Desc'), column_heading_style2)
            worksheet.write(row, 8, _('kind'), column_heading_style2)
            worksheet.write(row, 9, _('Product'), column_heading_style2)
            row = 4
        if not self.lot_id:
            for resource in self.env['stock.move.line'].search(
                    [('location_dest_id', '=', self.location_id.id),
                     ('product_id', '=', self.product_id.id), ('state', '=', 'done'),
                     ('date', '<', date_from)]):
                qty += round(resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5)
            for resource in self.env['stock.move.line'].search(
                    [('location_id', '=', self.location_id.id), ('state', '=', 'done'),
                     ('product_id', '=', self.product_id.id),
                     ('date', '<', date_from)]):
                qty -= round(resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5)

            self.qty = qty
            lb = self.qty
            if is_excel:
                worksheet.write(2, 5, 'Start Balance', cell_text_format_n)
                worksheet.write(2, 6, lb, cell_text_format_n)
            for resource in self.env['stock.move.line'].search(
                    ['|', ('location_id', '=', self.location_id.id), ('location_dest_id', '=', self.location_id.id),
                     ('state', '=', 'done'),
                     ('product_id', '=', self.product_id.id),
                     ('date', '>', date_from),
                     ('date', '<', date_to)], order="date"):
                if resource.state == 'done' and resource.location_dest_id == self.location_id:
                    if resource.picking_id:
                        lb += round(resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5)
                        if resource.picking_id.location:
                            location = resource.picking_id.location
                        else:
                            location = resource.location_id

                        if resource.lot_id.ref:
                            batch = resource.lot_id.ref
                        elif resource.picking_id.batch:
                            batch = resource.picking_id.batch
                        else:
                            batch = resource.lot_id.suplier_lot
                        if not is_excel:
                            line_ids.append((0, 0, {
                                'picking_id': resource.picking_id.id,
                                'name': resource.picking_id.name,
                                'in_qty': round(resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5),
                                'out_qty': 0,
                                'balance': lb,
                                'dest_location': location.id,
                                'lot_id': resource.lot_id.id,
                                'batch_no': batch,
                                'date': resource.date,
                                'product_id': resource.picking_id.mrp_product_id.id,
                                'partner_id': resource.picking_id.partner_id.id,
                                'picking_type_id': resource.picking_id.picking_type_id.id,

                            }))
                        else:
                            worksheet.write(row, 0, resource.picking_id.name, cell_text_format_n)
                            worksheet.write(row, 1, resource.date, fmt)
                            worksheet.write(row, 2, resource.lot_id.id, cell_text_format_n)
                            worksheet.write(row, 3, batch, cell_text_format_n)
                            worksheet.write(row, 4, round(resource.product_uom_id._compute_quantity(resource.qty_done,
                                                                                                    resource.product_id.uom_id),
                                                          5),
                                            cell_text_format_n)
                            worksheet.write(row, 5, 0, cell_text_format_n)
                            worksheet.write(row, 6, lb, cell_text_format_n)
                            if resource.picking_id.partner_id:
                                worksheet.write(row, 7, resource.picking_id.partner_id.name, cell_text_format_n)
                            else:
                                worksheet.write(row, 7, location.display_name, cell_text_format_n)

                            worksheet.write(row, 8, resource.picking_id.picking_type_id.name, cell_text_format_n)
                            worksheet.write(row, 9, resource.picking_id.mrp_product_id.display_name, cell_text_format_n)
                            row += 1
                    if not resource.picking_id:
                        lb += round(
                            resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5)
                        name = ""
                        if resource.move_id.inventory_id:
                            name += 'Inv. Adj.: ' + resource.move_id.inventory_id.name
                        if not is_excel:
                            line_ids.append((0, 0, {
                                # 'picking_id': resource.picking_id.id,
                                'name': name,
                                'in_qty': round (resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id),5),
                                'out_qty': 0,
                                'balance': lb,
                                'dest_location': resource.location_id.id,
                                'lot_id': resource.lot_id.id,
                                'batch_no': resource.lot_id.ref or resource.lot_id.suplier_lot,
                                'date': resource.date,

                            }))
                        else:
                            worksheet.write(row, 0, name, cell_text_format_n)
                            worksheet.write(row, 1, resource.date, fmt)
                            worksheet.write(row, 2, resource.lot_id.name, cell_text_format_n)
                            worksheet.write(row, 3, resource.lot_id.ref, cell_text_format_n)
                            worksheet.write(row, 4, round(resource.product_uom_id._compute_quantity(resource.qty_done,
                                                                                                    resource.product_id.uom_id),
                                                          5),
                                            cell_text_format_n)
                            worksheet.write(row, 5, 0, cell_text_format_n)
                            worksheet.write(row, 6, lb, cell_text_format_n)
                            worksheet.write(row, 7, resource.location_id.display_name, cell_text_format_n)
                            worksheet.write(row, 8, resource.picking_id.picking_type_id.name, cell_text_format_n)
                            row += 1
                if resource.state == 'done' and resource.location_id == self.location_id:
                    if resource.picking_id:
                        lb -= round(
                            resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5)
                        if resource.picking_id.location:
                            location = resource.picking_id.location
                        else:
                            location = resource.location_id

                        if resource.lot_id.ref:
                            batch = resource.lot_id.ref
                        elif resource.picking_id.batch:
                            batch = resource.picking_id.batch
                        else:
                            batch = resource.lot_id.suplier_lot
                        if not is_excel:
                            line_ids.append((0, 0, {
                                'picking_id': resource.picking_id.id,
                                'name': resource.picking_id.name,
                                'out_qty': round(resource.product_uom_id._compute_quantity(resource.qty_done,
                                                                                           resource.product_id.uom_id), 5),
                                'in_qty': 0,
                                'balance': lb,
                                'dest_location': location.id,
                                'lot_id': resource.lot_id.id,
                                'batch_no': batch,
                                'date': resource.date,
                                'product_id': resource.picking_id.mrp_product_id.id,
                                'partner_id': resource.picking_id.partner_id.id,
                                'picking_type_id': resource.picking_id.picking_type_id.id,

                            }))
                        else:
                            worksheet.write(row, 0, resource.picking_id.name, cell_text_format_n)
                            worksheet.write(row, 1, resource.date, fmt)
                            worksheet.write(row, 2, resource.lot_id.name, cell_text_format_n)
                            worksheet.write(row, 3, batch, cell_text_format_n)
                            worksheet.write(row, 4, 0,
                                            cell_text_format_n)
                            worksheet.write(row, 5, round(resource.product_uom_id._compute_quantity(resource.qty_done,
                                                                                                    resource.product_id.uom_id),
                                                          5),
                                            cell_text_format_n)
                            worksheet.write(row, 6, lb, cell_text_format_n)
                            if resource.picking_id.partner_id:
                                worksheet.write(row, 7, resource.picking_id.partner_id.name, cell_text_format_n)
                            else:
                                worksheet.write(row, 7, location.display_name, cell_text_format_n)

                            worksheet.write(row, 8, resource.picking_id.picking_type_id.name, cell_text_format_n)
                            worksheet.write(row, 9, resource.picking_id.mrp_product_id.display_name, cell_text_format_n)
                            row += 1
                    if not resource.picking_id:
                        lb -= round(
                            resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5)
                        name = ''
                        if resource.move_id.inventory_id:
                            name += 'Inv. Adj.: ' + resource.move_id.inventory_id.name
                        if not is_excel:
                            line_ids.append((0, 0, {
                                # 'picking_id': resource.picking_id.id,
                                'name': name,
                                'out_qty': round(resource.product_uom_id._compute_quantity(resource.qty_done,
                                                                                           resource.product_id.uom_id),
                                                 5),
                                'in_qty': 0,
                                'balance': lb,
                                'dest_location': resource.location_id.id,
                                'lot_id': resource.lot_id.id,
                                'batch_no': resource.lot_id.ref or resource.lot_id.suplier_lot,
                                'date': resource.date,

                            }))
                        else:
                            worksheet.write(row, 0, name, cell_text_format_n)
                            worksheet.write(row, 1, resource.date, fmt)
                            worksheet.write(row, 2, resource.lot_id.name, cell_text_format_n)
                            worksheet.write(row, 3, resource.lot_id.ref, cell_text_format_n)
                            worksheet.write(row, 4, 0, cell_text_format_n)
                            worksheet.write(row, 5, round(resource.product_uom_id._compute_quantity(resource.qty_done,
                                                                                                    resource.product_id.uom_id),
                                                          5),
                                            cell_text_format_n)
                            worksheet.write(row, 6, lb, cell_text_format_n)
                            worksheet.write(row, 7, resource.location_dest_id.display_name, cell_text_format_n)
                            worksheet.write(row, 8, resource.picking_id.picking_type_id.name, cell_text_format_n)
                            row += 1

        if self.lot_id:
            for resource in self.env['stock.move.line'].search(
                    [('location_dest_id', '=', self.location_id.id), ('lot_id', 'in', self.lot_id.ids),
                     ('product_id', '=', self.product_id.id), ('state', '=', 'done'),
                     ('date', '<', date_from)]):
                qty += round(resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5)
            for resource in self.env['stock.move.line'].search(
                    [('location_id', '=', self.location_id.id), ('state', '=', 'done'),
                     ('product_id', '=', self.product_id.id), ('lot_id', 'in', self.lot_id.ids),
                     ('date', '<', date_from)]):
                qty -= round(resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5)

            self.qty = qty
            lb = self.qty
            if is_excel:
                worksheet.write(2, 5, 'Start Balance', cell_text_format_n)
                worksheet.write(2, 6, lb, cell_text_format_n)
            for resource in self.env['stock.move.line'].search(
                    ['|', ('location_id', '=', self.location_id.id), ('location_dest_id', '=', self.location_id.id),
                     ('state', '=', 'done'), ('lot_id', 'in', self.lot_id.ids),
                     ('product_id', '=', self.product_id.id),
                     ('date', '>', date_from),
                     ('date', '<', date_to)], order="date"):
                batch = ''
                name = ''
                if resource.state == 'done' and resource.location_dest_id == self.location_id:
                    if resource.picking_id:
                        lb += round(
                            resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5)
                        if resource.picking_id.location:
                            location = resource.picking_id.location
                        else:
                            location = resource.location_id

                        if resource.lot_id.ref:
                            batch = resource.lot_id.ref
                        elif resource.picking_id.batch:
                            batch = resource.picking_id.batch
                        else:
                            batch = resource.lot_id.suplier_lot
                        if not is_excel:
                            line_ids.append((0, 0, {
                                'picking_id': resource.picking_id.id,
                                'name': resource.picking_id.name,
                                'in_qty': round (resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id),5),
                                'out_qty': 0,
                                'balance': lb,
                                'dest_location': location.id,
                                'lot_id': resource.lot_id.id,
                                'batch_no': batch,
                                'date': resource.date,
                                'product_id': resource.picking_id.mrp_product_id.id,
                                'partner_id': resource.picking_id.partner_id.id,
                                'picking_type_id': resource.picking_id.picking_type_id.id,

                            }))
                        else:
                            worksheet.write(row, 0, resource.picking_id.name, cell_text_format_n)
                            worksheet.write(row, 1, resource.date, fmt)
                            worksheet.write(row, 2, resource.lot_id.name, cell_text_format_n)
                            worksheet.write(row, 3, batch, cell_text_format_n)
                            worksheet.write(row, 4, round(resource.product_uom_id._compute_quantity(resource.qty_done,
                                                                                                    resource.product_id.uom_id),
                                                          5),
                                            cell_text_format_n)
                            worksheet.write(row, 5, 0, cell_text_format_n)
                            worksheet.write(row, 6, lb, cell_text_format_n)
                            if resource.picking_id.partner_id:
                                worksheet.write(row, 7, resource.picking_id.partner_id.name, cell_text_format_n)
                            else:
                                worksheet.write(row, 7, location.display_name, cell_text_format_n)

                            worksheet.write(row, 8, resource.picking_id.picking_type_id.name, cell_text_format_n)
                            worksheet.write(row, 9, resource.picking_id.mrp_product_id.display_name, cell_text_format_n)
                            row += 1
                    if not resource.picking_id:
                        lb += round(
                            resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5)
                        if resource.move_id.inventory_id:
                            name += 'Inv. Adj.: ' + resource.move_id.inventory_id.name
                        if not is_excel:

                            line_ids.append((0, 0, {
                                # 'picking_id': resource.picking_id.id,
                                'name': name,
                                'in_qty': round(resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5),
                                'out_qty': 0,
                                'balance': lb,
                                'dest_location': resource.location_id.id,
                                'lot_id': resource.lot_id.id,
                                'batch_no': resource.lot_id.ref or resource.lot_id.suplier_lot,
                                'date': resource.date,

                            }))
                        else:
                            worksheet.write(row, 0, name, cell_text_format_n)
                            worksheet.write(row, 1, resource.date, fmt)
                            worksheet.write(row, 2, resource.lot_id.name, cell_text_format_n)
                            worksheet.write(row, 3, resource.lot_id.ref, cell_text_format_n)
                            worksheet.write(row, 4, round(resource.product_uom_id._compute_quantity(resource.qty_done,
                                                                                                    resource.product_id.uom_id),
                                                          5),
                                            cell_text_format_n)
                            worksheet.write(row, 5, 0, cell_text_format_n)
                            worksheet.write(row, 6, lb, cell_text_format_n)
                            worksheet.write(row, 7, resource.location_id.display_name, cell_text_format_n)
                            worksheet.write(row, 8, resource.picking_id.picking_type_id.name, cell_text_format_n)
                            row += 1
                if resource.state == 'done' and resource.location_id == self.location_id:
                    if resource.picking_id:
                        lb -= round(
                            resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5)
                        if resource.picking_id.location:
                            location = resource.picking_id.location
                        else:
                            location = resource.location_dest_id

                        if resource.lot_id.ref:
                            batch = resource.lot_id.ref
                        elif resource.picking_id.batch:
                            batch = resource.picking_id.batch
                        else:
                            batch = resource.lot_id.suplier_lot
                        if not is_excel:
                            line_ids.append((0, 0, {
                                'name': resource.picking_id.name,
                                'picking_id': resource.picking_id.id,
                                'out_qty': round(resource.product_uom_id._compute_quantity(resource.qty_done,
                                                                                           resource.product_id.uom_id),
                                                 5),
                                'in_qty': 0,
                                'balance': lb,
                                'dest_location': location.id,
                                'lot_id': resource.lot_id.id,
                                'batch_no': batch,
                                'date': resource.date,
                                'product_id': resource.picking_id.mrp_product_id.id,
                                'partner_id': resource.picking_id.partner_id.id,
                                'picking_type_id': resource.picking_id.picking_type_id.id,

                            }))
                        else:
                            worksheet.write(row, 0, resource.picking_id.name, cell_text_format_n)
                            worksheet.write(row, 1, resource.date, fmt)
                            worksheet.write(row, 2, resource.lot_id.name, cell_text_format_n)
                            worksheet.write(row, 3, batch, cell_text_format_n)
                            worksheet.write(row, 4, 0, cell_text_format_n)
                            worksheet.write(row, 5, round(resource.product_uom_id._compute_quantity(resource.qty_done,
                                                                                                    resource.product_id.uom_id),
                                                          5),
                                            cell_text_format_n)
                            worksheet.write(row, 6, lb, cell_text_format_n)
                            if resource.picking_id.partner_id:
                                worksheet.write(row, 7, resource.picking_id.partner_id.name, cell_text_format_n)
                            else:
                                worksheet.write(row, 7, location.display_name, cell_text_format_n)

                            worksheet.write(row, 8, resource.picking_id.picking_type_id.name, cell_text_format_n)
                            worksheet.write(row, 9, resource.picking_id.mrp_product_id.display_name, cell_text_format_n)
                            row += 1
                    if not resource.picking_id:
                        lb -= round(
                            resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id), 5)
                        if resource.move_id.inventory_id:
                            name += 'Inv. Adj.: ' + resource.move_id.inventory_id.name
                        if not is_excel:
                            line_ids.append((0, 0, {
                                # 'picking_id': resource.picking_id.id,
                                'name': name,
                                'out_qty': round(resource.product_uom_id._compute_quantity(resource.qty_done,
                                                                                           resource.product_id.uom_id),
                                                 5),
                                'in_qty': 0,
                                'balance': lb,
                                'dest_location': resource.location_dest_id.id,
                                'lot_id': resource.lot_id.id,
                                'batch_no': resource.lot_id.ref or resource.lot_id.suplier_lot,
                                'date': resource.date,

                            }))
                        else:
                            worksheet.write(row, 0, name, cell_text_format_n)
                            worksheet.write(row, 1, resource.date, fmt)
                            worksheet.write(row, 2, resource.lot_id.name, cell_text_format_n)
                            worksheet.write(row, 3, resource.lot_id.ref, cell_text_format_n)
                            worksheet.write(row, 4, 0, cell_text_format_n)
                            worksheet.write(row, 5, round(resource.product_uom_id._compute_quantity(resource.qty_done,
                                                                                                    resource.product_id.uom_id),
                                                          5),
                                            cell_text_format_n)
                            worksheet.write(row, 6, lb, cell_text_format_n)
                            worksheet.write(row, 7, resource.location_dest_id.display_name, cell_text_format_n)
                            worksheet.write(row, 8, resource.picking_id.picking_type_id.name,
                                            cell_text_format_n)
                            row += 1
        if not is_excel:
            self.end_qty = lb
            # writing to One2many line_ids
            self.write({'line_ids': line_ids})
            context = {
                'lang': 'en_US',
                'active_ids': [self.id],
            }
            return {
                'context': context,
                'data': None,
                'type': 'ir.actions.report',
                'report_name': 'inventory_reports.item_quantity_report',
                'report_type': 'qweb-html',
                'report_file': 'inventory_reports.item_quantity_report',
                'name': 'Item Sheet',
                'flags': {'action_buttons': True},
            }
        else:
            worksheet.write(row, 5, 'End Balance', cell_text_format_n)
            worksheet.write(row, 6, lb, cell_text_format_n)

            workbook.close()
            file_download = base64.b64encode(fp.getvalue())

            fp.close()
            self.mapping_report_file = file_download
            self.file_name = file_name
            return {
                'view_mode': 'form',
                'res_id': self.id,
                'res_model': 'stock.wizerd.quantity',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'context': self.env.context,
                'target': 'new',
            }
