from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.eloapps_hr_payroll_dz.tools import commun, hr_rule_input, hr_salary_rule, hr_payroll_structure
from odoo.tools.safe_eval import safe_eval
import logging as log

class HrPayrollStructure(models.Model):
    """
    Salary structure used to defined
    - Basic
    - Allowances
    - Deductions
    """
    _name = 'hr.payroll.structure'
    _description = 'Salary Structure'

    @api.model
    def _get_parent(self):
        return self.env.ref('om_om_hr_payroll.structure_base', False)

    name = fields.Char(required=True,string='Nom')
    code = fields.Char(string='Référence', required=True)
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    note = fields.Text(string='Description')
    parent_id = fields.Many2one('hr.payroll.structure', string='Parent', default=_get_parent)
    children_ids = fields.One2many('hr.payroll.structure', 'parent_id', string='Children', copy=True)
    rule_ids = fields.Many2many('hr.salary.rule', 'hr_structure_salary_rule_rel', 'struct_id', 'rule_id', string='Salary Rules')
    default_structure = fields.Boolean('Structure par default')
    active = fields.Boolean('Active',default=True)


    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Vous ne pouvez pas créer une structure de salaire récursive.'))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, code=_("%s (copy)") % (self.code))
        return super(HrPayrollStructure, self).copy(default)

    def get_all_rules(self):
        """
        @return: returns a list of tuple (id, sequence) of rules that are maybe to apply
        """
        all_rules = []
        for struct in self:
            all_rules += struct.rule_ids._recursive_search_of_rules()
        return all_rules

    def _get_parent_structure(self):
        parent = self.mapped('parent_id')
        if parent:
            parent = parent._get_parent_structure()
        return parent + self


    @api.model
    def create_structures(self):
        st = self.env['hr.payroll.structure']
        rl = self.env['hr.salary.rule']
        base = st.create({
                'code': 'BASE',
                'name': 'Structure de base',
                'company_id': self.env.company.id,
                'rule_ids': [(6,0, rl.search([('code','in',['GROSS','NET'])]).ids)]
                })
        base = st.search([('code','=','BASE')])

        vals_hr_payroll_structure = hr_payroll_structure.prepare_vals_hr_payroll_structure(self, base)
        
        for val in vals_hr_payroll_structure :
            if not st.search([('code','=',val['code'])]):
                st.create(val)

class HrSalaryRuleCategory(models.Model):
    _name = 'hr.salary.rule.category'
    _description = 'Salary Rule Category'

    name = fields.Char(required=True, translate=True,  string='Nom')
    code = fields.Char(required=True, string='Référence')
    parent_id = fields.Many2one('hr.salary.rule.category', string='Parent',
        help="Lier une catégorie de salaire à son parent n'est utilisé qu'à des fins de rapport.")
    children_ids = fields.One2many('hr.salary.rule.category', 'parent_id', string='Enfants')
    note = fields.Text(string='Description')
    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company)
    active = fields.Boolean('Active',default=True)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Erreur! Vous ne pouvez pas créer de hiérarchie récursive de catégorie de règle de salaire.'))


    @api.model
    def create_categories(self):
        cat = self.env['hr.salary.rule.category']

        vals_hr_salary_rule_category = {
            'BASIC':'Base',
            'ALW':'Allocation',
            'GROSS':'Brut',
            'DED':'Déductible',
            'NET':'Net',
            'COT':'Cotisable',
            'IMP':'Imposable',
            'IMP10':'Imposable 10%',
            'IMP15':'Imposable 15%',
            'HJ':'Heure par jour',
            'INTERM':'Intermédiaire',
            'COEFF':'Coefficient'}

        for code, name in vals_hr_salary_rule_category.items():
            if code not in cat.search([]).mapped('code'):
                cat.create({
                    'name': name,
                    'code': code,
                    })

        parent = self.env['hr.salary.rule.category'].search([('code','=','ALW')])
        enfants = self.env['hr.salary.rule.category'].search([('code','in',['COT','IMP','IMP10','IMP15'])])
        for enfant in enfants:
            enfant.parent_id = parent.id

