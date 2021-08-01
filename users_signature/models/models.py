from odoo import api, fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    segimage = fields.Binary('Signature Image', store=True)


class ResCompany(models.Model):
    _inherit = 'res.company'

    stamp = fields.Binary("Company Stamp", store=True)
