from datetime import datetime, date

from odoo import api, fields, models, _


class CheckStatement(models.TransientModel):
    _name = 'check.statement'

    type_cash = fields.Selection([
        ('Partner', 'Partner')
        , ], store=True, default='Partner', invisible='1')

    @api.model
    def _getUserGroupId(self):
        return [('id', '=', self.env.user.default_report.ids), ('type', '=', 'bank'),
                ('account_check', 'in', ('check_send', 'check_received'))]

    journal_id = fields.Many2one('account.journal', 'Journal', store=True, track_visibility='onchange', required=True,
                                 domain=_getUserGroupId)

    @api.model
    def _getsafeId(self):
        return [('id', '=', self.env.user.default_report.ids), ('type', '=', 'cash'), ]

    safe_id = fields.Many2one('account.journal', 'Save', store=True, required=True, domain=_getsafeId)

    amount_payment = fields.Char('Amount')
    amount_cash = fields.Char('Amount')

    @api.model
    def _get_from_date(self):
        company = self.env.user.company_id
        current_date = date.today()
        from_date = company.compute_fiscalyear_dates(current_date)['date_from']
        return from_date

    def _get_date(self):
        today = date.today()
        first_day = today.replace(day=1)

        return first_day

    date_from = fields.Date("Start Date", default=_get_date)
    date_to = fields.Date("End Date", default=datetime.today(), )
    line_ids = fields.One2many('check.statement.line', 'wizard_id', required=True, ondelete='cascade')

    def print_pdf_check(self):
        line_ids = []
        # Unlink All one2many Line Ids from same wizard
        for wizard_id in self.env['check.statement.line'].search([('wizard_id', '=', self.id)]):
            if wizard_id.wizard_id.id == self.id:
                self.write({'line_ids': [(3, wizard_id.id)]})
        # Creating Temp dictionary for Product List

        for wizard in self:

            if wizard.type_cash == 'Partner':
                invoice_objs = self.env['account.move.line'].search(
                    [('date', '>=', wizard.date_from),
                     ('date', '<=', wizard.date_to),
                     ('account_id', '=', wizard.journal_id.default_account_id.id),

                     ('debit', '=', 0.0)
                     ])
                for invoice in invoice_objs:
                    line_ids.append((0, 0, {
                        'wizard_id': self.id,
                        'payment_date_check': invoice.date,
                        'communication_check': invoice.ref,
                        'journal_id_check': invoice.journal_id.name,
                        'amount_check': invoice.credit,
                        'partner_id_check': invoice.partner_id.name,
                        'ch_number': invoice.check_num,
                        'date_maturity': invoice.date_due,
                        'payment_partner': invoice.payment,

                    }))

                invoice_objs = self.env['account.move.line'].search(
                    [('date', '>=', wizard.date_from),
                     ('date', '<=', wizard.date_to),
                     ('account_id', '=', wizard.journal_id.default_account_id.id),

                     ('credit', '=', 0.0)
                     ])
                for invoice in invoice_objs:
                    line_ids.append((0, 0, {
                        'wizard_id': self.id,
                        'payment_date_check': invoice.date,
                        'communication_check': invoice.ref,
                        'journal_id_check': invoice.journal_id.name,
                        'amount_received': invoice.debit,
                        'partner_id_check': invoice.partner_id.name,
                        'ch_number': invoice.check_num,
                        'date_maturity': invoice.date_due,
                        'payment_partner': invoice.payment,

                    }))

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
            'report_name': 'cash.check_statement_report',
            'report_type': 'qweb-html',
            'report_file': 'cash.check_statement_report',
            'name': 'check_statement_report',
            'flags': {'action_buttons': True},
        }


class CustomerStatementLine(models.TransientModel):
    _name = 'check.statement.line'

    wizard_id = fields.Many2one('check.statement', required=True, ondelete='cascade')
    payment_date = fields.Date("Date")
    communication = fields.Char("Code")
    journal_id = fields.Char(string="Safe")
    amount = fields.Float("Amount Paid")
    amount_received = fields.Float("Amount Received")
    partner_id = fields.Char("Partner")
    employee_expense = fields.Char("Employee")
    date = fields.Date("Date")
    code = fields.Char("Refrence")
    journal_employee = fields.Char(string="Safe")
    amount_employee = fields.Float(string="Amount Paid")
    amount_re = fields.Float(string="Amount Receive")
    payment_type = fields.Selection([
        ('send_money', 'Send Money'),
        ('receive_money', 'Receive Money')])
    payment_partner = fields.Selection([
        ('expense', 'Expense'),
        ('partner', 'Partner'),
        ('loan', 'Loans'), ('custody', 'Custody'), ('other', 'Other')])

    payment_date_check = fields.Date('Date')
    communication_check = fields.Char('Reference')

    journal_id_check = fields.Char('Journal')
    amount_check = fields.Char('Amount')
    partner_id_check = fields.Char('Partner')
    ch_number = fields.Char('Check Number')
    date_maturity = fields.Date('Due Date')
    check_receive = fields.Char('Check Receive')

    date_check = fields.Date('Date')
    code_check = fields.Char('Refrence')
    journal_check = fields.Char('journal')
    payment_type_check = fields.Selection([
        ('send_money', 'Send Money'),
        ('receive_money', 'Receive Money')])
    payment_partner = fields.Char()

    amount_check = fields.Float('Amount Paid')
    amount_re_check = fields.Float('Amount Received')
    check_number = fields.Char('check Number')
    due_date = fields.Date('Due Date')
    bank = fields.Char('Bank')
    bank_account = fields.Char('Bank Account Number')

    employee_expense_check = fields.Char('Employee')
    _order = 'payment_date_check asc'
