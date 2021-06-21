from odoo import models, fields, api

_STATES = [
    ('draft', 'Draft'),
    ('send', 'Send'),
    ('receive', 'Receive')
]


class maintenance_edit(models.Model):
    _name = 'equipment.transfer'
    _description = 'equipment.transfer'
    state = fields.Selection(selection=_STATES, string='Status', index=True, tracking=True, required=True,
                             copy=False, default='draft', store=True)

    equipment = fields.Many2one('maintenance.equipment', 'Equipment', store=True)
    from_user = fields.Many2one('res.users', 'From User', store=True)
    to_user = fields.Many2one('res.users', 'To User', store=True)
    date = fields.Date('Date', store=True)
    brand = fields.Many2one(related="equipment.brand")
    model = fields.Char(related="equipment.model")
    serial_no = fields.Char(related="equipment.serial_no")
    note = fields.Text(related="equipment.note")

    def button_send(self):

        self.write({'state': 'send'})

    def button_receive(self):
        self.write({'state': 'receive'})
