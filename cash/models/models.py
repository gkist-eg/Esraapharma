# -*- coding: utf-8 -*-
import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

_STATES = [
    ('draft', 'Draft'),
    ('posted', 'Posted'),
]


class cash(models.Model):
    _name = 'cash.cash'
    _inherit = ['mail.thread']
    _rec_name = 'code'
    _order = "create_date desc"
    catg_id = fields.Many2one('product.category', store=True, string='Expense Category',
                              domain="[('is_expense','=',True)]")
    product_id = fields.Many2one('product.product', store=True, domain="[('categ_id', 'in', [catg_id])]")

    payment_type = fields.Selection([
        ('send_money', 'Send Money'),
        ('receive_money', 'Receive Money')],
        string='Payment Type', default='send_money', store=True, track_visibility='onchange')
    cash_method = fields.Selection([
        ('cash', 'Cash'),
        ('check', 'Check')],
        string='Payment Method', default='cash', store=True, track_visibility='onchange')
    partner_type = fields.Selection([
        ('supplier', 'Supplier'),
        ('customer', 'Customer')],
        string='Partner Type', store=True, track_visibility='onchange')

    payment_partner = fields.Selection([
        ('expense', 'Expense'),
        ('partner', 'Partner'),
        ('loan', 'Loans'), ('custody', 'Custody'), ('other', 'Other')],
        string='Type', default='expense')

    code = fields.Char('Reference', size=32, copy=False,
                       track_visibility='onchange', readonly=1,
                       default=lambda self: (" "))
    bank_receive = fields.Char('Bank')
    bank_account_receive = fields.Char('Account Number')
    invoice_ids = fields.Many2many('account.invoice', 'account_invoice_payment_rel', 'payment_id', 'invoice_id',
                                   string="Invoices", copy=False, readonly=True)

    bank = fields.Many2one('res.bank', string='Bank', store=True)
    bank_account = fields.Many2one('res.partner.bank', string='Account Number', domain="[('bank_id','in',[bank])]",
                                   store=True)

    @api.model
    def _getUserGroupId(self):
        return [('id', '=', self.env.user.default_journal_ids.ids), ('type', 'in', ('cash', 'bank')),
                ('account_check', 'not in', ('check_received', 'check_send'))]

    journal_id = fields.Many2one('account.journal', 'Payment Journal', store=True, copy=False,
                                 track_visibility='onchange', domain=_getUserGroupId)

    @api.model
    def _getUserGroupIdd(self):
        return [('id', '=', self.env.user.default_account.ids), ('account', 'not in', ('a', 'b', 'c', 'd', 'f')),
                ('deprecated', '=', False),
                ]

    account_other = fields.Many2one('account.account', string='Account', domain=_getUserGroupIdd)

    @api.onchange('catg_id')
    def _onchangeproduct(self):
        if self.catg_id:
            self.product_id = False

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if not self.invoice_ids:
            # Set default partner type for the payment type
            if self.payment_type == 'send_money':
                self.partner_type = 'supplier'
            elif self.payment_type == 'receive_money':
                self.partner_type = 'customer'
            else:
                self.partner_type = False

    state = fields.Selection(selection=_STATES, string='Status', index=True, track_visibility='onchange', required=True,
                             copy=False, default='draft', store=True)

    @api.model
    def _get_default_employee_id(self):
        return self.env['res.users'].browse(self.env.uid)

    employee_id = fields.Many2one('res.users',
                                  'Accountant',
                                  required=True,
                                  readonly=1,
                                  track_visibility='onchange',
                                  default=_get_default_employee_id, copy=False)

    # partner

    partner_id = fields.Many2one('res.partner', 'Partner', store=True, track_visibility='onchange',
                                 )
    partner_other = fields.Many2one('res.partner', 'Partner Other', store=True, track_visibility='onchange',
                                    )
    check_safe = fields.Many2one('account.journal', 'Safe of Check', store=True, track_visibility='onchange',
                                 domain=[('type', '=', ('cash')),
                                         ('account_check', 'not in', ('check_received', 'check_send'))])

    check_receive = fields.Many2one('account.journal', 'Payment Journal', store=True, track_visibility='onchange',
                                    domain=[('type', '=', 'bank'), ('account_check', '=', 'check_received')],
                                    default=lambda self: self.env['account.journal'].search(
                                        [('account_check', '=', 'check_received')], limit=1))
    check_send = fields.Many2one('account.journal', 'Payment Journal', store=True, track_visibility='onchange',
                                 domain=[('type', '=', 'bank'), ('account_check', '=', 'check_send')],
                                 default=lambda self: self.env['account.journal'].search(
                                     [('account_check', '=', 'check_send')], limit=1))
    check_number = fields.Char('Check Number', track_visibility='onchange', store=True, )
    due_date = fields.Date('Due Date', track_visibility='onchange', store=True, )

    # expense
    # catg_id.property_account_expense_categ_id.id = fields.Many2one('account.account', string='Cost Center', track_visibility='onchange',
    #                                      domain=[('account', '=', ('c')),
    #                                              ('deprecated', '=', False)])
    employee_expense = fields.Many2one(comodel_name="hr.employee", track_visibility='onchange', )
    amount = fields.Float('Amount Paid', store=True, track_visibility='onchange', required=True)
    amount_re = fields.Float('Amount Receive', store=True, track_visibility='onchange', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Cost Center', store=True,
                                          track_visibility='onchange')
    date = fields.Date("Date", default=fields.Datetime.now, store=True, readonly=1)

    # loan
    payment_condation = fields.Integer('Payment Condition', track_visibility='onchange', )
    description = fields.Char('Description', track_visibility='onchange', required=True, store=True)
    start_date_payment = fields.Date('Start Date of Payment', track_visibility='onchange', default=fields.Date.today(),
                                     store=True)
    account_loan = fields.Many2one('account.account', string='Account Loan', store=True,
                                   default=lambda self: self.env['account.account'].search([('account', '=', 'a')],
                                                                                           limit=1),
                                   domain=[('account', '=', ('a')),
                                           ('deprecated', '=', False)])

    # custody
    account_custody = fields.Many2one('account.account', string='Account Custody', store=True,
                                      default=lambda self: self.env['account.account'].search([('account', '=', 'b')],
                                                                                              limit=1),
                                      domain=[('account', '=', ('b')),
                                              ('deprecated', '=', False)])
    analytic_account_custody = fields.Many2one('account.analytic.account', string='Expense Type', store=True,
                                               track_visibility='onchange')
    account_cus = fields.Many2one('account.account', string='Account Expense', store=True,
                                  domain=[('deprecated', '=', False)])

    # income
    account_income = fields.Many2one('account.account', string='Account Income', store=True,
                                     domain=[('deprecated', '=', False)])

    _sql_constraints = [
        ('name_unique', 'unique(check_number)', 'Check Number Must Be Unique')
    ]

    journal_entries = fields.Many2many('account.move', string='Journal Entries', copy=False)

    def unlink(self):
        if any(record.state not in ['draft'] for record in self):
            raise UserError(_('Cannot delete a item in post state'))

        return super(cash, self).unlink()

    def button_journal_entries(self):
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('ref', '=', self.code)],
        }

    def button_account(self):

        return {
            'name': _('Balance'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.account',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', '=', self.journal_id.default_account_id.id)],
        }

    credit = fields.Many2one('account.account', related='journal_id.default_account_id')
    balance = fields.Float(string='Balance', readonly=True, compute='_find_account_balance')

    @api.onchange('credit', 'journal_id')
    def _find_account_balance(self):
        for account in self:
            values = self.env['account.move.line'].search(
                [('account_id', '=', account.credit.id), ('move_id.state', '=', 'posted')])
            total_debit = 0.0
            total_credit = 0.0
            for value in values:
                total_debit = total_debit + value.debit
                total_credit = total_credit + value.credit
            account.update({
                'balance': total_debit - total_credit,
            })

    department_id = fields.Many2one('hr.department', string='Department', compute='_compute_department', store=True)

    @api.onchange('payment_type')
    def _onchange_typ(self):
        if self.amount:
            self.amount = 0.0
        else:
            self.amount_re = 0.0

    @api.onchange('payment_partner')
    def _onchange_ty(self):
        if self.payment_partner:
            self.cash_method = 'cash'
        else:
            self.cash_method = 'cash'
            self.cash_method = 'cash'

    # @api.model
    # def create(self, vals):
    #     if vals['payment_type'] == 'send_money' and vals["cash_method"] == 'cash':
    #         if not self.code or self.code:
    #             vals['code'] = self.env['ir.sequence'].next_by_code('code.code') or ('New')
    #     elif vals['payment_type'] == 'receive_money' and vals['cash_method'] == 'cash':
    #         if not self.code or self.code:
    #             vals['code'] = self.env['ir.sequence'].next_by_code('code.code.out') or ('New')
    #
    #     elif vals['payment_type'] == 'send_money' and vals["cash_method"] == 'check':
    #         if not self.code or self.code:
    #             vals['code'] = self.env['ir.sequence'].next_by_code('code.check.out') or ('New')
    #     elif vals['payment_type'] == 'receive_money' and vals["cash_method"] == 'check':
    #         if not self.code or self.code:
    #             vals['code'] = self.env['ir.sequence'].next_by_code('code.check.in') or ('New')
    #     return super(cash, self).create(vals)

    def button_confirm(self):
        if self.payment_type == 'send_money':
            if not self.amount > 0.0:
                raise ValidationError(_('The payment amount must be strictly positive.'))
        if self.payment_type == 'receive_money':
            if not self.amount_re > 0.0:
                raise ValidationError(_('The payment amount must be strictly positive.'))
        if self.balance <= self.amount and self.cash_method == 'cash' and self.payment_type == 'send_money':
            raise UserError(_('You have not balance in your safe'))

        if not self.code:
            if self['payment_type'] == 'send_money' and self["cash_method"] == 'cash':
                if not self.code or self.code:
                    self['code'] = self.env['ir.sequence'].next_by_code('code.code') or ('New')
            elif self['payment_type'] == 'receive_money' and self['cash_method'] == 'cash':
                if not self.code or self.code:
                    self['code'] = self.env['ir.sequence'].next_by_code('code.code.out') or ('New')

            elif self['payment_type'] == 'send_money' and self["cash_method"] == 'check':
                if not self.code or self.code:
                    self['code'] = self.env['ir.sequence'].next_by_code('code.check.out') or ('New')
            elif self['payment_type'] == 'receive_money' and self["cash_method"] == 'check':
                if not self.code or self.code:
                    self['code'] = self.env['ir.sequence'].next_by_code('code.check.in') or ('New')

        for expense in self:
            res = self.env['account.move'].search([('ref', '=', expense.code), ('ref', '!=', '')])
            if not res:
                if self.payment_type == 'send_money' and self.payment_partner == 'expense' and self.cash_method == 'cash':
                    for expense_cash in self:
                        debit = credit = expense_cash.amount
                        move = {
                            'journal_id': expense_cash.journal_id.id,
                            'date': expense_cash.date,
                            'ref': expense_cash.code,
                            'line_ids': [(0, 0, {
                                'name': expense_cash.description,
                                'debit': debit,
                                'account_id': expense_cash.catg_id.property_account_expense_categ_id.id,
                                'analytic_account_id': expense_cash.analytic_account_id.id,
                                'employee_expense': expense_cash.employee_expense.id,
                                'cash_id': self.id,
                            }), (0, 0, {
                                'name': expense_cash.description,
                                'credit': credit,
                                'account_id': expense_cash.journal_id.default_account_id.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.cash_method == 'check' and self.payment_type == 'send_money' and self.payment_partner == 'expense':
                    for s_expense in self:
                        debit = credit = s_expense.amount
                        move = {
                            'journal_id': s_expense.check_send.id,
                            'date': s_expense.date,
                            'ref': s_expense.code,
                            'line_ids': [(0, 0, {
                                'name': '/',
                                'debit': debit,
                                'account_id': s_expense.catg_id.property_account_expense_categ_id.id,
                                'analytic_account_id': s_expense.analytic_account_id.id,
                                'employee_expense': s_expense.employee_expense.id,
                                'cash_id': self.id,
                                'check_number': self.check_number,
                                'check_due_date': self.due_date,
                            }), (0, 0, {
                                'name': '/',
                                'credit': credit,
                                'account_id': s_expense.check_send.default_account_id.id,
                                'employee_expense': s_expense.employee_expense.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.payment_type == 'send_money' and self.payment_partner == 'other' and self.cash_method == 'cash':
                    for other in self:
                        debit = credit = other.amount
                        move = {
                            'journal_id': other.journal_id.id,
                            'date': other.date,
                            'ref': other.code,
                            'line_ids': [(0, 0, {
                                'name': other.description,
                                'debit': debit,
                                'account_id': other.account_other.id,
                                'analytic_account_id': other.analytic_account_id.id,
                                'employee_expense': other.employee_expense.id,
                                'cash_id': self.id,
                            }), (0, 0, {
                                'name': other.description,
                                'credit': credit,
                                'account_id': other.journal_id.default_account_id.id,
                                'employee_expense': other.employee_expense.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.payment_type == 'send_money' and self.payment_partner == 'other' and self.cash_method == 'check':
                    for s_other in self:
                        debit = credit = s_other.amount
                        move = {
                            'journal_id': s_other.check_send.id,
                            'date': s_other.date,
                            'ref': s_other.code,
                            'line_ids': [(0, 0, {
                                'name': '/',
                                'debit': debit,
                                'account_id': s_other.account_other.id,
                                'analytic_account_id': s_other.analytic_account_id.id,
                                'employee_expense': s_other.employee_expense.id,
                                'cash_id': self.id,
                                'check_number': self.check_number,
                                'check_due_date': self.due_date,
                            }), (0, 0, {
                                'name': '/',
                                'credit': credit,
                                'account_id': s_other.check_send.default_account_id.id,
                                'employee_expense': s_other.employee_expense.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.payment_type == 'send_money' and self.payment_partner == 'loan':
                    for loa in self:
                        debit = credit = loa.amount
                        move = {
                            'journal_id': loa.journal_id.id,
                            'date': loa.date,
                            'ref': loa.code,
                            'line_ids': [(0, 0, {
                                'name': loa.description,
                                'debit': debit,
                                'account_id': loa.account_loan.id,
                                'employee_expense': loa.employee_expense.id,
                                'cash_id': self.id,
                            }), (0, 0, {
                                'name': loa.description,
                                'credit': credit,
                                'account_id': loa.journal_id.default_account_id.id,
                                'employee_expense': loa.employee_expense.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.payment_type == 'send_money' and self.payment_partner == 'custody' and self.cash_method == 'cash':
                    for cus in self:
                        debit = credit = cus.amount
                        move = {
                            'journal_id': cus.journal_id.id,
                            'date': cus.date,
                            'ref': cus.code,
                            'line_ids': [(0, 0, {
                                'name': cus.description,
                                'debit': debit,
                                'account_id': cus.account_custody.id,
                                'employee_expense': cus.employee_expense.id,
                                'cash_id': self.id,

                            }), (0, 0, {
                                'name': cus.description,
                                'credit': credit,
                                'account_id': cus.journal_id.default_account_id.id,
                                'employee_expense': cus.employee_expense.id,
                                'cash_id': self.id,

                            })
                                         ]

                        }

                elif self.payment_type == 'send_money' and self.payment_partner == 'custody' and self.cash_method == 'check':
                    for cus in self:
                        debit = credit = cus.amount
                        move = {
                            'journal_id': cus.check_send.id,
                            'date': cus.date,
                            'ref': cus.code,
                            'line_ids': [(0, 0, {
                                'name': cus.description,
                                'debit': debit,
                                'account_id': cus.account_custody.id,
                                'employee_expense': cus.employee_expense.id,
                                'cash_id': self.id,
                                'check_number': self.check_number,
                                'check_due_date': self.due_date,

                            }), (0, 0, {
                                'name': cus.description,
                                'credit': credit,
                                'account_id': cus.check_send.default_account_id.id,
                                'employee_expense': cus.employee_expense.id,
                                'cash_id': self.id,

                            })
                                         ]

                        }

                elif self.payment_type == 'send_money' and self.payment_partner == 'partner' and self.cash_method == 'cash':
                    for partner in self:
                        debit = credit = partner.amount
                        move = {
                            'journal_id': partner.journal_id.id,
                            'date': partner.date,
                            'ref': partner.code,
                            'line_ids': [(0, 0, {
                                'name': partner.description,
                                'debit': debit,
                                'account_id': partner.partner_id.property_account_payable_id.id,
                                'partner_id': partner.partner_id.id,
                                'cash_id': self.id,

                            }), (0, 0, {
                                'name': partner.description,
                                'credit': credit,
                                'account_id': partner.journal_id.default_account_id.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.payment_type == 'send_money' and self.payment_partner == 'partner' and self.cash_method == 'check':
                    for partner in self:
                        debit = credit = partner.amount
                        move = {
                            'journal_id': partner.check_send.id,
                            'date': partner.date,
                            'ref': partner.code,
                            'line_ids': [(0, 0, {
                                'name': partner.description,
                                'debit': debit,
                                'account_id': partner.partner_id.property_account_payable_id.id,
                                'partner_id': partner.id,
                                'cash_id': self.id,
                                'check_number': self.check_number,
                                'check_due_date': self.due_date,

                            }), (0, 0, {
                                'name': partner.description,
                                'credit': credit,
                                'account_id': partner.check_send.default_account_id.id,
                                'partner_id': partner.partner_id.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.payment_type == 'receive_money' and self.payment_partner == 'partner' and self.cash_method == 'cash':
                    for partne in self:
                        debit = credit = partne.amount_re
                        move = {
                            'journal_id': partne.journal_id.id,
                            'date': partne.date,
                            'ref': partne.code,
                            'line_ids': [(0, 0, {
                                'name': partne.description,
                                'debit': debit,
                                'account_id': partne.journal_id.default_account_id.id,
                                'partner_id': partne.partner_id.id,
                                'cash_id': self.id,

                            }), (0, 0, {
                                'name': partne.description,
                                'credit': credit,
                                'account_id': partne.partner_id.property_account_receivable_id.id,
                                'partner_id': partne.partner_id.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.payment_type == 'receive_money' and self.payment_partner == 'partner' and self.cash_method == 'check':
                    for partne in self:
                        debit = credit = partne.amount_re
                        move = {
                            'journal_id': partne.check_receive.id,
                            'date': partne.date,
                            'ref': partne.code,
                            'line_ids': [(0, 0, {

                                'name': partne.description,
                                'credit': credit,
                                'account_id': partne.partner_id.property_account_receivable_id.id,
                                'partner_id': partne.partner_id.id,
                                'cash_id': self.id,
                                'check_number': self.check_number,
                                'check_due_date': self.due_date,

                            }), (0, 0, {
                                'name': partne.description,
                                'debit': debit,
                                'account_id': partne.check_receive.default_account_id.id,
                                'partner_id': partne.partner_id.id,
                                'cash_id': self.id,
                            })]
                        }

                elif self.payment_type == 'receive_money' and self.payment_partner == 'expense' and self.cash_method == 'cash':
                    for income in self:
                        debit = credit = income.amount_re
                        move = {
                            'journal_id': income.journal_id.id,
                            'date': income.date,
                            'ref': income.code,
                            'line_ids': [(0, 0, {
                                'name': income.description,
                                'debit': debit,
                                'account_id': income.journal_id.default_account_id.id,
                                'employee_expense': income.employee_expense.id,
                                'cash_id': self.id,
                            }), (0, 0, {
                                'name': income.description,
                                'credit': credit,
                                'account_id': income.catg_id.property_account_expense_categ_id.id,
                                'employee_expense': income.employee_expense.id,
                                'analytic_account_id': income.analytic_account_id.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.payment_type == 'receive_money' and self.payment_partner == 'expense' and self.cash_method == 'check':
                    for income in self:
                        debit = credit = income.amount_re
                        move = {
                            'journal_id': income.check_receive.id,
                            'date': income.date,
                            'ref': income.code,
                            'line_ids': [(0, 0, {
                                'name': income.description,
                                'debit': debit,
                                'account_id': income.check_receive.default_account_id.id,
                                'cash_id': self.id,
                                'check_number': self.check_number,
                                'check_due_date': self.due_date,
                            }), (0, 0, {
                                'name': income.description,
                                'credit': credit,
                                'account_id': income.catg_id.property_account_expense_categ_id.id,
                                'employee_expense': income.employee_expense.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.payment_type == 'receive_money' and self.payment_partner == 'other' and self.cash_method == 'cash':
                    for income in self:
                        debit = credit = income.amount_re
                        move = {
                            'journal_id': income.journal_id.id,
                            'date': income.date,
                            'ref': income.code,
                            'line_ids': [(0, 0, {
                                'name': income.description,
                                'debit': debit,
                                'account_id': income.journal_id.default_account_id.id,
                                'employee_expense': income.employee_expense.id,
                                'cash_id': self.id,
                            }), (0, 0, {
                                'name': income.description,
                                'credit': credit,
                                'account_id': income.account_other.id,
                                'employee_expense': income.employee_expense.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.payment_type == 'receive_money' and self.payment_partner == 'other' and self.cash_method == 'check':
                    for income in self:
                        debit = credit = income.amount_re
                        move = {
                            'journal_id': income.check_receive.id,
                            'date': income.date,
                            'ref': income.code,
                            'line_ids': [(0, 0, {
                                'name': income.description,
                                'debit': debit,
                                'account_id': income.check_receive.default_account_id.id,
                                'employee_expense': income.employee_expense.id,
                                'cash_id': self.id,
                                'check_number': self.check_number,
                                'check_due_date': self.due_date,

                            }), (0, 0, {
                                'name': income.description,
                                'credit': credit,
                                'account_id': income.account_other.id,
                                'employee_expense': income.employee_expense.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.payment_type == 'receive_money' and self.payment_partner == 'loan':
                    for loan in self:
                        debit = credit = loan.amount_re
                        move = {
                            'journal_id': loan.journal_id.id,
                            'date': loan.date,
                            'ref': loan.code,
                            'line_ids': [(0, 0, {
                                'name': loan.description,
                                'debit': debit,
                                'account_id': loan.journal_id.default_account_id.id,
                                'employee_expense': loan.employee_expense.id,

                                'cash_id': self.id,
                            }), (0, 0, {
                                'name': loan.description,
                                'credit': credit,
                                'account_id': loan.account_loan.id,
                                'employee_expense': loan.employee_expense.id,
                                'cash_id': self.id,

                            })]
                        }

                elif self.payment_type == 'receive_money' and self.payment_partner == 'custody' and self.cash_method == 'cash':
                    for cus in self:
                        debit = credit = cus.amount_re
                        move = {
                            'journal_id': cus.journal_id.id,
                            'date': cus.date,
                            'ref': cus.code,
                            'line_ids': [(0, 0, {
                                'name': cus.description,
                                'debit': debit,
                                'account_id': cus.journal_id.default_account_id.id,
                                'employee_expense': cus.employee_expense.id,
                                'cash_id': self.id,

                            }), (0, 0, {
                                'name': cus.description,
                                'credit': credit,
                                'account_id': cus.account_custody.id,
                                'employee_expense': cus.employee_expense.id,
                                'cash_id': self.id,

                            })
                                         ]

                        }

                elif self.payment_type == 'receive_money' and self.payment_partner == 'custody' and self.cash_method == 'check':
                    for cus in self:
                        debit = credit = cus.amount_re
                        move = {
                            'journal_id': cus.journal_id.id,
                            'date': cus.date,
                            'ref': cus.code,
                            'line_ids': [(0, 0, {
                                'name': cus.description,
                                'debit': debit,
                                'account_id': cus.journal_id.default_account_id.id,
                                'employee_expense': cus.employee_expense.id,
                                'cash_id': self.id,
                                'check_number': self.check_number,
                                'check_due_date': self.due_date,

                            }), (0, 0, {
                                'name': cus.description,
                                'credit': credit,
                                'account_id': cus.account_custody.id,
                                'employee_expense': cus.employee_expense.id,
                                'cash_id': self.id,

                            })
                                         ]

                        }
                move_id = self.env['account.move'].create(move)
                move_id.post()
                expense.write({'state': 'posted'})
            else:
                raise ValidationError(_('You are already clicked'))


class planConfirm(models.TransientModel):
    _name = "cash.confirm"
    _description = "Confirm the selected operation"

    def cash_confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['cash.cash'].browse(active_ids):
            if record.state != 'draft':
                raise UserError(
                    _("Selected Operation(s) cannot be Confirmed "))
            record.button_confirm()
        return {'type': 'ir.actions.act_window_close'}


class user_unlink(models.Model):
    _inherit = "res.users"

    def unlink(self):
        for record in self:
            if record.journal_item_count != 0:
                raise UserError(_('Cannot delete this user'))

            return super(user_unlink, self).unlink()


class AccountMoveLinee(models.Model):
    _inherit = 'account.move.line'

    employee_expense = fields.Many2one(comodel_name="hr.employee", track_visibility='onchange', )
