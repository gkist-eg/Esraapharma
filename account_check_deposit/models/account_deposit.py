# -*- coding: utf-8 -*-
# © 2012-2016 Akretion (http://www.akretion.com/)
# @author: Benoît GUILLOT <benoit.guillot@akretion.com>
# @author: Chafique DELLI <chafique.delli@akretion.com>
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# @author: Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import ValidationError, UserError


class AccountCheckDeposit(models.Model):
    _name = "account.check.deposit"
    _description = "Account Check Deposit"
    _order = 'deposit_date desc'

    @api.depends(
        'company_id', 'currency_id', 'check_payment_ids.debit',
        'check_payment_ids.amount_currency',
        'move_id.line_ids.reconciled')
    def _compute_check_deposit(self):
        for deposit in self:
            total = 0.0
            count = 0
            reconcile = False
            currency_none_same_company_id = False
            if deposit.company_id.currency_id != deposit.currency_id:
                currency_none_same_company_id = deposit.currency_id.id
            for line in deposit.check_payment_ids:
                count += 1
                if line.debit != 0:
                    if currency_none_same_company_id:
                        total += line.amount_currency
                    else:
                        total += line.debit
                    if deposit.move_id:
                        for line in deposit.move_id.line_ids:
                            if line.debit > 0 and line.reconciled:
                                reconcile = True
                    deposit.total_amount = total
                    deposit.is_reconcile = reconcile
                    deposit.currency_none_same_company_id = \
                        currency_none_same_company_id
                    deposit.check_count = count

                elif line.credit != 0:
                    if currency_none_same_company_id:
                        total += line.amount_currency
                    else:
                        total += line.credit
                    if deposit.move_id:
                        for line in deposit.move_id.line_ids:
                            if line.credit > 0 and line.reconciled:
                                reconcile = True
                    deposit.total_amount = total
                    deposit.is_reconcile = reconcile
                    deposit.currency_none_same_company_id = \
                        currency_none_same_company_id
                    deposit.check_count = count

    name = fields.Char(string='Name', size=64, readonly=True, default='/')
    check_payment_ids = fields.One2many(
        'account.move.line', 'check_deposit_id', string='Check Payments',
        states={'done': [('readonly', '=', True)]})

    deposit_date = fields.Date(
        string='Deposit Date', required=True,
        states={'done': [('readonly', '=', True)]},
        default=fields.Date.context_today)
    journal_id = fields.Many2one(
        'account.journal', string='Journal',
        domain=[('type', '=', 'bank'), ('bank_account_id', '=', False),
                ('account_check', 'in', ('check_received', 'check_send'))],
        required=True, states={'done': [('readonly', '=', True)]})
    journal_default_account_id = fields.Many2one(
        'account.account', related='journal_id.payment_debit_account_id',
        string='Default Debit Account of the Journal', readonly=True, store=True)
    journal_default_account_ids = fields.Many2one(
        'account.account', related='journal_id.payment_credit_account_id',
        string='Default Debit Account of the Journal', readonly=True, store=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        states={'done': [('readonly', '=', True)]})

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('done', 'Done'),('reconcile','Reconcile')
        ], string='Status', default='draft', readonly=True)
    move_id = fields.Many2one(
        'account.move', string='Journal Entry', readonly=True)
    move_id2 = fields.Many2one(
        'account.move', string='Reconcile Journal Entry', readonly=True)
    bank_journal_id = fields.Many2one(
        'account.journal', string='Journal Bank',
        domain=[('type', '=', 'bank'), ('account_check', 'not in', ('check_received', 'check_send'))],
        required=True, states={'done': [('readonly', '=', True)]})
    line_ids = fields.One2many(
        'account.move.line', related='move_id.line_ids',
        string='Lines', readonly=True)

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        states={'done': [('readonly', '=', True)]},
        default=lambda self: self.env['res.company']._company_default_get(
            'account.check.deposit'))
    total_amount = fields.Float(
        string="Total Amount", readonly=True,
        digits=dp.get_precision('Account'))
    check_count = fields.Integer(
        readonly=True,
        string="Number of Checks")
    is_reconcile = fields.Boolean(
        readonly=True,
        string="Reconcile")

    def unlink(self):
        for deposit in self:
            if deposit.state == 'done':
                raise UserError(
                    _("The deposit '%s' is in valid state, so you must "
                      "cancel it before deleting it.")
                    % deposit.name)
        return super(AccountCheckDeposit, self).unlink()

    def backtodraft(self):
        for deposit in self:
            if deposit.move_id:
                # It will raise here if journal_id.update_posted = False
                deposit.move_id.button_cancel()
                for line in deposit.check_payment_ids:
                    if line.reconciled:
                        line.remove_move_reconcile()
                deposit.move_id.unlink()
            deposit.write({'state': 'draft'})
        return True

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence']. \
                next_by_code('account.check.deposit')
        return super(AccountCheckDeposit, self).create(vals)

    @api.model
    def _prepare_account_move_vals(self, deposit):

        if (
                deposit.company_id.check_deposit_offsetting_account ==
                'bank_account'):
            journal_id = deposit.bank_journal_id.id
        else:
            journal_id = deposit.journal_id.id
        move_vals = {
            'journal_id': journal_id,
            'date': deposit.deposit_date,
            'name': _('Check Deposit %s') % deposit.name,
            'ref': deposit.name,

        }

        return move_vals

    @api.model
    def _prepare_move_line_vals(self, line):

        if self.journal_id.account_check == 'check_received':
            assert (line.debit > 0), 'Debit must have a value'
            return {
                'name': _('Check Deposit - Ref. Check %s') % line.ref,
                'credit': line.debit,
                'debit': 0.0,
                'account_id': line.account_id.id,
                'partner_id': line.partner_id.id,
                'currency_id': line.currency_id.id or False,
                'amount_currency': line.amount_currency * -1,
                'check_number': line.check_number,
                'check_due_date': line.check_due_date,
                'deposit': True,
                'is_true': True,
            }
        elif self.journal_id.account_check == 'check_send':
            assert (line.credit > 0), 'Debit must have a value'
            return {
                'name': _('Check Deposit - Ref. Check %s') % line.ref,
                'credit': 0.0,
                'debit': line.credit,
                'account_id': line.account_id.id,
                'partner_id': line.partner_id.id,
                'currency_id': line.currency_id.id or False,
                'amount_currency': line.amount_currency * -1,
                'check_number': line.check_number,
                'check_due_date': line.check_due_date,
                'deposit': True,
                'is_true': True,

            }

    @api.model
    def _prepare_counterpart_move_lines_vals(self, deposit, total_debit, total_credit, total_amount_currency):
        company = deposit.company_id
        if self.journal_id.account_check == 'check_received':
            if not company.check_deposit_offsetting_account:
                raise UserError(_(
                    "You must configure the 'Check Deposit Offsetting Account' "
                    "on the Accounting Settings page"))
            if company.check_deposit_offsetting_account == 'bank_account':
                if not deposit.bank_journal_id.payment_debit_account_id:
                    raise UserError(_(
                        "Missing 'Default Debit Account' on bank journal '%s'")
                                    % deposit.bank_journal_id.name)
                account_id = deposit.bank_journal_id.payment_debit_account_id.id
            elif company.check_deposit_offsetting_account == 'transfer_account':
                if not company.check_deposit_transfer_account_id:
                    raise UserError(_(
                        "Missing 'Account for Check Deposits' on the "
                        "company '%s'.") % company.name)
                account_id = company.check_deposit_transfer_account_id.id
            else:

                account_id = deposit.bank_journal_id.payment_debit_account_id.id
            return {
                'name': _('Check Deposit %s') % deposit.name,
                'debit': total_debit,
                'credit': 0.0,
                'account_id': account_id,
                'partner_id': False,
                'amount_currency': total_debit,
            }
        elif self.journal_id.account_check == 'check_send':
            if not company.check_deposit_offsetting_account:
                raise UserError(_(
                    "You must configure the 'Check Deposit Offsetting Account' "
                    "on the Accounting Settings page"))
            if company.check_deposit_offsetting_account == 'bank_account':
                if not deposit.bank_journal_id.payment_credit_account_id:
                    raise UserError(_(
                        "Missing 'Default Debit Account' on bank journal '%s'")
                                    % deposit.bank_journal_id.name)
                account_id = deposit.bank_journal_id.payment_credit_account_id.id
            elif company.check_deposit_offsetting_account == 'transfer_account':
                if not company.check_deposit_transfer_account_id:
                    raise UserError(_(
                        "Missing 'Account for Check Deposits' on the "
                        "company '%s'.") % company.name)
                account_id = company.check_deposit_transfer_account_id.id
            else:
                account_id = deposit.bank_journal_id.payment_credit_account_id.id
            return {
                'name': _('Check Deposit %s') % deposit.name,
                'debit': 0,
                'credit': total_credit,
                'account_id': account_id,
                'partner_id': False,
                'amount_currency': total_credit,

            }

    def validate_deposit(self):
        if self.journal_id.account_check == 'check_received':
            am_obj = self.env['account.move']
            move_line_obj = self.env['account.move.line']
            for deposit in self:
                move_vals = self._prepare_account_move_vals(deposit)
                move = am_obj.create(move_vals)

                total_debit = 0.0
                total_amount_currency = 0.0
                for line in deposit.check_payment_ids:
                    total_debit += line.debit
                    total_amount_currency += line.amount_currency
                    line_vals = self._prepare_move_line_vals(line)
                    line_vals['move_id'] = move.id
                    move_line = move_line_obj.with_context(
                        check_move_validity=False).create(line_vals)

                # Create counter-part
                counter_vals = self._prepare_counterpart_move_lines_vals(
                    deposit, total_debit, 0.0, total_amount_currency)
                counter_vals['move_id'] = move.id
                move_line_obj.create(counter_vals)
                move.post()
                deposit.write({'state': 'done', 'move_id': move.id})

            return True
        elif self.journal_id.account_check == 'check_send':
            am_obj = self.env['account.move']
            move_line_obj = self.env['account.move.line']
            for deposit in self:
                move_vals = self._prepare_account_move_vals(deposit)
                move = am_obj.create(move_vals)
                total_credit = 0.0
                total_amount_currency = 0.0
                for line in deposit.check_payment_ids:
                    total_credit += line.credit
                    total_amount_currency += line.amount_currency
                    line_vals = self._prepare_move_line_vals(line)
                    line_vals['move_id'] = move.id
                    move_line = move_line_obj.with_context(
                        check_move_validity=False).create(line_vals)

                # Create counter-part
                counter_vals = self._prepare_counterpart_move_lines_vals(
                    deposit, 0.0, total_credit, total_amount_currency)
                counter_vals['move_id'] = move.id
                move_line_obj.create(counter_vals)

                deposit.write({'state': 'done', 'move_id': move.id})

            return True
    @api.model
    def _prepare_account_move_vals2(self, deposit):

        if (
                deposit.company_id.check_deposit_offsetting_account ==
                'bank_account'):
            journal_id = deposit.bank_journal_id.id
        else:
            journal_id = deposit.journal_id.id
        move_vals = {
            'journal_id': journal_id,
            'date': deposit.deposit_date,
            'name': _('Reconcile %s') % deposit.name,
            'ref': deposit.name,

        }

        return move_vals

    @api.model
    def _prepare_move_line_vals2(self, line):

        if self.journal_id.account_check == 'check_received':
            assert (line.debit > 0), 'Debit must have a value'
            return {
                'name': _('Check Deposit - Ref. Check %s') % line.ref,
                'credit': line.debit,
                'debit': 0.0,
                'account_id': self.bank_journal_id.payment_debit_account_id.id,
                'partner_id': line.partner_id.id,
                'currency_id': line.currency_id.id or False,
                'amount_currency': line.amount_currency * -1,
                'check_number': line.check_number,
                'check_due_date': line.check_due_date,
                'deposit': True,
                'is_true': True,
            }
        elif self.journal_id.account_check == 'check_send':
            assert (line.credit > 0), 'Debit must have a value'
            return {
                'name': _('Check Deposit - Ref. Check %s') % line.ref,
                'credit': 0.0,
                'debit': line.credit,
                'account_id': self.bank_journal_id.payment_credit_account_id.id,
                'partner_id': line.partner_id.id,
                'currency_id': line.currency_id.id or False,
                'amount_currency': line.amount_currency * -1,
                'check_number': line.check_number,
                'check_due_date': line.check_due_date,
                'deposit': True,
                'is_true': True,

            }

    @api.model
    def _prepare_counterpart_move_lines_vals2(self, deposit, total_debit, total_credit, total_amount_currency):
        company = deposit.company_id
        if self.journal_id.account_check == 'check_received':
            if not company.check_deposit_offsetting_account:
                raise UserError(_(
                    "You must configure the 'Check Deposit Offsetting Account' "
                    "on the Accounting Settings page"))
            if company.check_deposit_offsetting_account == 'bank_account':
                if not deposit.bank_journal_id.default_account_id:
                    raise UserError(_(
                        "Missing 'Default Debit Account' on bank journal '%s'")
                                    % deposit.bank_journal_id.name)
                account_id = deposit.bank_journal_id.default_account_id.id
            elif company.check_deposit_offsetting_account == 'transfer_account':
                if not company.check_deposit_transfer_account_id:
                    raise UserError(_(
                        "Missing 'Account for Check Deposits' on the "
                        "company '%s'.") % company.name)
                account_id = company.check_deposit_transfer_account_id.id
            else:

                account_id = deposit.bank_journal_id.default_account_id.id
            return {
                'name': _('Check Deposit %s') % deposit.name,
                'debit': total_debit,
                'credit': 0.0,
                'account_id': account_id,
                'partner_id': False,
                'amount_currency': total_debit,
            }
        elif self.journal_id.account_check == 'check_send':
            if not company.check_deposit_offsetting_account:
                raise UserError(_(
                    "You must configure the 'Check Deposit Offsetting Account' "
                    "on the Accounting Settings page"))
            if company.check_deposit_offsetting_account == 'bank_account':
                if not deposit.bank_journal_id.default_account_id:
                    raise UserError(_(
                        "Missing 'Default Debit Account' on bank journal '%s'")
                                    % deposit.bank_journal_id.name)
                account_id = deposit.bank_journal_id.default_account_id.id
            elif company.check_deposit_offsetting_account == 'transfer_account':
                if not company.check_deposit_transfer_account_id:
                    raise UserError(_(
                        "Missing 'Account for Check Deposits' on the "
                        "company '%s'.") % company.name)
                account_id = company.check_deposit_transfer_account_id.id
            else:
                account_id = deposit.bank_journal_id.default_account_id.id
            return {
                'name': _('Check Deposit %s') % deposit.name,
                'debit': 0,
                'credit': total_credit,
                'account_id': account_id,
                'partner_id': False,
                'amount_currency': total_credit,

            }

    def validate_deposit2(self):
        if self.journal_id.account_check == 'check_received':
            am_obj = self.env['account.move']
            move_line_obj = self.env['account.move.line']
            for deposit in self:
                move_vals = self._prepare_account_move_vals2(deposit)
                move = am_obj.create(move_vals)

                total_debit = 0.0
                total_amount_currency = 0.0
                for line in deposit.check_payment_ids:
                    total_debit += line.debit
                    total_amount_currency += line.amount_currency
                    line_vals = self._prepare_move_line_vals2(line)
                    line_vals['move_id'] = move.id
                    move_line = move_line_obj.with_context(
                        check_move_validity=False).create(line_vals)

                # Create counter-part
                counter_vals = self._prepare_counterpart_move_lines_vals2(
                    deposit, total_debit, 0.0, total_amount_currency)
                counter_vals['move_id'] = move.id
                move_line_obj.create(counter_vals)
                move.post()
                deposit.write({'state': 'reconcile', 'move_id': move.id})

            return True
        elif self.journal_id.account_check == 'check_send':
            am_obj = self.env['account.move']
            move_line_obj = self.env['account.move.line']
            for deposit in self:
                move_vals = self._prepare_account_move_vals2(deposit)
                move = am_obj.create(move_vals)
                total_credit = 0.0
                total_amount_currency = 0.0
                for line in deposit.check_payment_ids:
                    total_credit += line.credit
                    total_amount_currency += line.amount_currency
                    line_vals = self._prepare_move_line_vals2(line)
                    line_vals['move_id'] = move.id
                    move_line = move_line_obj.with_context(
                        check_move_validity=False).create(line_vals)

                # Create counter-part
                counter_vals = self._prepare_counterpart_move_lines_vals2(
                    deposit, 0.0, total_credit, total_amount_currency)
                counter_vals['move_id'] = move.id
                move_line_obj.create(counter_vals)

                deposit.write({'state': 'reconcile', 'move_id': move.id})

            return True
    @api.onchange('company_id')
    def onchange_company_id(self):
        if self.company_id:
            bank_journals = self.env['account.journal'].search([
                ('company_id', '=', self.company_id.id),
                ('type', '=', 'bank'),
                ('bank_account_id', '!=', False)])
            if len(bank_journals) == 1:
                self.bank_journal_id = bank_journals[0]
        else:
            self.bank_journal_id = False

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        if self.journal_id:
            if self.journal_id.currency_id:
                self.currency_id = self.journal_id.currency_id
            else:
                self.currency_id = self.journal_id.company_id.currency_id


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    check_deposit_id = fields.Many2one(
        'account.check.deposit', string='Check Deposit', copy=False)
    cheack_val = fields.Boolean(store=True)
