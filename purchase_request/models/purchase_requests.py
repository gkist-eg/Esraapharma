from datetime import datetime, time, timedelta
from odoo import api, fields, models, _


class PurchaseRequests(models.Model):
    _name = "purchase.requests"
    _description = "Purchase Requests"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    @api.model
    def gettt_values(self):
        purchase_approv = self.env.ref('purchase_request.id_purchase_approve_parm').sudo().value
        return int(purchase_approv)

    @api.model
    def _get_default_requested_by(self):
        if self.env.uid != 1:
            return self.env["res.users"].browse(self.env.uid)
        else:
            purchase_default = self.env.ref('purchase_request.id_purchase_request_default').sudo().value
            return self.env["res.users"].browse(int(purchase_default))


    @api.model
    def _get_default_departmnt_id(self):
        if self.env.uid != 1:
            departmnt = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).department_id
            return departmnt.id
        else:
            purchase_default = self.env.ref('purchase_request.id_purchase_request_default').sudo().value
            departmnt = self.env['hr.employee'].search([('user_id', '=', int(purchase_default))], limit=1).department_id
            return departmnt.id


    # @api.model
    # def _get_default_departmnt_user_id(self):
    #     departmnt=self.env['hr.employee'].search([('id','=',self.env.ref('purchase_request.id_department_purchase').id)],limit=1)
    #     return departmnt.id

    @api.model
    def _get_default_approver_id(self):
        if self.env.uid != 1:
            approver = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).parent_id
            return approver.id
        else:
            purchase_default = self.env.ref('purchase_request.id_purchase_request_default').sudo().value
            approver = self.env['hr.employee'].search([('user_id', '=',  int(purchase_default))], limit=1).parent_id
            return approver.id

    def name_get(self):
        res = []
        for rec in self:
            name = rec.nname + ' ' + rec.name
            res.append((rec.id, name))
        return res

    nname = fields.Char('Request Name', tracking=True, required=True)
    name = fields.Char('Serial', readonly=False, select=True, copy=False, default='New', tracking=True)
    requested_by_id = fields.Many2one('res.users', string='Requested By', readonly=False,
                                      track_visibility="onchange", default=_get_default_requested_by, tracking=True,
                                      copy=False)
    departmnt_id = fields.Many2one('hr.department', string='Department', copy=False, readonly=False,
                                   default=_get_default_departmnt_id, tracking=True)
    # departmnt_user_id = fields.Many2one('hr.department', string='Departmnt User', copy=False, readonly=True,default=_get_default_departmnt_user_id,tracking=True)
    request_line_ids = fields.One2many('purchase.request.line', 'request_line_id', string='Requested Product',
                                       tracking=True)
    approver_id = fields.Many2one('hr.employee', string='Direct Manager', readonly=False, copy=False,
                                  default=_get_default_approver_id, tracking=True)
    purchase_approver_id = fields.Many2one('res.users', string='Purchase Approver', readonly=True, copy=False,
                                           default=gettt_values, tracking=True)
    prioritty = fields.Selection([('urgent', 'Urgent'), ('high', 'High'), ('low', 'Low')], string="Priority",
                                 tracking=True, required=True)
    start_date = fields.Date("Creation Date", default=fields.Date.today, tracking=True, readonly=False)
    due_date = fields.Date("Due Date", tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments', tracking=True)
    request_category_id = fields.Many2one('product.category', string='Request Category', tracking=True, required=True)
    product_id = fields.Many2one('product.product', related='request_line_ids.product_id', string='Requested Product', )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'To Be Approved'),
        ('leader_approved', 'Leader Approved'),
        ('maneger_approved', 'Manager Approved'),
        ('request_approved', 'Request Approved'),
        ('fully_quotationed', 'Fully Quotationed'),
        ('cancel', 'Cancelled'),
    ], default='draft', readonly=False, tracking=True, store=True)

    to_be_approve = fields.Boolean("To Be Approved", default=False, compute="get_buttom_to_be_approv")
    to_reset = fields.Boolean("To Be Approved", default=False, compute="get_buttom_to_be_approv")
    is_approve_leader = fields.Boolean("leader Approved", default=False, compute="hide_buttom_leader_approv")
    is_leader_purchase = fields.Boolean("is_leader_purchase", default=False, compute="get_button_general")
    is_request_approv = fields.Boolean("is_request_approv", default=False, compute="get_button_request_approve")
    is_tap_qoutation = fields.Boolean("is_tap_qoutation", default=False, compute="get_button_quotation")
    is_tap_stte = fields.Boolean("is_tap_qoutation", default=False, compute="get_state_quotation")
    descript = fields.Html(string='Description')
    created_on = fields.Datetime("Created On", default=fields.Datetime.now, readonly=True, tracking=True)
    created_by = fields.Many2one('res.users', string='Created By', default=_get_default_requested_by, readonly=True,
                                 tracking=True)
    is_readonly = fields.Boolean(string="", compute="get_is_readonly")
    user_id = fields.Many2one(comodel_name="res.users", string="", required=False)

    @api.depends('state')
    def get_is_readonly(self):
        for rec in self:
            if rec.state == 'draft':
                rec.is_readonly = True
            elif rec.state == 'to_be_approved':
                if self.env.user.id == rec.approver_id.user_id.id:
                    rec.is_readonly = True
                else:
                    rec.is_readonly = False
            else:
                if self.env.user.id == rec.purchase_approver_id.id:
                    rec.is_readonly = True
                else:
                    rec.is_readonly = False

    # @api.depends('state')
    # def get_is_readonly(self):
    #     for rec in self:
    #         if rec.state == 'draft':
    #             rec.user_id = False
    #         elif rec.state == 'to_be_approved':
    #             rec.user_id = rec.approver_id.user_id.id
    #         else:
    #             rec.user_id = rec.purchase_approver_id.id

    def get_buttom_to_be_approv(self):
        for rec in self:
            if rec.env.user.id == rec.requested_by_id.id and rec.state == "draft":
                rec.to_be_approve = True
            else:
                rec.to_be_approve = False
            if rec.env.user.id == rec.requested_by_id.id and rec.state == "to_be_approved":
                rec.to_reset = True
            elif rec.env.user.id == rec.approver_id.user_id.id and rec.state == "leader_approved":
                rec.to_reset = True
            elif rec.env.user.id == rec.purchase_approver_id.id and rec.state == "maneger_approved":
                rec.to_reset = True
            else:
                rec.to_reset = False

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def hide_buttom_leader_approv(self):
        for rec in self:
            if rec.env.user.id == rec.approver_id.user_id.id and rec.state == "to_be_approved":
                rec.is_approve_leader = True
            else:
                rec.is_approve_leader = False

    def get_button_general(self):
        for rec in self:
            if rec.env.user.id == rec.purchase_approver_id.id and rec.state == "leader_approved":
                rec.is_leader_purchase = True
            else:
                rec.is_leader_purchase = False

    def get_button_quotation(self):
        for rec in self:
            if rec.env.user.id == rec.purchase_approver_id.id and rec.state == "request_approved":
                rec.is_tap_qoutation = True
            else:
                rec.is_tap_qoutation = False

    def get_button_request_approve(self):
        for rec in self:
            if rec.env.user.id == rec.purchase_approver_id.id and rec.state == "maneger_approved":
                rec.is_request_approv = True
            else:
                rec.is_request_approv = False

    @api.onchange("prioritty")
    def get_due_date(self):
        for rec in self:
            if rec.prioritty == "urgent":
                rec.due_date = rec.start_date + timedelta(days=5)
            elif rec.prioritty == "high":
                rec.due_date = rec.start_date + timedelta(days=10)
            elif rec.prioritty == "low":
                rec.due_date = rec.start_date + timedelta(days=15)
            else:
                rec.due_date = False

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.requests') or 'New'
        result = super(PurchaseRequests, self).create(vals)
        return result

    def purchase_approval(self):
        for rec in self:
            self.env['mail.message'].send("Purchase Request", 'Purchase Request need to be approved', self._name,
                                          self.id,
                                          self.name, self.approver_id.user_id)
            rec.state = "to_be_approved"

    def leadr_approved(self):
        for rec in self:
            self.env['mail.message'].send("Purchase Request", 'Purchase Request need to be approved', self._name,
                                          self.id,
                                          self.name, self.purchase_approver_id)
            rec.state = "leader_approved"

    def manegr_approved(self):
        for rec in self:
            rec.state = "maneger_approved"

    def requst_approved(self):
        for rec in self:
            recive = self.env['res.users'].search(
                [("groups_id", "=", self.env.ref('purchase.group_purchase_user').id)])

            self.env['mail.message'].send("Purchase Request", 'New Purchase Request been approved', self._name, self.id,
                                          self.name, recive)
            rec.state = "request_approved"

    def reset_action(self):
        for rec in self:
            if rec.state == "request_approved":
                rec.state = "maneger_approved"
            elif rec.state == 'maneger_approved':
                rec.state = "leader_approved"
            elif rec.state == 'leader_approved':
                rec.state = "to_be_approved"
            elif rec.state == 'to_be_approved':
                rec.state = "draft"

    def tap_for_quotation(self):
        order_linee = []
        attache = []
        for rec in self:
            for attach in rec.attachment_ids:
                attache.append(attach.id)
            # rec.state="fully_quotationed"
            # if line.state != "fully_quotationed":#for make product line of
            for line in rec.request_line_ids:
                order_linee.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'product_qty': line.product_qty,
                    'product_uom': line.product_uom_id.id,
                    'attachmentt_ids': [a.id for a in line.attachment_ids],
                    'purchase_requests_id': self.id,
                    'purchase_request_line': [line.id],

                }))

        return {
            'name': 'New Quotation',
            'domain': [],
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                "default_order_line": order_linee,
                "default_date_planned": self.due_date,
                "default_request_name": self.nname,
                "default_purchase_requests": self.id,
                "default_product_category_id": self.request_category_id.id,
                "default_attachmentt_ids": [i.id for i in self.attachment_ids],
                "default_purchase_request_ids": [self.id],
                "default_is_order_categ": [self.id],

            },
            'target': 'new',
        }

    @api.onchange("request_category_id")
    def delete_id_request_category(self):
        for rec in self:
            rec.request_line_ids = False

    @api.depends("request_line_ids")
    def get_state_quotation(self):
        fully_quotation = True
        is_lin = False
        for rec in self:
            for line in rec.request_line_ids:
                is_lin = True
                if line.state != "fully_quotationed":
                    fully_quotation = False
            if fully_quotation and is_lin:
                rec.state = "fully_quotationed"
            # else:
            #     rec.state=rec.state
            rec.is_tap_stte = True
