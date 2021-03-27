# -*- coding: utf-8 -*-
{
    'name': "cash",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Nourhan Ali",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account','hr','mail','product','sale','account','stock','sale_stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/cash.xml',
        'views/account.xml',
        'views/cash.xml',
        'views/code.xml',
        'report/report.xml',
        'report/safe_statement_report.xml',
        'report/bank_statement_report.xml',
        'report/check_statement_report.xml',
        'wizard/safe_statement_report.xml',
        'wizard/bank_statement_report.xml',
        'wizard/check_statement_report.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
