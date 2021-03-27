# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError


class NotificationUpdate(models.Model):
    _inherit = 'mail.message'

    def send(self, subject, body, model, res_id, record_name, recievers):

        self.env.cr.execute(
            "INSERT into mail_message(message_type,subject,body,model,res_id,subtype_id,author_id,create_uid,write_uid,record_name,create_date,write_date,date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (
                "notification", subject, body, model, res_id, '1',
                str(self.env.user.partner_id.id), str(self.env.user.id), str(self.env.user.id), record_name,
                datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)))
        pairs = self.env.cr.fetchone()
        for line in recievers:
            self.env.cr.execute(
                "INSERT into mail_message_res_partner_rel(mail_message_id,res_partner_id) VALUES (%s,%s) ",
                (pairs, line.partner_id.id))
            self.env.cr.execute(
                "INSERT into mail_message_res_partner_needaction_rel(mail_message_id,res_partner_id,notification_type) VALUES (%s,%s,%s) RETURNING id",
                (pairs, line.partner_id.id,'inbox'))


