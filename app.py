from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import cx_Oracle
import logging
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Database connection configuration
DB_USER = "sidd"
DB_PASSWORD = "student"
DB_DSN = "localhost:1521/XEPDB1"

# Function to connect to Oracle Database
def get_db_connection():
    return cx_Oracle.connect(DB_USER, DB_PASSWORD, DB_DSN)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            if user_type == 'admin':
                # Check admin credentials and get physician details
                cursor.execute("""
                    SELECT a.login_id, a.username, a.password, 
                           p.emp_id, p.name, p.position, p.dept_id
                    FROM admin_login a
                    JOIN physician p ON a.username = p.name
                    WHERE a.username = :1
                """, (username,))
                admin = cursor.fetchone()
                
                if admin and password == admin[2]:  # In production, use proper password hashing
                    session['user_id'] = admin[0]
                    session['username'] = admin[1]
                    session['user_type'] = 'admin'
                    session['emp_id'] = admin[3]
                    session['position'] = admin[5]
                    session['dept_id'] = admin[6]
                    # Check if name already starts with Dr.
                    name = admin[1]
                    if not name.startswith('Dr.'):
                        name = f'Dr. {name}'
                    flash(f'Welcome {name}!', 'success')
                    return redirect(url_for('physician_dashboard'))
                else:
                    flash('Invalid credentials!', 'error')
            
            elif user_type == 'patient':
                # Check patient credentials
                cursor.execute("""
                    SELECT pl.login_id, pl.username, pl.password,
                           p.patient_id, p.name, p.age, p.sex, p.phone_no, p.dept_id
                    FROM patient_login pl
                    JOIN patient p ON pl.username = p.name
                    WHERE pl.username = :1
                """, (username,))
                patient = cursor.fetchone()
                
                if patient and password == patient[2]:  # In production, use proper password hashing
                    session['user_id'] = patient[0]
                    session['username'] = patient[1]
                    session['user_type'] = 'patient'
                    session['patient_id'] = patient[3]
                    session['dept_id'] = patient[8]
                    flash(f'Welcome {patient[1]}!', 'success')
                    return redirect(url_for('patient_dashboard'))
                else:
                    flash('Invalid patient credentials!', 'error')
            else:
                flash('Please select a user type!', 'error')
            
            cursor.close()
            connection.close()
            
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        
        return redirect(url_for('login'))
        
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            password = request.form.get('password')
            phone = request.form.get('phone')
            age = request.form.get('age')
            sex = request.form.get('sex')
            dept_id = request.form.get('dept_id')

            if not all([name, password, phone, age, sex, dept_id]):
                flash('All fields are required!', 'error')
                return redirect(url_for('register'))

            connection = get_db_connection()
            cursor = connection.cursor()

            # First check if name already exists in patient_login
            cursor.execute("SELECT COUNT(*) FROM patient_login WHERE username = :1", [name])
            if cursor.fetchone()[0] > 0:
                flash('Name already exists!', 'error')
                return redirect(url_for('register'))

            # Get the next available patient_id
            cursor.execute("SELECT MAX(patient_id) FROM patient")
            max_id = cursor.fetchone()[0]
            new_patient_id = 1 if max_id is None else max_id + 1

            # Insert into patient table
            cursor.execute("""
                INSERT INTO patient (patient_id, name, age, sex, phone_no, dept_id)
                VALUES (:1, :2, :3, :4, :5, :6)
            """, [new_patient_id, name, age, sex, phone, dept_id])

            # Insert into patient_login table
            cursor.execute("""
                INSERT INTO patient_login (login_id, username, password)
                VALUES (:1, :2, :3)
            """, [new_patient_id, name, password])

            connection.commit()
            cursor.close()
            connection.close()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            print(f"Registration error: {str(e)}")
            flash(f'Registration failed: {str(e)}', 'error')
            return redirect(url_for('register'))

    # For GET request, fetch departments for the dropdown
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT dept_id, deptname FROM department ORDER BY deptname")
        departments = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as e:
        departments = []
        print(f"Error fetching departments: {str(e)}")

    return render_template('register.html', departments=departments)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        try:
            # Try with schema name explicitly
            cursor.execute("SELECT * FROM SIDD.PATIENT")
            patients = cursor.fetchall()
            print(f"Query result: {patients}")  # Debug line
            
            patient_list = []
            for row in patients:
                patient = {
                    'patient_id': row[0],
                    'name': row[1],
                    'age': row[2],
                    'sex': row[3],
                    'phone_no': row[4],
                    'dept_id': row[5]
                }
                patient_list.append(patient)
            
            cursor.close()
            connection.close()
            
            if patient_list:
                print(f"Found {len(patient_list)} patients")  # Debug line
            else:
                print("No patients found in list")  # Debug line
                
            return render_template('dashboard.html', patients=patient_list)
            
        except cx_Oracle.Error as e:
            print(f"Database error: {str(e)}")  # Debug line
            cursor.close()
            connection.close()
            return render_template('dashboard.html', patients=[])
            
    except Exception as e:
        print(f"Connection error: {str(e)}")  # Debug line
        return render_template('dashboard.html', patients=[])

