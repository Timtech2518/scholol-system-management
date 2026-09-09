from flask import Flask, render_template, request, redirect, send_from_directory, url_for, session
from werkzeug.utils import secure_filename
import os
from functools import wraps
from datetime import datetime
import mysql.connector


# ==========================================
# FLASK APP
# ==========================================

app = Flask(__name__)

app.secret_key = "stgabriel_secret_key"

app.config["UPLOAD_FOLDER"] = "uploads"

# Make sure uploads folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# ==========================================
# ADMIN PROTECTION
# ==========================================

def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if session.get("user_role") != "admin":
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


# ==========================================
# CONNECT FLASK TO MYSQL
# ==========================================

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Timtech@25",
    database="school_management"
)


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():

    return render_template("index.html")


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM users
            WHERE email = %s
            AND password = %s
        """, (email, password))

        user = cursor.fetchone()

        cursor.close()

        if user:

            session["user_id"] = user["id"]
            session["user_role"] = user["role"]
            session["user_name"] = user["full_name"]

            if user["role"] == "admin":

                return redirect(url_for("admin_dashboard"))

            elif user["role"] == "student":

                session["student_id"] = user["student_id"]

                return redirect(
                    url_for("student_dashboard")
                )

        return "Invalid email or password"

    return render_template("login.html")


# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.route("/admin")
@admin_required
def admin_dashboard():

    cursor = db.cursor(dictionary=True)

    # ==========================================
    # UNREAD CONTACT MESSAGES
    # ==========================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM contact_messages
        WHERE status = 'Unread'
    """)

    unread_messages = cursor.fetchone()["total"]


    # ==========================================
    # APPLICATION COUNTS
    # ==========================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM admissions
    """)

    total_applications = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM admissions
        WHERE status = 'Pending'
    """)

    pending_applications = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM admissions
        WHERE status = 'Approved'
    """)

    approved_applications = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM admissions
        WHERE status = 'Rejected'
    """)

    rejected_applications = cursor.fetchone()["total"]


    # ==========================================
    # RECENT APPLICATIONS
    # ==========================================

    cursor.execute("""
        SELECT
            id,
            full_name,
            intended_class,
            status,
            admission_number
        FROM admissions
        ORDER BY id DESC
        LIMIT 10
    """)

    applications = cursor.fetchall()


    # ==========================================
    # TOTAL STUDENTS
    # ==========================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM students
        WHERE status = 'Active'
    """)

    total_students = cursor.fetchone()["total"]


    # ==========================================
    # TOTAL TEACHERS
    # ==========================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM teachers
        WHERE status = 'Active'
    """)

    total_teachers = cursor.fetchone()["total"]


    # ==========================================
    # TOTAL CLASSES
    # ==========================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM classes
        WHERE status = 'Active'
    """)

    total_classes = cursor.fetchone()["total"]


    # ==========================================
    # TOTAL SUBJECTS
    # ==========================================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM subjects
        WHERE status = 'Active'
    """)

    total_subjects = cursor.fetchone()["total"]


    cursor.close()


    return render_template(
        "admin_dashboard.html",

        total_applications=total_applications,
        pending_applications=pending_applications,
        approved_applications=approved_applications,
        rejected_applications=rejected_applications,

        applications=applications,

        total_students=total_students,
        total_teachers=total_teachers,
        total_classes=total_classes,
        total_subjects=total_subjects,

        unread_messages=unread_messages
    )


# ==========================================
# VIEW ALL ADMISSIONS
# ==========================================

@app.route("/admin/admissions")
@admin_required
def admissions():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM admissions
        ORDER BY id DESC
    """)

    admission_list = cursor.fetchall()

    cursor.close()

    return render_template(
        "admissions.html",
        admissions=admission_list
    )


# ==========================================
# ADMIN APPLICATION DETAILS
# ==========================================

@app.route("/admin/application/<int:application_id>")
@admin_required
def view_application(application_id):

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM admissions
        WHERE id = %s
        """,
        (application_id,)
    )

    application = cursor.fetchone()

    cursor.close()

    if not application:

        return "Application not found.", 404

    return render_template(
        "application_details.html",
        application=application
    )


