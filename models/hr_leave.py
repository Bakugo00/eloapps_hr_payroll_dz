from odoo import models, api, fields
from datetime import datetime
import time
import logging

class HrHolidays(models.Model):

	_inherit = 'hr.leave'

	id_val = fields.Boolean(
        'id_val',
        default=lambda self: self.get_menu(),
    )

	name_desc = fields.Char(
        string="information", 
        readonly=True,
    )

	contract_type_is = fields.Char(
        compute='_get_contract_type',
    )

	# Remplir le champ information
	@api.model_create_multi
	def create(self, vals_list):
		res = super(HrHolidays, self).create(vals_list)
		if res.date_from:
			d_month = res.date_from.strftime("%m")
			d_year = res.date_from.strftime("%Y")
			date_month= res.month_string_to_number(int(d_month))
			res.name_desc = 'Attribution de congé pour ' + str(date_month) + ' ' + str(d_year)
		return res

	def _get_contract_type(self):
		for record in self:
			contract_ids = self.env['hr.contract'].search([('employee_id','=',record.employee_id.id)])
			for contra in contract_ids: 
				date_cr = record.create_date
				if contra.date_end :
					if (date_cr <= contra.date_end) and (date_cr >= contra.date_start) :
						record.contract_type_is = contra.type_id.name
				else :
					if date_cr >= contra.date_start:
						record.contract_type_is = contra.type_id.name

	def get_menu(self):
		if 'default_type' in self._context :
			if self._context['default_type'] != 'add':
				return True
			else:
				return False

	def month_string_to_number(self, number):
		months = {
			1: 'Janvier',
			2: 'Fevrier',
			3: 'Mars',
			4: 'Avril',
			5: 'Mai',
			6: 'Juin',
			7: 'Juillet',
			8: 'Aout',
			9: 'Septembre',
			10: 'Octobre',
			11: 'Novembre',
			12: 'Decembre'
		}
		return months[number]
		
class HrHolidaysType(models.Model):

	_inherit = 'hr.leave.type'

	code = fields.Char(string='Code')