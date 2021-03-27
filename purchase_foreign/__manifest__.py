# -*- coding: utf-8 -*-
{
    'name': "purchase_foreign",

    # 'summary': """
    #     # Short (1 phrase/line) summary of the module's purpose, used as
    #     # subtitle on modules listing or apps.openerp.com
    #     """,

    'description': """
        when we buy from foreign
    """,

    'author': "G K I S T",
    'website': "http://www.gkist-rg.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','purchase','purchase_stock','hr',],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/edit_purchase_order_foreign.xml',
        'views/purchase_foreign_view.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}
