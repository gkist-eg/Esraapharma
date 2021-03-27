import itertools
import logging

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, RedirectWarning, UserError


class AddManufact(models.Model):
    _inherit = 'product.product'
    man_for = fields.Boolean('Manufacturing For Others', related='product_tmpl_id.man_for', store=True)


class AddFixAssset(models.Model):
    _inherit = 'product.template'
    default_code = fields.Char('Internal Reference', index=True, required=True, store=True)

    main = fields.Many2one('prod.category', 'Main Category', store=True)
    sub11 = fields.Many2one('prod.sub', 'Sub Category', store=True)
    sub12 = fields.Many2one('prod.sub2', 'Sub Sub Category', store=True)
    market = fields.Many2one('prod.market')
    name1 = fields.Char(related='main.name')
    is_editable = fields.Boolean('edit')
    man_for = fields.Boolean('Manufacturing For Others', store=True)

    @api.depends('product_variant_ids', 'product_variant_ids.default_code')
    def _compute_default_code(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.default_code = template.product_variant_ids.default_code

    def _create_variant_ids(self):
        res = super(AddFixAssset, self)._create_variant_ids()
        for record in self:
            if len(record.product_variant_ids) > 1 and record.default_code:
                l = 1
                for variant in record.product_variant_ids:
                    variant.default_code = record.default_code + '-' + str(l)
                    l += 1

        return res

    @api.onchange('main', 'sub11', 'sub12', 'market')
    def compute_code(self):
        if self.main:
            self.default_code = self.main.code
            if self.sub11:
                self.default_code = self.main.code + self.sub11.code
                if self.sub12:
                    if self.market:
                        batch = ''
                        code = self.main.code + self.sub11.code + self.sub12.code + self.market.code
                        self.env.cr.execute(
                            "select default_code from product_template where default_code  like '" + code
                            + "___' order by default_code DESC LIMIT 1")
                        products = self.env.cr.fetchall()
                        for p in products:
                            if p:
                                seq = int(p[0][7:10]) + 1
                                batch = format(seq, '03d')
                        if not products:
                            batch = format(1, '03d')
                        self.default_code = code + batch

                    else:
                        batch = ''
                        code = self.main.code + self.sub11.code + self.sub12.code
                        self.env.cr.execute(
                            "select default_code from product_template where default_code  like '" + code
                            + "____' order by default_code DESC LIMIT 1")
                        products = self.env.cr.fetchall()
                        for p in products:
                            if p:
                                seq = int(p[0][6:10]) + 1
                                batch = format(seq, '04d')
                        if not products:
                            batch = format(1, '04d')
                        self.default_code = code + batch

    @api.onchange('main')
    def compute_codke(self):

        self.sub12 = False
        self.sub11 = False
        self.market = False
        self.default_code = ''


class ProductCategory(models.Model):
    _name = 'prod.category'
    name = fields.Char('Category Name', store=True, required=True)
    code = fields.Char('Code', store=True, size=2, required=True)
    sequance = fields.Char('Sequance', size=4, required=True, default='0000')


class ProductMarket(models.Model):
    _name = 'prod.market'
    name = fields.Char('Category Name', store=True, required=True)
    code = fields.Char('Code', store=True, size=1, required=True)


class SubCat(models.Model):
    _name = 'prod.sub'
    name = fields.Char('Category Name', store=True, required=True)
    code = fields.Char('Code', store=True, size=2, required=True)
    main_id = fields.Many2one('prod.category', 'Main Category', store=True, required=True)


class SubCat2(models.Model):
    _name = 'prod.sub2'
    name = fields.Char('Category Name', store=True, required=True)
    code = fields.Char('Code', store=True, size=2, required=True)
    main_id1 = fields.Many2one('prod.category', 'Main Category', store=True, required=True)