# ==========================================
# APPROVE / REJECT APPLICATION
# ==========================================

@app.route("/admin/application/<int:application_id>/status/<status>")
@admin_required
def update_application_status(application_id, status):

    if status not in ["Approved", "Rejected"]:

        return "Invalid status.", 400

    cursor = db.cursor(dictionary=True)


    # ==========================================
    # GET APPLICATION
    # ==========================================

    cursor.execute(
        """
        SELECT *
        FROM admissions
        WHERE id = %s
        """,
        (application_id,)
    )

    application = cursor.fetchone()


    if not application:

        cursor.close()

        return "Application not found.", 404


    # ==========================================
    # APPROVE APPLICATION
    # ==========================================

    if status == "Approved":

        if not application["admission_number"]:

            current_year = datetime.now().year

            admission_number = (
                f"STG-{current_year}-{application_id:04d}"
            )

        else:

            admission_number = application["admission_number"]


        # ==========================================
        # UPDATE ADMISSION
        # ==========================================

        cursor.execute(
            """
            UPDATE admissions
            SET
                status = %s,
                admission_number = %s
            WHERE id = %s
            """,
            (
                "Approved",
                admission_number,
                application_id
            )
        )


        # ==========================================
        # CHECK IF STUDENT ALREADY EXISTS
        # ==========================================

        cursor.execute(
            """
            SELECT id
            FROM students
            WHERE admission_number = %s
            """,
            (admission_number,)
        )

        existing_student = cursor.fetchone()


        # ==========================================
        # CREATE STUDENT AUTOMATICALLY
        # ==========================================

        if not existing_student:

            cursor.execute(
                """
                INSERT INTO students (
                    admission_number,
                    full_name,
                    date_of_birth,
                    gender,
                    nationality,
                    state_of_origin,
                    lga,
                    home_address,
                    parent_name,
                    parent_phone,
                    parent_email,
                    class_name,
                    admission_date,
                    status
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    CURDATE(), %s
                )
                """,
                (
                    admission_number,
                    application["full_name"],
                    application["date_of_birth"],
                    application["gender"],
                    application["nationality"],
                    application["state_of_origin"],
                    application["lga"],
                    application["home_address"],
                    application["parent_name"],
                    application["parent_phone"],
                    application["parent_email"],
                    application["intended_class"],
                    "Active"
                )
            )


        db.commit()

        cursor.close()

        return redirect(
            url_for(
                "view_application",
                application_id=application_id
            )
        )


    # ==========================================
    # REJECT APPLICATION
    # ==========================================

    elif status == "Rejected":

        cursor.execute(
            """
            UPDATE admissions
            SET status = %s
            WHERE id = %s
            """,
            (
                "Rejected",
                application_id
            )
        )

        db.commit()

        cursor.close()

        return redirect(
            url_for(
                "view_application",
                application_id=application_id
            )
        )


# ==========================================
# VIEW UPLOADED FILES
# ==========================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ==========================================
# ADMISSION APPLICATION
# ==========================================

