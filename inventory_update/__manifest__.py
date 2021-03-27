# -*- coding: utf-8 -*-
{
    'name': "Inventory updates",

    'summary': """""",

    'description': """
    """,

    'author': "G K I S T",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['stock','stock_account','product_expiry','sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/lot.xml',
        'views/views.xml',
        'views/location.xml',
        'views/templates.xml',
        'views/report.xml',
        'views/balet.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
