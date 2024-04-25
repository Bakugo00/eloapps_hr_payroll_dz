def prepare_vals_hr_payroll_structure(instance, base):

    vals_hr_payroll_structure = [
        {
            'code': 'STEPM',
            'name': 'Structure Employée (Mensuel)',
            'default_structure': True,
            'parent_id': base.id,
            'rule_ids': [(6,0,
                instance.env['hr.salary.rule'].search([('code','not in',['BASEJ','BASEH','COEFJ','COEFH','IRGC','R_IRGC','GROSS','NET'])]).ids)]
        },
        {
        'code': 'STEPJ',
        'name': 'Structure Employée (Jour)',
        'parent_id': base.id,
        'rule_ids': [(6,0, 
            instance.env['hr.salary.rule'].search([('code','not in',['BASEM','BASEH','CONTR','ABSJ','R_ABS','IM','R_IM','UCM','R_CM',
                'MM','R_CMM','COEFM','COEFH','IRGC','R_IRGC','GROSS','NET'])]).ids)]
        },
        {
        'code': 'STEPH',
        'name': 'Structure Employée (heure)',
        'parent_id': base.id,
        'rule_ids': [(6,0, 
            instance.env['hr.salary.rule'].search([('code','not in',['BASEM','BASEJ','CONTR','ABSJ','R_ABS','ABSH','R_ABSH','IM','R_IM','UCM','R_CM',
                'MM','R_CMM','COEFM','COEFJ','IRGC','R_IRGC','GROSS','NET'])]).ids)]
        },
        {
        'code': 'STCH',
        'name': 'Structure consultant (heure)',
        'parent_id': base.id,
        'rule_ids': [(6,0, 
            instance.env['hr.salary.rule'].search([('code','in',['BASEH','R_BASE','IRGC','R_IRGC','BASEINT','BCOT','SBI'])]).ids)]
        },
        {
        'code': 'STCJ',
        'name': 'Structure consultant (jour)',
        'parent_id': base.id,
        'rule_ids': [(6,0, 
            instance.env['hr.salary.rule'].search([('code','in',['BASEJ','R_BASE','IRGC','R_IRGC','BASEINT','BCOT','SBI'])]).ids)]
        },
        {
        'code': 'STCHSS',
        'name': 'Structure consultant SS (heure)',
        'parent_id': base.id,
        'rule_ids': [(6,0, 
            instance.env['hr.salary.rule'].search([('code','in',['BASEH','R_BASE','IRGC','R_IRGC','BASEINT','BCOT','SBI',
                                        'BASEINT','IEP','R_IEP','PRR','R_PR','CAIS','R_CAIS','NUIS',
                                        'R_NUIS','APRN','R_APRN','DANG','R_DANG','PRI','R_PRI','ICR',
                                        'R_ICR','CP','R_CP','HS50','R_HS50','HS75','R_HS75','HS100',
                                        'R_HS100','INDC','R_INDC','STC','IFSP','R_IFSP','IFS','R_IFS',
                                        'TRPST10','R_TRPST10','TRPST15','R_TRPST15','R_TRPST25',
                                        'TRPST25','ASTR','R_ASTR','ENSG','R_ENSG','GESRES','R_GESRES',
                                        'ACTR','R_ACTR','DOCU','R_DOCU','INSPC','R_INSPC','BCOT','MC','SBI','SS'])]).ids)]
        },
        {
        'code': 'STCJSS',
        'name': 'Structure consultant SS (jour)',
        'parent_id': base.id,
        'rule_ids': [(6,0, 
                        instance.env['hr.salary.rule'].search([('code','in',['BASEJ','R_BASE','IRGC','R_IRGC','BASEINT','BCOT','SBI',
                                        'BASEINT','IEP','R_IEP','PRR','R_PR','CAIS','R_CAIS','NUIS',
                                        'R_NUIS','APRN','R_APRN','DANG','R_DANG','PRI','R_PRI','ICR',
                                        'R_ICR','CP','R_CP','HS50','R_HS50','HS75','R_HS75','HS100',
                                        'R_HS100','INDC','R_INDC','STC','IFSP','R_IFSP','IFS','R_IFS',
                                        'TRPST10','R_TRPST10','TRPST15','R_TRPST15','R_TRPST25',
                                        'TRPST25','ASTR','R_ASTR','ENSG','R_ENSG','GESRES','R_GESRES',
                                        'ACTR','R_ACTR','DOCU','R_DOCU','INSPC','R_INSPC','BCOT','MC','SBI','SS'])]).ids)]
        }
    ]

    return vals_hr_payroll_structure
    