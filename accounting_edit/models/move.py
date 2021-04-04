from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    picking_ids = fields.Many2many(
        comodel_name='stock.picking', string='Related Pickings',
        copy=False,
        help="Related pickings "
             "(only when the invoice has been generated from a sale order).", compute='compute_picking_ids')

    def compute_picking_ids(self):
        for record in self:
                picking = self.env['stock.picking'].search([('origin', '=', record.invoice_origin), ('state', '=', 'done')])
                record.picking_ids += picking