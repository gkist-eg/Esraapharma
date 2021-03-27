from odoo import _, api, fields, models
from odoo.exceptions import UserError
from email.mime.text import MIMEText as text
import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_round
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_STATES = [
    ("draft", "Draft"),
    ("to_approve", "To be approved"),
    ("leader_approved", "Direct Manager Approved"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("done", "Done"),
]


class ItemRequest(models.Model):
    _name = 'item.request'
    _inherit = ["mail.thread"]
    _description = 'Item Request'
    _order = 'id desc'
    name = fields.Char(
        string="Request Reference", copy=False, default='New',tracking=True
    )
    description = fields.Text()
    origin = fields.Char(string="Source Document")
    date_start = fields.Date(
        string="Creation date",
        help="Date when the user initiated the " "request.",
        default=fields.Date.context_today,
        tracking=True,
    )
    manager_line_ids = fields.One2many('item.request.line', 'request_id','Requested Products')

    @api.model
    def create(self, data):
        if data.get('name', 'New') == 'New':
            data['name'] = self.env['ir.sequence'].next_by_code('item.request')
        return super(ItemRequest, self).create(data)

    @api.model
    def _company_get(self):
        return self.env["res.company"].browse(self.env.company.id)

    @api.model
    def _get_default_requested_by(self):
        return self.env["res.users"].browse(self.env.uid)

    requested_by = fields.Many2one(
        comodel_name="res.users",
        string="Requested by",
        required=True,
        copy=False,readonly=False,
        tracking=True,
        default=_get_default_requested_by,
        index=True,
    )
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Direct Manager",
        tracking=True,
        store=True, readonly=False,
        index=True, compute="_onchange_state",
    )

    @api.depends('requested_by')
    @api.onchange('requested_by')
    def _onchange_state(self):
        assigned_to = None
        department = None
        employee = self.requested_by.employee_ids
        if len(employee) > 0:
            if employee[0].department_id:
                department = employee[0].department_id
            if employee[0].department_id and employee[0].parent_id:
                assigned_to = employee[0].parent_id.user_id
            elif employee[0].parent_id:
                assigned_to = employee[0].parent_id.user_id
            elif employee[0].department_id and employee[0].department_id.manager_id:
                assigned_to = employee[0].department_id.manager_id.user_id
            elif not employee[0].department_id:
                assigned_to = employee[0].user_id
        self.assigned_to = assigned_to
        self.department_id = department

    location_id = fields.Many2one('stock.location',
                                  string='Source Location',
                                  store=True,
                                  domain=[('usage', '=', 'internal')], required=1)
    department_id = fields.Many2one('hr.department', string='Department', compute='_onchange_state', store=True,index=True)

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=_company_get,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="item.request.line",
        inverse_name="request_id",
        string="Products to Request",
        readonly=False,
        copy=True,
        tracking=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        related="line_ids.product_id",
        string="Product",
        readonly=True,
    )
    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
    )
    is_editable = fields.Boolean(
        string="Is editable", compute="_compute_is_editable", readonly=True
    )
    to_approve_allowed = fields.Boolean(compute="_compute_to_approve_allowed")

    def button_draft(self):
        return self.write({'state': 'draft'})

    @api.depends('state')
    def _compute_can_reject(self):
        self.can_reject = (self.can_leader_approved or self.can_manager_approved)

    def button_rejected(self):
        return self.write({'state': 'rejected'})

    can_reject = fields.Boolean(string='Can reject', compute='_compute_can_reject')
    can_manager_approved = fields.Boolean(string='Can Manager approved', compute='_compute_can_manager_approved')

    @api.depends('state')
    def _compute_can_leader_approved(self):
        current_user_id = self.env.uid
        if self.state == 'to_approve' and (
                current_user_id == self.assigned_to.id):
            self.can_leader_approved = True
        else:
            self.can_leader_approved = False

    can_leader_approved = fields.Boolean(string='Can Leader approved', compute='_compute_can_leader_approved')

    def _compute_can_manager_approved(self):
        current_user = self.env.user
        if self.state == 'leader_approved' and current_user.has_group('item_request.item_request_manager') and self.location_id in current_user.multi_locations :
            self.can_manager_approved = True
        else:
            self.can_manager_approved = False

    def _can_delivered(self):
        for record in self:
            if record.state == 'done' and (
                    record.requested_by == self.env.user or record.assigned_leader == self.env.user or record.assigned_to == self.env.user):
                for line in record.line_ids:
                    if line.done > line.delivered_qty:
                        record.can_delivered = True
                    else:
                        record.can_delivered = False
            else:
                record.can_delivered = False

    def confirm_delivered(self):
        qty = 0
        for line in self.line_ids:
            line.delivered_qty = line.done
            if line.delivered_qty == line.qty_to_proved:
                qty += 1
        if qty == len(self.line_ids):
            self.receive_state = 'received'
        else:
            self.receive_state = 'partially_received'

    can_delivered = fields.Boolean(compute="_can_delivered")
    
    def _can_be_deleted(self):
        self.ensure_one()
        return self.state == "draft"

    def unlink(self):
        for request in self:
            if not request._can_be_deleted():
                raise UserError(
                    _("You cannot delete an item request which is not draft.")
                )
        return super(ItemRequest, self).unlink()

    def copy(self, default=None):
        default = dict(default or {})
        self.ensure_one()
        default.update(
            {
                "state": "draft",
                "name": self.env["ir.sequence"].next_by_code("item.request"),
            }
        )
        return super(ItemRequest, self).copy(default)

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state == 'draft':
                rec.is_editable = True
            else:
                rec.is_editable = False

    picking_count = fields.Integer(compute='_compute_picking', string='Receptions', default=0)

    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking', string='Receptions', copy=False)

    def button_manager_approved(self):

        copy_record = self.env['stock.picking']
        for record in self:
            item = self.env['stock.picking'].search([('origin', '=', self.name)])
            if item:
                raise UserError(_('AlReady Issued '))
            order_lines = []
            for line in record.line_ids:
                if line.qty > 0.0:
                    order_lines.append((0, 0, {
                        'name': line.product_id.display_name,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom_id.id,
                        'date': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'picking_type_id': self.location_id.warehouse_id.out_type_id.id,
                        'restrict_lot_id': line.lot_id.id,
                        'origin': self.name,
                        'product_uom_qty': line.qty,
                    }))
            dest_location = self.env.ref("item_request.emploee_location").id
            copy_record.create({
                'origin': self.name,
                'picking_type_id': self.location_id.warehouse_id.out_type_id.id,
                'move_ids_without_package': order_lines,
                'location_id': self.location_id.id,
                'location_dest_id': dest_location,
                'partner_id': self.requested_by.partner_id.id,
            }).action_assign()
        self.line_ids._compute_qty()
        self.state = 'approved'

    def action_view_picking(self):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        When only one found, show the picking immediately.
        '''
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
                ('origin', '=', self.name)
            ])
            order.picking_ids = pickings
            order.picking_count = len(pickings)
    
    def button_to_approve(self):
        if not self.line_ids:
            raise UserError(_('Not thing to approve.'))
        if not self.department_id:
            raise UserError(_('You are not assigned to any department please contact your hr .'))
        # self.env['mail.message'].send("Message subject", 'Item request Need to be approved', self._name, self.id,
        #                               self.name, self.assigned_to)
        for l in self.line_ids:
            if l.product_qty <= 0:
                raise UserError(_('Quantity Can not be zero.'))
        self.env['mail.message'].send("Message subject", 'Item request Need to be approved', self._name, self.id,
                                      self.name, self.assigned_to)
        return self.write({'state': 'to_approve'})
    
    def button_leader_approved(self):
        recives = self.env['res.users']
        recive = self.env['res.users'].search(
                [("groups_id", "=", self.env.ref('item_request.item_request_manager').id)])
        for i in recive:
            if self.location_id in i.multi_locations:
                recives += i
        self.env['mail.message'].send("Message subject", 'Item request Need to be approved', self._name, self.id,
                                      self.name, recives)
        return self.write({'state': 'leader_approved'})




class ItemRequestLine(models.Model):

    _name = "item.request.line"
    _description = "Item Request Line"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _sql_constraints = [
        ('name_company_uniq', 'unique (name,company_id)', 'The request name must be unique per company !'),
    ]
    name = fields.Char(string="Description", tracking=True)
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Product Unit of Measure",
        tracking=True,
    )

    product_id = fields.Many2one("product.product", string="Product", tracking=True, required=True, domain="[('stock_quant_ids.location_id','=',location_id)]")

    lot_id = fields.Many2one('stock.production.lot', 'Serial/LOT', domain="[('quant_ids.location_id', '=', location_id), ('product_id', '=', product_id)]")

    product_qty = fields.Float(
        string="Quantity", tracking=True, digits="Product Unit of Measure"
    )

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
            domain = {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
            return {'domain': domain}
    qty = fields.Float(
        string="Confirmed Qty", tracking=True, digits="Product Unit of Measure"
    )
    request_id = fields.Many2one(
        comodel_name="item.request",
        string="Item Request",
        ondelete="cascade",
        readonly=True,
        index=True,
        auto_join=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="request_id.company_id",
        string="Company",
        store=True,
    )

    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        tracking=True,
    )

    date_start = fields.Date(related="request_id.date_start", store=True)

    date_required = fields.Date(
        string="Request Date",
        required=True,
        tracking=True,
        default=fields.Date.context_today,
    )
    is_editable = fields.Boolean(
        string="Is editable", compute="_compute_is_editable", readonly=True
    )

    @api.depends("request_id.state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.request_id.state == 'draft' and rec.request_id.requested_by == self.env.user:
                rec.is_editable = True
            elif rec.request_id.state == 'to_approve' and rec.request_id.assigned_to == self.env.user.id:
                rec.is_editable = True
            else:
                rec.is_editable = False

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
                if move.state not in ('cancel', 'done', 'draft'):
                    in_progress += move.product_uom_qty
                elif move.state == 'done':
                    done += move.product_uom_qty
                elif move.state == 'cancel':
                    cancel += move.product_uom_qty
            request.qty_in_progress = in_progress
            request.qty_done = done
            request.qty_cancelled = cancel

    # @api.onchange('request_id.location_id')
    # def _compute_location(self):
    #     self.location_id = self.request_id.location_id

    request_state = fields.Selection(
        string="Request state",
        related="request_id.state",
        selection=_STATES,
        store=True,
    )

    cancelled = fields.Boolean(
        string="Cancelled", readonly=True, default=False, copy=False
    )

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
    location_id = fields.Many2one(string='Source Location',
                                  store=True,
                                  related='request_id.location_id',
                                  readonly = True
                                  # compute='_compute_location',
                            )

    @api.onchange('product_qty')
    def _compute_value(self):
        self.qty = self.product_qty

    @api.model
    def _get_default_requested_by(self):
        return self.env["res.users"].browse(self.env.uid)

    requested_by = fields.Many2one(
        comodel_name="res.users",
        string="Requested by",
        copy=False,
        tracking=True,
        default=_get_default_requested_by,
        index=True,
    )
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Direct Manager",
        tracking=True,
        store=True,
        index=True, compute="_onchange_state",
    )

    @api.depends('requested_by')
    def _onchange_state(self):
        assigned_to = None
        department = None
        employee = self.requested_by.employee_ids
        if len(employee) > 0:
            if employee[0].department_id:
                department = employee[0].department_id
            if employee[0].department_id and employee[0].parent_id:
                assigned_to = employee[0].parent_id.user_id
            elif employee[0].parent_id:
                assigned_to = employee[0].parent_id.user_id
            elif employee[0].department_id and employee[0].department_id.manager_id:
                assigned_to = employee[0].department_id.manager_id.user_id
            elif not employee[0].department_id:
                assigned_to = employee[0].user_id
        self.assigned_to = assigned_to
        self.department_id = department


    department_id = fields.Many2one('hr.department', string='Department', compute='_onchange_state', store=True,)