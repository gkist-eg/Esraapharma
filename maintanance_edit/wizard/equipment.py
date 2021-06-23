from odoo import fields, models


class ActualVisit(models.TransientModel):
    _name = 'equipment.equipment'
    _description = 'equipment'

    line_ids = fields.One2many('equipment.statement', 'wizard_id', required=True, ondelete='cascade')
    department = fields.Many2one('hr.department')

    def print_device(self):
        line_ids = []

        # Unlink All one2many Line Ids from same wizard
        for wizard_id in self.env['equipment.statement'].search([('wizard_id', '=', self.id)]):
            if wizard_id.wizard_id.id == self.id:
                self.write({'line_ids': [(3, wizard_id.id)]})
                # Creating Temp dictionary for Product List
        for wizard in self:
            if wizard.department:

                actual_visit = self.env['maintenance.equipment'].search(

                    [
                        ('employee_id.department_id', '=', wizard.department.id)
                    ])
                for a in actual_visit:
                    line_ids.append((0, 0, {
                        'equipment': a.name,
                        'note': a.note,
                        'model': a.model,
                        'serial_no': a.serial_no,
                        'brand': a.brand.id,
                        'category_id': a.category_id.id,


                    }))

        self.write({'line_ids': line_ids})
        context = {
            'lang': 'en_US',
            'active_ids': [self.id],
        }
        return {
            'context': context,
            'data': None,
            'type': 'ir.actions.report',
            'report_name': 'maintanance_edit.equipment',
            'report_type': 'qweb-html',
            'report_file': 'maintanance_edit.equipment',
            'name': 'Equipment',
            'flags': {'action_buttons': True},

        }


class ActualApp(models.TransientModel):
    _name = 'equipment.statement'

    wizard_id = fields.Many2one('equipment.equipment', required=True, ondelete='cascade')

    device = fields.Char('device')
    brand = fields.Many2one('equipment.brand')
    category_id = fields.Many2one('maintenance.equipment.category')
    note = fields.Char('note')
    model = fields.Char('model')
    serial_no = fields.Char('serial_no')
    equipment = fields.Char('serial_no')
