# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class journal_default(models.Model):
    _inherit = ['res.users']

    default_journal_ids = fields.Many2many(
        'account.journal', 'account_journal_users_rel',
        'user_id', 'account_journal_id', string='Default Journal')
    default_report = fields.Many2many(
        'account.journal', 'account_journal_users_rel2',
        'user_id', 'account_journal_id', string='Default Journal Report')
    default_account = fields.Many2many(
        'account.account', 'account_users_rel3',
        'user_id', 'account_account_id', string='Default Account')


class account_journal(models.Model):
    _inherit = 'account.journal'
    account_check = fields.Selection([('check_received', 'Check Received'), ('check_send', 'Check Send')],
                                     string='Type Of Check')


class account_payment_registerr(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def _getUserGroupId(self):
        return [('id', '=', self.env.user.default_journal_ids.ids), ('type', 'in', ('cash', 'bank')),
                ]

    journal_id = fields.Many2one('account.journal', required=True, store=True, readonly=False, string='Payment Journal',
                                 domain=_getUserGroupId )
    type = fields.Selection('x', related='journal_id.type')
    cash_receive = fields.Many2one('hr.employee', 'Cash Recipient', store=True, index=True)
    check_receive = fields.Many2one('hr.employee', 'Check Recipient', store=True, index=True)
    check_number = fields.Char(string='Check Number', store=True, index=True)
    customer_bank = fields.Many2one('res.bank', string='Customer Bank ', index=True)
    bank_account = fields.Char(string='Bank Account', store=True, index=True)
    safe = fields.Many2one('account.journal', string='Safe', store=True, domain=[('type', '=', 'cash')])

    bank = fields.Many2one('res.bank', string='Bank ', store=True, index=True)
    bank_in = fields.Char(string='Bank ', store=True, index=True)
    bank_account_number = fields.Many2one('res.partner.bank', string='Account Number',
                                          domain="[('bank_id','in',[bank])]",
                                          store=True, index=True)

    check_due_date = fields.Date(store=True, index=True)
    cash_method = fields.Selection([
        ('Cash', 'Cash'),
        ('Check', 'Check')],
        string='Payment Method', store=True, invisible=True, index=True)

    @api.onchange('journal_id')
    def _onchange_type(self):
        if self.journal_id:
            self.cash_method = ''
        else:
            self.cash_method = ''

    def _create_payment_vals_from_wizard(self):
        payment_vals = {
            'date': self.payment_date,
            'amount': self.amount,
            'payment_type': self.payment_type,
            'partner_type': self.partner_type,
            'ref': self.communication,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_bank_id': self.partner_bank_id.id,
            'payment_method_id': self.payment_method_id.id,
            'destination_account_id': self.line_ids[0].account_id.id,
            'check_number': self.check_number,
            'check_due_date': self.check_due_date,
            'cash_method': self.cash_method,
            'check_receive': self.check_receive.id,
            'safe': self.safe.id,
            'bank_in': self.bank_in,
            'cash_receive': self.cash_receive.id,
        }

        if not self.currency_id.is_zero(self.payment_difference) and self.payment_difference_handling == 'reconcile':
            payment_vals['write_off_line_vals'] = {
                'name': self.writeoff_label,
                'amount': self.payment_difference,
                'account_id': self.writeoff_account_id.id,
            }
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        batch_values = self._get_wizard_values_from_batch(batch_result)
        return {
            'date': self.payment_date,
            'amount': batch_values['source_amount_currency'],
            'payment_type': batch_values['payment_type'],
            'partner_type': batch_values['partner_type'],
            'ref': self._get_batch_communication(batch_result),
            'journal_id': self.journal_id.id,
            'currency_id': batch_values['source_currency_id'],
            'partner_id': batch_values['partner_id'],
            'partner_bank_id': batch_result['key_values']['partner_bank_id'],
            'payment_method_id': self.payment_method_id.id,
            'destination_account_id': batch_result['lines'][0].account_id.id,
            'check_number': self.check_number,
            'check_due_date': self.check_due_date,
            'cash_method': self.cash_method,
            'check_receive': self.check_receive.id,
            'safe': self.safe.id,
            'bank_in': self.bank_in,
            'cash_receive': self.cash_receive.id
        }


class accountt_payment(models.Model):
    _inherit = 'account.payment'


    type = fields.Selection('x', related='journal_id.type')
    cash_receive = fields.Many2one('hr.employee', 'Cash Recipient', store=True, index=True)
    check_receive = fields.Many2one('hr.employee', 'Check Recipient', store=True, index=True)
    check_number = fields.Char(string='Check Number', store=True, index=True)
    customer_bank = fields.Many2one('res.bank', string='Customer Bank ', index=True)
    bank_account = fields.Char(string='Bank Account', store=True, index=True)
    safe = fields.Many2one('account.journal', string='Safe', store=True, domain=[('type', '=', 'cash')])

    bank = fields.Many2one('res.bank', string='Bank ', store=True, index=True)
    bank_in = fields.Char(string='Bank ', store=True, index=True)
    bank_account_number = fields.Many2one('res.partner.bank', string='Account Number',
                                          domain="[('bank_id','in',[bank])]",
                                          store=True, index=True)

    check_due_date = fields.Date(store=True, index=True)
    cash_method = fields.Selection([
        ('Cash', 'Cash'),
        ('Check', 'Check')],
        string='Payment Method', store=True, invisible=True, index=True)

    @api.onchange('journal_id')
    def _onchange_type(self):
        if self.journal_id:
            self.cash_method = ''
        else:
            self.cash_method = ''


    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or {}

        if not self.journal_id.payment_debit_account_id or not self.journal_id.payment_credit_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set on the %s journal.",
                self.journal_id.display_name))

        # Compute amounts.
        write_off_amount = write_off_line_vals.get('amount', 0.0)

        if self.payment_type == 'inbound':
            # Receive money.
            counterpart_amount = -self.amount
            write_off_amount *= -1
        elif self.payment_type == 'outbound':
            # Send money.
            counterpart_amount = self.amount
        else:
            counterpart_amount = 0.0
            write_off_amount = 0.0

        balance = self.currency_id._convert(counterpart_amount, self.company_id.currency_id, self.company_id, self.date)
        counterpart_amount_currency = counterpart_amount
        write_off_balance = self.currency_id._convert(write_off_amount, self.company_id.currency_id, self.company_id, self.date)
        write_off_amount_currency = write_off_amount
        currency_id = self.currency_id.id

        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                liquidity_line_name = _('Transfer to %s', self.journal_id.name)
            else: # payment.payment_type == 'outbound':
                liquidity_line_name = _('Transfer from %s', self.journal_id.name)
        else:
            liquidity_line_name = self.payment_reference

        # Compute a default label to set on the journal items.

        payment_display_name = {
            'outbound-customer': _("Customer Reimbursement"),
            'inbound-customer': _("Customer Payment"),
            'outbound-supplier': _("Vendor Payment"),
            'inbound-supplier': _("Vendor Reimbursement"),
        }

        default_line_name = self.env['account.move.line']._get_default_line_name(
            _("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
            self.amount,
            self.currency_id,
            self.date,
            partner=self.partner_id,
        )

        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name or default_line_name,
                'date_maturity': self.date,
                'amount_currency': -counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': balance < 0.0 and -balance or 0.0,
                'credit': balance > 0.0 and balance or 0.0,
                'partner_id': self.partner_id.id,

                'account_id': self.journal_id.payment_debit_account_id.id if balance < 0.0 else self.journal_id.payment_credit_account_id.id,
                'check_number': self.check_number,
                'check_due_date': self.check_due_date,
            },
            # Receivable / Payable.
            {
                'name': self.payment_reference or default_line_name,
                'date_maturity': self.date,
                'amount_currency': counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0,
                'currency_id': currency_id,
                'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.destination_account_id.id,
                'check_number': self.check_number,
                'check_due_date': self.check_due_date,
            },
        ]
        if write_off_balance:
            # Write-off line.
            line_vals_list.append({
                'name': write_off_line_vals.get('name') or default_line_name,
                'amount_currency': -write_off_amount_currency,
                'currency_id': currency_id,
                'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
                'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
                'partner_id': self.partner_id.id,
                'account_id': write_off_line_vals.get('account_id'),
                'check_number': self.check_number,
                'check_due_date': self.check_due_date,
            })
        return line_vals_list


class AccountMoveLine(models.Model):
    _name = 'account.move.line'
    _inherit = 'account.move.line'
    check_number = fields.Char('Check Number', store=True)
    check_due_date = fields.Date('Check Due Date', store=True)
    cash_id = fields.Many2one(
        'cash.cash',
        string='Cash',

    )

    @api.model
    def _getUserGroupIddaccount(self):
        return [('id', '=', self.env.user.default_account.ids),

                ]

    account_id = fields.Many2one('account.account', string='Account',
                                 index=True, ondelete="cascade",
                                 domain=_getUserGroupIddaccount,
                                 check_company=True,
                                 tracking=True)





