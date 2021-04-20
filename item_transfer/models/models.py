from odoo import api, fields, models, _, tools
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError
from odoo.exceptions import UserError, ValidationError

_STATES = [
    ('draft', 'Draft'),
    ('to_approve', 'To be approved'),
    ('leader_approved', 'Leader Approved'),
    ('qty_approved', 'Quantity Approved'),
    ('date_approved', 'Delivery Date Approved'),
    ('source_approved', 'Approved'),
    ('source_lapproved', 'Issued'),
    ('rejected', 'Rejected'),
    ('done', 'Done')
]


class ItemTransfer(models.Model):
    _name = 'item.transfer'
    _description = 'Items Transfer'
    _inherit = ['mail.thread']
    _order = 'id desc'
    _sql_constraints = [
        ('name_company_uniq', 'unique (name)', 'Transfer Referance must be unique per company !'),
    ]

    def confirm_qty(self):
        """Actions to perform when cancelling a purchase request line."""
        self.write({'state': 'qty_approved'})

    def delivery_date(self):
        """Actions to perform when cancelling a purchase request line."""
        self.write({'state': 'date_approved'})

    def button_import_transfer(self):

        self.ensure_one()
        context = {
            'default_request_id': self.id
        }
        return {
            'name': _('Import'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'item.transfer.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': context,
            'domain': [('request_id', '=', self.id)],
        }

    @api.model
    def _get_default_requested_by(self):
        return self.env['res.users'].browse(self.env.uid)

    name = fields.Char('Transfer Referance', size=32,
                       tracking=True,
                       copy=False,
                       default='New')

    date = fields.Date('Request Date',
                       help="Date when the user initiated the request.",
                       default=fields.Date.context_today,
                       copy=False,
                       tracking=True)
    requested_by = fields.Many2one('res.users',
                                   'Requested by',
                                   copy=False,

                                   tracking=True,
                                   default=_get_default_requested_by)

    description = fields.Html('Description')

    line_ids = fields.One2many('item.transfer.line', 'request_id',
                               'Products to Request',
                               readonly=False,
                               copy=True,
                               tracking=True)
    picking_done_ids = fields.Many2many('stock.picking', )
    state = fields.Selection(selection=_STATES,
                             string='Status',
                             index=True,
                             tracking=True,
                             required=True,
                             copy=False,
                             default='draft')
    source_approve = fields.Many2one("res.users", store=True, copy=False, )
    delivery_date_x = fields.Datetime('Delivery Date', store=True, copy=False, )

    location_id = fields.Many2one('stock.location', store=True
                                  , string='Source Location',
                                  domain="[('finish', '=', True),('warehouse_id', 'not in',[warehouse_dest_id])]"
                                  )

    @api.model
    def _getUserGroupId(self):
        if self.user_has_groups('restrict_warehouse.group_restrict_warehouse'):
            return [('id', '=', self.env.user.stock_location_ids.ids),
                    ('finish', '=', True),
                    ('warehouse_id', '!=', self.warehouse_id.id)]

    location_dest_id = fields.Many2one('stock.location', copy=False, string='Destination Location', store=True,
                                       domain=_getUserGroupId)

    warehouse_id = fields.Many2one('stock.warehouse', string='Source Warehouse',
                                   domain="[('id', 'not in',[warehouse_dest_id]) ]",
                                   store=True)

    warehouse_dest_id = fields.Many2one('stock.warehouse', copy=False, store=True, string='Destination Warehouse'
                                        , )

    @api.onchange('location_id', 'location_dest_id')
    def location_change(self):
        self.warehouse_id = self.location_id.warehouse_id.id
        self.warehouse_dest_id = self.location_dest_id.warehouse_id.id

    @api.depends('requested_by')
    def _compute_warehouse(self):
        self.warehouse_dest_id = self.requested_by.warehouse_ids

    @api.depends('requested_by')
    def _onchange_state(self):
        assigned_to = None
        employee = self.env['hr.employee'].search([('user_id', '=', self.requested_by.id)])
        if len(employee) > 0:
            if employee[0].department_id and employee[0].parent_id:
                assigned_to = employee[0].parent_id.user_id

            elif employee[0].department_id and employee[0].department_id.manager_id:
                assigned_to = employee[0].department_id.manager_id.user_id

            elif not employee[0].department_id:
                assigned_to = employee[0].user_id
        else:
            assigned_to = self.requested_by
        self.assigned_to = assigned_to

    assigned_to = fields.Many2one('res.users', 'Approver', compute='_onchange_state', store=True, readonly=False)

    @api.depends('requested_by')
    def _compute_department(self):
        if self.requested_by.id:
            self.department_id = None
            return
        employee = self.env['hr.employee'].search([('user_id', '=', self.requested_by.id)])
        if len(employee) > 0:
            self.department_id = employee[0].department_id.id
        else:
            self.department_id = None

    department_id = fields.Many2one('hr.department', string='Department', compute='_compute_department', store=True)

    @api.depends('state')
    def _compute_can_leader_approved(self):
        current_user_id = self.env.uid
        if self.state == 'to_approve' and self.env.user.has_group(
                'stock.group_stock_manager'):
            self.can_leader_approved = True
        if self.state == 'to_approve' and self.env.user.has_group(
                'stock.group_stock_manager'):
            self.can_leader_approved = True

        elif self.state == 'to_approve' and self.assigned_to.id == self.env.user.id:
            self.can_leader_approved = True
        else:
            self.can_leader_approved = False

    can_leader_approved = fields.Boolean(string='Can Leader approved', compute='_compute_can_leader_approved')

    @api.depends('state')
    def _compute_can_source_approved(self):
        user_locations = self.env.user.stock_location_ids

        if self.env.user.restrict_locations:
            if self.location_id in user_locations and self.state == 'date_approved':
                self.can_source_approved = True
            if self.location_id in user_locations and self.state == 'date_approved':
                self.can_source_approved = True
            else:
                self.can_source_approved = False
        else:
            self.can_source_approved = False

    can_source_approved = fields.Boolean(string='Can Leader approved', compute='_compute_can_source_approved')

    @api.depends('state')
    def _compute_can_reject(self):
        self.can_reject = self.can_leader_approved

    can_reject = fields.Boolean(string='Can reject', compute='_compute_can_reject')

    @api.depends('state')
    def _compute_can_done(self):
        x = self.env['stock.picking'].search([
            ('origin', 'in', ((self.name + '-01'), (self.name), (self.name + '-02'))), ('state', '=', 'done'), ('location_id', '=', self.location_id.id)
        ])
        if x:
            for line in x:
                if line not in self.picking_done_ids:
                    if self.location_dest_id in self.env.user.stock_location_ids:
                        self.can_done = True
                    else:
                        self.can_done = False
                else:
                    self.can_done = False
        else:
            self.can_done = False

    can_done = fields.Boolean(string='Can Done', compute='_compute_can_done')

    @api.depends('state')
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in ('rejected', 'done'):
                rec.is_editable = False
            else:
                rec.is_editable = True

    is_editable = fields.Boolean(string="Is editable",
                                 compute="_compute_is_editable",
                                 readonly=True)

    @api.model
    def create(self, data):
        if data.get('name', 'New') == 'New':
            data['name'] = self.env['ir.sequence'].next_by_code('item.transfer')
        request = super(ItemTransfer, self).create(data)
        return request

    def write(self, vals):
        res = super(ItemTransfer, self).write(vals)
        return res

    def button_draft(self):
        self.mapped('line_ids').do_uncancel()
        return self.write({'state': 'draft'})

    def unlink(self):
        if any(production.state not in ['draft', 'rejected'] for production in self):
            raise UserError(_('Cannot delete a item not in draft or cancel state'))
        return super(ItemTransfer, self).unlink()

    def button_to_approve(self):
        if not self.line_ids:
            raise UserError(_('Set lines First'))

        self.env['mail.message'].send("Message subject", 'Item Transfer Need to be approved', self._name, self.id,
                                      self.name, self.assigned_to)
        return self.write({'state': 'to_approve'})

    def send_notification_done(self):

        if self.requested_by:
            self.env['mail.message'].send("Item Transfer is ready to receive", "Item Transfer is ready to receive",
                                          self._name, self.id,
                                          self.name, self.requested_by)

        if self.assigned_to != self.requested_by:
            self.env['mail.message'].send("Item Transfer is ready to receive", "Item Transfer is ready to receive",
                                          self._name, self.id,
                                          self.name, self.assigned_to)

    def button_leader_approved(self):
        receivers_email = []
        names = self.env['res.users'].search(
            [("groups_id", "=", self.env.ref('stock.group_stock_user').id)])
        for name in receivers_email:
            if self.location_id in name.stock_location_ids:
                receivers_email.append(name)
        body = 'Item Transfer Requested From  ' + self.warehouse_id.name + ' To ' + self.warehouse_dest_id.name

        self.env['mail.message'].send(body, body,
                                      self._name,
                                      self.id,
                                      self.name,
                                      names)
        self.env['mail.message'].send(body, body,
                                      self._name,
                                      self.id,
                                      self.name,
                                      receivers_email)

        return self.write({'state': 'leader_approved'})

    @api.constrains('line_ids.qty_confirm')
    def qty_confirm_x(self):
        for record in self:
            for line in record.line_ids:
                if line.qty_confirm > line.product_qty:
                    raise ValidationError(_('Qty Confirm must not more than Quantity'))

    def button_manager_approved(self):
        copy_record = self.env['stock.picking']
        for record in self:
            item = self.env['stock.picking'].search([('origin', '=', self.name)])
            if item:
                raise UserError(_('AlReady Issued '))
            order_lines = []
            order_lines_dif = []

            for line in record.line_ids:
                if line.product_qty == line.qty_confirm:
                    order_lines.append(
                        (0, 0,
                         {
                             'name': line.product_id.name,
                             'product_id': line.product_id.id,
                             'product_uom': line.product_id.uom_id.id,
                             'location_id': self.location_id.id,
                             'location_dest_id': self.env.ref("item_transfer.transit_location").id,
                             'product_uom_qty': line.product_qty,
                             'origin': self.name,

                         }
                         ))
                if line.product_qty > line.qty_confirm :
                    order_lines.append(
                        (0, 0,
                         {
                             'name': line.product_id.name,
                             'product_id': line.product_id.id,
                             'product_uom': line.product_id.uom_id.id,
                             'location_id': self.location_id.id,
                             'location_dest_id': self.location_dest_id.id,
                             'product_uom_qty':  line.qty_confirm,
                             'origin': self.name,

                         }
                         ))
                    order_lines_dif.append(
                        (0, 0,
                         {
                             'name': line.product_id.name,
                             'product_id': line.product_id.id,
                             'product_uom': line.product_id.uom_id.id,
                             'location_id': self.location_id.id,
                             'location_dest_id': self.location_dest_id.id,
                             'product_uom_qty': line.product_qty-line.qty_confirm,
                             'origin': self.name,

                         }
                         ))

            if not record.warehouse_dest_id.sale_store:
                if order_lines:
                    copy_record.create({
                        'origin': self.name + '-01',
                        'picking_type_id': self.warehouse_id.int_type_id.id,
                        'move_ids_without_package': order_lines,
                        'location_id': self.location_id.id,
                        'location_dest_id': self.env.ref("item_transfer.transit_location").id,
                        'location': self.location_dest_id.id,
                    }).action_confirm()
                    self.assigned_for = self.env.user
                if order_lines_dif:
                    copy_record.create({
                        'origin': self.name + '-02',
                        'picking_type_id': self.warehouse_id.int_type_id.id,
                        'move_ids_without_package': order_lines_dif,
                        'location_id': self.location_id.id,
                        'location_dest_id': self.env.ref("item_transfer.transit_location").id,
                        'location': self.location_dest_id.id,
                    }).action_confirm()
                    self.assigned_for = self.env.user
            else:
                if order_lines:
                    copy_record.create({
                        'origin': self.name + '-01',
                        'picking_type_id': self.warehouse_id.int_type_id.id,
                        'move_ids_without_package': order_lines,
                        'location_id': self.location_id.id,
                        'location_dest_id': self.location_dest_id.id,
                    }).action_confirm()
                    self.assigned_for = self.env.user
                if order_lines_dif:
                    copy_record.create({
                        'origin': self.name + '-02',
                        'picking_type_id': self.warehouse_id.int_type_id.id,
                        'move_ids_without_package': order_lines_dif,
                        'location_id': self.location_id.id,
                        'location_dest_id': self.location_dest_id.id,
                    }).action_confirm()
                    self.assigned_for = self.env.user
        return self.write({'state': 'source_approved'})

    assigned_for = fields.Many2one('res.users', 'Approver', store=True)

    @api.depends('assigned_for')
    def _onchange_assigned(self):
        assigned_to = None
        employee = self.env['hr.employee'].search([('user_id', '=', self.assigned_for.id)])
        if len(employee) > 0:
            if len(employee) > 0:
                if employee[0].department_id and employee[0].department_id.parent_id:
                    assigned_to = employee[0].parent_id.user_id

                elif employee[0].department_id and employee[0].department_id.manager_id:
                    assigned_to = employee[0].department_id.manager_id.user_id

                elif not employee[0].department_id:
                    assigned_to = employee[0].user_id

        self.assigned_for_lead = assigned_to

    assigned_for_lead = fields.Many2one('res.users', 'Approver', compute='_onchange_assigned', store=True)

    def button_rejected(self):
        self.mapped('line_ids').do_cancel()
        return self.write({'state': 'rejected'})

    def button_approving(self):
        return self.write({'state': 'source_lapproved'})

    def check_auto_reject(self):
        """When all lines are cancelled the purchase request should be
        auto-rejected."""
        for pr in self:
            if not pr.line_ids.filtered(lambda l: l.cancelled is False):
                pr.write({'state': 'rejected'})

    def make_item_transfer(self):
        x = self.env['stock.picking'].search([
            ('origin', 'in', ((self.name + '-01'), (self.name), (self.name + '-02'))), ('state', '=', 'done'), ('location_id', '=', self.location_id.id)
        ])
        for picking in x:
            order_lines = []
            if picking not in self.picking_done_ids:
                self.picking_done_ids += picking
                new_picking = self.env['stock.picking'].create({
                    'origin': picking.origin,
                    'picking_type_id': self.warehouse_dest_id.int_type_id.id,
                    'location_id': picking.location_dest_id.id,
                    'location': self.location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                })
                for move in picking.move_lines:
                    move.copy({
                        'location_id': picking.location_dest_id.id,
                        'picking_id': new_picking.id,
                        'warehouse_id': self.warehouse_dest_id.id,
                        'location_dest_id': self.location_dest_id.id,
                        'picking_type_id': self.warehouse_dest_id.int_type_id.id,
                        'move_orig_ids': [(6, 0, move.ids)],

                    }
                    )
                new_picking.action_assign()

        return self.write({'state': 'done'})

    def make_it_transfer(self):
        return self.write({'state': 'done'})

    picking_count = fields.Integer(compute='_compute_picking', string='Receptions', default=0)

    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking', string='Receptions', copy=False)

    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]

        # override the context to get rid of the default filtering on picking type
        result.pop('id', None)
        result['context'] = {}
        pick_ids = sum([order.picking_ids.ids for order in self], [])
        # choose the view_mode accordingly
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result

    def _compute_picking(self):
        for order in self:
            pickings = self.env['stock.picking'].search([
                ('origin', 'in', ((self.name + '-01'), (self.name), (self.name + '-02')))
            ])
            picking_s = self.env['stock.picking']
            for picking in pickings:
                picking_s += self.env['stock.picking'].search([
                    ('origin', '=', picking.name)
                ])
            order.picking_ids = pickings + picking_s
            order.picking_count = len(pickings + picking_s)


