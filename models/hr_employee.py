from odoo import api, fields, models
from datetime import datetime
class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    slip_ids = fields.One2many('hr.payslip', 'employee_id', string='Bulletin de paie', readonly=True)
    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Nombre de bulletin de paie')

    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.slip_ids)
    