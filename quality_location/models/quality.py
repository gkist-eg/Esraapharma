import ast
from datetime import datetime
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.osv.expression import OR


class QualityPoint(models.Model):
    _inherit = "quality.alert.team"

    users_ids = fields.Many2many(
        'res.users',
        'quality_alert_team_allowed_users',
        'team_id',
        'user_id',
        'Team Member')
    read_users_ids = fields.Many2many(
        'res.users',
        'quality_alert_team_allowed_read_users',
        'team_id',
        'user_id',
        'Notifiy User')


class Quality(models.Model):
    _inherit = "quality.check"

    def do_fail(self):
        if self.env.user not in self.team_id.users_ids:
            raise UserError(_("You Don't have the authority to confirm"))
        return super(Quality, self).do_fail()

    def do_pass(self):
        if self.env.user not in self.team_id.users_ids:
            raise UserError(_("You Don't have the authority to confirm"))
        rec = []
        recive = self.env['res.users'].search(
            [("groups_id", "=", self.env.ref('stock.group_stock_manager').id)])
        quality_checks = self.env['quality.check'].sudo().search(
            [('product_id', '=', self.product_id.id), ('team_id', '=', self.team_id.id),
             ('id', '!=', self.id), ('quality_state', '=', 'none'),'|',
             ('finished_lot_id', '=', self.finished_lot_id.id),
             ('lot_id', '=', self.lot_id.id)])
        body =""
        if self.finished_lot_id :
            body += self.finished_lot_id.dispaly_name
        if not quality_checks:
            self.env['mail.message'].send("Finished test", " QC tests of lot " + body + " is finished and ready to be transferred", self._name,
                                      self.id,
                                      self.name, self.team_id.read_users_ids)

        return super(Quality, self).do_pass()