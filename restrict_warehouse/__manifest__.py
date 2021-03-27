# -*- coding: utf-8 -*-
{
    'name': "Restrict Warehouse",

    'summary': """
      """,

    'description': """
            Restrict Warehouse user    """,

    'author': "G K I S T",
    'category': 'Inventory/Purchase',
    'website': "http://www.gkist-eg.com/",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['stock','sale_stock','purchase_stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