@app.route("/admission", methods=["GET", "POST"])
def admission():

    if request.method == "POST":

        # ==========================================
        # APPLICANT INFORMATION
        # ==========================================

        full_name = request.form["full_name"]

        date_of_birth = request.form["date_of_birth"]

        gender = request.form["gender"]

        nationality = request.form["nationality"]

        state_of_origin = request.form["state_of_origin"]

        lga = request.form["lga"]

        home_address = request.form["home_address"]


        # ==========================================
        # PARENT / GUARDIAN INFORMATION
        # ==========================================

        guardian_name = request.form["guardian_name"]

        relationship = request.form["relationship"]

        guardian_phone = request.form["guardian_phone"]

        guardian_email = request.form.get("guardian_email")

        guardian_address = request.form["guardian_address"]


        # ==========================================
        # ACADEMIC INFORMATION
        # ==========================================

        previous_school = request.form["previous_school"]

        last_class = request.form["last_class"]

        intended_class = request.form["intended_class"]

        previous_result = request.form.get(
            "previous_result"
        )


        # ==========================================
        # UPLOADED DOCUMENTS
        # ==========================================

        passport_photo = request.files["passport_photo"]

        birth_certificate = request.files["birth_certificate"]

        previous_report = request.files["previous_report"]

        transfer_certificate = request.files.get(
            "transfer_certificate"
        )


        # ==========================================
        # SAVE PASSPORT PHOTO
        # ==========================================

        passport_filename = secure_filename(
            passport_photo.filename
        )

        passport_photo.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                passport_filename
            )
        )


        # ==========================================
        # SAVE BIRTH CERTIFICATE
        # ==========================================

        birth_filename = secure_filename(
            birth_certificate.filename
        )

        birth_certificate.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                birth_filename
            )
        )


        # ==========================================
        # SAVE PREVIOUS REPORT
        # ==========================================

        report_filename = secure_filename(
            previous_report.filename
        )

        previous_report.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                report_filename
            )
        )


        # ==========================================
        # SAVE TRANSFER CERTIFICATE
        # ==========================================

        transfer_filename = None

        if (
            transfer_certificate
            and transfer_certificate.filename
        ):

            transfer_filename = secure_filename(
                transfer_certificate.filename
            )

            transfer_certificate.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    transfer_filename
                )
            )


        # ==========================================
        # INSERT APPLICATION
        # ==========================================

        cursor = db.cursor()

        sql = """
        INSERT INTO admissions (
            full_name,
            date_of_birth,
            gender,
            nationality,
            state_of_origin,
            lga,
            home_address,
            parent_name,
            relationship,
            parent_phone,
            parent_email,
            parent_address,
            previous_school,
            last_class,
            intended_class,
            previous_result,
            passport_photo,
            birth_certificate,
            previous_report,
            transfer_certificate
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        """

        values = (
            full_name,
            date_of_birth,
            gender,
            nationality,
            state_of_origin,
            lga,
            home_address,

            guardian_name,
            relationship,
            guardian_phone,
            guardian_email,
            guardian_address,

            previous_school,
            last_class,
            intended_class,
            previous_result,

            passport_filename,
            birth_filename,
            report_filename,
            transfer_filename
        )

        cursor.execute(sql, values)

        db.commit()

        cursor.close()

        return "Application submitted successfully!"

    return render_template("admission.html")


# ==========================================
# VIEW ALL STUDENTS
# ==========================================

@app.route("/admin/students")
@admin_required
def students():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM students
        ORDER BY id DESC
    """)

    student_list = cursor.fetchall()

    cursor.close()

    return render_template(
        "students.html",
        students=student_list
    )


# ==========================================
# VIEW SINGLE STUDENT
# ==========================================

@app.route("/admin/student/<int:student_id>")
@admin_required
def view_student(student_id):

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM students
        WHERE id = %s
        """,
        (student_id,)
    )

    student = cursor.fetchone()

    cursor.close()

    if not student:

        return "Student not found.", 404

    return render_template(
        "student_details.html",
        student=student
    )


# ==========================================
# VIEW ALL TEACHERS
# ==========================================

@app.route("/admin/teachers")
@admin_required
def teachers():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM teachers
        ORDER BY id DESC
    """)

    teacher_list = cursor.fetchall()

    cursor.close()

    return render_template(
        "teachers.html",
        teachers=teacher_list
    )


# ==========================================
# ADD TEACHER
# ==========================================

@app.route("/admin/teachers/add", methods=["GET", "POST"])
@admin_required
def add_teacher():

    if request.method == "POST":

        full_name = request.form["full_name"]

        email = request.form.get("email")

        phone = request.form.get("phone")

        gender = request.form.get("gender")

        subject = request.form.get("subject")

        class_name = request.form.get("class_name")

        qualification = request.form.get("qualification")

        address = request.form.get("address")


        cursor = db.cursor(dictionary=True)


        # ==========================================
        # GET LAST TEACHER ID
        # ==========================================

        cursor.execute("""
            SELECT teacher_id
            FROM teachers
            WHERE teacher_id LIKE 'TCH-%'
            ORDER BY id DESC
            LIMIT 1
        """)

        last_teacher = cursor.fetchone()


        # ==========================================
        # GENERATE NEW TEACHER ID
        # ==========================================

        if last_teacher and last_teacher["teacher_id"]:

            last_id = last_teacher["teacher_id"]

            try:

                number = int(
                    last_id.replace("TCH-", "")
                )

                new_number = number + 1

            except ValueError:

                new_number = 1

        else:

            new_number = 1


        teacher_id = f"TCH-{new_number:04d}"


        # ==========================================
        # INSERT TEACHER
        # ==========================================

        cursor.execute("""
            INSERT INTO teachers (
                teacher_id,
                full_name,
                email,
                phone,
                gender,
                subject,
                class_name,
                qualification,
                address
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """, (
            teacher_id,
            full_name,
            email,
            phone,
            gender,
            subject,
            class_name,
            qualification,
            address
        ))

        db.commit()

        cursor.close()

        return redirect(
            url_for("teachers")
        )

    return render_template(
        "add_teacher.html"
    )


# ==========================================
# VIEW ALL CLASSES
# ==========================================

@app.route("/admin/classes")
@admin_required
def classes():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM classes
        ORDER BY id ASC
    """)

    class_list = cursor.fetchall()

    cursor.close()

    return render_template(
        "classes.html",
        classes=class_list
    )


# ==========================================
# ADD NEW CLASS
# ==========================================

@app.route("/admin/classes/add", methods=["GET", "POST"])
@admin_required
def add_class():

    cursor = db.cursor(dictionary=True)


    # ==========================================
    # GET ACTIVE TEACHERS
    # ==========================================

    cursor.execute("""
        SELECT
            id,
            full_name
        FROM teachers
        WHERE status = 'Active'
        ORDER BY full_name ASC
    """)

    teachers = cursor.fetchall()


    # ==========================================
    # SAVE CLASS
    # ==========================================

    if request.method == "POST":

        class_name = request.form["class_name"]

        class_level = request.form["class_level"]

        class_teacher = request.form.get(
            "class_teacher"
        )

        description = request.form.get(
            "description"
        )

        status = request.form["status"]


        cursor.execute("""
            INSERT INTO classes (
                class_name,
                class_level,
                class_teacher,
                description,
                status
            )
            VALUES (
                %s, %s, %s, %s, %s
            )
        """, (
            class_name,
            class_level,
            class_teacher,
            description,
            status
        ))

        db.commit()

        cursor.close()

        return redirect(
            url_for("classes")
        )

    cursor.close()

    return render_template(
        "add_class.html",
        teachers=teachers
    )


# ==========================================
# VIEW ALL SUBJECTS
# ==========================================

@app.route("/admin/subjects")
@admin_required
def subjects():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM subjects
        ORDER BY id ASC
    """)

    subject_list = cursor.fetchall()

    cursor.close()

    return render_template(
        "subjects.html",
        subjects=subject_list
    )


# ==========================================
# ADD SUBJECT
# ==========================================

@app.route("/admin/subjects/add", methods=["GET", "POST"])
@admin_required
def add_subject():

    if request.method == "POST":

        subject_code = request.form["subject_code"]

        subject_name = request.form["subject_name"]

        status = request.form["status"]

        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO subjects (
                subject_code,
                subject_name,
                status
            )
            VALUES (%s, %s, %s)
        """, (
            subject_code,
            subject_name,
            status
        ))

        db.commit()

        cursor.close()

        return redirect(
            url_for("subjects")
        )

    return render_template(
        "add_subject.html"
    )


# ==========================================
# STUDENT RESULTS
# ==========================================

