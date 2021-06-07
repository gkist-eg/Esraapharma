# from odoo import api, models
#
#
# class TotalInventoryReport(models.AbstractModel):
#     _name = 'report.total_inventory_report.total_inventory_report_template'
#     _description = 'Total Inventory Report'
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         #print('_______________________________________________________________________')
#         stock_moves = self.env['stock.move'].search([])
#         stock_move_list = []
#         for stock_move in stock_moves:
#             #print(stock_move.location_id.name + " " + stock_move.product_id.name)
#             vals = {
#                 'product_id': stock_move.product_id.default_code,
#                 'product_name': stock_move.product_id.name
#             }
#             stock_move_list.append(vals)
#             #print(stock_move_list)
#         return {
#             'doc_model': 'stock.move',
#             'data': data,
#             'docs': [self],
#             'stock_move_list': stock_move_list
#         }
