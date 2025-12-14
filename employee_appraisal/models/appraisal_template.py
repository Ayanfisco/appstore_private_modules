# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AppraisalTemplate(models.Model):
    _name = 'appraisal.template'
    _description = 'Appraisal Template'

    name = fields.Char(string='Template Name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    competency_ids = fields.Many2many(
        'appraisal.competency',
        string='Competencies'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.constrains('competency_ids')
    def _check_competencies(self):
        for record in self:
            if not record.competency_ids:
                raise ValidationError(
                    _('Template must have at least one competency.')
                )
            total_weightage = sum(record.competency_ids.mapped('weightage'))
            if abs(total_weightage - 100) > 0.01:
                raise ValidationError(
                    _('Total weightage must equal 100%%. Current: %.2f%%')
                    % total_weightage
                )