@app.route('/appointment/new', methods=['GET', 'POST'])
@login_required
def new_appointment():
    if 'user_type' not in session or session['user_type'] != 'patient':
        flash('Only patients can book appointments.', 'error')
        return redirect(url_for('dashboard'))

    connection = None
    cursor = None
    max_retries = 3
    retry_delay = 2  # seconds

    try:
        logger.info("Starting appointment booking process")
        connection = get_db_connection()
        cursor = connection.cursor()

        if request.method == 'POST':
            emp_id = request.form.get('emp_id')
            app_date = request.form.get('app_date')
            app_time = request.form.get('app_time')
            patient_id = session.get('patient_id')

            logger.info(f"Booking appointment - Patient ID: {patient_id}, Doctor ID: {emp_id}, Date: {app_date}, Time: {app_time}")

            if not all([emp_id, app_date, app_time, patient_id]):
                logger.warning("Missing required fields in appointment booking")
                flash('All fields are required.', 'error')
                return redirect(url_for('new_appointment'))

            # Book the appointment with retry mechanism
            logger.info("Attempting to book appointment")
            for attempt in range(max_retries):
                try:
                    cursor.execute("""
                        INSERT INTO appointments (emp_id, app_date, app_time, patient_id)
                        VALUES (:1, TO_DATE(:2, 'YYYY-MM-DD'), 
                               TO_DATE(:3, 'HH24:MI'),
                               :4)
                    """, [emp_id, app_date, app_time, patient_id])
                    
                    connection.commit()
                    logger.info("Appointment booked successfully")
                    flash('Appointment booked successfully!', 'success')
                    return redirect(url_for('patient_dashboard'))
                except cx_Oracle.Error as e:
                    error_code = e.args[0].code
                    error_message = str(e)
                    logger.error(f"Database error during appointment booking (attempt {attempt + 1}/{max_retries}). Code: {error_code}, Message: {error_message}")
                    
                    if error_code == 4036:  # ORA-04036: PGA memory exceeded
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                        else:
                            flash('The system is currently experiencing high load. Please try again in a few minutes.', 'error')
                    elif error_code == -20001:
                        flash('Sorry, appointments can only be scheduled between 10:00 AM and 7:00 PM.', 'error')
                    elif error_code == -20002:
                        flash(f'Sorry, the selected time slot ({app_time}) on {app_date} is already booked. Please choose a different time.', 'error')
                    else:
                        # Log the full error for debugging but show a user-friendly message
                        logger.error(f"Unexpected database error: {error_message}")
                        flash('Unable to book the appointment. Please try again or choose a different time.', 'error')
                    return redirect(url_for('new_appointment'))

        # Get departments for the form
        logger.info("Fetching departments for appointment form")
        try:
            cursor.execute("SELECT dept_id, deptname FROM department ORDER BY deptname")
            departments = [{'dept_id': row[0], 'deptname': row[1]} for row in cursor.fetchall()]
            logger.info(f"Retrieved {len(departments)} departments")
        except cx_Oracle.Error as e:
            logger.error(f"Error fetching departments: {str(e)}")
            departments = []
            flash('Error loading departments. Please try again.', 'error')

        from datetime import date
        today_date = date.today().isoformat()

        return render_template('new_appointment.html', 
                             departments=departments,
                             today_date=today_date)

    except Exception as e:
        logger.error(f"Unexpected error in appointment booking: {str(e)}")
        flash('An unexpected error occurred. Please try again later.', 'error')
        return redirect(url_for('patient_dashboard'))
    finally:
        # Ensure proper cleanup of database resources
        if cursor:
            try:
                cursor.close()
                logger.debug("Cursor closed successfully")
            except Exception as e:
                logger.error(f"Error closing cursor: {str(e)}")
        if connection:
            try:
                connection.close()
                logger.debug("Connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")