class HrSalaryRule(models.Model):
    _name = 'hr.salary.rule'
    _order = 'sequence, id'
    _description = 'Salary Rule'

    name = fields.Char(required=True, translate=True, string='Nom')
    code = fields.Char(required=True,string='Référence',
        help="Le code des règles salariales peut être utilisé comme référence dans le calcul d'autres règles. "
             "Dans ce cas, il est sensible à la casse.")
    sequence = fields.Integer(required=True, string="Séquence", index=True, default=5,
        help='À utiliser pour définir les séquences de calcul')
    quantity = fields.Char(default='1.0',
        help="Il est utilisé dans le calcul du pourcentage et du montant fixe. "
             "Par ex. Une règle pour les chèques-repas ayant un montant fixe de"
             u"1€ par jour ouvré peut avoir sa quantité définie en expression"
             "like worked_days.WORK100.number_of_days.", string='Quantité')
    category_id = fields.Many2one('hr.salary.rule.category', string='Catégorie', required=True)
    active = fields.Boolean(default=True,
        help="Si le champ actif est défini sur false, cela vous permettra de masquer la règle de salaire sans la supprimer.")
    appears_on_payslip = fields.Boolean(string='Apparaît sur le bulletin de paie', default=True,
        help="Utilisé pour montrer la règle de salaire sur la fiche de paie.")
    parent_rule_id = fields.Many2one('hr.salary.rule', string='Règle salariale parente', index=True)
    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company)
    condition_select = fields.Selection([
        ('none', 'Toujours vrai'),
        ('range', 'Plage'),
        ('python', 'Expression Python')
    ], string="Condition basée sur", default='none', required=True)
    condition_range = fields.Char(string='Plage basée sur', default='contract.wage',
        help="Ceci sera utilisé pour calculer les valeurs des champs % ; en général c'est sur basique,"
             'mais vous pouvez également utiliser des champs de code de catégories en minuscules comme noms de variables'
             '(hra, ma, lta, etc.) et la variable basic.'
             )
    condition_python = fields.Text(string='Condition Python', required=True,
        default='''
                    # Available variables:
                    #----------------------
                    # payslip: object containing the payslips
                    # employee: hr.employee object
                    # contract: hr.contract object
                    # rules: object containing the rules code (previously computed)
                    # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
                    # worked_days: object containing the computed worked days
                    # inputs: object containing the computed inputs

                    # Note: returned value have to be set in the variable 'result'

                    result = rules.NET > categories.NET * 0.10''',
        help='Appliquer cette règle pour le calcul si la condition est vraie. Vous pouvez spécifier une condition telle que basic > 1000.')
    condition_range_min = fields.Float(string='Plage minimum', help="Le montant minimum, appliqué pour cette règle.")
    condition_range_max = fields.Float(string='Plage maximum', help="Le montant miximum, appliqué pour cette règle.")
    amount_select = fields.Selection([
        ('percentage', 'Pourcentage (%)'),
        ('fix', 'Montant fixe'),
        ('code', 'Code Python'),
    ], string='Type de montant', index=True, required=True, default='fix', help="La méthode de calcul pour la règle de montant.")
    amount_fix = fields.Float(string='Montant fixe')
    amount_percentage = fields.Float(string='Pourcentage (%)',
        help='Par exemple, saisir 50.0 pour appliquer un pourcentage de 50%')
    amount_python_compute = fields.Text(string='Code Python',
        default='''
                    # Available variables:
                    #----------------------
                    # payslip: object containing the payslips
                    # employee: hr.employee object
                    # contract: hr.contract object
                    # rules: object containing the rules code (previously computed)
                    # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
                    # worked_days: object containing the computed worked days.
                    # inputs: object containing the computed inputs.

                    # Note: returned value have to be set in the variable 'result'

                    result = contract.wage * 0.10''')
    amount_percentage_base = fields.Char(string='Pourcentage basé sur', help='Le résultat sera affecté à une variable')
    child_ids = fields.One2many('hr.salary.rule', 'parent_rule_id', string='Règle de salaire enfant', copy=True)
    input_ids = fields.One2many('hr.rule.input', 'input_id', string='Entrées', copy=True)
    note = fields.Text(string='Description')

    analytic_account_id = fields.Many2one('account.analytic.account', 'Compte analytique')
    account_tax_id = fields.Many2one('account.tax', 'Tax')
    account_debit = fields.Many2one('account.account', 'Compte Débit', domain=[('deprecated', '=', False)])
    account_credit = fields.Many2one('account.account', 'Compte Crédit', domain=[('deprecated', '=', False)])


    @api.constrains('parent_rule_id')
    def _check_parent_rule_id(self):
        if not self._check_recursion(parent='parent_rule_id'):
            raise ValidationError(_('Error! You cannot create recursive hierarchy of Salary Rules.'))

    def _recursive_search_of_rules(self):
        """
        @return: returns a list of tuple (id, sequence) which are all the children of the passed rule_ids
        """
        children_rules = []
        for rule in self.filtered(lambda rule: rule.child_ids):
            children_rules += rule.child_ids._recursive_search_of_rules()
        return [(rule.id, rule.sequence) for rule in self] + children_rules

    #TODO should add some checks on the type of result (should be float)
    def _compute_rule(self, localdict):
        """
        :param localdict: dictionary containing the environement in which to compute the rule
        :return: returns a tuple build as the base/amount computed, the quantity and the rate
        :rtype: (float, float, float)
        """
        self.ensure_one()
        if self.amount_select == 'fix':
            try:
                return self.amount_fix, float(safe_eval(self.quantity, localdict)), 100.0
            except:
                raise UserError(_('Mauvaise quantité définie pour la règle de salaire %s (%s).') % (self.name, self.code))
        elif self.amount_select == 'percentage':
            try:
                return (float(safe_eval(self.amount_percentage_base, localdict)),
                        float(safe_eval(self.quantity, localdict)),
                        self.amount_percentage)
            except:
                raise UserError(_('Mauvaise base de pourcentage ou quantité définie pour la règle de salaire %s (%s).') % (self.name, self.code))
        else:
            try:
                safe_eval(self.amount_python_compute, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), 'result_qty' in localdict and localdict['result_qty'] or 1.0, 'result_rate' in localdict and localdict['result_rate'] or 100.0
            except:
                raise UserError(_('Mauvais code python défini pour la règle de salaire %s (%s).') % (self.name, self.code))

    def _satisfy_condition(self, localdict):
        """
        @param contract_id: id of hr.contract to be tested
        @return: returns True if the given rule match the condition for the given contract. Return False otherwise.
        """
        self.ensure_one()

        if self.condition_select == 'none':
            return True
        elif self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return self.condition_range_min <= result and result <= self.condition_range_max or False
            except:
                raise UserError(_("Mauvaise condition de l'intervalle défini pour la règle de salaire %s (%s).") % (self.name, self.code))
        else:  # python code
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return 'result' in localdict and localdict['result'] or False
            except:
                raise UserError(_('Mauvaise condition python définie pour la règle de salaire %s (%s).') % (self.name, self.code))


    @api.model
    def create_rules(self):
        sr = self.env['hr.salary.rule']
        vals_hr_salary_rules = hr_salary_rule.prepare_vals_hr_salary_rules(self)
        for val in vals_hr_salary_rules:
            if not sr.search(['|',('active','=',True),('active','=',False),('code','=',val['code'])]):
                sr.create(val)

    @api.model
    def check_old_new_rules(self):
        dict_code = {'300':'SS','BASIC':'BASEM','c180':'CP','103':'IEP','387':'PRR','252':'IPAN','253':'ITRS','410':'IRGC','400':'IRG','M380':'FRMS','356':'EXEP','NCIA':'P8M','S375':'PSCL','D381':'FDEP','UNP':'ABSJ','CB':'CONTR','RS251':'R_BASE','REIEP':'R_IEP','RAIEP':'R_IEP','RS254':'R_BASE','PR255':'PRI','PSU':'ISUQ',}
        payslip_lines = self.env['hr.payslip.line'].search([])
        for payslip_line in payslip_lines:
            for code in dict_code.keys():
                if payslip_line.code == code:
                    payslip_line.code = dict_code[payslip_line.code]

        dict_category_code = {'NONCOTIMP':'ALW'}
        payslip_categories = self.env['hr.salary.rule.category'].search([])
        for payslip_category in payslip_categories:
            for code in dict_category_code.keys():
                if payslip_category.code == code:
                    payslip_category.code = dict_category_code[payslip_category.code]

    @api.model
    def check_account_in_salary_rules(self):
        current_chart_package = self.env.company
        
        #get how many 0 to add to the code if we had some codes greater than the default lenght of a code (6)
        #and then concatenate it in the right side of the code
        diffrence = current_chart_package.chart_template_id.code_digits - 6
        if current_chart_package.chart_template_id.code_digits != 0 :
            if diffrence < 0:
                raise ValidationError(_('Erreur! code trop court.'))

            string_diff = ""+"0"*(diffrence)
            
            accounts_assets = list(suit + string_diff  for suit in commun.accounts)

            account_code = self.env['account.account'].search([('code','in',accounts_assets)])
            
            dict_debit = {k+string_diff: v for k, v in commun.code_account_debit_dict.items()}
            dict_credit = {k+string_diff: v for k, v in commun.code_account_credit_dict.items()}
            credit_account = tuple(dict_credit.items())[0][0]

            #Filling the accounting account of each corresponding salary rule.
            for account in account_code:
                if (account.code + string_diff) != (credit_account + string_diff):
                    for ref in self.env['hr.salary.rule'].search([('code','in',dict_debit[(account.code)])]):
                        
                        ref.write({'account_debit': account.id})
                else:
                    for ref in self.env['hr.salary.rule'].search([('code','in',dict_credit[(account.code)])]):
                        ref.write({'account_credit': account.id})

class HrRuleInput(models.Model):
    _name = 'hr.rule.input'
    _description = 'Salary Rule Input'

    name = fields.Char(string='Description', required=True)
    code = fields.Char(required=True, help="Code qui peut être utilisé dans les règles salariales", string="Référence")
    input_id = fields.Many2one('hr.salary.rule', string='Règle salariale en entrée', required=True)

    @api.model
    def create_inputs(self):
        inp = self.env['hr.rule.input']
        rl = self.env['hr.salary.rule']
        vals_hr_rule_input = hr_rule_input.HR_RULE_INPUT
        for val in vals_hr_rule_input:
            inp.create({
                        'code': val[0],
                        'name': val[1],
                        'input_id': rl.search(['|',('active','=',True),('active','=',False),('code','=',val[2])]).id,
                    })
