from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning
from calendar import calendar, monthrange
from datetime import datetime, time

class HolidaysAllocationInherited(models.Model):
    """ Allocation Requests Access specifications: similar to leave requests """
    _inherit = 'hr.leave.allocation'
    _description = 'Holidays Allocation Inherited'

    @api.model
    def _update_accrual(self):
        """
            Method called by the cron task in order to increment the number_of_days when
            necessary.
        """
        today = fields.Date.from_string(fields.Date.today())
        holidays = self.search([('allocation_type', '=', 'accrual'), ('employee_id.active', '=', True), ('state', '=', 'validate'), ('holiday_type', '=', 'employee'),
                                '|', ('date_to', '=', False), ('date_to', '>', fields.Datetime.now()),
                                '|', ('nextcall', '=', False), ('nextcall', '<=', today)])

        for holiday in holidays:
            values = {}
            delta = relativedelta(days=0)
            if holiday.interval_unit == 'days':
                delta = relativedelta(days=holiday.interval_number)
            if holiday.interval_unit == 'weeks':
                delta = relativedelta(weeks=holiday.interval_number)
            if holiday.interval_unit == 'months':
                delta = relativedelta(months=holiday.interval_number)
            if holiday.interval_unit == 'years':
                delta = relativedelta(years=holiday.interval_number)
            if holiday.nextcall:
                values['nextcall'] = holiday.nextcall + delta
            else:
                values['nextcall'] = holiday.date_from
                while values['nextcall'] <= datetime.combine(today, time(0, 0, 0)):
                    values['nextcall'] += delta

            period_start = datetime.combine(today, time(0, 0, 0)) - delta
            period_end = datetime.combine(today, time(0, 0, 0))

            # We have to check when the employee has been created
            # in order to not allocate him/her too much leaves
            start_date = holiday.employee_id._get_date_start_work()
            # If employee is created after the period, we cancel the computation
            if period_end <= start_date or period_end < holiday.date_from:
                holiday.write(values)
                continue

            # If employee created during the period, taking the date at which he has been created
            if period_start <= start_date:
                period_start = start_date

            employee = holiday.employee_id
            worked = employee._get_work_days_data_batch(
                period_start, period_end,
                domain=[('holiday_id.holiday_status_id.unpaid', '=', True), ('time_type', '=', 'leave')]
            )[employee.id]['days']
            left = employee._get_leave_days_data_batch(
                period_start, period_end,
                domain=[('holiday_id.holiday_status_id.unpaid', '=', True), ('time_type', '=', 'leave')]
            )[employee.id]['days']
            prorata = worked / (left + worked) if worked else 0


            days_to_give = holiday.number_per_interval

            if holiday.unit_per_interval == 'hours':
                # As we encode everything in days in the database we need to convert
                # the number of hours into days for this we use the
                # mean number of hours set on the employee's calendar
                days_to_give = days_to_give / (employee.resource_calendar_id.hours_per_day or HOURS_PER_DAY)
            values['number_of_days'] = holiday.number_of_days + days_to_give * prorata
            if holiday.accrual_limit > 0:
                values['number_of_days'] = min(values['number_of_days'], holiday.accrual_limit)

            if values['number_of_days'] - self.number_of_days > 0:
                obj = self.env['hr.annual.leave'].search([])
                m = datetime.now().date().month
                y = datetime.now().date().year
                cal = monthrange(y, m)[1]
                date_debut = datetime.now().date().replace(day=1)
                date_fin = datetime.now().date().replace(day=cal,month=m,year=y)
                
                leave_amount = 0
                payslip_id  = self.env['hr.payslip'].search([('employee_id','=',holiday.employee_id.id),('date_from','=',date_debut),('date_to','=',date_fin)],limit=1)
                if payslip_id:
                    for line in payslip_id.line_ids:
                        if line.code == 'MC':
                            leave_amount = line.total

                            

                date_month = datetime.now().date().month
                date_year = datetime.now().date().year
                last_day_of_month = monthrange(date_year,date_month)[1]

                obj.create({
                    "date_start" : "{}-{}-01".format(date_year,date_month),
                    "date_end" : "{}-{}-{}".format(date_year,date_month,last_day_of_month),
                    "name" : str(holiday.holiday_status_id.name) + " du " + "{}/{}/01".format(date_year,date_month) + " au " + "{}/{}/{}".format(date_year,date_month,last_day_of_month),
                    "employee_id": holiday.employee_id.id,
                    "leave_type_id" :holiday.holiday_status_id.id,
                    "allocated_days_number" : holiday.number_per_interval,
                    "leave_amount" : leave_amount,
                    })

            # if values['number_of_days'] > 0:
            #     log.warning("..........values['number_of_days']........... {}".format(values['number_of_days']))

            holiday.write(values)