@app.route('/get_physicians/<int:dept_id>')
@login_required
def get_physicians(dept_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT emp_id, name, position
            FROM physician
            WHERE dept_id = :1
            ORDER BY name
        """, [dept_id])

        physicians = [{'emp_id': row[0], 'name': row[1], 'position': row[2]} 
                     for row in cursor.fetchall()]

        cursor.close()
        connection.close()

        return jsonify(physicians)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_available_slots/<int:emp_id>/<date>')
@login_required
def get_available_slots(emp_id, date):
    try:
        # Generate all possible slots between 10 AM and 7 PM (30-minute intervals)
        all_slots = []
        for hour in range(10, 19):  # 10 AM to 7 PM
            for minute in [0, 30]:
                all_slots.append(f"{hour:02d}:{minute:02d}")

        return jsonify(all_slots)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        name = request.form['name']
        age = request.form['age']
        sex = request.form['sex']
        phone_no = request.form['phone_no']
        dept_id = request.form['dept_id']
        
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                INSERT INTO patient (patient_id, name, age, sex, phone_no, dept_id) 
                VALUES (:1, :2, :3, :4, :5, :6)
            """, (patient_id, name, age, sex, phone_no, dept_id))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            flash('Patient added successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except cx_Oracle.Error as e:
            flash(f'Error adding patient: {str(e)}', 'error')
            return redirect(url_for('add_patient'))
    
    return render_template('add_patient.html')

@app.route('/patient/edit/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        if request.method == 'POST':
            # Get form data
            name = request.form.get('name')
            age = request.form.get('age')
            sex = request.form.get('sex')
            phone_no = request.form.get('phone_no')
            dept_id = request.form.get('dept_id')
            
            # Update patient details
            cursor.execute("""
                UPDATE patient 
                SET name = :1, age = :2, sex = :3, phone_no = :4, dept_id = :5
                WHERE patient_id = :6
            """, (name, age, sex, phone_no, dept_id, patient_id))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            flash('Patient details updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        # Fetch patient details for editing
        cursor.execute("""
            SELECT patient_id, name, age, sex, phone_no, dept_id
            FROM patient
            WHERE patient_id = :1
        """, (patient_id,))
        
        row = cursor.fetchone()
        if row:
            patient = {
                'patient_id': row[0],
                'name': row[1],
                'age': row[2],
                'sex': row[3],
                'phone_no': row[4],
                'dept_id': row[5]
            }
        else:
            flash('Patient not found!', 'error')
            return redirect(url_for('dashboard'))
        
        cursor.close()
        connection.close()
        
        return render_template('edit_patient.html', patient=patient)
        
    except Exception as e:
        logger.error(f"Error editing patient: {e}")
        flash(f'Error editing patient: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    if 'username' not in session:
        return redirect(url_for('login'))
        
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # First check if patient exists
        cursor.execute("SELECT COUNT(*) FROM patient WHERE patient_id = :1", (patient_id,))
        if cursor.fetchone()[0] == 0:
            flash('Patient not found!', 'error')
            return redirect(url_for('dashboard'))
        
        # Delete the patient
        cursor.execute("DELETE FROM patient WHERE patient_id = :1", (patient_id,))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        flash('Patient deleted successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    except cx_Oracle.Error as e:
        flash(f'Database error: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/test_connection')
def test_connection():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Try a simple query to verify connection
        cursor.execute("SELECT 1 FROM dual")
        result = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        logger.debug("Database connection successful")
        return {"status": "Connected", "message": "Database connection successful"}
        
    except cx_Oracle.Error as e:
        logger.error(f"Oracle Database error: {e}")
        return {"status": "Error", "message": f"Database connection failed: {str(e)}"}
    except Exception as e:
        logger.error(f"General error: {e}")
        return {"status": "Error", "message": f"Error: {str(e)}"}

@app.route('/test_patients')
def test_patients():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # First, let's count the total patients
        cursor.execute("SELECT COUNT(*) FROM patient")
        count = cursor.fetchone()[0]
        
        # Now get all patient details
        cursor.execute("""
            SELECT patient_id, name, age, sex, phone_no, dept_id 
            FROM patient 
            ORDER BY patient_id
        """)
        patients = cursor.fetchall()
        
        # Convert to list of dictionaries for better display
        patient_list = []
        for patient in patients:
            patient_list.append({
                'patient_id': patient[0],
                'name': patient[1],
                'age': patient[2],
                'sex': patient[3],
                'phone_no': patient[4],
                'dept_id': patient[5]
            })
        
        cursor.close()
        connection.close()
        
        # Return both count and patient details in a formatted HTML
        html_response = f"""
        <h2>Total Patients: {count}</h2>
        <table border="1">
            <tr>
                <th>Patient ID</th>
                <th>Name</th>
                <th>Age</th>
                <th>Sex</th>
                <th>Phone</th>
                <th>Department ID</th>
            </tr>
        """
        
        for patient in patient_list:
            html_response += f"""
            <tr>
                <td>{patient['patient_id']}</td>
                <td>{patient['name']}</td>
                <td>{patient['age']}</td>
                <td>{patient['sex']}</td>
                <td>{patient['phone_no']}</td>
                <td>{patient['dept_id']}</td>
            </tr>
            """
        
        html_response += "</table>"
        
        if count == 0:
            return "No patients found in the database."
        
        return html_response
        
    except cx_Oracle.Error as e:
        logger.error(f"Oracle Database error: {e}")
        return f"Database error: {str(e)}"
    except Exception as e:
        logger.error(f"General error: {e}")
        return f"Error: {str(e)}"

@app.route('/test_db')
def test_db():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Test patient table
        cursor.execute("SELECT COUNT(*) FROM patient")
        patient_count = cursor.fetchone()[0]
        
        # Test department table
        cursor.execute("SELECT COUNT(*) FROM department")
        dept_count = cursor.fetchone()[0]
        
        # Get some sample data
        cursor.execute("SELECT * FROM patient WHERE ROWNUM <= 2")
        sample_patients = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return f"""
        <h3>Database Test Results:</h3>
        <p>Number of patients: {patient_count}</p>
        <p>Number of departments: {dept_count}</p>
        <p>Sample patient data: {sample_patients}</p>
        """
    except Exception as e:
        return f"Database error: {str(e)}"

@app.route('/test')
def test():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Try the exact same query that worked in SQL*Plus
        cursor.execute("SELECT * FROM patient")
        rows = cursor.fetchall()
        
        # Create a simple HTML response
        result = f"<h2>Found {len(rows)} patients:</h2>"
        for row in rows:
            result += f"<p>ID: {row[0]}, Name: {row[1]}, Age: {row[2]}, Sex: {row[3]}, Phone: {row[4]}, Dept: {row[5]}</p>"
        
        cursor.close()
        connection.close()
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/check')
def check():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Check current schema
        cursor.execute("SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM dual")
        current_schema = cursor.fetchone()[0]
        
        # Try with fully qualified name
        cursor.execute("SELECT * FROM SIDD.patient")
        patient_count = len(cursor.fetchall())
        
        # Check if table exists
        cursor.execute("""
            SELECT table_name 
            FROM all_tables 
            WHERE owner = 'SIDD' 
            AND table_name = 'PATIENT'
        """)
        table_info = cursor.fetchone()
        
        result = f"""
        <h3>Database Check:</h3>
        <p>Current Schema: {current_schema}</p>
        <p>Patient Table Exists: {table_info is not None}</p>
        <p>Number of Patients: {patient_count}</p>
        """
        
        cursor.close()
        connection.close()
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/diagnose')
def diagnose():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        results = []
        
        # Try different queries
        queries = [
            "SELECT COUNT(*) FROM patient",
            "SELECT COUNT(*) FROM SIDD.patient",
            "SELECT * FROM patient WHERE ROWNUM = 1",
            "SELECT patient_id FROM patient",
            "SELECT table_name, num_rows FROM all_tables WHERE owner='SIDD' AND table_name='PATIENT'"
        ]
        
        for query in queries:
            try:
                cursor.execute(query)
                result = cursor.fetchall()
                results.append(f"Query: {query}<br>Result: {result}<br><br>")
            except Exception as e:
                results.append(f"Query: {query}<br>Error: {str(e)}<br><br>")
        
        cursor.close()
        connection.close()
        
        return "<h3>Diagnostic Results:</h3>" + "".join(results)
        
    except Exception as e:
        return f"Connection Error: {str(e)}"

@app.route('/patient_dashboard')
def patient_dashboard():
    if 'user_type' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Get patient details including department name
        cursor.execute("""
            SELECT p.patient_id, p.name, p.age, p.sex, p.phone_no, 
                   p.dept_id, d.deptname
            FROM patient p
            LEFT JOIN department d ON p.dept_id = d.dept_id
            WHERE p.name = :1
        """, (session['username'],))
        
        patient_data = cursor.fetchone()
        
        if patient_data:
            patient = {
                'patient_id': patient_data[0],
                'name': patient_data[1],
                'age': patient_data[2],
                'sex': patient_data[3],
                'phone_no': patient_data[4],
                'dept_id': patient_data[5],
                'dept_name': patient_data[6]
            }
            
            # Store patient_id in session for prescription access
            session['patient_id'] = patient['patient_id']
            
            # Get assigned physician (from same department)
            cursor.execute("""
                SELECT p.emp_id, p.name, p.position
                FROM physician p
                WHERE p.dept_id = :1
            """, (patient['dept_id'],))
            
            physician_data = cursor.fetchone()
            if physician_data:
                physician = {
                    'emp_id': physician_data[0],
                    'name': physician_data[1],
                    'position': physician_data[2]
                }
            else:
                physician = None
        else:
            patient = None
            physician = None
            
        cursor.close()
        connection.close()
        
        return render_template('patient_dashboard.html', 
                             patient=patient,
                             physician=physician)
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/physician_dashboard')
def physician_dashboard():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect(url_for('login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Get physician details using stored procedure
        physician_cursor = connection.cursor()
        cursor.callproc("get_physician_details", [session['username'], physician_cursor])
        
        physician_data = physician_cursor.fetchone()
        print(f"DEBUG - Physician data: {physician_data}")  # Debug log
        physician_cursor.close()
        
        if physician_data:
            physician = {
                'emp_id': physician_data[0],
                'name': physician_data[1],
                'position': physician_data[2],
                'dept_id': physician_data[3],
                'dept_name': physician_data[4]
            }
            print(f"DEBUG - Physician emp_id: {physician['emp_id']}")  # Debug log
            
            # Get patients and their prescriptions using stored procedure
            patients_cursor = connection.cursor()
            cursor.callproc("get_patient_prescriptions", [physician['emp_id'], patients_cursor])
            
            # Debug: Print all raw data from cursor
            all_patient_data = patients_cursor.fetchall()
            print(f"DEBUG - Raw patient data: {all_patient_data}")  # Debug log
            
            patients = []
            for row in all_patient_data:
                patient_data = {
                    'patient_id': row[0],
                    'name': row[1],
                    'age': row[2],
                    'sex': row[3],
                    'phone_no': row[4],
                    'current_prescription': row[5] if row[5] else 'No prescription'
                }
                print(f"DEBUG - Processed patient data: {patient_data}")  # Debug log
                patients.append(patient_data)
            
            patients_cursor.close()

            # Get current week's appointments using stored procedure
            from datetime import datetime, timedelta
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)

            appointments_cursor = connection.cursor()
            cursor.execute("""
                BEGIN
                    get_weekly_appointments(
                        p_emp_id => :1,
                        p_start_date => TO_DATE(:2, 'YYYY-MM-DD'),
                        p_end_date => TO_DATE(:3, 'YYYY-MM-DD'),
                        p_cursor => :4
                    );
                END;
            """, [
                physician['emp_id'],
                week_start.strftime('%Y-%m-%d'),
                week_end.strftime('%Y-%m-%d'),
                appointments_cursor
            ])

            weekly_appointments = {}
            current_date = week_start
            while current_date <= week_end:
                day_str = current_date.strftime('%A, %B %d')
                weekly_appointments[day_str] = []
                current_date += timedelta(days=1)

            for row in appointments_cursor.fetchall():
                day_str = row[0].strftime('%A, %B %d')
                weekly_appointments[day_str].append({
                    'time': row[1],
                    'patient_id': row[2],
                    'patient_name': row[3]
                })

            appointments_cursor.close()

        else:
            physician = None
            patients = []
            weekly_appointments = {}
            
        cursor.close()
        connection.close()
        
        print(f"DEBUG - Final patients data being sent to template: {patients}")  # Debug log
        
        return render_template('physician_dashboard.html', 
                             physician=physician, 
                             patients=patients,
                             weekly_appointments=weekly_appointments)
        
    except Exception as e:
        print(f"DEBUG - Error in physician_dashboard: {str(e)}")  # Debug log
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/physician/schedule/<date>')
@login_required
def get_physician_schedule(date):
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        from datetime import datetime, timedelta
        start_date = datetime.strptime(date, '%Y-%m-%d')
        end_date = start_date + timedelta(days=6)

        connection = get_db_connection()
        cursor = connection.cursor()

        # Execute a block to handle date conversion
        appointments_cursor = connection.cursor()
        cursor.execute("""
            BEGIN
                get_weekly_appointments(
                    p_emp_id => :1,
                    p_start_date => TO_DATE(:2, 'YYYY-MM-DD'),
                    p_end_date => TO_DATE(:3, 'YYYY-MM-DD'),
                    p_cursor => :4
                );
            END;
        """, [
            session['emp_id'],
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            appointments_cursor
        ])

        # Process the results
        weekly_schedule = {}
        current_date = start_date
        while current_date <= end_date:
            day_str = current_date.strftime('%A, %B %d')
            weekly_schedule[day_str] = []
            current_date += timedelta(days=1)

        for row in appointments_cursor.fetchall():
            day_str = row[0].strftime('%A, %B %d')
            weekly_schedule[day_str].append({
                'time': row[1],
                'patient_id': row[2],
                'patient_name': row[3]
            })

        appointments_cursor.close()
        cursor.close()
        connection.close()

        return jsonify(weekly_schedule)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/patient/details/<int:patient_id>')
@login_required
def get_patient_details(patient_id):
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Get patient details including department name
        cursor.execute("""
            SELECT p.patient_id, p.name, p.age, p.sex, p.phone_no, 
                   p.dept_id, d.deptname
            FROM patient p
            LEFT JOIN department d ON p.dept_id = d.dept_id
            WHERE p.patient_id = :1
        """, [patient_id])

        row = cursor.fetchone()
        if row:
            patient_data = {
                'patient_id': row[0],
                'name': row[1],
                'age': row[2],
                'sex': row[3],
                'phone_no': row[4],
                'dept_id': row[5],
                'dept_name': row[6]
            }
            cursor.close()
            connection.close()
            return jsonify(patient_data)
        else:
            cursor.close()
            connection.close()
            return jsonify({'error': 'Patient not found'}), 404

    except Exception as e:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        return jsonify({'error': str(e)}), 500

@app.route('/get_medications')
@login_required
def get_medications():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT med_id, med_name FROM medication ORDER BY med_name")
        medications = [{'med_id': row[0], 'med_name': row[1]} for row in cursor.fetchall()]

        cursor.close()
        connection.close()

        return jsonify(medications)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/add_prescription', methods=['POST'])
@login_required
def add_prescription():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        med_id = data.get('med_id')
        emp_id = session.get('emp_id')

        if not all([patient_id, med_id, emp_id]):
            return jsonify({'error': 'Missing required fields'}), 400

        connection = get_db_connection()
        cursor = connection.cursor()

        # Create an output variable for the function result
        out_val = cursor.var(cx_Oracle.NUMBER)
        
        # Call the add_prescription function
        cursor.execute("""
            BEGIN
                :result := add_prescription(:emp_id, :patient_id, :med_id);
            END;
        """, {
            'result': out_val,
            'emp_id': emp_id,
            'patient_id': patient_id,
            'med_id': med_id
        })
        
        result = out_val.getvalue()
        
        # Commit the transaction
        connection.commit()

        cursor.close()
        connection.close()

        if result == 1:
            return jsonify({'message': 'Prescription added successfully'})
        elif result == 0:
            return jsonify({'error': 'You can only prescribe medications to patients who have appointments with you'}), 403
        elif result == -1:
            return jsonify({'error': 'This medication has already been prescribed to this patient'}), 400
        else:
            return jsonify({'error': 'An error occurred while adding the prescription'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_patient_list')
@login_required
def get_patient_list():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Get patients and their prescriptions using stored procedure
        patients_cursor = connection.cursor()
        cursor.callproc("get_patient_prescriptions", [session['emp_id'], patients_cursor])
        
        patients = []
        for row in patients_cursor.fetchall():
            patients.append({
                'patient_id': row[0],
                'name': row[1],
                'age': row[2],
                'sex': row[3],
                'phone_no': row[4],
                'current_prescription': row[5] if row[5] else 'No prescription'
            })
        
        patients_cursor.close()
        cursor.close()
        connection.close()

        return jsonify({'patients': patients})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_patient_prescriptions')
@login_required
def get_patient_prescriptions():
    # Check if user is logged in as patient
    if 'user_type' not in session or session['user_type'] != 'patient':
        logger.error("Unauthorized access attempt")
        return jsonify({'error': 'Unauthorized access'}), 403

    # Check if patient_id exists in session
    if 'patient_id' not in session:
        logger.error("No patient_id found in session")
        return jsonify({'error': 'Patient ID not found in session'}), 400

    patient_id = session['patient_id']
    logger.info(f"Fetching prescriptions for patient_id: {patient_id}")

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Get prescriptions with medication and physician details
        cursor.execute("""
            SELECT p.prescription_id, p.emp_id, p.med_id, 
                   m.med_name, ph.name as physician_name
            FROM prescription p
            JOIN medication m ON p.med_id = m.med_id
            JOIN physician ph ON p.emp_id = ph.emp_id
            WHERE p.patient_id = :1
            ORDER BY p.prescription_id DESC
        """, [patient_id])
        
        rows = cursor.fetchall()
        logger.info(f"Found {len(rows)} prescriptions")
        
        prescriptions = []
        for row in rows:
            prescriptions.append({
                'prescription_id': row[0],
                'emp_id': row[1],
                'med_id': row[2],
                'med_name': row[3],
                'physician_name': row[4]
            })
        
        return jsonify({'prescriptions': prescriptions})

    except Exception as e:
        logger.error(f"Error in get_patient_prescriptions: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection:
            try:
                connection.close()
            except:
                pass

@app.route('/get_patient_procedures')
@login_required
def get_patient_procedures():
    # Allow both admin and patient access
    if 'user_type' not in session or session['user_type'] not in ['admin', 'patient']:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Get patient_id from query params for admin, from session for patient
        patient_id = request.args.get('patient_id') if session['user_type'] == 'admin' else session.get('patient_id')
        if not patient_id:
            return jsonify({'error': 'Patient ID not found'}), 400

        # Get all procedures for the patient with proper joins
        cursor.execute("""
            SELECT p.procedure_id, p.name, p.cost, 
                   ph.name as physician_name
            FROM undergoes u
            JOIN procedure p ON u.procedure_id = p.procedure_id
            JOIN physician ph ON u.emp_id = ph.emp_id
            WHERE u.patient_id = :1
            ORDER BY p.name
        """, [patient_id])

        procedures = []
        for row in cursor.fetchall():
            procedures.append({
                'procedure_id': row[0],
                'name': row[1],
                'cost': row[2],
                'physician_name': row[3]
            })

        cursor.close()
        connection.close()

        return jsonify({'procedures': procedures})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_available_procedures')
@login_required
def get_available_procedures():
    # Allow both admin and patient access
    if 'user_type' not in session or session['user_type'] not in ['admin', 'patient']:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT procedure_id, name, cost
            FROM procedure
            ORDER BY name
        """)

        procedures = []
        for row in cursor.fetchall():
            procedures.append({
                'procedure_id': row[0],
                'name': row[1],
                'cost': row[2]
            })

        cursor.close()
        connection.close()

        return jsonify({'procedures': procedures})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/add_patient_procedure', methods=['POST'])
@login_required
def add_patient_procedure():
    # Only allow admin access
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400

        patient_id = data.get('patient_id')
        procedure_id = data.get('procedure_id')
        emp_id = session.get('emp_id')

        if not all([patient_id, procedure_id, emp_id]):
            return jsonify({'error': 'Missing required fields'}), 400

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            # Add the procedure to undergoes table
            cursor.execute("""
                INSERT INTO undergoes (patient_id, procedure_id, emp_id)
                VALUES (:1, :2, :3)
            """, [patient_id, procedure_id, emp_id])

            connection.commit()
            return jsonify({'success': True, 'message': 'Procedure added successfully'})

        except cx_Oracle.Error as e:
            error_code = e.args[0].code
            if error_code == 2291:  # Foreign key violation
                return jsonify({'error': 'Invalid patient or procedure ID'}), 400
            elif error_code == 1:  # Unique constraint violation
                return jsonify({'error': 'This procedure has already been added for this patient'}), 400
            else:
                return jsonify({'error': f'Database error: {str(e)}'}), 500

        finally:
            cursor.close()
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/remove_patient_procedure', methods=['POST'])
@login_required
def remove_patient_procedure():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        procedure_id = data.get('procedure_id')

        if not patient_id or not procedure_id:
            return jsonify({'error': 'Missing required fields'}), 400

        connection = get_db_connection()
        cursor = connection.cursor()

        # Remove procedure from undergoes table
        cursor.execute("""
            DELETE FROM undergoes 
            WHERE patient_id = :1 
            AND procedure_id = :2
        """, [patient_id, procedure_id])

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_available_rooms')
@login_required
def get_available_rooms():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Get rooms that are not currently occupied
        cursor.execute("""
            SELECT r.room_no, r.type
            FROM room r
            LEFT JOIN stay s ON r.room_no = s.room_no AND s.discharge_date IS NULL
            WHERE s.room_no IS NULL
            ORDER BY r.room_no
        """)

        rooms = []
        for row in cursor.fetchall():
            rooms.append({
                'room_no': row[0],
                'type': row[1]
            })

        cursor.close()
        connection.close()

        return jsonify({'rooms': rooms})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_patient_accommodation')
def get_patient_accommodation():
    if 'user_type' not in session or session['user_type'] != 'patient':
        return jsonify({'error': 'Not logged in'}), 401
        
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Get the patient's ID from the session
        patient_id = session.get('patient_id')
        
        if not patient_id:
            return jsonify({'error': 'Patient ID not found'}), 400
            
        print(f"Fetching accommodation for patient_id: {patient_id}")  # Debug log
        
        # Query to get the patient's current room
        cursor.execute("""
            SELECT room_no 
            FROM stay 
            WHERE patient_id = :1
        """, [patient_id])
        
        result = cursor.fetchone()
        print(f"Query result: {result}")  # Debug log
        
        if result:
            accommodation = {
                'room_no': result[0]
            }
            return jsonify({'accommodation': accommodation})
        else:
            return jsonify({'accommodation': None})
            
    except Exception as e:
        print(f"Error in get_patient_accommodation: {str(e)}")
        return jsonify({'error': 'Error fetching accommodation details'}), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/get_all_accommodations')
@login_required
def get_all_accommodations():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)  # Reduced from 10 to 5
        offset = (page - 1) * per_page

        print(f"Fetching accommodations page {page} with {per_page} items per page")  # Debug log

        # First, get the total count using a simpler query
        try:
            cursor.execute("""
                SELECT /*+ FIRST_ROWS(1) */ COUNT(*) 
                FROM stay
            """)
            total_count = cursor.fetchone()[0]
            print(f"Total accommodations found: {total_count}")  # Debug log
        except Exception as e:
            print(f"Error getting total count: {str(e)}")  # Debug log
            return jsonify({'error': f'Error getting total count: {str(e)}'}), 500

        # Then, get the paginated results with a more efficient query
        try:
            cursor.execute("""
                SELECT /*+ FIRST_ROWS(5) */ 
                       s.patient_id, 
                       p.name as patient_name, 
                       s.room_no
                FROM stay s
                JOIN patient p ON s.patient_id = p.patient_id
                ORDER BY s.room_no
                OFFSET :1 ROWS FETCH NEXT :2 ROWS ONLY
            """, [offset, per_page])
            print("Main query executed successfully")  # Debug log
        except Exception as e:
            print(f"Error executing main query: {str(e)}")  # Debug log
            return jsonify({'error': f'Error executing query: {str(e)}'}), 500

        # Process results
        accommodations = []
        try:
            rows = cursor.fetchall()
            print(f"Fetched {len(rows)} rows")  # Debug log
            
            for row in rows:
                accommodations.append({
                    'patient_id': row[0],
                    'patient_name': row[1],
                    'room_no': row[2]
                })
        except Exception as e:
            print(f"Error processing results: {str(e)}")  # Debug log
            return jsonify({'error': f'Error processing results: {str(e)}'}), 500

        print(f"Successfully processed {len(accommodations)} accommodations")  # Debug log

        return jsonify({
            'accommodations': accommodations,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page
        })

    except Exception as e:
        print(f"General error in get_all_accommodations: {str(e)}")  # Debug log
        return jsonify({'error': f'General error: {str(e)}'}), 500

    finally:
        # Ensure proper cleanup
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                print(f"Error closing cursor: {str(e)}")  # Debug log
        if connection:
            try:
                connection.close()
            except Exception as e:
                print(f"Error closing connection: {str(e)}")  # Debug log

@app.route('/add_accommodation', methods=['POST'])
@login_required
def add_accommodation():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400

        patient_id = data.get('patient_id')
        room_no = data.get('room_no')

        if not all([patient_id, room_no]):
            return jsonify({'error': 'Missing required fields'}), 400

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            # Check if the room is already occupied
            cursor.execute("""
                SELECT COUNT(*) FROM stay 
                WHERE room_no = :1
            """, [room_no])
            
            if cursor.fetchone()[0] > 0:
                return jsonify({'error': 'Room is already occupied'}), 400

            # Add the accommodation
            cursor.execute("""
                INSERT INTO stay (patient_id, room_no)
                VALUES (:1, :2)
            """, [patient_id, room_no])

            connection.commit()
            return jsonify({'success': True, 'message': 'Accommodation added successfully'})

        except cx_Oracle.Error as e:
            error_code = e.args[0].code
            if error_code == 2291:  # Foreign key violation
                return jsonify({'error': 'Invalid patient ID'}), 400
            elif error_code == 1:  # Unique constraint violation
                return jsonify({'error': 'Patient already has an accommodation'}), 400
            else:
                return jsonify({'error': f'Database error: {str(e)}'}), 500

        finally:
            cursor.close()
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/discharge_patient', methods=['POST'])
@login_required
def discharge_patient():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400

        patient_id = data.get('patient_id')
        room_no = data.get('room_no')

        if not all([patient_id, room_no]):
            return jsonify({'error': 'Missing required fields'}), 400

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            # Remove the accommodation
            cursor.execute("""
                DELETE FROM stay 
                WHERE patient_id = :1 AND room_no = :2
            """, [patient_id, room_no])

            if cursor.rowcount == 0:
                return jsonify({'error': 'No accommodation found for this patient and room'}), 404

            connection.commit()
            return jsonify({'success': True, 'message': 'Accommodation removed successfully'})

        except cx_Oracle.Error as e:
            return jsonify({'error': f'Database error: {str(e)}'}), 500

        finally:
            cursor.close()
            connection.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
