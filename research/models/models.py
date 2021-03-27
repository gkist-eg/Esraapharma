from odoo import models, fields, api, _
from odoo.exceptions import UserError


class research(models.Model):
    _inherit = 'mrp.bom'

    @api.constrains('bom_line_ids', 'product_qty', 'type', 'product_uom_id')
    def _constraint_bom_line_ids(self):
        if self.type == 'phantom' and not self.env.user.has_group('research.group_research_user'):
            raise UserError(_('Bulk can not been updated'))

        if self.type != 'phantom' and not self.env.user.has_group('mrp.group_mrp_manager'):
            raise UserError(_('Bom can not been updated'))
