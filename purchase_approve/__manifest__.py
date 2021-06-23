# -*- coding: utf-8 -*-
{
    'name': "Gkist Purchase Approve",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        edit system approve in purchase order
    """,

    'author': "G K I S T",
    'website': "http://www.gkist-eg.com",



    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',"purchase","purchase_stock"],

    # always loaded
    'data': [
        'security/security.xml',
        'views/templates.xml',

        # 'security/ir.model.access.csv',
        'views/edit_purchase_approve.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