class ItemTransferLine(models.Model):
    _name = "item.transfer.line"
    _description = "item Request Line"
    _inherit = ['mail.thread']
    request_id = fields.Many2one('item.transfer',
                                 'item Request',
                                 ondelete='cascade', readonly=True)

    product_code = fields.Char(
        'Product Code',
        tracking=True, )

    @api.depends('product_code')
    def compute_onchange_product(self):
        for line in self:
            products = self.env['product.map.line'].search(
                [('sale_code', '=', line.product_code),
                 ('distributor', '=', line.request_id.warehouse_dest_id.partner_id.id)
                 ])
            if products:

                line.product_id = products.product_id

            else:

                line.product_id = False

    @api.depends('product_id2')
    def compute_onchange_productx(self):
        for r in self:
            if r.product_id2:
                self.product_id = r.product_id2
            else:
                self.product_id = False

    product_id2 = fields.Many2one(
        'product.product', 'Product2',
        tracking=True, store=True)

    product_id = fields.Many2one(
        'product.product', 'Product',
        tracking=True, store=True, readonly=False, compute='compute_onchange_product')

    product_uom_id = fields.Many2one('uom.uom', 'Product Unit of Measure', tracking=True)

    product_qty = fields.Float('Quantity', tracking=True,
                               digits='Product Unit of Measure')

    qty_confirm = fields.Float('Qty Confirm', tracking=True,
                               digits='Product Unit of Measure')

    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 store=True, readonly=True)

    date = fields.Date(related='request_id.date',
                       string='Request Date', readonly=True,
                       store=True)

    description = fields.Html(related='request_id.description',
                              string='Description', readonly=True,
                              store=True)
    date_required = fields.Date(string='Request Date', required=True,
                                tracking=True,
                                default=fields.Date.context_today)
    location_id = fields.Many2one(related='request_id.location_id')

    specifications = fields.Text(string='Specifications')

    lot_id = fields.Many2one('stock.production.lot', 'Serial /lOT', domain="[('product_id', 'in', [product_id])]")

    request_state = fields.Selection(string='Request state',
                                     readonly=True,
                                     related='request_id.state',
                                     selection=_STATES,
                                     store=True)

    cancelled = fields.Boolean(
        string="Cancelled", readonly=True, default=False, copy=False)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            name = self.product_id.name
            if self.product_id.code:
                name = '[%s] %s' % (name, self.product_id.code)
            if self.product_id.description_purchase:
                name += '\n' + self.product_id.description_purchase
            self.product_uom_id = self.product_id.uom_id.id
            self.product_qty = 1

    def do_cancel(self):
        """Actions to perform when cancelling a purchase request line."""
        self.write({'cancelled': True})

    def do_uncancel(self):
        """Actions to perform when uncancelling a purchase request line."""
        self.write({'cancelled': False})

    def _compute_is_editable(self):
        for rec in self:
            if rec.request_id.state in ('draft', 'to_approve'):
                rec.is_editable = False
            else:
                rec.is_editable = True

    is_editable = fields.Boolean(string='Is editable',
                                 compute="_compute_is_editable",
                                 readonly=True)

    @api.model
    def create(self, data):
        res = super(ItemTransferLine, self).create(data)
        return res

    def write(self, vals):
        res = super(ItemTransferLine, self).write(vals)
        if vals.get('cancelled'):
            requests = self.mapped('request_id')
            requests.check_auto_reject()
        return res

    @api.onchange('request_id.state')
    def _compute_qty(self):
        for request in self:
            in_progress = 0
            done = 0
            cancel = 0
            moves = self.env['stock.move'].search([
                ('origin', '=', request.request_id.name), ('product_id', '=', request.product_id.id)
            ])
            for move in moves:
                if move.state not in ('cancel', 'done', 'draft') and move.location_id == self.request_id.location_id:
                    in_progress += move.product_uom_qty
                elif move.state == 'done' and move.location_dest_id == self.request_id.location_dest_id:
                    done += move.product_uom_qty
                elif move.state == 'cancel':
                    cancel += move.product_uom_qty
            request.qty_in_progress = in_progress
            request.qty_done = done
            request.qty_cancelled = cancel

    qty_in_progress = fields.Float(
        string="Qty In Progress",
        digits="Product Unit of Measure",
        readonly=True,
        compute="_compute_qty",
        store=True,
        help="Quantity in progress.",
    )

    qty_done = fields.Float(
        string="Qty Done",
        digits="Product Unit of Measure",
        readonly=True,
        compute="_compute_qty",
        store=True,
        help="Quantity completed",
    )
    qty_cancelled = fields.Float(
        string="Qty Cancelled",
        digits="Product Unit of Measure",
        readonly=True,
        compute="_compute_qty",
        store=True,
        help="Quantity cancelled",
    )

    @api.onchange('product_code')
    def compute_onchange_product_store(self):
        for line in self:

            products = self.env['sale.in.month'].search(
                [('product_code', '=', line.product_code), ('product_id', '=', line.product_id.id),
                 ('distributor', '=', line.request_id.warehouse_dest_id.partner_id.id)
                 ], order='create_date desc', )
            t = []
            for l in products:
                t.append(l.quantity)
            if t:
                x = t[0]
                line.store_qty = x
                return x

            else:

                line.store_qty = 0

    store_qty = fields.Float('Store Quantity', tracking=True,
                             digits='Product Unit of Measure', compute='compute_onchange_product_store')

    @api.onchange('qty_confirm')
    def _onchangeqtycon(self):
        if self.qty_confirm:

            if self.qty_confirm > self.product_qty:
                self.qty_confirm = 0
                return {
                    'warning': {'title': "Warning", 'message': "Qty Confirm must not more than Quantity"}}
