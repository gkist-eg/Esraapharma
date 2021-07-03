from odoo import models, fields, api, _
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

    equipment = fields.Many2one('maintenance.equipment', 'Equipment', store=True, domain=_getequipment, required=True)

    @api.onchange('equipment')
    def onchange_equipment(self):
        for record in self:
            if record.equipment:
                record.from_user = record.equipment.employee_have_device
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
                record.assign_date = False

    @api.onchange('employee')
    def onchange_employee(self):
        for record in self:
            if record.employee:
                record.to_user = record.employee.parent_id.user_id

            else:
                record.to_user = False

    from_user = fields.Many2one('hr.employee', string='From Employee', store=True, readonly=True, )
    to_user = fields.Many2one('res.users', 'Manager', store=True, required=True)
    employee = fields.Many2one('hr.employee', 'To Employee', store=True, required=True)
    date = fields.Date('Date', store=True, required=True)
    assign_date = fields.Date('Receive Date', store=True, )
    brand = fields.Many2one('equipment.brand', store=True)
    model = fields.Char('Model', store=True)
    serial_no = fields.Char('Serial No', store=True)
    note = fields.Text('Describtion', store=True)

    def button_send(self):

        self.write({'state': 'send'})

    def button_receive(self):
        if self.equipment:
            for line in self:
                equipment = self.env['maintenance.equipment'].search([('id', '=', self.equipment.id),
                                                                      ])

                for x in equipment:
                    x.employee_id = line.employee
        self.write({'state': 'receive'})

    @api.model
    def _get_default_employee_id(self):
        return self.env['res.users'].browse(self.env.uid)

    employee_id = fields.Many2one('res.users', 'User', readonly=True, index=True, tracking=True,
                                  default=_get_default_employee_id, copy=False, store=True)

    @api.depends('employee')
    def _compute_employee_department(self):
        for r in self:
            if self.employee:
                r.department_id = r.employee.department_id
            else:
                r.department_id = False

    department_id = fields.Many2one('hr.department', compute='_compute_employee_department', store=True, readonly=True,

                                    string="Department")

    @api.depends('state')
    def _compute_can_manager(self):

        if self.env.uid == self.to_user.id and self.state == 'send':
            self.can_leader_approved = True
        else:
            self.can_leader_approved = False

    can_leader_approved = fields.Boolean(string='Can Leader approved', compute='_compute_can_manager')


class maintenance_stage(models.Model):
    _inherit = 'maintenance.stage'

    type = fields.Selection([('creator', 'Creator'), ('technical', 'Technical')],store=True)


class maintenance_request(models.Model):
    _inherit = 'maintenance.request'
    cost=fields.Char('Cost',store=True)
    type = fields.Selection([('in_company', 'In Company'), ('out_company', 'Out Company')],store=True)

    @api.constrains('stage_id')
    def _check_actual_visit(self):
       if self.stage_id:
        for record in self:

            if self.stage_id.type == 'creator' and self.employee_id.user_id.id != self.env.uid:
                raise ValidationError(_('Creator the only one modify this stage') )
            elif self.stage_id.type == 'technical' and self.user_id.id != self.env.uid:
                raise ValidationError(_('Technical the only one modify this stage') )
