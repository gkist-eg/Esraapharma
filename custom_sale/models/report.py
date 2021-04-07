from odoo import models, fields, api


class InvoiceReport(models.TransientModel):
    _name = 'invoice.wizard'
    lines = fields.Many2many(comodel_name="account.move.line")

    from_date = fields.Date(string="", required=False, )
    to_date = fields.Date(string="", required=False, )
    invoices = fields.Many2many(comodel_name="account.move")
    state = fields.Selection(string="", selection=[('all', 'All Partner'), ('only', 'Only Partner'), ],
                             required=False, default='all')
    partner_ids = fields.Many2many(comodel_name="res.partner", string='Partner')
    return_inv=fields.Boolean('Returns')
    invoice_inv=fields.Boolean('Invoices',default=True)

    @api.onchange('state')
    def _onchange_FIELD_NAME(self):
        for rec in self:
            if rec.state == 'all':
                rec.partner_ids = False

    def get_partner(self):
        for rec in self:
            partners = []
            if rec.partner_ids:
                for partner in rec.partner_ids:
                    partners.append(partner.id)
            else:
                customer = self.env['res.partner'].search([])
                for partner in customer:
                    partners.append(partner.id)
            return partners

    def generate_report(self):
        for rec in self:
            rec.invoices = False
            partners = rec.get_partner()

            invoices = self.env['account.move'].search([
                ('invoice_date', '>=', rec.from_date), ('invoice_date', '<=', rec.to_date), (
                    'move_type', 'in', ['out_invoice','out_refund']), ('partner_id', 'in', partners)])
            invoice = []
            for inv in invoices:
                invoice.append(inv.id)
            # rec.write({'invoices':[(6,0,invoice)]})
            rec.invoices = [(6, 0, invoice)]
            print(rec.invoices)
            return self.env.ref('custom_sale.report_wizard_invoice').report_action(self)


class DetailsReport(models.TransientModel):
    _name = 'detail.wizard'

    from_date = fields.Date(string="", required=False, )
    to_date = fields.Date(string="", required=False, )
    invoices = fields.Many2many(comodel_name="account.move")
    lines = fields.Many2many(comodel_name="account.move.line")
    state = fields.Selection(string="", selection=[('all', 'All Partner'), ('only', 'Only Partner'), ],
                             required=False, default='all')
    partner_ids = fields.Many2many(comodel_name="res.partner", string='Partner')
    return_inv = fields.Boolean('Returns')
    invoice_inv = fields.Boolean('Invoices',default=True)

    @api.onchange('state')
    def _onchange_FIELD_NAME(self):
        for rec in self:
            if rec.state == 'all':
                rec.partner_ids = False

    def get_partner(self):
        for rec in self:
            partners = []
            if rec.partner_ids:
                for partner in rec.partner_ids:
                    partners.append(partner.id)
            else:
                customer = self.env['res.partner'].search([])
                for partner in customer:
                    partners.append(partner.id)
            return partners

    def generate_report(self):
        for rec in self:
            rec.invoices = False
            partners = rec.get_partner()
            if self.invoice_inv:
                invoices = self.env['account.move'].search([
                    ('invoice_date', '>=', rec.from_date), ('invoice_date', '<=', rec.to_date), (
                        'move_type', '=', 'out_invoice'), ('partner_id', 'in', partners)
                    ])

                # rec.write({'invoices':[(6,0,invoice)]})
                lines = self.env['account.move.line'].search([
                    ('exclude_from_invoice_tab', '=', False), ('move_id', 'in', invoices.ids)])
                print(lines.ids)
                rec.invoices = [(6, 0, invoices.ids)]
                rec.lines = [(6, 0, lines.ids)]
                print(rec.lines)
            if self.return_inv:
                invoices = self.env['account.move'].search([
                    ('invoice_date', '>=', rec.from_date), ('invoice_date', '<=', rec.to_date), (
                        'move_type', '=', 'out_refund'), ('partner_id', 'in', partners)
                    ])

                # rec.write({'invoices':[(6,0,invoice)]})
                lines = self.env['account.move.line'].search([
                    ('exclude_from_invoice_tab', '=', False), ('move_id', 'in', invoices.ids)])
                print(lines.ids)
                rec.invoices = [(6, 0, invoices.ids)]
                rec.lines = [(6, 0, lines.ids)]
                print(rec.lines)
            if self.invoice_inv and self.return_inv:
                invoices = self.env['account.move'].search([
                    ('invoice_date', '>=', rec.from_date), ('invoice_date', '<=', rec.to_date), (
                        'move_type', 'in',('out_refund','out_invoice') ), ('partner_id', 'in', partners)
                ])

                # rec.write({'invoices':[(6,0,invoice)]})
                lines = self.env['account.move.line'].search([
                    ('exclude_from_invoice_tab', '=', False), ('move_id', 'in', invoices.ids)])
                print(lines.ids)
                rec.invoices = [(6, 0, invoices.ids)]
                rec.lines = [(6, 0, lines.ids)]
                print(rec.lines)
            return self.env.ref('custom_sale.report_wizard_detail').report_action(self)


