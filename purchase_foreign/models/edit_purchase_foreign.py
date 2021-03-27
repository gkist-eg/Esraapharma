# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EditPurchaseOrder(models.Model):
    _inherit = "purchase.order"

    statt = fields.Selection([
        ('import_approval', ' Import Approval'),
        ('transfer_money', 'Transfer Money'),
        ('send_swift', 'Send Swift'),
        ('send_doc', 'Send Doc'),
        ('send_form', 'Send Form4'),
        ('moh', 'MOH Release'),
        ('clearance', 'Clearance'),
    ], default='import_approval', readonly=True)
    attachmenttt_id = fields.Many2many('ir.attachment', 'attache', string='Attachments', )
    DateDate = fields.Date("Date", default=fields.Date.today, tracking=True, )
    foreign_ids = fields.One2many('purchase.foreignn', 'foreign_id', string='foreign_ids', tracking=True)
    is_country = fields.Boolean("is country", default=False)
    is_invisible = fields.Boolean("is invisible", default=False)
    due_term = fields.Html("body")
    note = fields.Text("Note", )

    def action_confirm_conf(self):
        attachmenttt_id = []
        note = []
        DateDate = []
        for rec in self:
            if rec.statt == "import_approval":
                rec.statt = "transfer_money"
                foriegn = self.env['purchase.foreignn'].create(
                    {
                        'foreign_id': rec.id,
                        'name': 'Transfer Money',
                        'attachment_id': rec.attachmenttt_id,
                        'note': rec.note,
                        'DateDate': rec.DateDate,
                    })
            elif rec.statt == "transfer_money":
                rec.statt = "send_swift"
                foriegn = self.env['purchase.foreignn'].create(
                    {
                        'foreign_id': rec.id,
                        'name': 'Send Swift',
                        'attachment_id': rec.attachmenttt_id,
                        'note': rec.note,
                        'DateDate': rec.DateDate,
                    })
            elif rec.statt == "send_swift":
                rec.statt = "send_doc"
                foriegn = self.env['purchase.foreignn'].create(
                    {
                        'foreign_id': rec.id,
                        'name': 'Send Doc',
                        'attachment_id': rec.attachmenttt_id,
                        'note': rec.note,
                        'DateDate': rec.DateDate,
                    })
            elif rec.statt == "send_doc":
                rec.statt = "send_form"
                foriegn = self.env['purchase.foreignn'].create(
                    {
                        'foreign_id': rec.id,
                        'name': 'Send Form4',
                        'attachment_id': rec.attachmenttt_id,
                        'note': rec.note,
                        'DateDate': rec.DateDate,
                    })
            elif rec.statt == "send_form":
                rec.statt = "moh"
                foriegn = self.env['purchase.foreignn'].create(
                    {
                        'foreign_id': rec.id,
                        'name': 'MOH Release',
                        'attachment_id': rec.attachmenttt_id,
                        'note': rec.note,
                        'DateDate': rec.DateDate,
                    })
            elif rec.statt == "moh":
                rec.statt = "clearance"
                rec.is_invisible = True
                foriegn = self.env['purchase.foreignn'].create(
                    {
                        'foreign_id': rec.id,
                        'name': 'Clearance',
                        'attachment_id': rec.attachmenttt_id,
                        'note': rec.note,
                        'DateDate': rec.DateDate,
                    })
                self._create_picking()



    @api.onchange("partner_id")
    def get_currency_id(self):
        for rec in self:
            rec.currency_id = rec.partner_id.property_purchase_currency_id
            country_id = self.env.ref('base.eg').id
            if country_id == rec.partner_id.country_id.id or rec.partner_id.country_id.name == "Egypt":
                rec.is_country = True
            else:
                rec.is_country = False



    def button_confirm(self):
        self.state = "sent"
        # self.approverrr_id=self.env.user.id
        res=super(EditPurchaseOrder, self).button_confirm()
        return res



    def button_approve(self, force=False):
        self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
        self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        if self.is_country:
            self._create_picking()
        return True

    class PurchaseOrderForeign(models.Model):
        _name = "purchase.foreignn"
        _description = "Purchase Foreign"

        name = fields.Char("state")
        attachment_id = fields.Many2many('ir.attachment', string='Attachments', )
        note = fields.Text("Note",)
        DateDate = fields.Date("Date", default=fields.Date.today,  )
        foreign_id = fields.Many2one('purchase.order', string='Purchase foreign', )