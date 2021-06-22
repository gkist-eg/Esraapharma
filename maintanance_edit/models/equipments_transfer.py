from odoo import models, fields, api,_
from odoo.exceptions import UserError, ValidationError

_STATES = [
    ('draft', 'Draft'),
    ('send', 'Send'),
    ('receive', 'Receive')
]


class maintenance_edit(models.Model):
    _name = 'equipment.transfer'
    _description = 'equipment.transfer'
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    file_attach = fields.Binary('Attach File', visibility='onchange', )

    state = fields.Selection(selection=_STATES, string='Status', index=True, tracking=True, required=True,
                             copy=False, default='draft', store=True)

    @api.depends('maintenance_team')
    def get_equipment(self):
        for p in self:
            employees = self.env['maintenance.equipment'].search([('maintenance_team_id', '=', p.maintenance_team.id),
                                                                  ])
            if employees:
                for employee in employees:
                    p.equipment = employee.id

    @api.model
    def _getequipment(self):
        t = []
        equipment = self.env['maintenance.equipment'].search([('technician_user_id', '=', self.env.uid),
                                                             ])

        if equipment:
            for l in equipment:
                t.append(l.id)
            return [('id', 'in', t)]

    equipment = fields.Many2one('maintenance.equipment', 'Equipment', store=True, domain=_getequipment)

    @api.depends('equipment')
    def onchange_equipment(self):
        for record in self:
            if record.equipment:
                record.from_user = record.equipment.employee_id
                record.brand = record.equipment.brand
                record.model = record.equipment.model
                record.serial_no = record.equipment.serial_no
                record.note = record.equipment.note
                record.assign_date = record.equipment.assign_date
            else:
                record.from_user = False
                record.brand = False
                record.model = False
                record.serial_no = False
                record.note = False
                record.assign_date= False

    from_user = fields.Many2one('hr.employee', string='From User', store=True, compute='onchange_equipment')
    to_user = fields.Many2one('res.users', 'To User', store=True)
    date = fields.Date('Date', store=True)
    assign_date = fields.Date('Receive Date', store=True,compute='onchange_equipment')
    brand = fields.Many2one('equipment.brand', compute='onchange_equipment')
    model = fields.Char('Model', compute='onchange_equipment')
    serial_no = fields.Char('Serial No', compute='onchange_equipment')
    note = fields.Text('Describtion', compute='onchange_equipment')

    def button_send(self):

        self.write({'state': 'send'})

    def button_receive(self):
        self.write({'state': 'receive'})

    @api.model
    def _get_default_employee_id(self):
        return self.env['res.users'].browse(self.env.uid)

    employee_id = fields.Many2one('res.users', 'Employee', readonly=True, index=True, tracking=True,
                                  default=_get_default_employee_id, copy=False)
