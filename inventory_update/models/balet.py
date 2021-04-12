from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BaletLocation(models.Model):
    _name = 'balet.location'

    name = fields.Char('Name', required=True, store=True)

    _sql_constraints = [('name_unique', 'unique(name)', 'name already exists!')]


class BaletLocationChange(models.Model):
    _name = 'balet.change'
    lot_id = fields.Many2one('stock.production.lot', 'Lots/Serial Numbers', required=True)
    balet_ids = fields.Many2many('balet.location',"balet_location_change_old", string="Old Ballets", readonly='1', store=True)
    balet_new_ids = fields.Many2many('balet.location',"balet_location_change_new", string="New Ballets")
    check = fields.Boolean('Checked', default=False)

    @api.onchange('lot_id')
    def balet_lot_change(self):
        if self.lot_id:
            if not self.check and self.balet_new_ids == self.balet_ids:
                self.balet_ids = self.lot_id.balet_ids
                self.balet_new_ids = self.lot_id.balet_ids


    def confirm(self):
        self.check = True
        if self.check:
            self.lot_id.sudo().write({'balet_ids': [(6, 0, self.balet_new_ids.ids)]})
            return {'type': 'ir.actions.act_window_close'}