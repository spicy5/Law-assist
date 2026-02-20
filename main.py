import base64
from flask import Flask, session, render_template, request, redirect, url_for, flash, Response
from app.connection import create_connection
from psycopg2.extras import DictCursor
import io

app = Flask(__name__)
app.secret_key = 'bojackhorseman07'


from datetime import datetime

def parse_datetime(value):
    if not value or value == 'None':
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@app.route('/')
#@app.route('/homepage')
def index():
    return render_template('homepage.html')
@app.route('/dashboard1')
def dashboard1():
    return render_template('client_dashboard.html')

@app.route('/dashboard3')
def dashboard3():
    session['username'] = 'admin'
    session['usertype'] = 'admin'
    return render_template('admin_dashboard.html')

@app.route('/dashboard2')
def dashboard2():
    if 'username' not in session:
        return redirect(url_for('login'))

    usertype = session.get('usertype')
    if usertype not in ('advocate', 'client'):
        flash("Invalid user type.")
        return redirect(url_for('login'))

    uploaded_by_id = session.get('advocate_id') if usertype == 'advocate' else session.get('client_id')

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT document_id, document_title FROM case_documents WHERE uploaded_by_id = %s',
                   (uploaded_by_id,))

    documents = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('advocate_dashboard.html', documents=documents)


@app.route('/profile')
def profile():
    return render_template('profile_update.html')
@app.route('/advdoc')
def advdoc():
    return render_template('adv_doc_cases.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        client_name = request.form['client_name']
        dob = request.form['dob']
        phone = request.form['phone']
        email = request.form['email']
        gender = request.form['gender']
        age = request.form['age']
        address = request.form['address']
        username = request.form['username']
        password = request.form['password']
        usertype = request.form['usertype']

        conn = create_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''INSERT INTO client_register
               (client_name, dob, phone, email, gender, age, address, username, password, usertype) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (client_name, dob, phone, email, gender, age, address, username, password, usertype)
        )

        cursor.execute(
            'INSERT INTO login(username, password,usertype) VALUES (%s, %s ,%s)',
            (username, password ,usertype)
        )

        conn.commit()
        cursor.close()
        conn.close()

        flash("Registration successfull!")
        return redirect(url_for('index'))

    return render_template('client_register.html')

