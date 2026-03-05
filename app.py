from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
import re, random
from datetime import datetime, timedelta
from flask_mail import Mail, Message

# ---------------- APP CONFIG ----------------
app = Flask(__name__, static_folder=".", static_url_path="")
app.secret_key = "secret123"

# -------- EMAIL CONFIG --------
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = "sm12302040701178@gmail.com"
app.config["MAIL_PASSWORD"] = "nigcttarvcqmikdn"

mail = Mail(app)

@app.route("/resend_otp")
def resend_otp():
    email = session.get("verify_email")
    user_id = session.get("login_user_id")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    if email:
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
    elif user_id:
        cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        user = cur.fetchone()
    else:
        return redirect("/login_page")

    if not user:
        return redirect("/login_page")

    # Generate new OTP
    new_otp = generate_otp()
    expiry = datetime.now() + timedelta(minutes=5)

    cur = db.cursor()
    cur.execute("""
        UPDATE users
        SET otp=%s, otp_expiry=%s
        WHERE id=%s
    """, (new_otp, expiry, user["id"]))
    db.commit()

    send_otp(user["email"], new_otp)

    flash("OTP has been resent successfully!")

    return redirect(request.referrer)

# ---------------- DATABASE CONNECTION ----------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="ride_sharing"
    )

VEHICLE_PATTERN = r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$'

# ---------------- HELPER FUNCTIONS ----------------
def login_required(role=None):
    if "user_id" not in session:
        return False
    if role and session.get("role") != role:
        return False
    return True

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp(email, otp):
    msg = Message(
        subject="Ride Sharing System - OTP Verification",
        sender=app.config["MAIL_USERNAME"],
        recipients=[email]
    )
    msg.body = f"Your OTP is {otp}. It is valid for 5 minutes."
    mail.send(msg)
# ---------------- HOME ----------------
@app.route("/", methods=["GET", "POST"])
def home():
    rides = None
    if request.method == "POST":
        db = get_db_connection()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT * FROM rides
            WHERE start_point=%s AND end_point=%s AND status='Scheduled'
        """, (request.form.get("start"), request.form.get("end")))
        rides = cur.fetchall()
    return render_template("home.html", rides=rides)


# ---------------- AUTH PAGES ----------------
@app.route("/login_page")
def login_page():
    return render_template("login.html")

@app.route("/signup_page")
def signup_page():
    return render_template("signup.html")


# ---------------- SIGNUP (OTP MANDATORY) ----------------
@app.route("/signup", methods=["POST"])
def signup():
    name = request.form.get("name")
    mobile = request.form.get("mobile")
    email = request.form.get("email")
    password = request.form.get("password")
    role = request.form.get("role")
    vehicle = request.form.get("vehicle_number")

    if role == "driver" and (not vehicle or not re.match(VEHICLE_PATTERN, vehicle)):
        return "Invalid Vehicle Number Format"

    try:
        db = get_db_connection()
        cur = db.cursor()

        # Create user as NOT VERIFIED
        cur.execute("""
            INSERT INTO users
            (name, mobile, email, password, role, vehicle_number, is_verified)
            VALUES (%s,%s,%s,%s,%s,%s,FALSE)
        """, (name, mobile, email, password, role, vehicle))
        db.commit()

        # Generate OTP
        otp = generate_otp()
        expiry = datetime.now() + timedelta(minutes=5)

        cur.execute("""
            UPDATE users
            SET otp=%s, otp_expiry=%s
            WHERE email=%s
        """, (otp, expiry, email))
        db.commit()

        send_otp(email, otp)
        session["verify_email"] = email
        return redirect("/verify_signup_otp")

    except mysql.connector.Error:
        return "Mobile or Email already registered!"


# ---------------- VERIFY SIGNUP OTP ----------------
@app.route("/verify_signup_otp", methods=["GET", "POST"])
def verify_signup_otp():
    if request.method == "POST":
        entered_otp = request.form.get("otp")
        email = session.get("verify_email")

        db = get_db_connection()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT otp, otp_expiry
            FROM users
            WHERE email=%s AND is_verified=FALSE
        """, (email,))
        user = cur.fetchone()

        if user and user["otp"] == entered_otp and datetime.now() <= user["otp_expiry"]:
            cur.execute("""
                UPDATE users
                SET otp=NULL, otp_expiry=NULL, is_verified=TRUE
                WHERE email=%s
            """, (email,))
            db.commit()
            return redirect("/login_page")

        return "Invalid or Expired OTP"

    return render_template("verify_otp.html")
