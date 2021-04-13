from odoo import models, fields, api,_


class Quant(models.Model):
    _inherit = 'stock.quant'
    value = fields.Monetary('Value', compute='_compute_value', groups='account.group_account_manager')

    removal_date = fields.Date(related='lot_id.removal_date', store=True, readonly=False)
    suplier_lot = fields.Char(related='lot_id.suplier_lot',string='Suplier Lot', store=True, readonly=False)
    batch = fields.Char(related='lot_id.ref', store=True, readonly=False)

    @api.model
    def action_view_quants(self):
        self = self.with_context(search_default_internal_loc=1)
        if not self.user_has_groups('stock.group_stock_multi_locations'):
            company_user = self.env.company
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
            if warehouse:
                self = self.with_context(default_location_id=warehouse.lot_stock_id.id)

        # If user have rights to write on quant, we set quants in inventory mode.
        if self.user_has_groups('stock.group_stock_manager'):
            self = self.with_context(inventory_mode=False)
        return self._get_quants_action(extend=True)



class LotNumber(models.Model):
    _inherit = 'stock.production.lot'
    box_no = fields.Float('No Of Boxes', default=1.0, store=True)
    box_qty = fields.Float('Box weight / Qty', default=1.0, store=True)
    prod_date = fields.Date(string='Production Date', help='This is the date on which the product made.', store=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments', )
    balet_ids = fields.Many2many('balet.location', string="Ballets")
    suplier_lot = fields.Char(string='Supplier Lot', store=True)

    expiration_date = fields.Date(string='Expiration Date',
                                      help='This is the date on which the goods with this Serial Number may become dangerous and must not be consumed.')
    use_date = fields.Date(string='Best before Date',
                               help='This is the date on which the goods with this Serial Number start deteriorating, without being dangerous yet.')
    removal_date = fields.Date(string='Removal Date',
                                   help='This is the date on which the goods with this Serial Number should be removed from the stock. This date will be used in FEFO removal strategy.')
    alert_date = fields.Date(string='Alert Date',
                                 help='Date to determine the expired lots and serial numbers using the filter "Expiration Alerts".')
    history_count = fields.Integer(compute='_compute_history', string='Receptions', default=0)

    history_ids = fields.One2many('balet.change', 'lot_id', string='Receptions', copy=False)

    def _compute_history(self):
        for order in self:
            order.history_count = len(order.history_ids)

    def action_view_history(self):
        action = self.env.ref('inventory_update.action_balet_change_location')
        result = action.read()[0]
        result.pop('id', None)
        result['context'] = {}
        pick_ids = sum([order.history_ids.ids for order in self], [])
        result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        return result

    @api.depends('expiration_date')
    def _compute_product_expiry_alert(self):
        current_date = fields.date.today()
        for lot in self:
            if lot.expiration_date:
                lot.product_expiry_alert = lot.expiration_date <= current_date
            else:
                lot.product_expiry_alert = False


class LotNumberLot(models.Model):
    _inherit = 'stock.move.line'

    origin_qty = fields.Float('Origin Qty', store=True)
    box_no = fields.Float('No Of Boxes', store=True)
    box_qty = fields.Float('Box weight / Qty', store=True)
    suplier_lot = fields.Char(string='supplier lot', store=True)
    prod_date = fields.Date(string='Production Date', help='This is the date on which the product made.', store=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments', )
    balet_ids = fields.Many2many('balet.location', string="Ballets")
    lot_name = fields.Char('Lot/Serial Number Name', store=True)

    @api.onchange('box_no', 'box_qty')
    def _onchange_box_weight(self):
        if self.box_qty > 0 and self.box_no:
            self.qty_done = self.box_no * self.box_qty

    @api.onchange('prod_date', 'box_qty', 'box_no')
    def _onchange_production(self):
        if not self.lot_id and not self.lot_name and self.product_id.tracking != "none":
            self.lot_name = self.env['ir.sequence'].next_by_code('stock.lot.serial')
        else:
            self.lot_name = self.lot_name

    def _assign_production_lot(self, lot):
        super()._assign_production_lot(lot)
        self.lot_id.prod_date = self.prod_date
        self.lot_id.box_qty = self.box_qty
        self.lot_id.box_no = self.box_no
        self.lot_id.suplier_lot = self.suplier_lot
        self.lot_id.attachment_ids = self.attachment_ids
        self.lot_id.balet_ids = self.balet_ids