@app.route('/advocate_register', methods=['GET', 'POST'])
def advocate_register():
    if request.method == 'POST':
        adv_name = request.form['adv_name']
        dob = request.form['dob']
        phone = request.form['phone']
        email = request.form['email']
        gender = request.form['gender']
        age = request.form['age']
        barid = request.form['barid']
        licnum = request.form['licnum']
        year = request.form['year']
        username = request.form['username']
        password = request.form['password']
        usertype = request.form['usertype']
        court_address = request.form['court_address']
        practice_division = request.form['practice_division']
        adv_photo_file = request.files['adv_photo']
        adv_photo = adv_photo_file.read() if adv_photo_file else None

        conn = create_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''INSERT INTO advocate_register 
               (adv_name, dob, phone, email, gender, age, barid , licnum, year, username, password, usertype, court_address, practice_division) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s , %s, %s, %s, %s)''',
            (adv_name, dob, phone, email, gender, age, barid , licnum , year , username, password, usertype, court_address, practice_division)
        )

        cursor.execute(
            'INSERT INTO login(username, password,usertype) VALUES (%s, %s, %s)',
            (username, password , usertype)
        )

        conn.commit()
        cursor.close()
        conn.close()

        flash("Registration successfull!")
        return redirect(url_for('index'))

    return render_template('advocate_register.html',)


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')
        usertype = request.form.get('usertype')


        if not all([username, password, usertype]):
            flash("All fields are required.")
            return redirect(url_for('login'))


        conn   = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1
              FROM login
             WHERE username = %s
               AND password = %s
               AND usertype = %s
        """, (username, password, usertype))
        valid = cursor.fetchone()
        cursor.close(); conn.close()

        if not valid:
            flash("Invalid credentials. Please try again.")
            return redirect(url_for('login'))


        session['username'] = username
        session['usertype'] = usertype

        if usertype == 'advocate':
            conn = create_connection()
            cur = conn.cursor()

            cur.execute("SELECT barid FROM advocate_register WHERE username = %s", (username,))
            barid_row = cur.fetchone()
            if barid_row:
                session['bar_id'] = barid_row[0]

            cur.close()
            conn.close()

        if username == 'admin' and password == 'admin':
            return render_template('admin_dashboard.html')

        if usertype == 'advocate':
            return redirect(url_for('dashboard2'))
        else:
            if usertype == 'client':
                return redirect(url_for('dashboard1'))


    return render_template('login07.html')


@app.route('/client_caseup', methods=['GET', 'POST'])
def client_caseup():
    if 'username' not in session or session['usertype'] != 'client':
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get form data
        case_title    = request.form['case_title']
        case_type     = request.form['case_type']
        case_desc     = request.form['case_desc']
        case_priority = request.form['case_priority']
        evidence_url  = request.form['evidence_url']
        adv_name      = request.form.get('adv_name')
        bar_id        = request.form.get('bar_id')
        username      = session['username']

        # Insert into DB
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO client_cases (
                case_title, case_type, case_desc,
                case_priority, evidence_url, adv_name, bar_id, username
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (case_title, case_type, case_desc, case_priority, evidence_url, adv_name, bar_id, username)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Case uploaded successfully!")
        return redirect(url_for('dashboard1'))

    else:

# GET method: prefill form

        bar_id = request.args.get('bar_id')
        adv_name = request.args.get('adv_name', '')

        return render_template('client_caseupload.html', adv_name=adv_name, bar_id=bar_id)


@app.route('/advocate_browse')
def advocate_browse():

    conn = create_connection()
    cur  = conn.cursor()

    cur.execute("""
        SELECT adv_id, adv_name, barid, licnum, year, phone, email ,court_address, practice_division, adv_photo
        FROM advocate_register
        ORDER BY adv_name
    """)
    advocates = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("advocate_browse.html", advocates=advocates)


@app.route('/edit_client_profile/<int:id>', methods=['GET', 'POST'])
def edit_client_profile(id):
    if 'username' not in session or session.get('usertype') != 'client':
        flash("Please log in as a client to view your profile.")
        return redirect(url_for('login'))

    username = session['username']


    conn = create_connection()
    cursor = conn.cursor()

    if request.method == 'POST':

        data = (
            request.form['client_name'],
            request.form['dob'],
            request.form['phone'],
            request.form['email'],
            request.form['gender'],
            request.form['age'],
            request.form['address'],
            username
        )
        cursor.execute(""" UPDATE client_register SET client_name = %s,
                       dob         = %s,
                       phone       = %s,
                       email       = %s,
                       gender      = %s,
                       age         = %s,
                       address     = %s
                 WHERE username     = %s
            """, data)
        conn.commit()
        cursor.close();
        conn.close()
        flash("Profile updated!")
        return redirect(url_for('dashboard1'))


    cursor.execute("""
            SELECT * FROM client_register
             WHERE username = %s
            """, (username,))
    client = cursor.fetchone()
    cursor.close();
    conn.close()

    if client is None:
        flash("No profile found for this user.")
        return redirect(url_for('dashboard1'))


    return render_template('profile_update.html', client=client)
@app.route('/logout')
def logout():

    return redirect(url_for('login'))

# nidhun bai
@app.route('/clientviewcase', methods=['GET'])
def clientviewcase():
    if 'username' not in session or session.get('usertype') != 'client':
        return redirect(url_for('login'))

    username = session['username']

    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM client_cases where username = %s", (username,))
    case = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('caseview.html', case=case)

@app.route('/advviewcase')
def advviewcase():
    if 'username' not in session or session.get('usertype') != 'advocate':
        return redirect(url_for('login'))

    if 'barid' not in session:
        username = session['username']
        conn = create_connection()
        cur = conn.cursor()
        cur.execute("SELECT barid FROM advocate_register WHERE username = %s", (username,))
        result = cur.fetchone()
        cur.close(); conn.close()

        if result:
            session['barid'] = result[0]
        else:
            flash("Bar ID not found; please log in again.")
            return redirect(url_for('logout'))

    barid = session['barid']

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM client_cases
        WHERE bar_id = %s AND NOT EXISTS (
            SELECT 1 FROM advocate_cases
            WHERE advocate_cases.client_case_id = client_cases.client_case_id
        )
    """, (barid,))
    cases = cur.fetchall()
    cur.close(); conn.close()

    return render_template('adv_caseview.html', cases=cases)




@app.route('/adv_own_viewcase')
def adv_own_viewcase():
    if 'username' not in session or session.get('usertype') != 'advocate':
        return redirect(url_for('login'))

    barid = session.get('barid')
    source = session.get('source')
    if not barid:
        flash("Bar ID missing; please log in again.")
        return redirect(url_for('logout'))

    conn = create_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM advocate_cases WHERE bar_id = %s AND source=%s",
        (barid,'advocate')
    )
    cases = cur.fetchall()
    cur.close(); conn.close()

    return render_template('adv_own_caseview.html', cases=cases)


@app.route('/adv_case_details/<int:id>', methods=['GET', 'POST'])
def adv_case_details(id):
    if 'username' not in session or session.get('usertype') != 'advocate':
        flash("Please log in as a client to view your profile.")
        return redirect(url_for('login'))

    conn = create_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        status = request.form['status']


        cursor.execute("""
            UPDATE client_cases
            SET status = %s, reviewed_at = NOW()
            WHERE client_case_id = %s
        """, (status, id))


        cursor.execute("""
            UPDATE advocate_cases
            SET status = %s
            WHERE client_case_id = %s
        """, (status, id))

        conn.commit()
        cursor.close()
        conn.close()
        flash("Status updated!")
        return redirect(url_for('dashboard2'))


    cursor.execute("SELECT * FROM client_cases WHERE client_case_id = %s", (id,))
    case = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('adv_case_details.html', case=case)


@app.route('/edit_client_details/<int:id>', methods=['GET', 'POST'])
def client_case_details(id):
    if 'username' not in session or session.get('usertype') != 'client':
        flash("Please log in as a client to view your profile.")
        return redirect(url_for('login'))

    username = session['username']
    conn = create_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        adv_name = request.form['adv_name']
        bar_id = request.form['bar_id']
        case_title = request.form['case_title']
        case_type = request.form['case_type']
        case_desc = request.form['case_desc']
        case_priority = request.form['case_priority']
        status = request.form['status']
        evidence_url=request.form['evidence_url']

        submitted_at = parse_datetime(request.form.get('submitted_at'))
        reviewed_at = parse_datetime(request.form.get('reviewed_at'))

        update_sql = """
            UPDATE client_cases
            SET 
                adv_name = %s,
                bar_id = %s,
                username = %s,
                case_title = %s,
                case_type = %s,
                case_desc = %s,
                case_priority = %s,
                status = %s,
                evidence_url = %s,
                submitted_at = %s,
                reviewed_at = %s
            WHERE client_case_id = %s AND username = %s
        """

        update_data = (
            adv_name,
            bar_id,
            username,
            case_title,
            case_type,
            case_desc,
            case_priority,
            status,
            evidence_url,
            submitted_at,
            reviewed_at,
            id,
            username
        )

        cur.execute(update_sql, update_data)
        conn.commit()
        cur.close()
        conn.close()

        flash("Case updated!")
        return redirect(url_for('dashboard1'))

    cur.execute("SELECT * FROM client_cases WHERE client_case_id = %s", (id,))
    client_case = cur.fetchone()
    cur.close()
    conn.close()

    if client_case is None:
        flash("No case found for this user.")
        return redirect(url_for('dashboard1'))

    return render_template('client_case_details.html', client_case=client_case)


@app.route('/edit_adv_profile', methods=['GET', 'POST'])
def edit_adv_profile():
    if 'username' not in session or session.get('usertype') != 'advocate':
        flash("Please log in as a client to view your profile.")
        return redirect(url_for('login'))

    username = session['username']


    conn = create_connection()
    cursor = conn.cursor()

    if request.method == 'POST':

        data = (
            request.form['adv_name'],
            request.form['dob'],
            request.form['phone'],
            request.form['email'],
            request.form['gender'],
            request.form['age'],
            request.form['barid'],
            request.form['licnum'],
            request.form['year'],
            request.form['court_address'],
            request.form['practice_division'],
            request.files['adv_photo'].read() if 'adv_photo' in request.files and request.files['adv_photo'].filename != '' else None,
            username
        )
        cursor.execute(""" UPDATE advocate_register SET adv_name = %s,
                       dob         = %s,
                       phone       = %s,
                       email       = %s,
                       gender      = %s,
                       age         = %s,
                       barid       = %s,
                       licnum        = %s,
                       year         = %s,
                       court_address = %s,
                       practice_division = %s,
                       adv_photo      = %s
                 WHERE username     = %s
            """, data)
        conn.commit()
        cursor.close();
        conn.close()
        flash("Profile updated!")
        return redirect(url_for('dashboard2'))


    cursor.execute("""
            SELECT * FROM advocate_register
             WHERE username = %s
            """, (username,))
    advocate = cursor.fetchone()
    cursor.close();
    conn.close()

    if advocate is None:
        flash("No profile found for this user.")
        return redirect(url_for('dashboard2'))


    return render_template('adv_profile_update.html', advocate=advocate)

@app.route('/handle_case_action/<int:id>/<action>', methods=['GET'])
def handle_case_action(id, action):
    if 'username' not in session or session.get('usertype') != 'advocate':
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    conn = create_connection()
    cursor = conn.cursor()


    cursor.execute("SELECT * FROM client_cases WHERE client_case_id = %s", (id,))
    case = cursor.fetchone()

    if not case:
        flash("Case not found.")
        return redirect(url_for('dashboard2'))

    if action == 'accept':

        cursor.execute("""
            INSERT INTO advocate_cases (
                client_case_id, bar_id, case_title,
                case_type, case_desc, case_priority,
                status, accepted_at ,evidence_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s ,%s)
        """, (
            case[0],
            case[2],
            case[4],
            case[5],
            case[6],
            case[7],
            case[8],
            case[10],
            case[11]
        ))

        flash("Case accepted and assigned to you.")

    elif action == 'reject':
        flash("Case rejected.")

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('adv_case_details', id=id))

@app.route('/adv_pending_cases')
def adv_pending_cases():

    if 'username' not in session or session.get('usertype') != 'advocate':
        return redirect(url_for('login'))

    bar_id = session.get('bar_id')
    if not bar_id:
        flash("Advocate ID missing; please log in again.")
        return redirect(url_for('logout'))

    conn = create_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM advocate_cases WHERE bar_id = %s  AND status = 'pending'",
        (bar_id,)
    )
    advocate = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('adv_pending_case.html', advocate=advocate)

@app.route('/adv_ongoing_cases')
def adv_ongoing_cases():

    if 'username' not in session or session.get('usertype') != 'advocate':
        return redirect(url_for('login'))

    bar_id = session.get('bar_id')
    if not bar_id:
        flash("Advocate ID missing; please log in again.")
        return redirect(url_for('logout'))

    conn = create_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM advocate_cases WHERE bar_id = %s  AND status = 'ongoing'",
        (bar_id,)
    )
    advocate = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('adv_ongoing_case.html', advocate=advocate)

@app.route('/adv_closed_cases')
def adv_closed_cases():

    if 'username' not in session or session.get('usertype') != 'advocate':
        return redirect(url_for('login'))

    bar_id = session.get('bar_id')
    if not bar_id:
        flash("Advocate ID missing; please log in again.")
        return redirect(url_for('logout'))

    conn = create_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM advocate_cases WHERE bar_id = %s  AND status = 'closed'",
        (bar_id,)
    )
    advocate = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('adv_closed_case.html', advocate=advocate)

@app.route('/adv_doc_cases')
def adv_doc_cases():

    if 'username' not in session or session.get('usertype') != 'advocate':
        return redirect(url_for('login'))

    bar_id = session.get('bar_id')
    if not bar_id:
        flash("Advocate ID missing; please log in again.")
        return redirect(url_for('logout'))

    conn = create_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM advocate_cases WHERE bar_id = %s",
        (bar_id,)
    )
    advocate = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('adv_doc_cases.html', advocate=advocate)

@app.route('/adv_caseup', methods=['GET', 'POST'])
def adv_caseup():
    if 'username' not in session or session['usertype'] != 'advocate':
        return redirect(url_for('login'))

    username = session['username']

    if request.method == 'POST':
        source = request.form['source']
        case_title = request.form['case_title']
        case_type = request.form['case_type']
        case_desc = request.form['case_desc']
        case_priority = request.form['case_priority']
        evidence_url = request.form['evidence_url']


        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT barid FROM advocate_register WHERE username = %s", (username,))
        result = cursor.fetchone()

        bar_id = result[0] if result else ""

        cursor.execute(
            '''INSERT INTO advocate_cases
               (source, case_title, case_type, case_desc,
                case_priority, evidence_url, bar_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (source, case_title, case_type, case_desc, case_priority, evidence_url, bar_id)
        )

        conn.commit()
        cursor.close()
        conn.close()

        flash("Case uploaded successfully!")
        return redirect(url_for('dashboard2'))

    else:

        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT barid FROM advocate_register WHERE username = %s", (username,))
        result = cursor.fetchone()
        conn.close()
        session['source'] = 'advocate'
        bar_id = result[0] if result else ""

        return render_template('advocate_caseupload.html', bar_id=bar_id)


