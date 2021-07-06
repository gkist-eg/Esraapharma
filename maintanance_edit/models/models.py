# -*- coding: utf-8 -*-

from odoo import models, fields, api


class maintenance_edit(models.Model):
    _name = 'equipment.brand'
    _description = 'equipment.brand'

    name = fields.Char('Brand', store=True)


class maintenance_edit2(models.Model):
    _inherit = 'maintenance.equipment'

    brand = fields.Many2one('equipment.brand', 'Brand', store=True)
    employee_have_device = fields.Many2one('hr.employee', 'Employee Have Device', store=True)
