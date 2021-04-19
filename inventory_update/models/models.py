import json
import time
from ast import literal_eval
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_datetime
import json
from collections import defaultdict
from datetime import datetime,date
from itertools import groupby
from operator import itemgetter
from re import findall as regex_findall
from re import split as regex_split
from dateutil import relativedelta
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_repr, float_round
from odoo.tools.misc import format_date, OrderedSet


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    pubprice = fields.Float("Customer Price", store=True, index=True)

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.depends('has_tracking', 'picking_type_id.use_create_lots', 'picking_type_id.use_existing_lots', 'state')
    def _compute_display_assign_serial(self):
        for move in self:
            move.display_assign_serial = (
                    move.has_tracking != 'none' and
                    move.state in ('partially_available', 'assigned', 'confirmed') and
                    move.picking_type_id.use_create_lots and
                    not move.picking_type_id.use_existing_lots
            )

    next_serial = fields.Char('First SN', readonly=True, store=True, copy=False)

    def _generate_serial_numbers(self, next_serial_count=False):
        """ This method will generate `lot_name` from a string (field
        `next_serial`) and create a move line for each generated `lot_name`.
        """
        self.ensure_one()

        if not next_serial_count:
            next_serial_count = self.next_serial_count
        # We look if the serial number contains at least one digit.
        caught_initial_number = regex_findall("\d+", self.next_serial)
        if not caught_initial_number:
            raise UserError(_('The serial number must contain at least one digit.'))
        # We base the serie on the last number find in the base serial number.
        initial_number = caught_initial_number[-1]
        padding = len(initial_number)
        # We split the serial number to get the prefix and suffix.
        splitted = regex_split(initial_number, self.next_serial)
        # initial_number could appear several times in the SN, e.g. BAV023B00001S00001
        prefix = initial_number.join(splitted[:-1])
        suffix = splitted[-1]
        initial_number = int(initial_number)

        lot_names = []
        for i in range(0, next_serial_count):
            if i == 0:
                lot_names.append('%s%s%s' % (
                    prefix,
                    self.next_serial,
                    suffix
                ))
            else:
                lot_names.append('%s%s%s' % (
                    prefix,
                    self.env['ir.sequence'].next_by_code('stock.lot.serial'),
                    suffix
                ))
        move_lines_commands = self._generate_serial_move_line_commands(lot_names)
        self.write({'move_line_ids': move_lines_commands})
        return True

    def action_show_details(self):
        """ Returns an action that will open a form view (in a popup) allowing to work on all the
        move lines of a particular move. This form view is used when "show operations" is not
        checked on the picking type.
        """
        self.ensure_one()
        if not self.next_serial and self.display_assign_serial:
            self.next_serial = self.env['ir.sequence'].next_by_code('stock.lot.serial')
        picking_type_id = self.picking_type_id or self.picking_id.picking_type_id

        # If "show suggestions" is not checked on the picking type, we have to filter out the
        # reserved move lines. We do this by displaying `move_line_nosuggest_ids`. We use
        # different views to display one field or another so that the webclient doesn't have to
        # fetch both.
        if picking_type_id.show_reserved:
            view = self.env.ref('stock.view_stock_move_operations')
        else:
            view = self.env.ref('stock.view_stock_move_nosuggest_operations')

        return {
            'name': _('Detailed Operations'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.move',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id,
            'context': dict(
                self.env.context,
                show_owner=self.picking_type_id.code != 'incoming',
                show_lots_m2o=self.has_tracking != 'none' and (
                            picking_type_id.use_existing_lots or self.state == 'done' or self.origin_returned_move_id.id),
                # able to create lots, whatever the value of ` use_create_lots`.
                show_lots_text=self.has_tracking != 'none' and picking_type_id.use_create_lots and not picking_type_id.use_existing_lots and self.state != 'done' and not self.origin_returned_move_id.id,
                show_source_location=self.picking_type_id.code != 'incoming',
                show_destination_location=self.picking_type_id.code != 'outgoing',
                show_package=not self.location_id.usage == 'supplier',
                show_reserved_quantity=self.state != 'done' and not self.picking_id.immediate_transfer and self.picking_type_id.code != 'incoming'
            ),
        }

    @api.onchange('product_id', 'location_id')
    def _onchange_domain_id(self):
        if self.location_id.usage == "internal":
            domain = {'product_id': [('stock_quant_ids.location_id', '=', self.location_id.id)]}
            return {'domain': domain}

    def do_unreserve(self):
        self._do_unreserve()

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        self.ensure_one()
        # apply putaway
        location_dest_id = self.location_dest_id._get_putaway_strategy(self.product_id).id or self.location_dest_id.id
        vals = {
            'move_id': self.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'location_id': self.location_id.id,
            'location_dest_id': location_dest_id,
            'picking_id': self.picking_id.id,
            'company_id': self.company_id.id,
        }
        if quantity and self.location_id.usage in ('internal', 'transit'):
            uom_quantity = self.product_id.uom_id._compute_quantity(quantity, self.product_uom,
                                                                    rounding_method='HALF-UP')
            uom_quantity_back_to_product_uom = self.product_uom._compute_quantity(uom_quantity, self.product_id.uom_id,
                                                                                  rounding_method='HALF-UP')
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                vals = dict(vals, product_uom_qty=uom_quantity, qty_done=uom_quantity)
            else:
                vals = dict(vals, product_uom_qty=quantity, qty_done=quantity, product_uom_id=self.product_id.uom_id.id)
        if reserved_quant:
            vals = dict(
                vals,
                location_id=reserved_quant.location_id.id,
                lot_id=reserved_quant.lot_id.id or False,
                package_id=reserved_quant.package_id.id or False,
                owner_id=reserved_quant.owner_id.id or False,
            )

        return vals


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    name = fields.Char(
        'Reference', default='/',
        copy=False, index=True, readonly=False)

    partner_id = fields.Many2one(
        'res.partner', 'Contact',
        check_company=True, readonly=True,
        states={'draft': [('readonly', False)]})

    origin = fields.Char(
        'Source Document', index=True, readonly=True,
        states={'draft': [('readonly', False)]},
        help="Reference of the document")

    @api.depends('state')
    def _compute_show_validate(self):
        for picking in self:
            if picking.state == 'assigned' and picking.approve and self.location_id in self.env.user.stock_location_ids and self.location_dest_id in self.env.user.stock_location_ids and self.env.user.has_group(
                    'stock.group_stock_manager'):
                picking.show_validate = True
            else:
                picking.show_validate = False

    def _check_expired_lots(self):
        super(StockPicking, self)._check_expired_lots()
        expired_pickings = self.move_line_ids.filtered(lambda ml: ml.lot_id.product_expiry_alert and (not ml.location_id.scrap_location and not ml.location_dest_id.scrap_location )).picking_id
        return expired_pickings

    @api.depends('state')
    def compute_show_confirm(self):
        for picking in self:
            if picking.state == 'assigned' and not picking.approve and self.location_id in self.env.user.stock_location_ids and self.location_dest_id in self.env.user.stock_location_ids and self.env.user.has_group(
                    'stock.group_stock_user'):
                picking.show_cofirm = True
            else:
                picking.show_cofirm = False

    def _set_scheduled_date(self):
        for picking in self:
            picking.move_lines.write({'date': picking.scheduled_date})

    approve = fields.Boolean('Confirmed', copy=False, index=True)
    show_cofirm = fields.Boolean('Show Confirm', copy=False, compute='compute_show_confirm', index=True)
    keeper_id = fields.Many2one('Inventory Keeper', copy=False, index=True)

    def keeper_approve(self):
        # Clean-up the context key at validation to avoid forcing the creation of immediate
        # transfers.
        ctx = dict(self.env.context)
        ctx.pop('default_immediate_transfer', None)
        self = self.with_context(ctx)
        # Sanity checks.
        pickings_without_moves = self.browse()
        pickings_without_quantities = self.browse()
        pickings_without_lots = self.browse()
        products_without_lots = self.env['product.product']
        for picking in self:
            if not picking.move_lines and not picking.move_line_ids:
                pickings_without_moves |= picking

            picking.message_subscribe([self.env.user.partner_id.id])
            picking_type = picking.picking_type_id
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            no_quantities_done = all(
                float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in
                picking.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
            no_reserved_quantities = all(
                float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line
                in picking.move_line_ids)
            if no_reserved_quantities and no_quantities_done:
                pickings_without_quantities |= picking

            if picking_type.use_create_lots or picking_type.use_existing_lots:
                lines_to_check = picking.move_line_ids
                if not no_quantities_done:
                    lines_to_check = lines_to_check.filtered(
                        lambda line: float_compare(line.qty_done, 0, precision_rounding=line.product_uom_id.rounding))
                for line in lines_to_check:
                    product = line.product_id
                    if product and product.tracking != 'none':
                        if not line.lot_name and not line.lot_id:
                            pickings_without_lots |= picking
                            products_without_lots |= product

        if not self._should_show_transfers():
            if pickings_without_moves:
                raise UserError(_('Please add some items to move.'))
            if pickings_without_quantities:
                raise UserError(self._get_without_quantities_error_message())
            if pickings_without_lots:
                raise UserError(_('You need to supply a Lot/Serial number for products %s.') % ', '.join(
                    products_without_lots.mapped('display_name')))
        else:
            message = ""
            if pickings_without_moves:
                message += _('Transfers %s: Please add some items to move.') % ', '.join(
                    pickings_without_moves.mapped('name'))
            if pickings_without_quantities:
                message += _(
                    '\n\nTransfers %s: You cannot validate these transfers if no quantities are reserved nor done. To force these transfers, switch in edit more and encode the done quantities.') % ', '.join(
                    pickings_without_quantities.mapped('name'))
            if pickings_without_lots:
                message += _('\n\nTransfers %s: You need to supply a Lot/Serial number for products %s.') % (
                ', '.join(pickings_without_lots.mapped('name')),
                ', '.join(products_without_lots.mapped('display_name')))
            if message:
                raise UserError(message.lstrip())
        self.approve = True
        self.keeper_id = self.env.user.id
        rec = []
        recive = self.env['res.users'].search(
            [("groups_id", "=", self.env.ref('stock.group_stock_manager').id)])
        for i in recive:
            if self.location_id in self.env.user.stock_location_ids and self.location_dest_id in self.env.user.stock_location_ids:
                rec.append(i)
        self.env['mail.message'].send("Picking need to be Valdited", "Picking need to be Valdited", self._name,
                                      self.id,
                                      self.name, rec)

    def _action_done(self):
        res = super()._action_done()
        for picking in self:
            if picking.picking_type_id.code == 'incoming' and picking.picking_type_id.use_create_lots and not picking.picking_type_id.use_existing_lots:
               picking.name = self.env['ir.sequence'].next_by_code('delivered.picking')
        return res

    def action_confirm(self):
        res = super().action_confirm()
        for record in self:
            rec = []
            recive = self.env['res.users'].search(
                [("groups_id", "=", record.env.ref('stock.group_stock_user').id)])
            for i in recive:
                if record.location_id in record.env.user.stock_location_ids and record.location_dest_id in record.env.user.stock_location_ids:
                    rec.append(i)
            if rec:
                record.env['mail.message'].send("Picking been created", "Picking been created", record._name,
                                                record.id,
                                                record.name, rec)
        return res
