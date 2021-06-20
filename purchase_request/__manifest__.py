# -*- coding: utf-8 -*-


{
    'name': 'Purchase Request',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['base', "purchase", "hr", "account", 'purchase_stock', ],
    'data': [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/inherit_sequence.xml",
        "views/view_purchase_requests.xml",
        # "views/print_pdf.xml",
        "views/id_line_sequence.xml",
        "views/edit_menuitem_purchase_order.xml",
        "views/purchase_request_line_view.xml",
        # "views/purchase_foreign_view.xml",
        "views/edit_purchase_order.xml",
        "data/purchase_approve_data.xml",
        "views/id_sequence.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
