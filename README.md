Hospital Management System (Flask + Oracle)

This is a role-based hospital management web application built using Flask (Python) and Oracle Database. It allows patients and physicians/admins to interact with hospital services including appointments, prescriptions, procedures, and room accommodations.

User Roles and Workflows:

1. Authentication
- Login system for Admin (Physician) and Patient.
- Session is created after successful login, storing user info like ID, department, etc.

2. Admin (Physician) Workflow
After login, the admin is redirected to the Physician Dashboard.

Functions:
- View personal profile and department
- View patients assigned to their department with prescription details
- View current week’s appointments (via stored procedure)
- Add prescriptions to patients (if appointment exists)
- Assign/remove medical procedures
- View and manage room accommodations (assign/discharge)
- Edit or delete patient records

3. Patient Workflow
After login/registration, patient is redirected to the Patient Dashboard.

Functions:
- View personal details and assigned doctor
- Book appointment by selecting department, doctor, date & time slot
- System checks for conflicts using validations and stored procedures
- View all prescriptions and medical procedures
- Check current room accommodation (if assigned)

Backend Details:
- Routes: Flask handles all HTTP routes and sessions
- SQL DB:
  - Tables: patient, physician, appointments, prescription, stay, procedure, medication, department, etc.
  - Stored Procedures: get_physician_details, get_patient_prescriptions, get_weekly_appointments, add_prescription
- Validations and retry logic for DB errors
- Flash messages for UI feedback

Test Utilities:
- /test_connection: Check DB connectivity
- /test_db, /test_patients: Display data for testing
- /check, /diagnose: Schema and permission checks
- /get_* routes: JSON APIs for dynamic frontend features

