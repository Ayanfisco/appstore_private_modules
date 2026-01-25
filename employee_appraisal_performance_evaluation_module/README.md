# Employee Appraisal Management for Odoo 19

## 📋 Overview

A comprehensive Employee Performance Appraisal System for Odoo 19 that enables organizations to conduct structured performance reviews with self-assessment, manager evaluation, goal tracking, and competency-based appraisals.

## ✨ Features

- **Complete Appraisal Workflow**
  - Draft → Pending → Self Assessment → Manager Review → Done
  - Multi-stage approval process
  - Email notifications at each stage

- **Competency Management**
  - Create custom competencies
  - Category-based organization (Technical, Leadership, Communication, etc.)
  - Weighted scoring system
  - Self-rating and manager-rating

- **Goal Tracking**
  - Set individual goals
  - Track achievement percentage
  - Monitor goal status (Not Started, In Progress, Completed)
  - Target date tracking

- **Appraisal Templates**
  - Pre-configured competency sets
  - Reusable templates for different roles
  - Automatic competency assignment

- **Comprehensive Reporting**
  - Individual appraisal reports
  - Department-wise analytics
  - Rating visualization
  - Export to PDF

- **Security & Access Control**
  - User-level access (view own appraisals)
  - Manager-level access (view team appraisals)
  - Record-level security rules

## 📦 Module Information

- **Name:** Employee Appraisal Management
- **Technical Name:** employee_appraisal
- **Version:** 19.0.1.0.0
- **Category:** Human Resources
- **Author:** Tech Joe
- **Website:** ayanfiscoss@gmail.com
- **License:** LGPL-3
- **Price:** $99.00 USD
- **Depends:** hr, mail

## 🚀 Installation

### Step 1: Download Module
Download the `employee_appraisal` folder to your Odoo addons directory.

### Step 2: Update Apps List
1. Login to Odoo as Administrator
2. Go to Apps menu
3. Click "Update Apps List"
4. Search for "Employee Appraisal Management"

### Step 3: Install Module
Click "Install" button on the module card

## ⚙️ Configuration

### 1. Set Up Competencies

Navigate to: **Appraisals > Configuration > Competencies**

Create competencies for your organization:

**Example Competencies:**
- **Technical Skills** (Category: Technical)
  - Description: Proficiency in required technical tools and technologies
  - Default Weightage: 25%

- **Communication** (Category: Communication)
  - Description: Ability to communicate effectively with team and clients
  - Default Weightage: 20%

- **Problem Solving** (Category: Problem Solving)
  - Description: Ability to analyze and solve complex problems
  - Default Weightage: 20%

- **Teamwork** (Category: Teamwork)
  - Description: Collaboration and contribution to team success
  - Default Weightage: 15%

- **Leadership** (Category: Leadership)
  - Description: Leadership qualities and mentoring abilities
  - Default Weightage: 20%

### 2. Create Appraisal Templates

Navigate to: **Appraisals > Configuration > Appraisal Templates**

Create templates for different roles:

**Example Template: Software Developer**
- Template Name: "Software Developer Annual Review"
- Competencies:
  - Technical Skills (30%)
  - Problem Solving (25%)
  - Communication (20%)
  - Teamwork (15%)
  - Leadership (10%)

**Total weightage must equal 100%**

### 3. Assign User Access Rights

Navigate to: **Settings > Users & Companies > Users**

Assign groups:
- **Employee Appraisal / User**: Can view and complete their own appraisals
- **Employee Appraisal / Manager**: Can manage team appraisals

## 📖 User Guide

### For Employees

#### Starting Self-Assessment

1. Navigate to **Appraisals > Employee Appraisals**
2. Open your assigned appraisal
3. Click "Start Self Assessment"
4. Rate yourself on each competency (0-5 scale)
5. Add comments for each competency
6. Fill in "Self Assessment Comments"
7. Click "Submit Self Assessment"

#### Adding Goals

1. Go to "Goals" tab
2. Click "Add a line"
3. Enter:
   - Goal name
   - Description
   - Target date
   - Achievement percentage (0-100%)
   - Status

