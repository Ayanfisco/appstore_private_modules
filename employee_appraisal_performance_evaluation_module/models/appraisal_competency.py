# -*- coding: utf-8 -*-
from odoo import models, fields


class AppraisalCompetency(models.Model):
    _name = 'appraisal.competency'
    _description = 'Appraisal Competency'

    name = fields.Char(string='Competency Name', required=True)
    description = fields.Text(string='Description')
    category = fields.Selection([
        ('technical', 'Technical Skills'),
        ('behavioral', 'Behavioral Competencies'),
        ('leadership', 'Leadership'),
        ('communication', 'Communication'),
        ('teamwork', 'Teamwork'),
        ('problem_solving', 'Problem Solving')
    ], string='Category', required=True)
    weightage = fields.Float(string='Default Weightage (%)', default=10.0)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )