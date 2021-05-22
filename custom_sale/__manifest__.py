# -*- coding: utf-8 -*-
{
    'name': "custom_sale",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Asem Tal3t",
    'website': "asemasem728@gmail.com",

    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','contacts','sale','account','hr','stock','sale_stock'],

    # always loaded
    'data': [
        'views/data.xml',

        'security/ir.model.access.csv',
        'security/security.xml',
        'views/public_price.xml',
        'views/views.xml',
        'views/edit.xml',
        'views/data.xml',
        #'views/report.xml',
        'views/refund.xml',
        'views/templates.xml',
        'views/air_delivery_order.xml',
        'views/sale_report.xml',
        'demo/demo.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #
    # ],
}