### For Managers

#### Creating Appraisal

1. Navigate to **Appraisals > Employee Appraisals**
2. Click "Create"
3. Fill in details:
   - Employee
   - Appraisal Template
   - Start Date
   - End Date
4. Competencies auto-populate from template
5. Click "Submit" to send to employee

#### Reviewing Employee Assessment

1. Open appraisal in "Manager Review" state
2. Review employee's self-ratings
3. Provide your manager ratings (0-5 scale)
4. Add manager comments
5. Fill in:
   - Strengths
   - Areas for Improvement
   - Recommendation (Promotion, Training, etc.)
6. Click "Complete Review"

### Appraisal Workflow States

1. **Draft**: Initial creation, editable
2. **Pending**: Submitted, waiting for employee
3. **Self Assessment**: Employee is completing self-evaluation
4. **Manager Review**: Manager is providing feedback
5. **Done**: Appraisal completed
6. **Cancelled**: Appraisal cancelled

## 📊 Reports

### Generate Appraisal Report

1. Open completed appraisal
2. Click "Print Report" button
3. PDF report generates with:
   - Employee details
   - Competency ratings comparison
   - Goals achievement
   - Manager recommendations
   - Comments and feedback

## 🔧 Technical Details

### Module Structure

```
employee_appraisal/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── employee_appraisal.py      # Main appraisal model
│   ├── appraisal_template.py      # Template management
│   ├── appraisal_competency.py    # Competency definitions
│   └── appraisal_goal.py          # Goal tracking
├── views/
│   ├── employee_appraisal_views.xml
│   ├── appraisal_template_views.xml
│   ├── appraisal_competency_views.xml
│   ├── appraisal_goal_views.xml
│   └── appraisal_menu.xml
├── security/
│   ├── ir.model.access.csv        # Access rights
│   └── security.xml               # Security groups & rules
├── data/
│   └── appraisal_data.xml         # Initial data
├── report/
│   ├── __init__.py
│   ├── appraisal_report.py
│   └── appraisal_report_template.xml
└── static/
    └── description/
        ├── icon.png
        └── index.html
```

### Key Models

**employee.appraisal**
- Main appraisal record
- Inherits: mail.thread, mail.activity.mixin
- Workflow states and transitions
- Rating calculations

**appraisal.template**
- Reusable appraisal configurations
- Competency mappings

**appraisal.competency**
- Master competency definitions
- Categories and descriptions

**appraisal.competency.line**
- Competency ratings per appraisal
- Self and manager ratings

**appraisal.goal.line**
- Individual goal tracking
- Achievement monitoring

### Important Notes for Odoo 19

1. **No `attrs` in views** - Use `invisible`, `readonly`, `required` directly
2. **No `tree` string in One2many/Many2many** - Use field definition only
3. **Use `invisible` instead of `attrs={'invisible': ...}`**
4. **Email templates use proper Odoo 19 syntax**

## 🐛 Troubleshooting

### Issue: Template weightage error
**Solution**: Ensure total competency weightages equal 100%

### Issue: Cannot submit self-assessment
**Solution**: Fill in mandatory "Self Assessment Comments" field

### Issue: Rating not calculating
**Solution**: Ensure all competencies have ratings entered

### Issue: Access denied
**Solution**: Check user has correct security group assigned

## 🔄 Upgrade & Migration

This module is built specifically for Odoo 19. It follows Odoo 19 best practices:
- No deprecated `attrs` attribute
- Modern view syntax
- Compatible with Odoo 19 security model

## 📝 Changelog

### Version 19.0.1.0.0
- Initial release
- Complete appraisal workflow
- Competency management
- Goal tracking
- Template system
- Report generation

## 🤝 Support

For support, please contact:
- **Email:** ayanfiscoss@gmail.com
- **Company:** Tech Joe

## 📄 License

This module is licensed under LGPL-3.

## 🙏 Credits

**Author:** Tech Joe  
**Maintainer:** Tech Joe  
**Website:** ayanfiscoss@gmail.com

---

**Ready for Odoo App Store Submission** ✅