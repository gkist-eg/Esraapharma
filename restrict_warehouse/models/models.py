from odoo import models, fields, api, _
from odoo.exceptions import Warning

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    allow_return = fields.Boolean(
        string="Return Operation",
    )


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'
    _description = 'Return Picking'

    @api.model
    def _getUserGroupId(self):
        # if self.user_has_groups('restrict_warehouse.group_restrict_warehouse'):
            return [('id', '=', self.original_location_id.id), ('return_location', '=', True), ('id', 'in',  self.env.user.stock_location_ids.ids), ]

    location_id = fields.Many2one(
        'stock.location', 'Return Location', domain=_getUserGroupId )
        # domain="['|', ('id', '=', original_location_id), '|', '&', ('return_location', '=', True), ('company_id', '=', False), '&', ('return_location', '=', True), ('company_id', '=', company_id)]")


class Quant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def _get_quants_action(self, domain=None, extend=False):
        """ Returns an action to open quant view.
        Depending of the context (user have right to be inventory mode or not),
        the list view will be editable or readonly.

        :param domain: List for the domain, empty by default.
        :param extend: If True, enables form, graph and pivot views. False by default.
        """
        self._quant_tasks()
        ctx = dict(self.env.context or {})
        ctx.pop('group_by', None)
        action = {
            'name': _('Stock On Hand'),
            'view_type': 'tree',
            'view_mode': 'list,form',
            'res_model': 'stock.quant',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'domain': domain or [],
            'help': """
                    <p class="o_view_nocontent_empty_folder">No Stock On Hand</p>
                    <p>This analysis gives you an overview of the current stock
                    level of your products.</p>
                    """
        }
        if self.user_has_groups('restrict_warehouse.group_restrict_warehouse'):
             action['domain'] = [('location_id', 'in', self.env.user.stock_location_ids.ids)]

        if self._is_inventory_mode():
            action['view_id'] = self.env.ref('stock.view_stock_quant_tree_editable').id
            form_view = self.env.ref('stock.view_stock_quant_form_editable').id
        else:
            action['view_id'] = self.env.ref('stock.view_stock_quant_tree').id
            form_view = self.env.ref('stock.view_stock_quant_form').id
        action.update({
            'views': [
                (action['view_id'], 'list'),
                (form_view, 'form'),
            ],
        })
        if extend:
            action.update({
                'view_mode': 'tree,form,pivot,graph',
                'views': [
                    (action['view_id'], 'list'),
                    (form_view, 'form'),
                    (self.env.ref('stock.view_stock_quant_pivot').id, 'pivot'),
                    (self.env.ref('stock.stock_quant_view_graph').id, 'graph'),
                ],
            })
        return action


class ResUsers(models.Model):
    _inherit = 'res.users'

    restrict_locations = fields.Boolean('Restrict Location')

    stock_location_ids = fields.Many2many(
        'stock.location',
        'location_security_stock_location_users',
        'user_id',
        'location_id',
        'Stock Locations')

    default_picking_type_ids = fields.Many2many(
        'stock.picking.type', 'stock_picking_type_users_rel',
        'user_id', 'picking_type_id', string='Default Warehouse Operations')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _getUserGroupId(self):
       if self.user_has_groups('restrict_warehouse.group_restrict_warehouse'):
           return [('id', '=', self.env.user.stock_location_ids.ids)]

    @api.model
    def _getdefaultSrc(self):
        picking_type = self.env['stock.picking.type'].browse(
            self._context.get('default_picking_type_id'))
        if picking_type.code == 'internal':
            return picking_type.default_location_src_id


    @api.onchange('picking_type_id', 'partner_id')
    def onchange_picking_type(self):
        if(self.picking_type_id.code == 'internal' or self.picking_type_id.allow_return) and self.state == 'draft':
            self = self.with_company(self.company_id)
            if self.picking_type_id.default_location_src_id:
                location_id = self.picking_type_id.default_location_src_id.id
            elif self.partner_id:
                location_id = self.partner_id.property_stock_supplier.id
            else:
                customerloc, location_id = self.env['stock.warehouse']._get_partner_locations()

            if self.picking_type_id.default_location_dest_id:
                location_dest_id = self.picking_type_id.default_location_dest_id.id
            elif self.partner_id:
                location_dest_id = self.partner_id.property_stock_customer.id
            else:
                location_dest_id, supplierloc = self.env['stock.warehouse']._get_partner_locations()

            self.location_id = location_id
            self.location_dest_id = location_dest_id
            (self.move_lines | self.move_ids_without_package).update({
                "picking_type_id": self.picking_type_id,
                "company_id": self.company_id,
            })

        if self.partner_id and self.partner_id.picking_warn:
            if self.partner_id.picking_warn == 'no-message' and self.partner_id.parent_id:
                partner = self.partner_id.parent_id
            elif self.partner_id.picking_warn not in (
            'no-message', 'block') and self.partner_id.parent_id.picking_warn == 'block':
                partner = self.partner_id.parent_id
            else:
                partner = self.partner_id
            if partner.picking_warn != 'no-message':
                if partner.picking_warn == 'block':
                    self.partner_id = False
                return {'warning': {
                    'title': ("Warning for %s") % partner.name,
                    'message': partner.picking_warn_msg
                }}
    @api.model
    def _getdefaultDest(self):
        picking_type = self.env['stock.picking.type'].browse(
            self._context.get('default_picking_type_id'))
        if picking_type.code == 'internal':
            return picking_type.default_location_dest_id

    location_id = fields.Many2one(
        'stock.location', "Source Location",
        default=_getdefaultSrc,
        check_company=True, readonly=True, required=True, domain=_getUserGroupId,
        states={'draft': [('readonly', False)]})
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        default=_getdefaultDest,
        check_company=True, readonly=True, required=True, domain=_getUserGroupId,
        states={'draft': [('readonly', False)]})


