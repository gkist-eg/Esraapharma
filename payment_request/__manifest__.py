# -*- coding: utf-8 -*-
{
    'name': "Gkist Payment Request",

    'summary': """
       """,

    'description': """
    """,

    'author': "Alzahraa Gamal",
    'website': "http://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['purchase_stock','mail','account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
