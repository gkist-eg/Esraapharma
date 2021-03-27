from datetime import datetime, date
from itertools import groupby
from operator import itemgetter

from dateutil.relativedelta import relativedelta
from stdnum.exceptions import ValidationError
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval


class BankStatement(models.TransientModel):
    _name = 'bank.statement'

    type_cash = fields.Selection([
        ('Partner', 'Partner')
        , ], store=True, default='Partner', invisible='1')

    amount_payment = fields.Float('Amount')
    end_amount = fields.Float('e')

    amount_cash = fields.Char('Amount')

    @api.model
    def _getUserGroupId(self):
        return [('id', '=', self.env.user.default_report.ids), ('type', '=', 'bank'),
                ('account_check', 'not in', ('check_send', 'check_received'))]

    journal_id = fields.Many2one('account.journal', 'Bank', store=True, track_visibility='onchange', required=True,
                                 domain=_getUserGroupId)

    @api.model
    def _get_from_date(self):
        company = self.env.user.company_id
        current_date = datetime.today()
        from_date = company.compute_fiscalyear_dates(current_date)['date_from']
        return from_date

    def _get_date(self):
        today = date.today()
        first_day = today.replace(day=1)

        return first_day

    date_from = fields.Date("Start Date", default=_get_date)
    date_to = fields.Date("End Date", default=datetime.today(), )
    line_ids = fields.One2many('bank.statement.line', 'wizard_id', required=True, ondelete='cascade')

    def print_pdf_bank(self):
        line_ids = []
        # Unlink All one2many Line Ids from same wizard
        for wizard_id in self.env['bank.statement.line'].search([('wizard_id', '=', self.id)]):
            if wizard_id.wizard_id.id == self.id:
                self.write({'line_ids': [(3, wizard_id.id)]})
        # Creating Temp dictionary for Product List
        amount_received = 0

        for source in self.env['account.move.line'].search(
                [
                    ('date', '<', self.date_from), ('account_id', '=', self.journal_id.default_account_id.id)]):
            amount_received += source.debit

        amount_paid = 0

        for source in self.env['account.move.line'].search(
                [
                    ('date', '<', self.date_from), ('account_id', '=', self.journal_id.default_account_id.id), ]):
            amount_paid += source.credit

        self.amount_payment = amount_received - amount_paid
        lb = self.amount_payment

        for wizard in self:

            if wizard.type_cash == 'Partner':

                invoice_objs = self.env['account.move.line'].search(
                    [('date', '>=', wizard.date_from),
                     ('date', '<=', wizard.date_to),
                     ('account_id', '=', wizard.journal_id.default_account_id.id), ('credit', '=', 0.0),
                     ('move_id.state', '=', 'posted'),
                     ])

                for invoice in invoice_objs:
                    lb += invoice.debit
                    line_ids.append((0, 0, {
                        'wizard_id': self.id,
                        'payment_date': invoice.date,
                        'communication': invoice.ref,
                        'journal_id': invoice.journal_id.name,
                        'amount_received': invoice.debit,
                        'name': invoice.name,

                    }))
                invoice_objs = self.env['account.move.line'].search(
                    [('date', '>=', wizard.date_from),
                     ('date', '<=', wizard.date_to),
                     ('account_id', '=', wizard.journal_id.default_account_id.id),
                     ('debit', '=', 0.0), ('move_id.state', '=', 'posted'),
                     ])

                for invoice in invoice_objs:
                    lb -= invoice.credit
                    line_ids.append((0, 0, {
                        'wizard_id': self.id,
                        'payment_date': invoice.date,
                        'communication': invoice.ref,
                        'journal_id': invoice.journal_id.name,
                        'amount': invoice.credit,
                        'name': invoice.name,

                    }))

        self.end_amount = lb
        # writing to One2many line_ids
        self.write({'line_ids': line_ids})
        context = {
            'lang': 'en_US',
            'active_ids': [self.id],
        }

        return {
            'context': context,
            'data': None,
            'type': 'ir.actions.report',
            'report_name': 'report.bank_statement_report',
            'report_type': 'qweb-html',
            'report_file': 'report.bank_statement_report',
            'name': 'bank_statement_report',
            'flags': {'action_buttons': True},
        }


class bankStatementLine(models.TransientModel):
    _name = 'bank.statement.line'

    wizard_id = fields.Many2one('bank.statement', required=True, ondelete='cascade')
    payment_date = fields.Char("Date")
    communication = fields.Char("Code")
    journal_id = fields.Char(string="Safe")
    amount = fields.Float("Amount Paid")
    amount_received = fields.Float("Amount Received")
    partner_id = fields.Char("Partner")
    employee_expense = fields.Char("Employee")
    date = fields.Char("Date")
    code = fields.Char("Refrence")
    journal_employee = fields.Char(string="Safe")
    amount_employee = fields.Float(string="Amount Paid")
    amount_re = fields.Float(string="Amount Receive")
    payment_type = fields.Selection([
        ('send_money', 'Send Money'),
        ('receive_money', 'Receive Money')])
    payment_partner = fields.Char('Type')
    name = fields.Char('Description')
    _order = 'payment_date asc'
