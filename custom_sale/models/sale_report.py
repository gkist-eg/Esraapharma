# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit= "sale.report"


    cust_categ_id = fields.Many2one('category.customer', 'Customer Category', readonly=True)
    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['cust_categ_id'] = ', s.cust_categ_id as cust_categ_id'

        groupby += ', s.cust_categ_id'

        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)