# ---------------- LOGIN (STEP 1: CHECK CREDENTIALS) ----------------
@app.route("/login", methods=["POST"])
def login():
    mobile = request.form.get("mobile")
    email = request.form.get("email")
    password = request.form.get("password")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    # Check all three: mobile + email + password
    cur.execute("""
        SELECT * FROM users
        WHERE mobile=%s AND email=%s AND password=%s AND is_verified=TRUE
    """, (mobile, email, password))
    user = cur.fetchone()

    if not user:
        return "Invalid credentials OR account not verified"

    # Credentials correct → send OTP
    otp = generate_otp()
    expiry = datetime.now() + timedelta(minutes=5)

    cur.execute("""
        UPDATE users
        SET otp=%s, otp_expiry=%s
        WHERE id=%s
    """, (otp, expiry, user["id"]))
    db.commit()

    send_otp(email, otp)
    session["login_user_id"] = user["id"]

    return redirect("/verify_login_otp")


# ---------------- VERIFY LOGIN OTP ----------------
@app.route("/verify_login_otp", methods=["GET", "POST"])
@app.route("/verify_login_otp", methods=["GET", "POST"])
def verify_login_otp():
    if request.method == "POST":
        entered_otp = request.form.get("otp")
        user_id = session.get("login_user_id")

        db = get_db_connection()
        cur = db.cursor(dictionary=True)

        cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        user = cur.fetchone()

        if not user:
            return "User not found"

        # ✅ ADMIN SPECIAL CASE
        if user["role"] == "admin":
            if entered_otp == "000000":
                session["user_id"] = user["id"]
                session["role"] = user["role"]
                session["name"] = user["name"]
                return redirect("/admin/dashboard")
            else:
                return "Invalid Admin OTP"

        # ✅ NORMAL USER OTP CHECK
        if user["otp"] == entered_otp and datetime.now() <= user["otp_expiry"]:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["name"] = user["name"]

            cur.execute("""
                UPDATE users
                SET otp=NULL, otp_expiry=NULL
                WHERE id=%s
            """, (user["id"],))
            db.commit()

            return redirect(f"/{user['role']}/dashboard")

        return "Invalid or Expired OTP"

    return render_template("verify_otp.html")
# ================== ADMIN MODULE ==================

