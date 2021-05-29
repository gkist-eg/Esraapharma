from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_round, float_compare


class Worpkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    user_ids = fields.Many2many(
        'res.users',
        'mrp_workcenter_security_users',
        'workcenter_id',
        'user_id',
        'Allowed Users')


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'
    batch = fields.Char('Batch Number',related='production_id.batch', index=True, copy=False, tracking=True,readonly=True,store =True)

    def _get_duration_expected(self, alternative_workcenter=False, ratio=1):
        self.ensure_one()
        if not self.workcenter_id:
            return self.duration_expected
        if not self.operation_id:
            duration_expected_working = (self.duration_expected - self.workcenter_id.time_start - self.workcenter_id.time_stop) * self.workcenter_id.time_efficiency / 100.0
            if duration_expected_working < 0:
                duration_expected_working = 0
            return self.workcenter_id.time_start + self.workcenter_id.time_stop + duration_expected_working * ratio * 100.0 / self.workcenter_id.time_efficiency
        qty_production = self.production_id.product_uom_id._compute_quantity(self.qty_production, self.production_id.product_id.uom_id)
        cycle_number = 1
        if alternative_workcenter:
            # TODO : find a better alternative : the settings of workcenter can change
            duration_expected_working = (self.duration_expected - self.workcenter_id.time_start - self.workcenter_id.time_stop) * self.workcenter_id.time_efficiency / (100.0 * cycle_number)
            if duration_expected_working < 0:
                duration_expected_working = 0
            return alternative_workcenter.time_start + alternative_workcenter.time_stop + cycle_number * duration_expected_working * 100.0 / alternative_workcenter.time_efficiency
        time_cycle = self.operation_id and self.operation_id.time_cycle or 60.0
        return self.workcenter_id.time_start + self.workcenter_id.time_stop + cycle_number * time_cycle * 100.0 / self.workcenter_id.time_efficiency


    def action_generate_serial(self):
        self.ensure_one()
        self.finished_lot_id = self.env['stock.production.lot'].create({
            'product_id': self.product_id.id,
            'company_id': self.company_id.id,
            'ref': self.batch,
        })

    def button_start(self):
        not_done = self.env['stock.picking'].search([('origin', '=', self.production_id.name), ('state', 'not in', ('done', 'cancel')), ('location_dest_id', '=', self.production_id.location_src_id.id)])
        if not_done:
            raise UserError(_('Material is not found'))
        if self.workcenter_id and self.env.user.id not in self.workcenter_id.user_ids.ids:
            raise UserError(_('You are not allowed to access this workorder'))
        res = super().button_start()
        return res

    def open_tablet_view(self):
        self.ensure_one()
        not_done = self.env['stock.picking'].search(
            [('origin', '=', self.production_id.name), ('state', 'not in', ('done', 'cancel')),
             ('location_dest_id', '=', self.production_id.location_src_id.id)])
        if not_done:
            raise UserError(_('Material is not found'))
        if self.workcenter_id and self.env.user.id not in self.workcenter_id.user_ids.ids:
            raise UserError(_('You are not allowed to access this workorder'))

        # if self.state == 'pending':
        #     raise UserError(_('Finish the previous steps first'))
        if not self.is_user_working and self.working_state != 'blocked' and self.state in ('ready', 'progress', 'pending'):
            self.button_start()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'views': [[self.env.ref('mrp_workorder.mrp_workorder_view_form_tablet').id, 'form']],
            'res_id': self.id,
            'target': 'fullscreen',
            'flags': {
                'withControlPanel': False,
                'form_view_initial_mode': 'edit',
            },
            'context': {'from_production_order': self.env.context.get('from_production_order')},
        }

    def _create_checks(self):
        for wo in self:
            # Track components which have a control point
            processed_move = self.env['stock.move']

            production = wo.production_id

            move_raw_ids = wo.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
            move_finished_ids = wo.move_finished_ids.filtered(lambda m: m.state not in ('done', 'cancel') and m.product_id != wo.production_id.product_id)
            previous_check = self.env['quality.check']
            for point in wo.quality_point_ids:
                # Check if we need a quality control for this point
                if point.check_execute_now():
                    moves = self.env['stock.move']
                    values = {
                        'production_id': production.id,
                        'workorder_id': wo.id,
                        'point_id': point.id,
                        'team_id': point.team_id.id,
                        'company_id': wo.company_id.id,
                        'product_id': production.product_id.id,
                        # Two steps are from the same production
                        # if and only if the produced quantities at the time they were created are equal.
                        'finished_product_sequence': wo.qty_produced,
                        'previous_check_id': previous_check.id,
                    }
                    if point.test_type == 'register_byproducts':
                        moves = move_finished_ids.filtered(lambda m: m.product_id == point.component_id)
                    elif point.test_type == 'register_consumed_materials':
                        moves = move_raw_ids.filtered(lambda m: m.product_id == point.component_id)
                    else:
                        check = self.env['quality.check'].create(values)
                        previous_check.next_check_id = check
                        previous_check = check
                    # Create 'register ...' checks
                    for move in moves:
                        check_vals = values.copy()
                        check_vals.update(wo._defaults_from_move(move))
                        # Create quality check and link it to the chain
                        check_vals.update({'previous_check_id': previous_check.id})
                        check = self.env['quality.check'].create(check_vals)
                        previous_check.next_check_id = check
                        previous_check = check
                    processed_move |= moves

            # Generate quality checks associated with unreferenced components
            moves_without_check = move_finished_ids.filtered(lambda move: move.has_tracking != 'none' or move.operation_id)
            quality_team_id = self.env['quality.alert.team'].search([], limit=1).id
            for move in moves_without_check:
                values = {
                    'production_id': production.id,
                    'workorder_id': wo.id,
                    'product_id': production.product_id.id,
                    'company_id': wo.company_id.id,
                    'component_id': move.product_id.id,
                    'team_id': quality_team_id,
                    # Two steps are from the same production
                    # if and only if the produced quantities at the time they were created are equal.
                    'finished_product_sequence': wo.qty_produced,
                    'previous_check_id': previous_check.id,
                }
                if move in move_raw_ids:
                    test_type = self.env.ref('mrp_workorder.test_type_register_consumed_materials')
                if move in move_finished_ids:
                    test_type = self.env.ref('mrp_workorder.test_type_register_byproducts')
                values.update({'test_type_id': test_type.id})
                values.update(wo._defaults_from_move(move))
                check = self.env['quality.check'].create(values)
                previous_check.next_check_id = check
                previous_check = check

            # Set default quality_check
            wo.skip_completed_checks = False
            wo._change_quality_check(position='first')
        return True