@app.route("/admin/results")
@admin_required
def student_results():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            sr.*,
            s.full_name,
            s.admission_number,
            sub.subject_name,
            sub.subject_code
        FROM student_results sr
        JOIN students s
            ON sr.student_id = s.id
        JOIN subjects sub
            ON sr.subject_id = sub.id
        ORDER BY sr.id DESC
    """)

    results = cursor.fetchall()

    cursor.close()

    return render_template(
        "student_results.html",
        results=results
    )


# ==========================================
# ADD STUDENT RESULT
# ==========================================

@app.route("/admin/results/add", methods=["GET", "POST"])
@admin_required
def add_result():

    cursor = db.cursor(dictionary=True)


    # ==========================================
    # GET STUDENTS
    # ==========================================

    cursor.execute("""
        SELECT
            id,
            admission_number,
            full_name
        FROM students
        ORDER BY full_name ASC
    """)

    students = cursor.fetchall()


    # ==========================================
    # GET SUBJECTS
    # ==========================================

    cursor.execute("""
        SELECT
            id,
            subject_code,
            subject_name
        FROM subjects
        ORDER BY subject_name ASC
    """)

    subjects = cursor.fetchall()


    # ==========================================
    # SAVE RESULT
    # ==========================================

    if request.method == "POST":

        student_id = request.form["student_id"]

        subject_id = request.form["subject_id"]

        session = request.form["session"]

        term = request.form["term"]

        ca_score = float(
            request.form["ca_score"]
        )

        exam_score = float(
            request.form["exam_score"]
        )


        # ==========================================
        # CALCULATE TOTAL
        # ==========================================

        total_score = (
            ca_score + exam_score
        )


        # ==========================================
        # CALCULATE GRADE
        # ==========================================

        if total_score >= 75:

            grade = "A"
            remark = "Excellent"

        elif total_score >= 65:

            grade = "B"
            remark = "Very Good"

        elif total_score >= 55:

            grade = "C"
            remark = "Good"

        elif total_score >= 45:

            grade = "D"
            remark = "Pass"

        elif total_score >= 40:

            grade = "E"
            remark = "Fair"

        else:

            grade = "F"
            remark = "Fail"


        # ==========================================
        # INSERT RESULT
        # ==========================================

        cursor.execute(
            """
            INSERT INTO student_results (
                student_id,
                subject_id,
                session,
                term,
                ca_score,
                exam_score,
                total_score,
                grade,
                remark
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                student_id,
                subject_id,
                session,
                term,
                ca_score,
                exam_score,
                total_score,
                grade,
                remark
            )
        )

        db.commit()

        cursor.close()

        return redirect(
            url_for("student_results")
        )


    cursor.close()

    return render_template(
        "add_result.html",
        students=students,
        subjects=subjects
    )


# ==========================================
# SCHOOL FEES
# ==========================================

@app.route("/admin/fees")
@admin_required
def fees():

    cursor = db.cursor(dictionary=True)


    # ==========================================
    # GET ALL ACTIVE STUDENTS
    # ==========================================

    cursor.execute("""
        SELECT
            id,
            admission_number,
            full_name,
            class_name
        FROM students
        WHERE status = 'Active'
        ORDER BY full_name ASC
    """)

    students = cursor.fetchall()

    fee_summary = []


    for student in students:

        cursor.execute("""
            SELECT
                COALESCE(SUM(amount), 0) AS total_amount,
                COALESCE(SUM(amount_paid), 0) AS total_paid
            FROM fees
            WHERE student_id = %s
        """, (student["id"],))

        summary = cursor.fetchone()

        total_amount = float(
            summary["total_amount"] or 0
        )

        total_paid = float(
            summary["total_paid"] or 0
        )

        balance = total_amount - total_paid


        if total_paid <= 0:

            payment_status = "Pending"

        elif total_paid < total_amount:

            payment_status = "Partial"

        else:

            payment_status = "Paid"


        fee_summary.append({
            "id": student["id"],
            "admission_number": student["admission_number"],
            "full_name": student["full_name"],
            "class_name": student["class_name"],
            "total_amount": total_amount,
            "total_paid": total_paid,
            "balance": balance,
            "payment_status": payment_status
        })


    # ==========================================
    # GET ALL INDIVIDUAL FEE RECORDS
    # ==========================================

    cursor.execute("""
        SELECT
            f.*,
            s.full_name,
            s.admission_number,
            s.class_name
        FROM fees f
        JOIN students s
            ON f.student_id = s.id
        ORDER BY f.id DESC
    """)

    fee_records = cursor.fetchall()

    cursor.close()


    return render_template(
        "fees.html",
        fees=fee_summary,
        fee_records=fee_records
    )


