# MediCore — Clinic & Healthcare Management (Odoo 18)

## Overview

A complete, production-ready clinic and hospital management module for **Odoo 18 Community & Enterprise**.
Includes a **patient-facing portal** — patients log in via Odoo's standard portal (`/web/login`) and land directly on their personal health dashboard at `/my/health`.

---

## Features

| Module | Description |
|---|---|
| **Patients** | Full patient registry with medical history, insurance, allergies, photo |
| **Appointments** | Calendar scheduling, status workflow, doctor availability |
| **Consultations** | Clinical notes, ICD-10 diagnosis, treatment plan, follow-up |
| **Vital Signs** | BP, pulse, temperature, weight, BMI, O₂ saturation, blood sugar |
| **Prescriptions** | Medications with dosage/frequency/duration, printable PDF Rx |
| **Lab Tests** | Request, track, and record lab results with PDF report |
| **Billing** | Itemised bills with VAT, discounts, payment tracking |
| **Pharmacy** | Dispensing linked to prescriptions with Odoo Inventory integration |
| **Reports** | PDF prescription, lab report, patient card, clinic bill |
| **Security** | 5 role groups: Manager, Doctor, Nurse/Receptionist, Lab Tech, Pharmacist |
| **Patient Portal** | Read-only portal: appointments, prescriptions, lab results, profile |

---

## Patient Portal

Portal users have **read-only** access to their own records. They cannot create, modify, or delete any data.

### How it works

1. Staff registers the patient and clicks **"Grant Portal Access"** on the patient record.
2. Odoo sends the patient a portal invite email.
3. Patient logs in at `/web/login` — Odoo redirects them to `/my`.
4. The portal home page shows a **"My Health Dashboard"** link leading to `/my/health`.

### Portal pages

| URL | What the patient sees |
|---|---|
| `/my/health` | Dashboard — upcoming appointments, recent prescriptions, lab tests |
| `/my/health/appointments` | Full appointment history |
| `/my/health/prescriptions` | All prescriptions |
| `/my/health/lab-results` | Lab test results |
| `/my/health/profile` | Personal information (read-only) |

> **Note:** The profile page is view-only. Patients cannot update their own records — contact the clinic to make changes.

---

## Installation

### Method 1 — Zip Upload (Recommended)
1. Go to **Settings → Apps → Upload App**
2. Upload `clinic_management.zip`
3. Search for "Clinic" and click **Install**

### Method 2 — Manual
1. Extract `clinic_management/` into your Odoo addons directory:
   ```
   /path/to/odoo/addons/clinic_management/
   ```
2. Restart Odoo server:
   ```bash
   sudo systemctl restart odoo
   # or
   python odoo-bin -u clinic_management -d your_database
   ```
3. Go to **Settings → Apps**, search **Clinic**, click **Install**

---

## Dependencies

These standard Odoo modules must be installed (they usually are by default):
- `base`, `mail`, `product`, `account`, `stock`, `calendar`, `web`, `portal`, `website`, `auth_signup`

---

## User Roles & Access

| Role | Can Do |
|---|---|
| **Clinic Manager** | Full access — all records, configuration, reports |
| **Doctor** | Consultations, prescriptions, lab requests, patient records |
| **Nurse/Receptionist** | Patient registration, appointments, vital signs, billing |
| **Lab Technician** | Process lab requests, enter results |
| **Pharmacist** | View prescriptions, dispense medications |
| **Portal User (Patient)** | Read-only view of own appointments, prescriptions, lab results |

Assign staff roles at: **Settings → Users → Edit User → Clinic Management**

Grant patient portal access from the patient record: **Clinic → Patients → [Patient] → Grant Portal Access**

---

## Configuration After Install

1. **Add your Doctors** — Clinic → Configuration → Doctors
2. **Verify Departments** — Clinic → Configuration → Departments (pre-loaded)
3. **Set Consultation Fees** per doctor
4. **Link Medications to Products** in the pharmacy section for stock deduction
5. **Company Details** — Settings → Company for report letterhead

---

## Module Structure

```
clinic_management/
├── __manifest__.py          # Module metadata
├── __init__.py
├── models/
│   ├── clinic_patient.py    # Patient model (with portal partner link)
│   ├── clinic_doctor.py     # Doctor + Department models
│   ├── clinic_appointment.py
│   ├── clinic_consultation.py
│   ├── clinic_prescription.py
│   ├── clinic_lab_test.py   # Lab test + catalog
│   ├── clinic_vital_signs.py
│   ├── clinic_billing.py
│   └── clinic_pharmacy.py
├── views/
│   ├── website/
│   │   ├── portal_templates.xml         # Patient portal pages
│   │   └── website_appointment_templates.xml
│   └── ...                  # Backend views
├── controllers/
│   └── clinic_controller.py  # Portal + public booking routes
├── reports/                 # QWeb PDF report templates
├── security/                # Groups + access control (portal: read-only)
├── data/                    # Sequences, departments, lab catalog
├── demo/                    # Sample data for quick demo
├── wizards/                 # Quick appointment booking wizard
└── static/src/css/          # Custom styling
```

---

## Customization Tips

- **Change VAT rate**: Edit `clinic_billing.py` → `_compute_totals` method (default 7.5% for Nigeria)
- **Add more lab tests**: Clinic → Laboratory → Test Catalog
- **Custom report branding**: Edit `reports/clinic_prescription_report.xml`
- **Extend patient model**: Inherit `clinic.patient` in your own module

---

## Support & Contribution

- Report issues on GitHub
- Pull requests welcome
- For commercial customization, contact your Odoo partner

---

## License

LGPL-3 — Free to use, modify, and distribute.