@app.route('/adv_doc_up/<int:case_id>', methods=['GET', 'POST'])
def adv_doc_up(case_id):

    if 'username' not in session or session['usertype'] not in ('advocate', 'client'):
        return redirect(url_for('login'))


    if request.method == 'POST':
        case_type        = request.form['case_type']
        document_title   = request.form['document_title']
        document_url     = request.form['document_url']
        file_type        = request.form['file_type']
        is_confidential  = request.form['is_confidential']

        if session['usertype'] == 'client':
            client_case_id = case_id
            adv_case_id = None
            uploaded_by_id = session.get('client_id')
        else:
            adv_case_id = case_id
            client_case_id = None
            uploaded_by_id = session.get('advocate_id')

        conn   = create_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''
            INSERT INTO case_documents
                (case_type, client_case_id, adv_case_id, uploaded_by_id,
                 document_title, document_url, file_type, is_confidential)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (case_type, client_case_id, adv_case_id, uploaded_by_id,
             document_title, document_url, file_type, is_confidential)
        )

        conn.commit()
        cursor.close()
        conn.close()
        flash("Document uploaded successfully!")
        return redirect(url_for('dashboard2'))


    return render_template('adv_doc_upload.html',
                           case_id=case_id,
                           usertype=session['usertype'])

@app.route('/adv_replace_cases')
def adv_replace_cases():
    if 'username' not in session or session.get('usertype') != 'advocate':
        return redirect(url_for('login'))

    bar_id = session.get('bar_id')
    if not bar_id:
        flash("Advocate ID missing; please log in again.")
        return redirect(url_for('logout'))

    conn = create_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT cd.*
        FROM case_documents cd
        JOIN advocate_cases ac ON cd.adv_case_id::BIGINT = ac.adv_case_id
        WHERE ac.bar_id = %s
    """, (bar_id,))

    documents = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('adv_replace_cases.html', documents=documents)

@app.route('/adv_replace_doc/<int:doc_id>', methods=['GET', 'POST'])
def adv_replace_doc(doc_id):
    if 'username' not in session or session.get('usertype') != 'advocate':
        return redirect(url_for('login'))

    conn = create_connection()
    cur = conn.cursor()

    # Fetch the document details
    cur.execute("""
        SELECT document_title, document_url, file_type, is_confidential
        FROM case_documents
        WHERE document_id = %s
    """, (doc_id,))
    document = cur.fetchone()

    if not document:
        cur.close()
        conn.close()
        flash("Document not found.")
        return redirect(url_for('adv_replace_cases'))

    if request.method == 'POST':
        new_title = request.form['document_title']
        new_url = request.form['document_url']
        new_file_type = request.form['file_type']
        new_conf = request.form['is_confidential']

        cur.execute("""
            UPDATE case_documents
            SET document_title = %s, document_url = %s,
                file_type = %s, is_confidential = %s
            WHERE document_id = %s
        """, (new_title, new_url, new_file_type, new_conf, doc_id))

        conn.commit()
        cur.close()
        conn.close()
        flash("Document updated successfully.")
        return redirect(url_for('adv_replace_cases'))

    cur.close()
    conn.close()
    return render_template('adv_doc_replace.html', document=document, doc_id=doc_id, usertype=session['usertype'])

@app.route('/delete_adv_document/<int:doc_id>', methods=['POST'])
def delete_adv_document(doc_id):
    if 'username' not in session or session.get('usertype') != 'advocate':
        return redirect(url_for('login'))

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM case_documents WHERE document_id = %s", (doc_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Document deleted successfully.")
    return redirect(url_for('adv_replace_cases'))

@app.route('/client_doc_cases')
def client_doc_cases():

    if 'username' not in session or session.get('usertype') != 'client':
        return redirect(url_for('login'))

    username = session.get('username')
    if not username:
        flash("Client ID missing; please log in again.")
        return redirect(url_for('logout'))

    conn = create_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM client_cases WHERE username = %s",
        (username,)
    )
    client = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('client_doc_cases.html', client=client)

@app.route('/client_doc_up/<int:case_id>', methods=['GET', 'POST'])
def client_doc_up(case_id):

    if 'username' not in session or session['usertype'] not in ('advocate', 'client'):
        return redirect(url_for('login'))


    if request.method == 'POST':
        case_type        = request.form['case_type']
        document_title   = request.form['document_title']
        document_url     = request.form['document_url']
        file_type        = request.form['file_type']
        is_confidential  = request.form['is_confidential']

        if session['usertype'] == 'client':
            client_case_id = case_id
            adv_case_id = None
            uploaded_by_id = session.get('client_id')
        else:
            adv_case_id = case_id
            client_case_id = None
            uploaded_by_id = session.get('advocate_id')

        conn   = create_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''
            INSERT INTO case_documents
                (case_type, client_case_id, adv_case_id, uploaded_by_id,
                 document_title, document_url, file_type, is_confidential)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (case_type, client_case_id, adv_case_id, uploaded_by_id,
             document_title, document_url, file_type, is_confidential)
        )

        conn.commit()
        cursor.close()
        conn.close()
        flash("Document uploaded successfully!")
        return redirect(url_for('dashboard1'))


    return render_template('client_doc_upload.html',
                           case_id=case_id,
                           usertype=session['usertype'])

@app.route('/client_replace_cases')
def client_replace_cases():
    print("Session:", session)

    if 'username' not in session:
        flash("You must be logged in.")
        return redirect(url_for('login'))

    if session.get('usertype') != 'client':
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    username = session.get('username')
    if not username:
        flash("User ID missing; please log in again.")
        return redirect(url_for('logout'))

    conn = create_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT cd.*
        FROM case_documents cd
        JOIN client_cases ac ON cd.client_case_id::BIGINT = ac.client_case_id
        WHERE ac.username = %s
    """, (username,))

    documents = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('client_replace_cases.html', documents=documents)

