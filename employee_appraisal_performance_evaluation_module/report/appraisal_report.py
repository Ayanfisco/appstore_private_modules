# -*- coding: utf-8 -*-
from odoo import models


class AppraisalReport(models.AbstractModel):
    _name = 'report.employee_appraisal.appraisal_report_template'
    _description = 'Appraisal Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['employee.appraisal'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'employee.appraisal',
            'docs': docs,
            'data': data,
        }