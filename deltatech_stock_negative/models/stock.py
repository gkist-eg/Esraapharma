# ©  2015-2019 Deltatech
# See README.rst file on addons root folder for license details


from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.constrains('quantity')
    def _update_quantity(self):
        if self.location_id.usage in ("transit", "internal") and round(self.quantity, 6) < 0.000000000 and self.env.company.subcontracting_location_id != self.location_id:
            if self.location_id.company_id.no_negative_stock:
                raise ValidationError(
                    _(
                        "You have chosen to avoid negative stock. \
                         pieces of  but you want to transfer  \
                        %s   pieces of %s of lot %s . Please adjust your quantities or \
                        correct your stock with an inventory adjustment."
                    )
                    % (self.quantity,self.product_id.name,self.lot_id.name)
                )



    # @api.model
    # def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False):
    #     available_quantity = self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id,
    #                                                       owner_id=owner_id, strict=strict)
    #     if location_id.usage == "internal" and (available_quantity + quantity) < 0:
    #         if location_id.company_id.no_negative_stock:
    #             raise UserError(
    #                 _(
    #                     "You have chosen to avoid negative stock. \
    #                     %s pieces of %s are remaining in location %s  but you want to transfer  \
    #                     %s pieces. Please adjust your quantities or \
    #                     correct your stock with an inventory adjustment."
    #                 )
    #                 % (available_quantity, product_id.name, location_id.name, quantity)
    #             )
    #
    #     return super(StockQuant, self)._update_reserved_quantity(product_id, location_id, quantity, lot_id, package_id, owner_id, strict)
