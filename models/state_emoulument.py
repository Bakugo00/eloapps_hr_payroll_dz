from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import Warning
import logging as log


class StateEmoulument(models.Model):
   
    _name = 'state.emoulument'
    _description = "Relevé des émoluments"

    name = fields.Char('Nom', readonly=True, required=True, copy=False, default='New')

    company_id = fields.Many2one('res.company', 'Société' ,default=lambda self: self.env.company)
    company_address = fields.Char('Adresse', compute="_compute_company_info")
    company_phone = fields.Char('Téléphone', compute="_compute_company_info")

    @api.depends('company_id')
    def _compute_company_info(self):
        for record in self:
            record.company_address = record.company_id.street
            record.company_phone = record.company_id.phone

    def domain_employee(self): 
        contract_ids = self.env['hr.contract'].search([('struct_id.code','in' ,['STCH','STCJ'])])
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
            record.employee_phone = record.employee_id.phone
            record.social_security = record.employee_id.sec_social
            record.birthday = record.employee_id.birthday
            record.place_of_birth = record.employee_id.place_of_birth


    date_from = fields.Date('Date de début')
    date_to = fields.Date('Date de fin')
    last_print_date = fields.Datetime('Dernière date de création')

    line_ids = fields.One2many('state.emoulument.line','emolument_id', 'Lignes')
    note = fields.Text("Note")


    def name_get(self):
        """ This method used to customize display name of the record """
        result = []
        for record in self:
            rec_name = "%s" % ("Relevé des émoluments /" + str(record.date_from.strftime('%d/%m/%Y')) + " - " + str(record.date_to.strftime('%d/%m/%Y')))
            result.append((record.id, rec_name))
        return result


    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':

            vals['name'] = 'Relevé des émoluments ' + vals['date_from'].replace('-', '/') + " - " + vals['date_to'].replace('-', '/')

        return super(StateEmoulument,self).create(vals)



    def print_emoulument_report(self):

        self.last_print_date = datetime.now()
        return self.env.ref('eloapps_hr_payroll_dz.hr_statement_emoulument').report_action(self)


    def calcule_lines(self):

        self.line_ids.unlink()



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
        ## iterate through the payslips
        for payslip in payslips.search(domain):
            month = payslip.date_from.month


            # lines_sp = lines.search([('id','in', payslip.line_ids.ids),('category_id.code','in',['BASIC','COT'])])
            # lines_b_impo = lines.search([('id','in', payslip.line_ids.ids),'|',('category_id.code','in',['BASIC','COT','IMP','IMP10','IMP15']),('code','=','SS')])
            lines_sbase = lines.search([('id','in', payslip.line_ids.ids),('category_id.code','=','BASIC')])
            lines_ss = lines.search([('id','in', payslip.line_ids.ids),('code','=','SS')])
            lines_snet = lines.search([('id','in', payslip.line_ids.ids),('category_id.code','=','NET')])
            lines_sbrut = lines.search([('id','in', payslip.line_ids.ids),('category_id.code','=','GROSS')])

            lines_divers = lines.search([('id','in', payslip.line_ids.ids),('category_id.code','in',['COT','IMP','IMP10','IMP15','ALW'])])
            
            rubs = [
                    # ['SP',lines_sp],
                    # ['B Impo.', lines_b_impo],
                    ['Salaire de base', lines_sbase],
                    ['Sécurité Sociale', lines_ss],
                    ['divers', lines_divers],
                    ['Salaire Brut', lines_sbrut],
                    ['Salaire Net', lines_snet]]

  
            for r in rubs:
                if r[0] == 'divers':
                    for l in lines_divers:
                        if l.code in dict_lines:
                            if months[month] in dict_lines[l.code ]:
                                dict_lines[l.code ][months[month]] += l.total
                            else: 
                                dict_lines[l.code ].update({months[month]: l.total})
                        else :
                            dict_lines.update({l.code : {'rub': l.name,  months[month]: l.total} })
                    continue

           
                if r[0] in dict_lines:
                    if months[month] in dict_lines[r[0]]:
                        dict_lines[r[0]][months[month]] += sum(r[1].mapped('total'))
                    else: 
                        dict_lines[r[0]].update({months[month]: sum(r[1].mapped('total'))})
                else :
                  
                    dict_lines.update({r[0]: {'rub': r[0], months[month]: sum(r[1].mapped('total'))} })

            
        log.warning('dict_lines')
        log.warning(dict_lines)
        for d in dict_lines:
            self.line_ids += self.env['state.emoulument.line'].create(dict_lines[d])



class StateEmoulumentLine(models.Model):
   
    _name = 'state.emoulument.line'
    _description = "Lignes de relevé des émoluments"

    rub = fields.Char('Rub')
    january = fields.Float('Janvier')
    february = fields.Float('Février')
    mars = fields.Float('Mars')
    april = fields.Float('Avril')
    may = fields.Float('Mai')
    june = fields.Float('Juin')
    july = fields.Float('Juillet')
    august = fields.Float('Aôut')
    september = fields.Float('Septembre')
    october = fields.Float('Octobre')
    november = fields.Float('Novembre')
    december = fields.Float('Décembre')

    emolument_id = fields.Many2one('state.emoulument')