@app.route('/client_replace_doc/<int:doc_id>', methods=['GET', 'POST'])
def client_replace_doc(doc_id):
    if 'username' not in session or session.get('usertype') != 'client':
        return redirect(url_for('login'))

    conn = create_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT document_title, document_url, file_type, is_confidential
        FROM case_documents
        WHERE document_id = %s
    """, (doc_id,))
    document = cur.fetchone()

    if not document:
        cur.close()
        conn.close()
        flash("Document not found.")
        return redirect(url_for('client_replace_cases'))

    if request.method == 'POST':
        new_title = request.form['document_title']
        new_url = request.form['document_url']
        new_file_type = request.form['file_type']
        new_conf = request.form['is_confidential']

        cur.execute("""
            UPDATE case_documents
            SET document_title = %s, document_url = %s,
                file_type = %s, is_confidential = %s
            WHERE document_id = %s
        """, (new_title, new_url, new_file_type, new_conf, doc_id))

        conn.commit()
        cur.close()
        conn.close()
        flash("Document updated successfully.")
        return redirect(url_for('client_replace_cases'))

    cur.close()
    conn.close()
    return render_template('client_doc_replace.html', document=document, doc_id=doc_id, usertype=session['usertype'])

@app.route('/delete_client_document/<int:doc_id>', methods=['POST'])
def delete_client_document(doc_id):
    if 'username' not in session or session.get('usertype') != 'client':
        return redirect(url_for('login'))

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM case_documents WHERE document_id = %s", (doc_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Document deleted successfully.")
    return redirect(url_for('client_replace_cases'))

@app.route('/delete_client_case/<int:case_id>', methods=['POST'])
def delete_client_case(case_id):
    if 'username' not in session or session.get('usertype') != 'client':
        return redirect(url_for('login'))

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM client_cases WHERE client_case_id = %s", (case_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Case deleted successfully.")
    return redirect(url_for('clientviewcase'))

@app.route('/delete_adv_case/<int:case_id>', methods=['POST'])
def delete_adv_case(case_id):
    if 'username' not in session or session.get('usertype') != 'advocate':
        return redirect(url_for('login'))

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM advocate_cases WHERE adv_case_id = %s", (case_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Case deleted successfully.")
    return redirect(url_for('adv_own_viewcase'))

@app.route('/admin_adv_details')
def admin_adv_details():

    if 'username' not in session or session.get('username') != 'admin':
        return redirect(url_for('login'))


    conn = create_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM advocate_register WHERE usertype = 'advocate'")
    adv = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_adv_view.html', adv=adv)

@app.route('/delete_admin_adv_det/<int:adv_id>', methods=['POST'])
def delete_admin_adv_det(adv_id):
    if 'username' not in session or session.get('username') != 'admin':
        return redirect(url_for('login'))

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM advocate_register WHERE adv_id = %s", (adv_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Advocate deleted successfully.")
    return redirect(url_for('admin_adv_details'))

@app.route('/admin_client_details')
def admin_client_details():

    if 'username' not in session or session.get('username') != 'admin':
        return redirect(url_for('login'))


    conn = create_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM client_register WHERE usertype = 'client'")
    client = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_client_view.html', client=client)

@app.route('/delete_admin_client_det/<int:client_id>', methods=['POST'])
def delete_admin_client_det(client_id):
    if 'username' not in session or session.get('username') != 'admin':
        return redirect(url_for('login'))

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM client_register WHERE client_id = %s", (client_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Client deleted successfully.")
    return redirect(url_for('admin_client_details'))

@app.route('/admin_adv_cases')
def admin_adv_cases():

    if 'username' not in session or session.get('username') != 'admin':
        return redirect(url_for('login'))

    conn = create_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM advocate_cases")
    adv = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_adv_caseview.html', adv=adv)

@app.route('/delete_admin_advcase/<int:adv_case_id>', methods=['POST'])
def delete_admin_advcase(adv_case_id):
    if 'username' not in session or session.get('username') != 'admin':
        return redirect(url_for('login'))

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM advocate_cases WHERE adv_case_id = %s", (adv_case_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Advocate Case deleted successfully.")
    return redirect(url_for('admin_adv_cases'))

@app.route('/admin_client_cases')
def admin_client_cases():

    if 'username' not in session or session.get('username') != 'admin':
        return redirect(url_for('login'))

    conn = create_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM client_cases")
    client = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_client_caseview.html', client=client)

@app.route('/delete_admin_clientcase/<int:client_case_id>', methods=['POST'])
def delete_admin_clientcase(client_case_id):
    if 'username' not in session or session.get('username') != 'admin':
        return redirect(url_for('login'))

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM client_cases WHERE client_case_id = %s", (client_case_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Advocate Case deleted successfully.")
    return redirect(url_for('admin_client_cases'))

@app.route('/admin_adv_documents')
def admin_adv_documents():

    if 'username' not in session or session.get('username') != 'admin':
        return redirect(url_for('login'))

    conn = create_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM case_documents WHERE case_type='advocate'")
    adv = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_adv_docview.html', adv=adv)

@app.route('/delete_admin_advdoc/<int:document_id>', methods=['POST'])
def delete_admin_advdoc(document_id):
    if 'username' not in session or session.get('username') != 'admin':
        return redirect(url_for('login'))

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM case_documents WHERE document_id = %s", (document_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Advocate Case Document deleted successfully.")
    return redirect(url_for('admin_adv_documents'))

@app.route('/admin_client_documents')
def admin_client_documents():

    if 'username' not in session or session.get('username') != 'admin':
        return redirect(url_for('login'))

    conn = create_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM case_documents WHERE case_type='client'")
    client = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_client_docview.html', client=client)

@app.route('/delete_admin_clientdoc/<int:document_id>', methods=['POST'])
def delete_admin_clientdoc(document_id):
    if 'username' not in session or session.get('username') != 'admin':
        return redirect(url_for('login'))

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM case_documents WHERE document_id = %s", (document_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Client Case Document deleted successfully.")
    return redirect(url_for('admin_client_documents'))

@app.route('/advocate_photo')
def advocate_photo():
    if 'username' not in session or session.get('usertype') != 'advocate':
        return '', 403

    username = session['username']
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT adv_photo FROM advocate_register WHERE username = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result and result[0]:
        return Response(result[0], mimetype='image/jpeg')
    else:

        return redirect(url_for('static', filename='img/default_avatar.jpg'))


@app.route('/advocate_photo_by_barid/<barid>')
def advocate_photo_by_barid(barid):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT adv_photo FROM advocate_register WHERE barid = %s", (barid,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row and row[0]:
        return Response(row[0], mimetype='image/jpeg')
    else:

        return redirect(url_for('static', filename='img/default_avatar.jpg'))


if __name__ == '__main__':
    app.run(debug=True)
