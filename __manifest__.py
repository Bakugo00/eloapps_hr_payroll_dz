# -*- coding: utf-8 -*-
{
    'name': "Paie - Algérie",
    'summary': """ Intégration de la paie en fonction des réglementations algérienne """,

    'version'       : "16.0.1.0",
    'category'      : "Human Resources/Employees",

    "contributors": [
        
        
    ],
    
    'sequence': 1,
    
    'company'       : 'Elosys',
    'author'        : 'Elosys',
    'maintainer'    : 'Elosys',

    'website': "https://www.elosys.net/",
    'support' : "support@elosys.net",
    'live_test_url' : "https://www.elosys.net/shop/employes-algerie-50?category=13#attr=102",


    'depends': [
        'base',
        'eloapps_hr_dz',
        'hr_contract',
        'hr_holidays',
    ],
    
    'data': [
        'security/hr_payroll_security.xml',
        'security/ir.model.access.csv',
        'security/security.xml',

        'data/hr_payroll_sequence.xml',
        'data/hr_payroll_leave_type.xml',
        'data/cron_functions.xml',
        'data/data_create_function.xml',

        'wizards/hr_payroll_payslips_by_employees_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
        'reports/report_payslip_templates.xml',

        'reports/report_emoulument.xml',
        'reports/report_virement_bancaire.xml',

        'views/hr_leave.xml',
        'views/hr_leave_type.xml',
        'views/refund_tree_form.xml',
        'views/hr_annual_leave.xml',
        'views/hr_annual_leave_line.xml',
        'views/menu_item.xml',

        'reports/employee_payslip_reports.xml',
        'reports/report_fiche_paie_individuel.xml',
        'reports/report_custom.xml',
        
        'reports/actions_reports_payroll.xml',
        'wizards/wizard_hr_virbanc.xml',
        'wizards/wizard_hr_emoulument.xml',
    ],



    'license'       : "LGPL-3",
    'price'         : "260",
    'currency'      : 'Eur',

    'images'        : [
        'images/banner.gif'
        ],

    'installable': True,
    'auto_install': False,
    'application': True,
}