class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.depends('name')
    def _compute_purchase_order_ids(self):
        for lot in self:
            if self.user_has_groups('restrict_warehouse.group_restrict_warehouse'):
                    stock_moves = self.env['stock.move.line'].search([
                        ('lot_id', '=', lot.id),
                        ('state', '=', 'done'), ('location_id', 'in', self.env.user.stock_location_ids.ids),
                        ('location_dest_id', 'in', self.env.user.stock_location_ids.ids),
                    ]).mapped('move_id')
            else:
                stock_moves = self.env['stock.move.line'].search([
                    ('lot_id', '=', lot.id),
                    ('state', '=', 'done')
                ]).mapped('move_id')

            stock_moves = stock_moves.search([('id', 'in', stock_moves.ids)]).filtered(
                    lambda move: move.picking_id.location_id.usage == 'supplier' and move.state == 'done')
            lot.purchase_order_ids = stock_moves.mapped('purchase_line_id.order_id')
            lot.purchase_order_count = len(lot.purchase_order_ids)

    @api.depends('name')
    def _compute_sale_order_ids(self):
        for lot in self:
            if self.user_has_groups('restrict_warehouse.group_restrict_warehouse'):
                stock_moves = self.env['stock.move.line'].search([
                    ('lot_id', '=', lot.id),
                    ('state', '=', 'done'), ('location_id', 'in', self.env.user.stock_location_ids.ids),
                        ('location_dest_id', 'in', self.env.user.stock_location_ids.ids),
                ]).mapped('move_id')
            else:
                stock_moves = self.env['stock.move.line'].search([
                    ('lot_id', '=', lot.id),
                    ('state', '=', 'done')
                ]).mapped('move_id')

            stock_moves = stock_moves.search([('id', 'in', stock_moves.ids)]).filtered(
                lambda move: move.picking_id.location_dest_id.usage == 'customer' and move.state == 'done')
            lot.sale_order_ids = stock_moves.mapped('sale_line_id.order_id')
            lot.sale_order_count = len(lot.sale_order_ids)


class stock_move(models.Model):
    _inherit = 'stock.move'

    @api.constrains('state', 'location_id', 'location_dest_id')
    def check_user_location_rights(self):
        for record in self :
            if record.state == 'draft':
                return True
            user_locations = record.env.user.stock_location_ids

            if record.env.user.restrict_locations and not record.move_orig_ids:
                message = _(
                    'Invalid Location. You cannot process this move since you do '
                    'not control the location "%s". '
                    'Please contact your Adminstrator.')
                if record.location_id not in user_locations:
                    raise Warning(message % record.location_id.name)
                elif record.location_dest_id not in user_locations:
                    raise Warning(message % record.location_dest_id.name)


class MrpStockReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    @api.model
    def get_lines(self, line_id=None, **kw):
        context = dict(self.env.context)
        model = kw and kw['model_name'] or context.get('model')
        rec_id = kw and kw['model_id'] or context.get('active_id')
        level = kw and kw['level'] or 1
        lines = self.env['stock.move.line']
        move_line = self.env['stock.move.line']
        if rec_id and model == 'stock.production.lot':
            if self.user_has_groups('restrict_warehouse.group_restrict_warehouse'):
                lines = move_line.search([
                    ('lot_id', '=', context.get('lot_name') or rec_id),
                    ('state', '=', 'done'), ('location_id', 'in', self.env.user.stock_location_ids.ids), ('location_dest_id', 'in', self.env.user.stock_location_ids.ids),
                ])
            else:
                lines = move_line.search([
                    ('lot_id', '=', context.get('lot_name') or rec_id),
                    ('state', '=', 'done')
                ])
        elif rec_id and model == 'stock.move.line' and context.get('lot_name'):
            record = self.env[model].browse(rec_id)
            dummy, is_used = self._get_linked_move_lines(record)
            if is_used:
                lines = is_used
        elif rec_id and model in ('stock.picking', 'mrp.production'):
            record = self.env[model].browse(rec_id)
            if model == 'stock.picking':
                lines = record.move_lines.mapped('move_line_ids').filtered(lambda m: m.lot_id and m.state == 'done')
            else:
                lines = record.move_finished_ids.mapped('move_line_ids').filtered(lambda m: m.state == 'done')
        move_line_vals = self._lines(line_id, model_id=rec_id, model=model, level=level, move_lines=lines)
        final_vals = sorted(move_line_vals, key=lambda v: v['date'], reverse=True)
        lines = self._final_vals_to_lines(final_vals, level)
        return lines