# ==========================================
# ADD FEE PAYMENT
# ==========================================

@app.route(
    "/admin/fees/add",
    methods=["GET", "POST"]
)
@admin_required
def add_fee():

    cursor = db.cursor(dictionary=True)


    # ==========================================
    # GET ACTIVE STUDENTS
    # ==========================================

    cursor.execute("""
        SELECT
            id,
            admission_number,
            full_name,
            class_name
        FROM students
        WHERE status = 'Active'
        ORDER BY full_name ASC
    """)

    students = cursor.fetchall()


    if request.method == "POST":

        student_id = request.form["student_id"]

        session = request.form["session"]

        term = request.form["term"]

        fee_type = request.form["fee_type"]

        amount = float(
            request.form["amount"]
        )

        amount_paid = float(
            request.form["amount_paid"] or 0
        )

        payment_date = request.form.get(
            "payment_date"
        )

        description = request.form.get(
            "description"
        )


        # ==========================================
        # CHECK EXISTING FEE
        # ==========================================

        cursor.execute("""
            SELECT
                id,
                amount,
                amount_paid
            FROM fees
            WHERE student_id = %s
            AND session = %s
            AND term = %s
            AND fee_type = %s
            LIMIT 1
        """, (
            student_id,
            session,
            term,
            fee_type
        ))

        existing_fee = cursor.fetchone()


        # ==========================================
        # EXISTING FEE
        # ==========================================

        if existing_fee:

            fee_id = existing_fee["id"]

            original_amount = float(
                existing_fee["amount"]
            )

            already_paid = float(
                existing_fee["amount_paid"] or 0
            )

            remaining = (
                original_amount - already_paid
            )


            if amount_paid > remaining:

                cursor.close()

                return (
                    f"Payment is greater than "
                    f"the remaining balance. "
                    f"Remaining balance is "
                    f"₦{remaining:,.2f}"
                ), 400


            new_amount_paid = (
                already_paid + amount_paid
            )


            if new_amount_paid >= original_amount:

                payment_status = "Paid"

            elif new_amount_paid > 0:

                payment_status = "Partial"

            else:

                payment_status = "Pending"


            cursor.execute("""
                UPDATE fees
                SET
                    amount_paid = %s,
                    payment_date = %s,
                    payment_status = %s,
                    description = %s
                WHERE id = %s
            """, (
                new_amount_paid,
                payment_date,
                payment_status,
                description,
                fee_id
            ))


        # ==========================================
        # NEW FEE
        # ==========================================

        else:

            if amount_paid >= amount:

                payment_status = "Paid"

            elif amount_paid > 0:

                payment_status = "Partial"

            else:

                payment_status = "Pending"


            cursor.execute("""
                INSERT INTO fees (
                    student_id,
                    session,
                    term,
                    fee_type,
                    amount,
                    amount_paid,
                    payment_date,
                    payment_status,
                    description
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
            """, (
                student_id,
                session,
                term,
                fee_type,
                amount,
                amount_paid,
                payment_date,
                payment_status,
                description
            ))


        db.commit()

        cursor.close()

        return redirect(
            url_for("fees")
        )


    cursor.close()

    return render_template(
        "add_fee.html",
        students=students
    )


# ==========================================
# ANNOUNCEMENTS
# ==========================================

