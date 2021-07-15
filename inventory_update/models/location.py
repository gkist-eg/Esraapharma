from odoo import models, fields, api


class Locations(models.Model):
    _inherit = 'stock.location'

    type = fields.Selection([
        ('normal', 'Normal'), ('plan', 'Sample Location'),
        ('mfo', 'Manufacturing to Other')], string='Location Usage',
        copy=True, store=True, track_visibility='onchange', default='normal', )
    stock_usage = fields.Selection([('release', 'Release Location'),
                                    ('qrtin', 'Quarantine Location'),
                                    ('receipt', 'receipt Location'),
                                    ('reject', 'Reject Location'),
                                    ('production', 'Production Location')], store=True, string='Internal Location Type')

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', store=True)
    categ_id = fields.Many2many('product.category', string='Default Category', store=True)
    finish = fields.Boolean('Source Location', store=True)
    origin = fields.Char('Store Code', default=lambda self: self.env['ir.sequence'].next_by_code('stock.code'))
    scrap_stock = fields.Boolean(
        string="can scrap on",
        store=True)

    def should_bypass_reservation(self):
        self.ensure_one()
        return self.usage in ('supplier', 'customer', 'inventory', 'production') or self.scrap_location
