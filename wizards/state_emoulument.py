# -*- coding:utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from odoo.exceptions import Warning
import logging as log
from collections import OrderedDict
from dateutil import relativedelta
from odoo.exceptions import ValidationError


class StateEmoulument(models.TransientModel):
   
    _name = 'state.emoulument'
    _description = "Relevé des émoluments"

    company_id = fields.Many2one('res.company', 'Société' ,default=lambda self: self.env.company)
    company_address = fields.Char('Adresse', compute="_compute_company_info")
    company_phone = fields.Char('Téléphone', compute="_compute_company_info")

    @api.depends('company_id')
    def _compute_company_info(self):
        for record in self:
            record.company_address = record.company_id.street
            record.company_phone = record.company_id.phone

    def domain_employee(self): 
        contract_ids = self.env['hr.contract'].search([('struct_id.code','in', ['STCH','STCJ'])])

        return [('contract_id','not in', contract_ids.ids)]

    employee_id = fields.Many2one('hr.employee','Employé', domain=domain_employee)
    job_name = fields.Char('Travail', compute="_compute_employee_info")
    employee_address = fields.Char('Adresse', compute="_compute_employee_info")
    employee_phone = fields.Char('Téléphone', compute="_compute_employee_info")
    social_security = fields.Char('Sécurité Sociale', compute="_compute_employee_info")
    birthday = fields.Date('Date de naissance', compute="_compute_employee_info")
    place_of_birth = fields.Char('Lieu de naissance', compute="_compute_employee_info")

    @api.depends('employee_id')
    def _compute_employee_info(self):
        for record in self:
            record.employee_address = record.employee_id.address_id.street
            record.job_name = record.employee_id.contract_id.job_id.name
            record.employee_phone = record.employee_id.mobile_phone
            record.social_security = record.employee_id.sec_social
            record.birthday = record.employee_id.birthday
            record.place_of_birth = record.employee_id.place_of_birth

    date_from = fields.Date('Date de début')
    date_to = fields.Date('Date de fin')

    @api.onchange('date_from')
    def onchange_date_from(self):
        log.warning('in const')
        if self.date_from and self.date_from.day != 1:
            log.warning('in if  const')
            self.date_from = date(day= 1, month= self.date_from.month, year= self.date_from.year)

    @api.onchange('date_to')
    def onchange_date_to(self):
        if self.date_to :
            self.date_to = date(day=1, month= self.date_to.month+1 if self.date_to.month< 12 else 1 , year= self.date_to.year) - timedelta(days=1)





    def print_report(self):

        delta = relativedelta.relativedelta(self.date_to, self.date_from)
      
        if delta.months <= 12 :
            return self.env.ref('eloapps_hr_payroll_dz.hr_statement_emoulument').report_action(self)
        else:
            raise models.ValidationError("La période ne doit pas être superieure à 12 mois")


    def months_between(self, start_date, end_date):

        year = start_date.year
        month = start_date.month
        liist = []
        while (year, month) <= (end_date.year, end_date.month):
            liist.append(date(year, month, 1))
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
        return liist

    def months_number_list(self ,start_date,end_date ):

        a = self.months_between(start_date, end_date)
   
        numbers = []
        for m in a:
            numbers.append(m.month)
        return numbers


    def calcule_lines(self):

        a = self.months_between(self.date_from, self.date_to)
     

        ## to ease the work
        payslips = self.env['hr.payslip']
        lines = self.env['hr.payslip.line']
  

        months = {1:'january',2:'february',3:'mars',4:'april',
        5:'may',6:'june',7:'july',8:'august',9:'september',
        10:'october',11:'november',12:'december'}


        ## domain for paysilp with the date mentionned
        domain = [
              ('employee_id', '=', self.employee_id.id),
              ('state', 'in', ['done', 'draft']), 
              ('credit_note', '=', False), 
              ('refund_payslip', '=', False),
              ('date_from', '<=', self.date_to),
              ('date_to', '>=', self.date_from)]


        dict_lines = {}
        dict_total = {}
        ## iterate through the payslips
        lines_sbase = lines_ss = lines_snet = lines_sbrut = lines_divers = lines
        for payslip in payslips.search(domain):
            month = payslip.date_from.month


            # lines_sp += lines.search([('id','in', payslip.line_ids.ids),('category_id.code','in',['BASIC','COT'])])
            # lines_b_impo += lines.search([('id','in', payslip.line_ids.ids),'|',('category_id.code','in',['BASIC','COT','IMP','IMP10','IMP15']),('code','=','SS')])
            lines_sbase += lines.search([('id','in', payslip.line_ids.ids),('category_id.code','=','BASIC')])
            lines_ss += lines.search([('id','in', payslip.line_ids.ids),('code','=','SS')])
            lines_snet += lines.search([('id','in', payslip.line_ids.ids),('category_id.code','=','NET')])
            lines_sbrut += lines.search([('id','in', payslip.line_ids.ids),('category_id.code','=','GROSS')])

            lines_divers += lines.search([('id','in', payslip.line_ids.ids),('category_id.code','in',['COT','IMP','IMP10','IMP15','ALW'])])
            
        rubs = [
                # ['SP',lines_sp],
                # ['B Impo.', lines_b_impo],
                ['Salaire de base', lines_sbase],
                ['Sécurité Sociale', lines_ss],
                ['divers', lines_divers],
                ['Salaire Brut', lines_sbrut],
                ['Salaire Net', lines_snet]]


        for r in rubs:
            # month = r[1].slip_id.date_from.month
            if r[0] == 'divers':
                for l in lines_divers:
                    month = str(l.slip_id.date_from.year )+ '/' + str(l.slip_id.date_from.month)
                    if l.code in dict_lines:
                        if month in dict_lines[l.code ]:
                            dict_lines[l.code ][month] += l.total
                        else: 
                            dict_lines[l.code ].update({month: l.total})
                    else :
                        dict_lines.update({l.code : {'rub': l.name,  month: l.total} })

                    if month in dict_total:
                        dict_total[month] += l.total
                    else:
                        dict_total.update({month: l.total})
                continue

       
            if r[0] in dict_lines:
                for l in r[1]:
                    month = str(l.slip_id.date_from.year )+ '/' + str(l.slip_id.date_from.month)
                    if month in dict_lines[r[0]]:
                        dict_lines[r[0]][month] += l.total
                    else: 
                        dict_lines[r[0]].update({month: l.total })

                    if month in dict_total:
                        dict_total[month] += l.total
                    else:
                        dict_total.update({month: l.total})
            else :
                first = True 
                for l in r[1]:
                    month = str(l.slip_id.date_from.year )+ '/' + str(l.slip_id.date_from.month)
                    if first :
                        dict_lines.update({r[0]: {'rub': r[0], month: l.total} })
                        first = False
                    else :
                        if month in dict_lines[r[0]]:
                            dict_lines[r[0]][month] += l.total
                        else: 
                            dict_lines[r[0]].update({month: l.total })

                    if month in dict_total:
                        dict_total[month] += l.total
                    else:
                        dict_total.update({month: l.total})

        
        
        log.warning('dict_lines')
        log.warning(dict_lines)

        log.warning('dict_total')
        log.warning(dict_total)
        return dict_lines, dict_total