@app.route("/admin/announcements")
@admin_required
def announcements():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM announcements
        ORDER BY id DESC
    """)

    announcement_list = cursor.fetchall()

    cursor.close()

    return render_template(
        "announcements.html",
        announcements=announcement_list
    )


# ==========================================
# ADD ANNOUNCEMENT
# ==========================================

@app.route(
    "/admin/announcements/add",
    methods=["GET", "POST"]
)
@admin_required
def add_announcement():

    cursor = db.cursor()


    if request.method == "POST":

        title = request.form["title"]

        message = request.form["message"]

        audience = request.form["audience"]

        status = request.form["status"]


        cursor.execute(
            """
            INSERT INTO announcements (
                title,
                message,
                audience,
                status
            )
            VALUES (
                %s, %s, %s, %s
            )
            """,
            (
                title,
                message,
                audience,
                status
            )
        )


        db.commit()

        cursor.close()

        return redirect(
            url_for("announcements")
        )


    cursor.close()

    return render_template(
        "add_announcement.html"
    )


# ==========================================
# STUDENT DASHBOARD
# ==========================================

@app.route("/student")
def student_dashboard():

    if "student_id" not in session:

        return redirect(
            url_for("login")
        )


    student_id = session["student_id"]

    cursor = db.cursor(dictionary=True)


    # ==========================================
    # STUDENT INFORMATION
    # ==========================================

    cursor.execute("""
        SELECT *
        FROM students
        WHERE id = %s
    """, (student_id,))

    student = cursor.fetchone()


    # ==========================================
    # STUDENT RESULTS
    # ==========================================

    cursor.execute("""
        SELECT
            sr.*,
            sub.subject_name,
            sub.subject_code
        FROM student_results sr
        JOIN subjects sub
            ON sr.subject_id = sub.id
        WHERE sr.student_id = %s
        ORDER BY sr.id DESC
    """, (student_id,))

    results = cursor.fetchall()


    # ==========================================
    # STUDENT FEES
    # ==========================================

    cursor.execute("""
        SELECT *
        FROM fees
        WHERE student_id = %s
        ORDER BY id DESC
    """, (student_id,))

    fees = cursor.fetchall()


    # ==========================================
    # ANNOUNCEMENTS
    # ==========================================

    cursor.execute("""
        SELECT *
        FROM announcements
        WHERE status = 'Published'
        AND (
            audience = 'Everyone'
            OR audience = 'Students'
        )
        ORDER BY id DESC
    """)

    announcements = cursor.fetchall()

    cursor.close()


    return render_template(
        "student_dashboard.html",
        student=student,
        results=results,
        fees=fees,
        announcements=announcements
    )


# ==========================================
# STUDENT RESULTS PAGE
# ==========================================

@app.route("/student/results")
def student_results_page():

    if session.get("user_role") != "student":

        return redirect(
            url_for("login")
        )


    student_id = session.get(
        "student_id"
    )

    cursor = db.cursor(dictionary=True)


    # ==========================================
    # RESULTS
    # ==========================================

    cursor.execute("""
        SELECT
            sr.*,
            sub.subject_name,
            sub.subject_code
        FROM student_results sr
        JOIN subjects sub
            ON sr.subject_id = sub.id
        WHERE sr.student_id = %s
        ORDER BY
            sr.session DESC,
            sr.term DESC,
            sub.subject_name ASC
    """, (student_id,))

    results = cursor.fetchall()


    # ==========================================
    # STUDENT
    # ==========================================

    cursor.execute("""
        SELECT *
        FROM students
        WHERE id = %s
    """, (student_id,))

    student = cursor.fetchone()

    cursor.close()


    return render_template(
        "student_results_page.html",
        results=results,
        student=student
    )


# ==========================================
# CONTACT FORM
# ==========================================

@app.route("/contact", methods=["POST"])
def contact():

    full_name = request.form["full_name"].strip()

    email = request.form["email"].strip()

    subject = request.form["subject"].strip()

    message = request.form["message"].strip()


    if not full_name or not email or not subject or not message:

        return "Please fill in all fields.", 400


    cursor = db.cursor()


    cursor.execute("""
        INSERT INTO contact_messages (
            full_name,
            email,
            subject,
            message
        )
        VALUES (
            %s, %s, %s, %s
        )
    """, (
        full_name,
        email,
        subject,
        message
    ))


    db.commit()

    cursor.close()


    return redirect(
        url_for("home") + "#contact"
    )


# ==========================================
# ADMIN CONTACT MESSAGES
# ==========================================

@app.route("/admin/contact-messages")
@admin_required
def contact_messages():

    cursor = db.cursor(dictionary=True)


    cursor.execute("""
        SELECT *
        FROM contact_messages
        ORDER BY id DESC
    """)


    messages = cursor.fetchall()

    cursor.close()


    return render_template(
        "contact_messages.html",
        messages=messages
    )


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(debug=True)