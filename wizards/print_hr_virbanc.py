# -*- coding:utf-8 -*-
from odoo import fields, api, models, _
from datetime import datetime, date ,timedelta
import calendar
from collections import OrderedDict

from odoo.exceptions import UserError, ValidationError

import logging as log
global_datas = {}

class hr_payroll_report_virbanc(models.TransientModel):
   
    _name = 'hr.payroll.report.virbanc'
    _description = "Virement bancaire"

    employee_id = fields.Many2one(
        'hr.employee', 
        string="Employé",
    )

    def _compute_w_tri_selection(self):
        w_tri_list = [('T1', 'Premier Trimestre'),
                    ('T2', 'Deuxième Trimestre'),
                    ('T3', 'Troisième Trimestre'),
                    ('T4', 'Quatrième Trimestre')
        ]
        return w_tri_list

    w_tri = fields.Selection(
        selection=lambda self: self._compute_w_tri_selection(),
        string="Trimestre",
    )

    def _compute_year_selection(self):
        return [(num, str(num)) for num in range(1990,(datetime.now().year)+ 2)]
   
    def _compute_month_selection(self):
        return [(num, calendar.month_name[num]) for num in range(1, 13)]
        
    year = fields.Char(
        string="Année",
        default=datetime.now().year,
        required=True,
    )
    w_month = fields.Selection(
        selection=[
        ('1','Janvier'),
        ('2','Février'),
        ('3','Mars'),
        ('4','Avril'),
        ('5','Mai'),
        ('6','Juin'),
        ('7','Juillet'),
        ('8','Août'),
        ('9','Septembre'),
        ('10','Octobre'),
        ('11','Novembre'),
        ('12','Décembre'),
        ],
        string='Mois',
        
    )
  
   

    all_employee = fields.Boolean(
        string="Tous les employés", 
        default=True,

    )

    employee_ids = fields.Many2many(
        'hr.employee', 
        string="Employé à exclure",
    )

    def get_tri(self, T):
        """this function return the full name of selected trimester in interface
        :Parameters:
        -------------
        :param T:the selected trimester
        :type : Selection (Str)
        :returns: return the the full name of the parameters T
        :rtype: String
        """
        if T == 'T1':
            return '1 er Trimestre'
        if T == 'T2':
            return '2 ème Trimestre'
        if T == 'T3':
            return '3 ème Trimestre'
        if T == 'T4':
            return '4 ème Trimestre'

    


    @api.model
    def get_datas(self):
        global global_datas
        return global_datas

    def print_report(self):
        """this function generates a Leave report as PDF

        :returns: this returns an 'action.report'
        :rtype: action

        """
        global global_datas

        report_name = 'eloapps_hr_payroll_dz.hr_payroll_virement_bancaire'
        line = self.get_line_virement()


        global_datas.update({'lines': line})
        return self.env.ref(report_name).report_action(self)


    def get_line_virement(self):
        payslips = self.env['hr.payslip']
        lines = self.env['hr.payslip.line']

        dict_lines = {}

        if self.all_employee :
            employees = self.env['hr.employee'].search([('bank_account_id','!=',False)])
        else :
            employees = self.env['hr.employee'].search([('bank_account_id','!=',False),('id','not in',self.employee_ids.ids)])
        
        domain = [('employee_id', 'in', employees.ids),
                  ('date_from', '>=', date(year=int(self.year), month=int(self.w_month), day=1)),
                  ('date_to', '<=', date(year=int(self.year), month=int(self.w_month), day=calendar.monthrange(int(self.year), int(self.w_month))[1]))]
        
        emps = self.env['hr.employee']
        for pay in payslips.search(domain):
            if pay.employee_id not in emps:
                emps += pay.employee_id 

        for emp in emps:
            pays = payslips.search([('employee_id', '=', emp.id),
                  ('date_from', '>=', date(year=int(self.year), month=int(self.w_month), day=1)),
                  ('date_to', '<=', date(year=int(self.year), month=int(self.w_month), day=calendar.monthrange(int(self.year), int(self.w_month))[1]))])
            total = sum(lines.search([('slip_id','in',pays.ids),('category_id.code','=','NET')]).mapped('total'))

            if emp.bank_account_id.bank_name not in dict_lines.keys():
                dict_lines.update({emp.bank_account_id.bank_name : {emp.name:[emp.address_home_id.street,
                    emp.address_home_id.city, emp.address_home_id.zip, emp.bank_account_id.acc_number,
                    total] }})
            else :
                dict_lines[emp.bank_account_id.bank_name].update({emp.name:[emp.address_home_id.street,
                    emp.address_home_id.city, emp.address_home_id.zip, emp.bank_account_id.acc_number,
                    total]})

        return dict_lines


