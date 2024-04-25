from odoo import models, fields, api, _
from datetime import datetime, date ,timedelta ,time
from calendar import monthrange
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning
import logging as log

class HrAnnualLeave(models.Model):

    _name = 'hr.annual.leave'
    _description = 'Congés annuel'
    _order = 'date_start'

    _sql_constraints = [ 
      ('name', 'UNIQUE (name,employee_id)', 'Vous ne pouvez pas attribuer pour le même mois (et même année) un montant d\'allocation de congé') 
       ]

    @api.depends("annual_leave_line_ids")
    def compute_received_amount(self):
        for rec in self:
            sum = 0
            for line in rec.annual_leave_line_ids:
                sum += line.amount
            rec.received_amount = sum

    @api.depends("annual_leave_line_ids")
    def compute_used_number_days(self):
        for rec in self:
            sum = 0
            for line in rec.annual_leave_line_ids:
                sum += line.number_of_days
            rec.used_number_days = sum

    @api.depends("received_amount","leave_amount")
    def compute_diff_amount(self):
        for rec in self:
            rec.diff_amount = rec.received_amount + rec.leave_amount
  
    name = fields.Char(string="Nom")
    period = fields.Char(string="Période")

    date_start = fields.Date('Date de début')
    date_end = fields.Date('Date de fin')

    employee_id = fields.Many2one('hr.employee', string = 'Employé')
    company_id = fields.Many2one('res.company' , string = 'Société' ,default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency',default=lambda self: self.company_id.currency_id)

    leave_type_id = fields.Many2one('hr.leave.type', string = 'Type de congé')
    payslip_ids = fields.Many2many('hr.payslip' ,string = 'Bulletin de paie')
    annual_leave_line_ids = fields.One2many('hr.annual.leave.line', 'annual_leave_id', string = 'Ligne de congé annuel')

    allocated_days_number = fields.Float(string="Nbr. de jours attribué")
    used_number_days = fields.Float(string="Nbr. de jours utilisé", compute=compute_used_number_days)

    leave_amount = fields.Monetary('Montant du congé','currency_id')
    received_amount = fields.Monetary('Montant reçu' ,'currency_id', compute=compute_received_amount, store=True)
    diff_amount = fields.Monetary('Montant du congé','currency_id', compute=compute_diff_amount, store=True)
  
    @api.onchange("date_start","date_end","leave_type_id")
    def attribution_name(self):
        for rec in self:
            type = str(rec.leave_type_id.name) if rec.leave_type_id.name else "-"
            date_start = str(rec.date_start.strftime('%Y/%m/%d')) if rec.date_start else "-"
            date_end = str(rec.date_end.strftime('%Y/%m/%d')) if rec.date_end else "-"
            rec.name = type + " du " + date_start + " au " + date_end

# ligne de congé annuel
class HrLeaveLine(models.Model):

    _name = 'hr.annual.leave.line'
    _description = 'Lines de congés annuel'

    @api.depends("annual_leave_id")
    def compute_type(self):
        for rec in self:
            rec.leave_type_id = rec.annual_leave_id.leave_type_id

    @api.depends("annual_leave_id","number_of_days")
    def compute_amount(self):
        for rec in self:
            if rec.annual_leave_id:
                if rec.annual_leave_id.allocated_days_number != 0:
                    rec.amount = ( rec.annual_leave_id.leave_amount * rec.number_of_days ) / rec.annual_leave_id.allocated_days_number
            else:
                rec.amount = 0
            
    name = fields.Char(string="Nom")
    employee_id = fields.Many2one('hr.employee', string = 'Employé')
    currency_id = fields.Many2one('res.currency',default=lambda self: self.env.user.company_id.currency_id)

    payslip_id = fields.Many2one('hr.payslip', string = 'Bulletin de paie')
    annual_leave_id = fields.Many2one('hr.annual.leave' , string = 'Congé annuel')
    leave_type_id = fields.Many2one('hr.leave.type', string = 'Type de congé',compute=compute_type)

    number_of_days = fields.Float(string="Nombre de jours")
    amount = fields.Monetary('Montant' ,'currency_id', compute=compute_amount, store=True)
