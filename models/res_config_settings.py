from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    recrutement_date = fields.Boolean(string="Date de recrutement")

    iep_rate = fields.Boolean(string="Taux IEP")
    
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_om_hr_payroll_account = fields.Boolean(string='Comptabilité de la paie')

    recrutement_date = fields.Boolean(string="Date de recrutement" ,readonly=False)

    iep_rate = fields.Boolean(string="Taux IEP",readonly=False)
    
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        company = self.env.company
        company and res.update(
            recrutement_date= company.recrutement_date,
            iep_rate= company.iep_rate,
        )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        company = self.env.company
        company and company.write({
            'recrutement_date': self.recrutement_date,
            'iep_rate': self.iep_rate,
        })
        return res
