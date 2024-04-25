import babel
from  calendar import monthrange
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from pytz import timezone

from math import *

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.exceptions import Warning

from odoo.tools import float_compare, float_is_zero

base_number = 0

class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _description = 'Pay Slip'
    _order = 'id desc'

    @api.depends("employee_id","leave_type_id")
    def compute_annual_leave(self):
        for rec in self:
            rec.write({'annual_leave_ids': [(5,0,0)]})
            # for line in rec.annual_leave_ids:
            #     line.unlink()
            annuals = self.env["hr.annual.leave"].search([('employee_id','=',rec.employee_id.id),('leave_type_id','in',rec.leave_type_id.ids)],order='date_start asc')
            for annual in annuals:
                if annual.allocated_days_number > annual.used_number_days:
                    rec.annual_leave_ids += annual

    @api.depends("leave_line_ids")
    def compute_amount(self):
        for rec in self:
            sum = 0
            for line in rec.leave_line_ids:
                sum += line.amount
            rec.leave_used_amount = sum
    
            

    total_holiday_pay = fields.Float(string = "Total des indemnités de congé")    
    
    leave_type_id = fields.Many2many('hr.leave.type' ,string='Type de congé')
    annual_leave_ids = fields.Many2many('hr.annual.leave' ,string='Congé annuel',store=True,compute=compute_annual_leave)
    leave_line_ids = fields.One2many('hr.annual.leave.line','payslip_id')
    leave_used_amount = fields.Monetary('Montant du congé','currency_id',compute=compute_amount, store=True)
    currency_id = fields.Many2one('res.currency',default=lambda self: self.env.user.company_id.currency_id)

    def compute_conge(self):
        for rec in self :
            if not rec.contract_id:
                raise UserError(_('Vous ne pouvez pas attribuer les congés pour un employé sans contract'))
                
            for line in rec.leave_line_ids:
                line.unlink()
            if not rec.worked_days_line_ids:
                return
            if not rec.leave_type_id:
                return
            if not rec.annual_leave_ids:
                return

            amount_total = 0.0
            if rec.all_accounts_balance  == True :
                holiday = self.env["hr.annual.leave"].search([('employee_id','=',rec.employee_id.id),('diff_amount','!=',0)])
                for holidays in holiday:
                    amount_total += holidays.leave_amount - holidays.received_amount
            rec.total_holiday_pay = amount_total

            #nombre de CP 
            leave_number_of_days = 0
            


            diff = 0
            prep_annual_leave_line = []
            annual_leaves = rec.annual_leave_ids


            #boucler sur les lignes de résumé de congé
            for annual_leave in annual_leaves:

                if rec.holi_number_day_cp >= diff:

                    leave_number_of_days = rec.holi_number_day_cp - diff

                    if annual_leave.allocated_days_number == annual_leave.used_number_days:
                        continue
                    if annual_leave.allocated_days_number > annual_leave.used_number_days: 

                        diff = annual_leave.allocated_days_number - annual_leave.used_number_days
                        if diff > leave_number_of_days:

                            prep_annual_leave_line.append({
                                'payslip_id': rec.id,
                                'employee_id': rec.employee_id.id,
                                'annual_leave_id': annual_leave.id,
                                'number_of_days': leave_number_of_days
                                })
                            continue

                        prep_annual_leave_line.append({
                            'payslip_id': rec.id,
                            'employee_id': rec.employee_id.id,
                            'annual_leave_id': annual_leave.id,
                            'number_of_days': diff
                            })


            rec.leave_line_ids.browse([]).create(prep_annual_leave_line)
        return 

    struct_id = fields.Many2one('hr.payroll.structure', string='Structure salariale',
        readonly=True, states={'draft': [('readonly', False)]})
    name = fields.Char(string='Nom', readonly=True, states={'draft': [('readonly', False)]})
    number = fields.Char(string='Référence', readonly=True, copy=False, states={'draft': [('readonly', False)]})
    employee_id = fields.Many2one('hr.employee', string='Employé', required=True, readonly=True, states={'draft': [('readonly', False)]})
    date_from = fields.Date(string='Date Début', readonly=True, required=True, default=lambda self: fields.Date.to_string(date.today().replace(day=1)), states={'draft': [('readonly', False)]})
    date_to = fields.Date(string='Date Fin', readonly=True, required=True, default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()),
        states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Broullion'),
        ('verify', 'En attente'),
        ('done', 'Fait'),
        ('cancel', 'Rejeté'),
    ], string='Statut', index=True, readonly=True, copy=False, default='draft')
    line_ids = fields.One2many('hr.payslip.line', 'slip_id', string='Lignes du bulletin', readonly=True,
        states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Société', readonly=True, copy=False,
                                 default=lambda self: self.env.company,
                                 states={'draft': [('readonly', False)]})
    worked_days_line_ids = fields.One2many('hr.payslip.worked_days', 'payslip_id',
        string='Bulletin de paie jours travaillés', copy=True, readonly=True,
        states={'draft': [('readonly', False)]})
    input_line_ids = fields.One2many('hr.payslip.input', 'payslip_id', string='Entrées du bulletin de salaire',
        readonly=True, copy=True, states={'draft': [('readonly', False)]})
    paid = fields.Boolean(string="Établir l'ordre de paiement  ?", readonly=True, copy=False,
        states={'draft': [('readonly', False)]})
    note = fields.Text(string='Note interne', readonly=True, states={'draft': [('readonly', False)]})
    contract_id = fields.Many2one('hr.contract', string='Contrat', readonly=True,
        states={'draft': [('readonly', False)]})
    credit_note = fields.Boolean(string='Avoir', readonly=True,
        states={'draft': [('readonly', False)]},
        help="Indique que ce bulletin de paie est le remboursement d'un autre")
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Lots de bulletins de paie', readonly=True,
        copy=False, states={'draft': [('readonly', False)]})
    payslip_count = fields.Integer(compute='_compute_payslip_count', string="Détails pour le calcul du bulletin")
    
    date = fields.Date('Date de référence comptable', states={'draft': [('readonly', False)]}, readonly=True)
    journal_id = fields.Many2one('account.journal', 'Journal salarial', readonly=True, required=True,
        states={'draft': [('readonly', False)]}, default=lambda self: self.env['account.journal'].search([('type', '=', 'general')], limit=1))
    move_id = fields.Many2one('account.move', 'Écriture comptable', readonly=True, copy=False)

    payslip_ref = fields.Many2one('hr.payslip', string="bulletin de reference",)

    refund_payslip = fields.One2many('hr.payslip', 'payslip_ref', string="bulletins remboursé",)

    base_vals = fields.Float(string="basenumber",)

    # Fonction pour savoir si le contrat de l'empoyée est de type consultat
    etat = fields.Boolean(compute='default_etat')

    all_accounts_balance = fields.Boolean(string="Solde de tout comptes" ,default=False)

    balance_date = fields.Date(string="Date du solde" ,default=datetime.today())

    holi_number_day_cp = fields.Float(string="Nombre de jour de congé")


    def default_etat(self):
        contract_type = self.contract_id.job_id.name
        if contract_type == 'Consultant':
            self.etat = True
        else:
            self.etat = False

    def _compute_payslip_count(self):
        for payslip in self:
            payslip.payslip_count = len(payslip.line_ids)

    # Contrainte pour vérifier les dates de bulletins 
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(self.filtered(lambda payslip: payslip.date_from > payslip.date_to)):
            raise ValidationError(_("La « Date de début» de la fiche de paie doit être inférieur à la « Date de fin»."))

    # Action pour modifier l'état en broullion
    def action_payslip_draft(self):
        self.move_id.button_draft()
        return self.write({'state': 'draft'})

    # Action pour modifier l'état en fait
    def action_payslip_done(self):
        total = 0
        conge = self.env['hr.annual.leave'].search([('date_start','=',self.date_from),
                                                    ('date_end','=',self.date_to),
                                                    ('employee_id','=',self.employee_id.id)])

        if conge:
            line = self.env['hr.payslip.line'].search([('id','in',self.line_ids.ids),('code','=', 'MC')])
            conge.leave_amount = self.env['hr.payslip.line'].search([('id','in',self.line_ids.ids),('code','=', 'MC')]).total

        for slip in self:
            line_ids = []
            date = slip.date or slip.date_to
            currency = slip.company_id.currency_id

            name = _('Bulletin de %s') % (slip.employee_id.name)
            move_dict = {
                'narration': name,
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'date': date,
            }
            if not slip.line_ids:
                raise UserError(_('Veuillez lancer le calcule du bulletin de paie pour pouvoir le confirmer'))
      
            if not any(line.salary_rule_id.account_debit or line.salary_rule_id.account_credit for line in slip.line_ids):
                raise UserError(_('Compte de débit ou de crédit manquant dans la règle de salaire'))
            for line in slip.line_ids:
                amount = currency.round(slip.credit_note and -line.total or line.total)
                
                if currency.is_zero(amount):
                    continue
                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id
                if line.code != "NET":
                    
                    if debit_account_id:
                        debit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': line._get_partner_id(credit_account=False),
                            'account_id': debit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': amount > 0.0 and amount or 0.0,
                            'credit': amount < 0.0 and -amount or 0.0,
                            'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        total = (total + amount) 

                    if credit_account_id:
                        credit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': line._get_partner_id(credit_account=True),
                            'account_id': credit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': amount < 0.0 and -amount or 0.0,
                            'credit': amount > 0.0 and amount or 0.0,
                            'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        total = total - amount

                if line.code == "NET":
                    if debit_account_id:
                        total = total + amount
                        debit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': line._get_partner_id(credit_account=False),
                            'account_id': debit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': amount > 0.0 and (amount + total)or 0.0,
                            'credit': amount < 0.0 and (-amount + total)or 0.0,
                            'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        
                    if credit_account_id:
                        total = total - amount
                        credit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': line._get_partner_id(credit_account=True),
                            'account_id': credit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': amount < 0.0 and (-amount + total) or 0.0,
                            'credit': amount > 0.0 and (amount + total) or 0.0,
                            'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                    line.total = (line.total - total) if total < 0.0 else (line.total + total)

            move_dict['line_ids'] = line_ids
            if slip.move_id :
                slip.move_id.line_ids.unlink()
             
                slip.move_id.update({'line_ids': line_ids}) 

                slip.write({'date': date})
                slip.move_id.post()
            else :
                move = self.env['account.move'].create(move_dict)
                slip.write({'move_id': move.id, 'date': date})
                move.post()
            
        return self.write({'state': 'done'})


    # Action pour modifier l'état en annulé
    def action_payslip_cancel(self):
        moves = self.mapped('move_id')
        moves.filtered(lambda x: x.state == 'posted').button_cancel()
        # if self.filtered(lambda slip: slip.state == 'done'):
        #     raise UserError(_("Impossible d'annuler un bulletin de paie terminé."))
        return self.write({'state': 'cancel'})

    # Action de remboursement d'un bulletin
    def refund_sheet(self):
        for record in self:
            if not record.refund_payslip:
                for payslip in self:
                    copied_payslip = payslip.copy({'credit_note': True, 'name': _('Remboursement: ') + payslip.name, 'payslip_ref': payslip.id})
                    number = copied_payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
                    copied_payslip.write({'number': number})
                    copied_payslip.with_context(without_compute_sheet=True).action_payslip_done()
                formview_ref = self.env.ref('eloapps_hr_payroll_dz.view_hr_payslip_form', False)
                treeview_ref = self.env.ref('eloapps_hr_payroll_dz.view_hr_payslip_tree', False)
                return {
                    'name': ("Refund Payslip"),
                    'view_mode': 'tree, form',
                    'view_id': False,
                    'view_type': 'form',
                    'res_model': 'hr.payslip',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
                    'views': [(treeview_ref and treeview_ref.id or False, 'tree'), (formview_ref and formview_ref.id or False, 'form')],
                    'context': {}
                }
            else:
                raise Warning(_('Ce bulletin a déjà été remboursé.'))
                return True

    # Fonction de suppression
    def unlink(self):
        if any(self.filtered(lambda payslip: payslip.state not in ('draft', 'cancel'))):
            raise UserError(_('Vous ne pouvez supprimer une fiche de paie qui ne soit ni brouillon ni annulée!'))
        self.leave_line_ids.unlink()
        return super(HrPayslip, self).unlink()

    # Fonction pour récupérer les contrats valides
    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee : ensemble d'enregistrements de l'employé
        @param date_from : champ de date
        @param date_to : champ de date
        @return : renvoie les identifiants de tous les contrats pour l'employé donné qui doivent être pris en compte pour les dates données
        """
        # Un contrat est valable s'il se termine entre les dates indiquées
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # Ou s'il commence entre les dates données
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # Ou s'il commence avant le date_from et se termine après le date_end (ou ne finit jamais)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), ('state', '=', 'open'), '|', '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final).ids
    
    # Fontion de  calcule des jours travaillés
    def compute_work(self):
        for record in self:
            if not record.contract_id:
                raise UserError(_('Vous ne pouvez pas calculer le temps de travail sans contract'))
            record.holi_number_day_cp = 0.0
            if record.worked_days_line_ids:
                leave_days, leave_hours = (0,) * 2
                wdli = record.worked_days_line_ids
                base_mois = record.contract_id.base_mois

                for line in wdli:
                    if line.code not in  ["WORK100","ABSA","JC"]:
                        leave_days += line.number_of_days
                        leave_hours += line.number_of_hours
                    if line.code == 'CP':
                        record.holi_number_day_cp = line.number_of_days

                if leave_days > base_mois or leave_hours > 173.33:
                    raise Warning(('Veuillez vérifier le nombre de jours des Congés / Absences'))
                else:
                    for l in wdli.filtered(lambda r: r.code == 'WORK100'):
                        l.number_of_days = base_mois - leave_days
                        l.number_of_hours = 173.33 - leave_hours
                        break

    # Fonction de calcule de bulletin de paie
    def compute_sheet(self):
        # for record in self:
        #     record.compute_work()

        for payslip in self:
            if payslip.struct_id:
                number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
                # delete old payslip lines
                payslip.line_ids.unlink()
                # set the list of contract for which the rules have to be applied
                # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
                contract_ids = payslip.contract_id.ids or \
                    self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
                lines = [(0, 0, line) for line in self._get_payslip_lines(contract_ids, payslip.id)]
                payslip.write({'line_ids': lines, 'number': number})

        return True

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)

            # compute leave days
            leaves = {}
            calendar_om = contract.resource_calendar_id
            tz = timezone(calendar_om.tz)
            day_leave_intervals = contract.employee_id.list_leaves(day_from, day_to, calendar=contract.resource_calendar_id)

            for day, hours, leave in day_leave_intervals:
                holiday = leave.holiday_id
                
                current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
                    'name': holiday.holiday_status_id.name or _('Global Leaves'),
                    'sequence': 5,
                    'code': holiday.holiday_status_id.code or 'GLOBAL',
                    'number_of_days': 0.0,
                    'number_of_hours': 0.0,
                    'contract_id': contract.id,
                })
                
                work_hours = calendar_om.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if work_hours:
                    if holiday.holiday_status_id.request_unit == "hour":
                        current_leave_struct['number_of_hours'] += hours
                        current_leave_struct['number_of_days'] += hours / (173.33 / contract.base_mois)

                    if holiday.holiday_status_id.request_unit != "hour":    
                        current_leave_struct['number_of_hours'] += (hours / work_hours) * (173.33 / contract.base_mois)
                        current_leave_struct['number_of_days'] += hours / work_hours
            
            leave_number_of_hours = 0
            leave_number_of_days = 0
            for value in leaves.values():
                if value['code'] in ['ABSA','JC']:
                    continue
                leave_number_of_hours += value['number_of_hours']
                leave_number_of_days += value['number_of_days']
            work_number_of_days = self.employee_id.contract_id.base_mois - leave_number_of_days
            work_number_of_hours = 173.33 - leave_number_of_hours

            # compute worked days
            attendances = {
                'name': _("Jours de travail payés"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_number_of_days,
                'number_of_hours': work_number_of_hours,
                'contract_id': contract.id,
            }
            res.append(attendances)
            res.extend(leaves.values())
        return res

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        res = []

        structure_ids = contracts.get_all_structures()
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids).mapped('input_ids')

        for contract in contracts:
            for input in inputs:
                input_data = {
                    'name': input.name,
                    'code': input.code,
                    'contract_id': contract.id,
                }
                res += [input_data]
        return res

    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id):
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = category.code in localdict['categories'].dict and localdict['categories'].dict[category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, dict, env):
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                            FROM hr_payslip as hp, hr_payslip_line as pl
                            WHERE hp.employee_id = %s AND hp.state = 'done'
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                            (self.employee_id, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        #we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)

        baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days, 'inputs': inputs}
        #get the ids of the structures on the contracts and their parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(set(payslip.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()
        #get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        #run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)

        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee, contract=contract)
            for rule in sorted_rules:
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                #check if the rule can be applied
                if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                    #compute the amount of the rule
                    amount, qty, rate = rule._compute_rule(localdict)
                    #check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    #set/overwrite the amount computed for this rule in the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    #sum the amount for its salary category
                    localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                    #create/overwrite the rule in the temporary results
                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                        'account_debit': rule.account_debit.id,
                        'account_credit': rule.account_credit.id,
                    }
                else:
                    #blacklist this rule and its children
                    blacklist += [id for id, seq in rule._recursive_search_of_rules()]

        return list(result_dict.values())

    def _onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
        empolyee_obj = self.env['hr.employee']
        contract_obj = self.env['hr.contract']
        worked_days_obj = self.env['hr.payslip.worked_days']
        input_obj = self.env['hr.payslip.input']

        #delete old worked days lines
        worked_days_ids_to_remove=[]
        old_worked_days_ids = self.ids and worked_days_obj.search([('payslip_id', '=', self.ids[0])]) or False
        if old_worked_days_ids:
            worked_days_ids_to_remove = map(lambda x: (2, x,),old_worked_days_ids)

        #delete old input lines
        input_line_ids_to_remove=[]
        old_input_ids = self.ids and input_obj.search([('payslip_id', '=', self.ids[0])]) or False
        if old_input_ids:
            input_line_ids_to_remove = map(lambda x: (2,x,), old_input_ids)


        #defaults
        res = {'value':{
                      'line_ids':[],
                      'input_line_ids': input_line_ids_to_remove,
                      'worked_days_line_ids': worked_days_ids_to_remove,
                      #'details_by_salary_head':[], TODO put me back
                      'name':'',
                      'contract_id': False,
                      'struct_id': False,
                      }
            }

        if (not employee_id) or (not date_from) or (not date_to):
            return res

        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        employee_id = empolyee_obj.browse(employee_id)
        locale = self.env.context.get('lang') or 'fr_FR'
        res['value'].update({
            'name': _('Bulletin de paie de %s pour %s') % (employee_id.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale))),
            'company_id': employee_id.company_id.id,
        })

        if not self.env.context.get('contract'):
            #fill with the first contract of the employee
            contract_ids = self.get_contract(employee_id, date_from, date_to)
        else:
            if contract_id:
                #set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                #if we don't give the contract, then the input to fill should be for all current contracts of the employee
                contract_ids = self.get_contract(employee_id, date_from, date_to)
                
        if not contract_ids:
            return res
        contract_record = contract_obj.browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract_record and contract_record.id or False
        })

        struct_record = contract_record and contract_record.struct_id or False
        if not struct_record:
            return res
        res['value'].update({
            'struct_id': struct_record.id,
        })

        #computation of the salary input
        contracts = contract_obj.browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })

        months_fr = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet',
                     'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        mois = months_fr[date_from.month - 1]
        if employee_id:
            res['value']['name'] = ('Bulletin de paye de {employee} '
                                'pour {mois} {annee}'
                                '').format(employee=(employee_id.name),
                                           mois=mois,
                                           annee=date_from.year)
        if employee_id and contract_id:
            contract = contract_obj.browse(contract_id)
            if contract.date_end < date_to and contract.date_end:
                res['value'].update({'date_to': contract.date_end})
            if contract.date_start > date_from and contract.date_start:
                res['value'].update({'date_from': contract.date_start})

        if self.contract_id and self.contract_id.date_end:
            if self.date_to > self.contract_id.date_end:
                self.date_to = self.contract_id.date_end

        return res

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        self.ensure_one()
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []

        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        locale = self.env.context.get('lang') or 'en_US'
        self.name = _('Bulletin de paie  %s pour %s') % (employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))
        self.company_id = employee.company_id

        if not self.env.context.get('contract') or not self.contract_id:
            contract_ids = self.get_contract(employee, date_from, date_to)
            if not contract_ids:
                return
            self.contract_id = self.env['hr.contract'].browse(contract_ids[0])

        if not self.contract_id.struct_id:
            return
        self.struct_id = self.contract_id.struct_id

        #computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        if contracts:
            worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
            worked_days_lines = self.worked_days_line_ids.browse([])
            for r in worked_days_line_ids:
                worked_days_lines += worked_days_lines.new(r)
            self.worked_days_line_ids = worked_days_lines

            input_line_ids = self.get_inputs(contracts, date_from, date_to)
            input_lines = self.input_line_ids.browse([])
            for r in input_line_ids:
                input_lines += input_lines.new(r)
            self.input_line_ids = input_lines
            return

    @api.onchange('contract_id')
    def onchange_contract(self):
        if not self.contract_id:
            self.struct_id = False
        self.with_context(contract=True).onchange_employee()
        self.journal_id = self.contract_id.journal_id.id or (not self.contract_id and self.default_get(['journal_id'])['journal_id'])
        return

    def get_salary_line_total(self, code):
        self.ensure_one()
        line = self.line_ids.filtered(lambda line: line.code == code)
        if line:
            return line[0].total
        else:
            return 0.0

    @api.model
    def create(self, vals):
        if 'journal_id' in self.env.context:
            vals['journal_id'] = self.env.context.get('journal_id')
        return super(HrPayslip, self).create(vals)


class HrPayslipLine(models.Model):
    _name = 'hr.payslip.line'
    _inherit = 'hr.salary.rule'
    _description = 'Payslip Line'
    _order = 'contract_id, sequence'

    slip_id = fields.Many2one('hr.payslip', string='Feuille de paie', required=True, ondelete='cascade')
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Règle', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employé', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contrat', required=True, index=True)
    rate = fields.Float(string='Taux (%)', default=100.0)
    amount = fields.Float(string='Montant')
    quantity = fields.Float(default=1.0, string='Quantité')
    total = fields.Float(compute='_compute_total', string='Total')

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        for line in self:
            line.total = float(line.quantity) * line.amount * line.rate / 100

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'employee_id' not in values or 'contract_id' not in values:
                payslip = self.env['hr.payslip'].browse(values.get('slip_id'))
                values['employee_id'] = values.get('employee_id') or payslip.employee_id.id
                values['contract_id'] = values.get('contract_id') or payslip.contract_id and payslip.contract_id.id
                if not values['contract_id']:
                    raise UserError(_('Vous devez définir un contrat pour créer une ligne de bulletin de paie.'))
        return super(HrPayslipLine, self).create(vals_list)


    def _get_partner_id(self, credit_account):
        """
        Get partner_id of slip line to use in account_move_line
        """
        # use partner of salary rule or fallback on employee's address
        partner_id = self.slip_id.employee_id.address_home_id.id
        if credit_account:
            if self.salary_rule_id.account_credit.account_type in ('asset_receivable','asset_payable'):
                return partner_id
        else:
            if self.salary_rule_id.account_debit.account_type in ('asset_receivable','asset_payable'):
                return partner_id
        return False

class HrPayslipWorkedDays(models.Model):
    _name = 'hr.payslip.worked_days'
    _description = 'Payslip Worked Days'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Description', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Feuille de paie', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, string="Séquence", index=True, default=10)
    code = fields.Char(required=True, help="Code qui peut être utilisé dans les règles salariales")
    number_of_days = fields.Float(string='Nombre de jours')
    number_of_hours = fields.Float(string="Nombre d'heures")
    contract_id = fields.Many2one('hr.contract', string='Contrat', 
        help="Le contrat auquel s'applique cette entrée")
        
    @api.onchange('number_of_hours')
    def onchange_number_of_days(self):
        self.number_of_days = (self.number_of_hours * self.contract_id.base_mois / 173.33) if self.contract_id else self.number_of_days

    @api.onchange('number_of_days')
    def onchange_number_of_hours(self):
        self.number_of_hours = (self.number_of_days * 173.33 / self.contract_id.base_mois) if self.contract_id else self.number_of_hours

class HrPayslipInput(models.Model):
    _name = 'hr.payslip.input'
    _description = 'Payslip Input'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Description', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Feuille de paie', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, string="Séquence", index=True, default=10)
    code = fields.Char(required=True, help="Code qui peut être utilisé dans les règles salariales")
    amount = fields.Float(help="It is used in computation. For e.g. A rule for sales having "
                               "1% commission of basic salary for per product can defined in expression "
                               "like result = inputs.SALEURO.amount * contract.wage*0.01.", string="Montant")
    contract_id = fields.Many2one('hr.contract', string='Contrat', required=True,
        help="The contract for which applied this input")


class HrPayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _description = 'Payslip Batches'

    name = fields.Char(required=True, readonly=True, states={'draft': [('readonly', False)]}, string="Nom")
    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Feuilles de paie', readonly=True,
                               states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Broullion'),
        ('done', 'Fait'),
        ('close', 'Fermer'),
    ], string='Statut', index=True, readonly=True, copy=False, default='draft')
    date_start = fields.Date(string='Date Début', required=True, readonly=True,
                             states={'draft': [('readonly', False)]}, default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_end = fields.Date(string='Date Fin', required=True, readonly=True,
                           states={'draft': [('readonly', False)]},
                           default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    credit_note = fields.Boolean(string='Avoir', readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 help="If its checked, indicates that all payslips generated from here are refund payslips.")

    journal_id = fields.Many2one('account.journal', 'Journal salarial', states={'draft': [('readonly', False)]}, readonly=True,
        required=True, default=lambda self: self.env['account.journal'].search([('type', '=', 'general')], limit=1))
        
    def draft_payslip_run(self):
        return self.write({'state': 'draft'})

    def close_payslip_run(self):
        return self.write({'state': 'close'})

    def done_payslip_run(self):
        for line in self.slip_ids:
            line.action_payslip_done()
        return self.write({'state': 'done'})

    def unlink(self):
        for rec in self:
            if rec.state == 'done':
                raise ValidationError(_('Vous ne pouvez pas supprimer les lots de fiches de paie terminés'))
        return super(HrPayslipRun, self).unlink()
