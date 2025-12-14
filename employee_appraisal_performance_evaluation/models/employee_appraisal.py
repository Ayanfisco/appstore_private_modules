# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EmployeeAppraisal(models.Model):
    _name = 'employee.appraisal'
    _description = 'Employee Appraisal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Job Position',
        related='employee_id.job_id',
        store=True
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string='Manager',
        related='employee_id.parent_id',
        store=True
    )
    template_id = fields.Many2one(
        'appraisal.template',
        string='Appraisal Template'
    )
    date_start = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    date_end = fields.Date(
        string='End Date',
        required=True,
        tracking=True
    )
    date_final = fields.Date(
        string='Final Review Date',
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('self', 'Self Assessment'),
        ('manager', 'Manager Review'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    competency_ids = fields.One2many(
        'appraisal.competency.line',
        'appraisal_id',
        string='Competencies'
    )
    goal_ids = fields.One2many(
        'appraisal.goal.line',
        'appraisal_id',
        string='Goals'
    )

    # Rating fields (0-5 scale)
    self_rating = fields.Float(
        string='Self Rating',
        compute='_compute_ratings',
        store=True,
        help="Average self rating across all competencies (0-5 scale)"
    )
    manager_rating = fields.Float(
        string='Manager Rating',
        compute='_compute_ratings',
        store=True,
        help="Average manager rating across all competencies (0-5 scale)"
    )
    final_rating = fields.Float(
        string='Final Rating',
        compute='_compute_ratings',
        store=True,
        help="Average of self and manager ratings (0-5 scale)"
    )

    # Percentage fields for progress bars (0-100 scale)
    self_rating_percent = fields.Float(
        string='Self Rating %',
        compute='_compute_rating_percent',
        store=True
    )
    manager_rating_percent = fields.Float(
        string='Manager Rating %',
        compute='_compute_rating_percent',
        store=True
    )
    final_rating_percent = fields.Float(
        string='Final Rating %',
        compute='_compute_rating_percent',
        store=True
    )

    weighted_final_rating = fields.Float(
        string='Weighted Final Rating',
        compute='_compute_weighted_rating',
        store=True,
        help="Final rating considering competency weightages (0-5 scale)"
    )

    self_comments = fields.Html(string='Self Assessment Comments')
    manager_comments = fields.Html(string='Manager Comments')
    strength = fields.Text(string='Strengths')
    weakness = fields.Text(string='Areas for Improvement')
    recommendation = fields.Selection([
        ('promotion', 'Promotion'),
        ('salary_increase', 'Salary Increase'),
        ('training', 'Training Required'),
        ('maintain', 'Maintain Current Position'),
        ('pip', 'Performance Improvement Plan'),
        ('termination', 'Termination')
    ], string='Recommendation', tracking=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'employee.appraisal') or _('New')
        return super().create(vals)

    @api.depends('competency_ids.self_rating',
                 'competency_ids.manager_rating')
    def _compute_ratings(self):
        """Compute simple average ratings (not weighted) on 0-5 scale"""
        for record in self:
            if record.competency_ids:
                total_self = sum(
                    line.self_rating for line in record.competency_ids
                )
                total_manager = sum(
                    line.manager_rating for line in record.competency_ids
                )
                count = len(record.competency_ids)

                record.self_rating = total_self / count if count else 0.0
                record.manager_rating = total_manager / count if count else 0.0
                record.final_rating = (
                                              record.self_rating + record.manager_rating
                                      ) / 2 if count else 0.0
            else:
                record.self_rating = 0.0
                record.manager_rating = 0.0
                record.final_rating = 0.0

    @api.depends('self_rating', 'manager_rating', 'final_rating')
    def _compute_rating_percent(self):
        """Convert 0-5 ratings to 0-100 percentages for progress bars"""
        for record in self:
            record.self_rating_percent = (record.self_rating / 5.0) * 100 if record.self_rating else 0.0
            record.manager_rating_percent = (record.manager_rating / 5.0) * 100 if record.manager_rating else 0.0
            record.final_rating_percent = (record.final_rating / 5.0) * 100 if record.final_rating else 0.0

    @api.depends('competency_ids.self_rating',
                 'competency_ids.manager_rating',
                 'competency_ids.weightage')
    def _compute_weighted_rating(self):
        """Compute weighted rating considering competency importance"""
        for record in self:
            if record.competency_ids:
                weighted_score = 0.0

                for line in record.competency_ids:
                    if line.self_rating and line.manager_rating:
                        avg_rating = (line.self_rating + line.manager_rating) / 2
                        weighted_score += avg_rating * (line.weightage / 100)

                record.weighted_final_rating = weighted_score
            else:
                record.weighted_final_rating = 0.0

    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Auto-populate competencies from template"""
        if self.template_id:
            competency_lines = []
            for comp in self.template_id.competency_ids:
                competency_lines.append((0, 0, {
                    'competency_id': comp.id,
                    'weightage': comp.weightage,
                }))
            self.competency_ids = competency_lines

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_end <= record.date_start:
                raise ValidationError(
                    _('End date must be after start date.')
                )

    @api.constrains('competency_ids')
    def _check_competency_weightage(self):
        """Ensure total weightage equals 100%"""
        for record in self:
            if record.competency_ids:
                total_weight = sum(record.competency_ids.mapped('weightage'))
                if abs(total_weight - 100) > 0.01:
                    raise ValidationError(
                        _('Total competency weightage must equal 100%%. Current total: %.2f%%')
                        % total_weight
                    )

    def action_submit(self):
        """Submit appraisal for employee to start"""
        if not self.competency_ids:
            raise ValidationError(
                _('Please add competencies before submitting.')
            )
        self.write({'state': 'pending'})

    def action_start_self_assessment(self):
        """Employee starts self-assessment"""
        self.write({'state': 'self'})

    def action_submit_self_assessment(self):
        """Employee submits self-assessment"""
        # Check if all competencies have self ratings
        unrated = self.competency_ids.filtered(lambda c: not c.self_rating)
        if unrated:
            raise ValidationError(
                _('Please provide self ratings for all competencies: %s')
                % ', '.join(unrated.mapped('competency_id.name'))
            )
        if not self.self_comments:
            raise ValidationError(
                _('Please provide self assessment comments.')
            )
        self.write({'state': 'manager'})

    def action_manager_review(self):
        """Manager completes final review"""
        # Check if all competencies have manager ratings
        unrated = self.competency_ids.filtered(lambda c: not c.manager_rating)
        if unrated:
            raise ValidationError(
                _('Please provide manager ratings for all competencies: %s')
                % ', '.join(unrated.mapped('competency_id.name'))
            )
        if not self.manager_comments:
            raise ValidationError(
                _('Please provide manager comments.')
            )
        if not self.recommendation:
            raise ValidationError(
                _('Please provide a recommendation.')
            )
        self.write({
            'state': 'done',
            'date_final': fields.Date.today()
        })

    def action_cancel(self):
        """Cancel appraisal"""
        self.write({'state': 'cancel'})

    def action_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})


class AppraisalCompetencyLine(models.Model):
    _name = 'appraisal.competency.line'
    _description = 'Appraisal Competency Line'

    appraisal_id = fields.Many2one(
        'employee.appraisal',
        string='Appraisal',
        ondelete='cascade'
    )
    competency_id = fields.Many2one(
        'appraisal.competency',
        string='Competency',
        required=True
    )
    description = fields.Text(
        related='competency_id.description',
        string='Description'
    )
    weightage = fields.Float(
        string='Weightage (%)',
        default=10.0,
        help="Importance of this competency in overall evaluation (must total 100%)"
    )
    self_rating = fields.Float(
        string='Self Rating',
        digits=(3, 2),
        help="Employee's self assessment (0-5 scale: 0=N/A, 1=Poor, 2=Below, 3=Meets, 4=Exceeds, 5=Outstanding)"
    )
    manager_rating = fields.Float(
        string='Manager Rating',
        digits=(3, 2),
        help="Manager's assessment (0-5 scale: 0=N/A, 1=Poor, 2=Below, 3=Meets, 4=Exceeds, 5=Outstanding)"
    )
    comments = fields.Text(string='Comments')

    @api.constrains('self_rating', 'manager_rating')
    def _check_ratings(self):
        """Ensure ratings are within 0-5 range"""
        for record in self:
            if record.self_rating and (
                    record.self_rating < 0 or record.self_rating > 5
            ):
                raise ValidationError(
                    _('Self rating must be between 0 and 5.')
                )
            if record.manager_rating and (
                    record.manager_rating < 0 or record.manager_rating > 5
            ):
                raise ValidationError(
                    _('Manager rating must be between 0 and 5.')
                )

    @api.constrains('weightage')
    def _check_weightage(self):
        """Ensure weightage is valid"""
        for record in self:
            if record.weightage < 0 or record.weightage > 100:
                raise ValidationError(
                    _('Weightage must be between 0 and 100.')
                )
