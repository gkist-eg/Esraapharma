# -*- coding: utf-8 -*-
{
    'name': "Product Quantity Report",

    'summary': """
        Product Quantity Report""",

    'description': """
        Product Quantity Report
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'stock', 'restrict_warehouse'],

    # always loaded
    'data': [
        'wizard/product_quantity_wizard.xml',
        'report/product_quantity_report_template.xml',
        'report/product_quantity_report.xml',
        'security/ir.model.access.csv'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
