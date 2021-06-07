# -*- coding: utf-8 -*-
{
    'name': "Total_Inventory_Report",

    'summary': """
        Total Inventory Report""",

    'description': """
        Total Inventory Report
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'stock'],

    # always loaded
    'data': [
        'wizards/total_inventory_wizard.xml',
        'report/total_inventory_report.xml',
        'report/total_inventory_report_template.xml',
        'security/ir.model.access.csv',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