class BalanceReport(models.TransientModel):
    _name = 'balance.wizard'

    from_date = fields.Date(string="", required=False, )
    to_date = fields.Date(string="", required=False, )
    # invoices = fields.Many2many(comodel_name="account.move")
    state = fields.Selection(string="", selection=[('all', 'All Partner'), ('only', 'Only Partner'),('category','Category') ],
                             required=False, default='all')
    partner_ids = fields.Many2many(comodel_name="res.partner", string='Partner')
    category_type = fields.Many2one(comodel_name="category.customer", string="", )

    @api.onchange('state')
    def _onchange_FIELD_NAME(self):
        for rec in self:
            if rec.state == 'all':
                rec.partner_ids = False

    def get_partner(self):
        for rec in self:
            partners = []
            if rec.partner_ids:
                for partner in rec.partner_ids:
                    partners.append(partner.id)
            elif rec.category_type:
                customer = self.env['res.partner'].search([('categ_id.category_type','=',rec.category_type.category_type)])
                for partner in customer:
                    partners.append(partner.id)
            else:
                customer = self.env['res.partner'].search([])
                for partner in customer:
                    partners.append(partner.id)
            return partners

    def generate_report(self):
        for rec in self:
            partners = rec.get_partner()
            data = []

            for partner in partners:
                if self.state == 'category':
                    invoices = self.env['account.move'].search([
                        ('invoice_date', '>=', rec.from_date), ('invoice_date', '<=', rec.to_date), (
                            'move_type', '=', 'out_invoice'), ('partner_id', '=', partner),('cust_categ_id.category_type','=',self.category_type.category_type)])
                    total = 0
                    res = 0
                    status=' '
                    for inv in invoices:
                        total += inv.amount_total
                        res += inv.amount_residual
                    totals=+total
                    paid = total - res
                    if paid ==0:
                        status='Paid'
                    partner_name = self.env['res.partner'].search([('id', '=', partner)])

                    datas = {'partner': partner_name.name, 'code': partner_name.code, 'paid': paid, 'total': total,'totals': totals,
                             'res': res}
                    if total == 0:
                        continue
                    else:
                        data.append(datas)
                else:
                    invoices = self.env['account.move'].search([
                        ('invoice_date', '>=', rec.from_date), ('invoice_date', '<=', rec.to_date), (
                            'move_type', '=', 'out_invoice'), ('partner_id', '=', partner)])
                    total = 0
                    res = 0
                    status=''

                    for inv in invoices:
                        total += inv.amount_total
                        res += inv.amount_residual
                        if res ==0:
                            status == 'Paid'
                        else:
                            status == 'Not Paid'
                    paid = total - res
                    totals=+total

                    partner_name = self.env['res.partner'].search([('id', '=', partner)])

                    datas = {'partner': partner_name.name, 'code': partner_name.code, 'paid': paid, 'total': total, 'totals': totals,
                             'res': res,'status':status}
                    if total == 0:
                        continue
                    else:
                        data.append(datas)
            report = {'data': data, 'from_date': self.from_date, 'to_date': self.to_date}

            return self.env.ref('custom_sale.report_wizard_balance').report_action(self, data=report)


class ReportSaleDetails(models.AbstractModel):
    _name = 'report.custom_sale.report_balance'
    _description = 'Customer Balance'

    @api.model
    def _get_report_values(self, docids, data=None):
        print(data)
        data = dict(data or {})
        return data
