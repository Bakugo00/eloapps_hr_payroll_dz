# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, time
import logging as log

from pytz import utc

class ResourceMixin(models.AbstractModel):
    _inherit = "resource.mixin"

    def list_leaves(self, from_datetime, to_datetime, calendar=None, domain=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a list of tuples (day, hours, resource.calendar.leaves)
            for each leave in the calendar.
        """
        resource = self.resource_id
        calendar = calendar or self.resource_calendar_id
        # naive datetimes are made explicit in UTC
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=utc)

        attendances = calendar._attendance_intervals_batch(from_datetime, to_datetime, resource)[resource.id]
        leaves = calendar._leave_intervals_batch(from_datetime, to_datetime, resource, domain)[resource.id]
        result = []
        for start, stop, leave in (leaves & attendances):
            hours = (stop - start).total_seconds() / 3600
            result.append((start.date(), hours, leave))
        return result




class HrPayslipEmployees(models.TransientModel):
    _name = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'


    def _domain_employee(self):
        payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))
        contracts = self.env['hr.contract'].search([('date_start','<', payslip_run.date_end),
                                                    '|',('date_end','>',payslip_run.date_start),
                                                     ('date_end','=',False)])

        emp = contracts.mapped('employee_id')
        return [('id','in', emp.ids)]

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employés',domain=_domain_employee)


    def compute_sheet(self):
        journal_id = False
        if self.env.context.get('active_id'):
            journal_id = self.env['hr.payslip.run'].browse(self.env.context.get('active_id')).journal_id.id

        payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start', 'date_end', 'credit_note'])
        
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        if not data['employee_ids']:
            raise UserError(_("Vous devez sélectionnner un (des) employé(s) pour générer une (des) fiche(s) de paie."))

        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            slip_data = self.env['hr.payslip']._onchange_employee_id(from_date, to_date, employee.id, contract_id=False)
            
            #Recuperer les types de congé a partir des jours travaillé 
            contract = self.env['hr.contract'].search([('id','=',slip_data['value'].get('contract_id') )])
            day_from = datetime.combine(fields.Date.from_string(from_date), time.min)
            day_to = datetime.combine(fields.Date.from_string(to_date), time.min)
            if not contract:
                raise UserError(_('Vous ne pouvez pas calculer le temps de travail sans contract'))
            day_leave_intervals = contract.employee_id.list_leaves(day_from, day_to, calendar=contract.resource_calendar_id)
            types = self.env['hr.leave.type']
            for day, hours, leave in day_leave_intervals:
                holiday = leave.holiday_id
                if holiday.holiday_status_id not in types:
                    types += holiday.holiday_status_id


            #Recuperer les congés annuals par types 
            annuals = self.env["hr.annual.leave"].search([('employee_id','=',employee.id),('leave_type_id','in',types.ids)])
            filtred_annuals = self.env["hr.annual.leave"]
            for annual in annuals:
                if annual.allocated_days_number > annual.used_number_days:
                    filtred_annuals += annual


            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': slip_data['value'].get('struct_id'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': active_id,
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': run_data.get('credit_note'),
                'company_id': employee.company_id.id,
                'leave_type_id': types.ids,
                'journal_id': employee.contract_id.journal_id.id,

                
                
            }
            pays = self.env['hr.payslip'].create(res)
            pays.write({
                
                'annual_leave_ids': filtred_annuals.ids,
                })
            payslips += pays



        payslips.compute_work()
        payslips.compute_conge()
        payslips.compute_sheet()
        
        return {'type': 'ir.actions.act_window_close'}