@app.route("/admin/dashboard")
def admin_dashboard():
    if not login_required("admin"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM users ORDER BY id DESC")
    users = cur.fetchall()

    cur.execute("""
        SELECT r.start_point, r.end_point, r.ride_date, r.ride_time, r.status,
               u.name AS driver_name, rr.rating
        FROM rides r
        JOIN users u ON r.driver_id = u.id
        LEFT JOIN ride_requests rr ON rr.ride_id = r.id
    """)
    rides = cur.fetchall()

    return render_template("admin_dashboard.html", users=users, rides=rides)


@app.route("/admin/add_user", methods=["POST"])
def admin_add_user():
    if not login_required("admin"):
        return redirect("/login_page")

    role = request.form.get("role")
    vehicle = request.form.get("vehicle_number") if role == "driver" else None

    db = get_db_connection()
    cur = db.cursor()

    cur.execute("""
        INSERT INTO users (name, mobile, email, password, role, vehicle_number, is_verified)
        VALUES (%s,%s,%s,%s,%s,%s,TRUE)
    """, (
        request.form.get("name"),
        request.form.get("mobile"),
        request.form.get("email"),
        request.form.get("password"),
        role,
        vehicle
    ))
    db.commit()

    return redirect("/admin/dashboard")


@app.route("/admin/delete_user/<int:id>")
def delete_user(id):
    if not login_required("admin"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (id,))
    db.commit()

    return redirect("/admin/dashboard")


@app.route("/admin/history")
def admin_history():
    if not login_required("admin"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT r.*, u.name AS driver_name,
               p.name AS passenger_name, rr.rating
        FROM rides r
        JOIN users u ON r.driver_id = u.id
        LEFT JOIN ride_requests rr ON r.id = rr.ride_id
        LEFT JOIN users p ON rr.passenger_id = p.id
        WHERE r.status='Completed'
    """)
    history = cur.fetchall()

    return render_template("admin_history.html", history=history)


# ================== DRIVER MODULE ==================

@app.route("/driver/history")
def driver_history():
    if not login_required("driver"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT r.start_point,
               r.end_point,
               r.ride_date,
               r.ride_time,
               u.name AS passenger_name,
               rr.rating
        FROM rides r
        JOIN ride_requests rr ON r.id = rr.ride_id
        JOIN users u ON rr.passenger_id = u.id
        WHERE r.driver_id = %s
        AND r.status = 'Completed'
        AND rr.status = 'Accepted'
    """, (session["user_id"],))

    history = cur.fetchall()

    return render_template("driver_history.html", history=history)



@app.route("/driver/dashboard")
def driver_dashboard():
    if not login_required("driver"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    # Driver's own rides
    cur.execute("""
    SELECT * FROM rides
    WHERE driver_id=%s
    AND status != 'Completed'
    ORDER BY ride_date DESC
""", (session["user_id"],))

    my_rides = cur.fetchall()

    # Ride requests
    cur.execute("""
        SELECT rr.*, u.name AS passenger_name, u.mobile AS passenger_mobile
        FROM ride_requests rr
        JOIN users u ON rr.passenger_id = u.id
        JOIN rides r ON rr.ride_id = r.id
        WHERE r.driver_id=%s
    """, (session["user_id"],))
    requests = cur.fetchall()

    return render_template(
        "driver_dashboard.html",
        my_rides=my_rides,
        requests=requests
    )


@app.route("/edit_ride/<int:ride_id>", methods=["GET", "POST"])
def edit_ride(ride_id):
    if not login_required("driver"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    # Ensure driver owns the ride
    cur.execute("""
        SELECT * FROM rides
        WHERE id=%s AND driver_id=%s
    """, (ride_id, session["user_id"]))
    ride = cur.fetchone()

    if not ride:
        return "Unauthorized Access"

    if request.method == "POST":
        cur = db.cursor()
        cur.execute("""
            UPDATE rides
            SET start_point=%s,
                end_point=%s,
                seats=%s,
                ride_date=%s,
                ride_time=%s
            WHERE id=%s
        """, (
            request.form.get("start"),
            request.form.get("end"),
            request.form.get("seats"),
            request.form.get("ride_date"),
            request.form.get("ride_time"),
            ride_id
        ))
        db.commit()
        return redirect("/driver/dashboard")

    return render_template("edit_ride.html", ride=ride)


@app.route("/delete_ride/<int:ride_id>")
def delete_ride(ride_id):
    if not login_required("driver"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor()

    cur.execute("""
        DELETE FROM rides
        WHERE id=%s AND driver_id=%s
    """, (ride_id, session["user_id"]))

    db.commit()
    return redirect("/driver/dashboard")


@app.route("/add_ride", methods=["POST"])
def add_ride():
    if not login_required("driver"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor()

    cur.execute("""
        INSERT INTO rides (driver_id, start_point, end_point, seats, ride_date, ride_time, status)
        VALUES (%s,%s,%s,%s,%s,%s,'Scheduled')

    """, (
        session["user_id"],
        request.form.get("start"),
        request.form.get("end"),
        request.form.get("seats"),
        request.form.get("ride_date"),
        request.form.get("ride_time")
    ))
    db.commit()

    return redirect("/driver/dashboard")


@app.route("/accept/<int:req_id>/<int:ride_id>")
def accept_request(req_id, ride_id):
    db = get_db_connection()
    cur = db.cursor()

    cur.execute("UPDATE ride_requests SET status='Accepted' WHERE id=%s", (req_id,))
    cur.execute("UPDATE rides SET seats = seats - 1 WHERE id=%s", (ride_id,))
    db.commit()

    return redirect("/driver/dashboard")


@app.route("/reject/<int:req_id>")
def reject_request(req_id):
    db = get_db_connection()
    cur = db.cursor()

    cur.execute("UPDATE ride_requests SET status='Rejected' WHERE id=%s", (req_id,))
    db.commit()

    return redirect("/driver/dashboard")


@app.route("/start_ride/<int:ride_id>")
def start_ride(ride_id):
    if not login_required("driver"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor()

    cur.execute("""
        UPDATE rides
        SET status='Ongoing'
        WHERE id=%s AND driver_id=%s AND status='Scheduled'
    """, (ride_id, session["user_id"]))

    db.commit()
    db.close()

    return redirect("/driver/dashboard")


@app.route("/complete_ride/<int:ride_id>")
def complete_ride(ride_id):
    if not login_required("driver"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor()

    cur.execute("""
        UPDATE rides
        SET status='Completed'
        WHERE id=%s AND driver_id=%s AND status='Ongoing'
    """, (ride_id, session["user_id"]))

    db.commit()
    db.close()

    return redirect("/driver/dashboard")

# ================== PASSENGER MODULE ==================

@app.route("/passenger/dashboard", methods=["GET", "POST"])
def passenger_dashboard():
    if not login_required("passenger"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    rides = None

    # 🔥 SEARCH AVAILABLE RIDES WITH DRIVER NAME
    if request.method == "POST":
        cur.execute("""
            SELECT r.*, u.name AS driver_name
            FROM rides r
            JOIN users u ON r.driver_id = u.id
            WHERE r.start_point=%s
              AND r.end_point=%s
              AND r.status='Scheduled'
              AND r.seats > 0
        """, (request.form.get("start"), request.form.get("end")))
        
        rides = cur.fetchall()

    # 🔥 FETCH PASSENGER REQUESTS
    cur.execute("""
    SELECT rr.id,
           rr.status,
           rr.rating,
           r.start_point,
           r.end_point,
           r.ride_date,
           r.ride_time,
           r.status AS ride_status,
           u.name AS driver_name,
           u.mobile AS driver_mobile,
           u.vehicle_number
    FROM ride_requests rr
    JOIN rides r ON rr.ride_id = r.id
    JOIN users u ON r.driver_id = u.id
    WHERE rr.passenger_id=%s
    AND rr.rating IS NULL

""", (session["user_id"],))

    
    my_requests = cur.fetchall()

    return render_template(
        "passenger_dashboard.html",
        rides=rides,
        requests=my_requests
    )


@app.route("/request_ride/<int:ride_id>")
def request_ride(ride_id):
    if not login_required("passenger"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor()

    cur.execute("""
        SELECT * FROM ride_requests
        WHERE ride_id=%s AND passenger_id=%s
    """, (ride_id, session["user_id"]))

    if cur.fetchone():
        return "You already requested this ride"

    cur.execute("""
        INSERT INTO ride_requests (ride_id, passenger_id, status)
        VALUES (%s,%s,'Pending')
    """, (ride_id, session["user_id"]))
    db.commit()

    return redirect("/passenger/dashboard")


@app.route("/withdraw/<int:req_id>")
def withdraw_request(req_id):
    if not login_required("passenger"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor()

    cur.execute("""
        DELETE FROM ride_requests
        WHERE id=%s AND status='Pending'
    """, (req_id,))
    db.commit()

    return redirect("/passenger/dashboard")


@app.route("/rate_driver/<int:req_id>", methods=["POST"])
def rate_driver(req_id):
    if not login_required("passenger"):
        return redirect("/login_page")

    rating = request.form.get("rating")

    db = get_db_connection()
    cur = db.cursor()

    cur.execute("""
        UPDATE ride_requests
        SET rating=%s
        WHERE id=%s
    """, (rating, req_id))
    db.commit()

    return redirect("/passenger/dashboard")


@app.route("/passenger/history")
def passenger_history():
    if not login_required("passenger"):
        return redirect("/login_page")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT r.start_point,
               r.end_point,
               r.ride_date,
               r.ride_time,
               u.name AS driver_name
        FROM ride_requests rr
        JOIN rides r ON rr.ride_id = r.id
        JOIN users u ON r.driver_id = u.id
        WHERE rr.passenger_id = %s
        AND r.status = 'Completed'
        AND rr.status = 'Accepted'
        ORDER BY r.ride_date DESC
    """, (session["user_id"],))

    history = cur.fetchall()

    return render_template("passenger_history.html", history=history)


# ================== LOGOUT ==================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ================== RUN APPLICATION ==================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)