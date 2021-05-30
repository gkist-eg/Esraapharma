from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _

import datetime
from odoo.exceptions import UserError


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

    qty = fields.Float('Quantity',digits='Product Unit of Measure')
    end_qty = fields.Float('Quantity',digits='Product Unit of Measure')

    @api.model
    def _get_from_date(self):
        company = self.env.user.company_id
        current_date = datetime.datetime.today()
        from_date = company.compute_fiscalyear_dates(current_date)['date_from']
        return from_date

    date_from = fields.Date("Start Date", default=_get_from_date)
    date_to = fields.Date("End Date", default=datetime.datetime.today())
    date_from2 = fields.Date("Start Date", compute='compute_date_to2')
    date_to2 = fields.Date("End Date", compute='compute_date_to2')

    def compute_date_to2(self):
        for record in self:
            record.date_to2 =record.date_to- relativedelta(days=1)
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

        line_ids = []
        for wizard_id in self.env['stock.wizerd.quantity.line'].search([('wizerd_id', '=', self.id)]):
            if wizard_id.wizard_id.id == self.id:
                self.write({'line_ids': [(3, wizard_id.id)]})
        date_from = self.date_from - relativedelta(days=1)
        date_to = self.date_to + relativedelta(days=1)
        qty = 0
        lb = 0
        if not self.lot_id:
            for resource in self.env['stock.move.line'].search(
                    [('location_dest_id', '=', self.location_id.id),
                     ('product_id', '=', self.product_id.id), ('state', '=', 'done'),
                     ('date', '<', date_from)]):
                qty += resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id)
            for resource in self.env['stock.move.line'].search(
                    [('location_id', '=', self.location_id.id), ('state', '=', 'done'),
                     ('product_id', '=', self.product_id.id),
                     ('date', '<', date_from)]):
                qty -= resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id)

            self.qty = qty
            lb = self.qty

            for resource in self.env['stock.move.line'].search(
                    ['|', ('location_id', '=', self.location_id.id), ('location_dest_id', '=', self.location_id.id),
                     ('state', '=', 'done'),
                     ('product_id', '=', self.product_id.id),
                     ('date', '>', date_from),
                     ('date', '<', date_to)], order="date"):
                if resource.state == 'done' and resource.location_dest_id == self.location_id:
                    if resource.picking_id:
                        lb += resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id)
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
                        line_ids.append((0, 0, {
                            'picking_id': resource.picking_id.id,
                            'name': resource.picking_id.name,
                            'in_qty': resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id),
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
                    if not resource.picking_id:
                        lb += resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id)
                        name=""
                        if resource.move_id.inventory_id :
                            name += 'Inv. Adj.: ' + resource.move_id.inventory_id.name
                        line_ids.append((0, 0, {
                            # 'picking_id': resource.picking_id.id,
                            'name': name,
                            'in_qty': resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id),
                            'out_qty': 0,
                            'balance': lb,
                            'dest_location': resource.location_id.id,
                            'lot_id': resource.lot_id.id,
                            'batch_no': resource.lot_id.ref or resource.lot_id.suplier_lot,
                            'date': resource.date,

                        }))

                if resource.state == 'done' and resource.location_id == self.location_id:
                    if resource.picking_id:
                        lb -= resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id)
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
                        line_ids.append((0, 0, {
                            'picking_id': resource.picking_id.id,
                            'name': resource.picking_id.name,
                            'out_qty': resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id),
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
                    if not resource.picking_id:
                        lb -= resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id)
                        name=''
                        if resource.move_id.inventory_id:
                            name += 'Inv. Adj.: ' + resource.move_id.inventory_id.name
                        line_ids.append((0, 0, {
                            # 'picking_id': resource.picking_id.id,
                            'name': name,
                            'out_qty': resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id),
                            'in_qty': 0,
                            'balance': lb,
                            'dest_location': resource.location_id.id,
                            'lot_id': resource.lot_id.id,
                            'batch_no': resource.lot_id.ref or resource.lot_id.suplier_lot,
                            'date': resource.date,

                        }))

        if self.lot_id:
            for resource in self.env['stock.move.line'].search(
                    ['|', ('location_id', '=', self.location_id.id), ('location_dest_id', '=', self.location_id.id),
                     ('state', '=', 'done'), ('lot_id', 'in', self.lot_id.ids),
                     ('product_id', '=', self.product_id.id),
                     ('date', '>', date_from),
                     ('date', '<', date_to)], order="date"):
                batch = ''
                name=''
                if resource.state == 'done' and resource.location_dest_id == self.location_id:
                    if resource.picking_id:
                        lb += resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id)
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
                        line_ids.append((0, 0, {
                            'picking_id': resource.picking_id.id,
                            'name': resource.picking_id.name,
                            'in_qty': resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id),
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
                    if not resource.picking_id:
                        lb += resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id)
                        if resource.move_id.inventory_id:
                            name += 'Inv. Adj.: ' + resource.move_id.inventory_id.name
                        line_ids.append((0, 0, {
                            # 'picking_id': resource.picking_id.id,
                            'name': name,
                            'in_qty': resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id),
                            'out_qty': 0,
                            'balance': lb,
                            'dest_location': resource.location_id.id,
                            'lot_id': resource.lot_id.id,
                            'batch_no': resource.lot_id.ref or resource.lot_id.suplier_lot,
                            'date': resource.date,

                        }))

                if resource.state == 'done' and resource.location_id == self.location_id:
                        if resource.picking_id:
                            lb -= resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id)
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
                            line_ids.append((0, 0, {
                                'name': resource.picking_id.name,
                                'picking_id': resource.picking_id.id,
                                'out_qty': resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id),
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
                        if not resource.picking_id:
                            lb -= resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id)
                            if resource.move_id.inventory_id:
                                name += 'Inv. Adj.: ' + resource.move_id.inventory_id.name
                            line_ids.append((0, 0, {
                                # 'picking_id': resource.picking_id.id,
                                'name': name,
                                'out_qty': resource.product_uom_id._compute_quantity(resource.qty_done, resource.product_id.uom_id),
                                'in_qty': 0,
                                'balance': lb,
                                'dest_location': resource.location_dest_id.id,
                                'lot_id': resource.lot_id.id,
                                'batch_no': resource.lot_id.ref or resource.lot_id.suplier_lot,
                                'date': resource.date,

                            }))

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
