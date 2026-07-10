import hmac
import logging
import os
import secrets
from datetime import date
from functools import wraps

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from markupsafe import Markup

from PoolCar import Databaze
from weeks import get_weeks_of_month


logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)

if not os.environ.get("SECRET_KEY"):
    logger.warning("Using generated in-memory SECRET_KEY. Set SECRET_KEY for persistent sessions.")


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return Markup(f'<input type="hidden" name="csrf_token" value="{token}">')


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def validate_csrf_token():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return

    session_token = session.get("_csrf_token")
    request_token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")

    if not session_token or not request_token or not hmac.compare_digest(session_token, request_token):
        logger.warning("Rejected invalid CSRF token for %s", request.path)
        abort(400)


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin", False):
            flash("Access denied.", "error")
            return redirect(url_for("home"))
        return view(*args, **kwargs)

    return wrapped_view


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user"):
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def _missing_fields(form_data, required_fields):
    return [field for field in required_fields if not form_data.get(field)]


def _reservation_context(employee_info=None, error=None):
    db = Databaze()
    employee_id = None if session.get("admin") else session.get("employee_id")
    employees = db.get_employee_choices(employee_id=employee_id)

    if employee_info is None and employees:
        employee_info = employees[0]

    context = {
        "employee_info": employee_info or {},
        "employees": employees,
        "car_info": db.get_car_info(),
    }
    if error:
        context["error"] = error
    return context


def _employee_access_allowed(employee_id):
    if session.get("admin"):
        return True
    return str(session.get("employee_id")) == str(employee_id)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("login.html"), 400

        db_instance = Databaze(username=username, password=password)
        user = db_instance.login()

        if user:
            session.clear()
            session["user"] = user.get("login", username)
            session["employee_id"] = user.get("idZamestnance")
            session["admin"] = bool(user.get("admin", False))
            logger.info("Successful login for user: %s", username)
            return redirect(url_for("home"))

        logger.warning("Failed login attempt for user: %s", username)
        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/auta")
@admin_required
def auta():
    return render_template("auta.html")


@app.route("/zamestnanci", methods=["GET", "POST"])
@admin_required
def zamestnanci():
    if request.method == "POST":
        required_fields = [
            "idZamestnance",
            "firstName",
            "lastName",
            "login",
            "password",
            "email",
            "division",
            "department",
        ]
        form_data = {field: request.form.get(field, "").strip() for field in required_fields}
        missing = _missing_fields(form_data, required_fields)

        if missing:
            flash(f"Missing required fields: {', '.join(missing)}", "error")
            return render_template("zamestnanci.html", data=form_data), 400

        db = Databaze()
        saved = db.insert_employee(
            form_data["idZamestnance"],
            form_data["firstName"],
            form_data["lastName"],
            form_data["login"],
            form_data["password"],
            form_data["email"],
            form_data["division"],
            form_data["department"],
        )

        if not saved:
            flash("Employee could not be saved.", "error")
            return render_template("zamestnanci.html", data=form_data), 500

        flash("Employee saved.", "success")
        return redirect(url_for("zamestnanci"))

    return render_template("zamestnanci.html")


@app.route("/result", methods=["POST"])
def result():
    try:
        selected_year = int(request.form["rok"])
        selected_month = int(request.form["mesic"])
        if not (1 <= selected_month <= 12 and selected_year > 1900):
            raise ValueError("Invalid date range")
    except (ValueError, KeyError):
        flash("Invalid date input.", "error")
        return redirect(url_for("home"))

    weeks = get_weeks_of_month(selected_year, selected_month)
    return render_template(
        "result.html",
        year=selected_year,
        month=selected_month,
        weeks=weeks,
    )


@app.route("/rezervace", methods=["GET"])
@login_required
def rezervace():
    return render_template("rezervace.html", **_reservation_context())


@app.route("/getEmployeeInfo")
@login_required
def get_employee_info():
    employee_id = request.args.get("employee_id", "").strip()
    if not employee_id:
        return jsonify({"employeeInfo": {}}), 400

    if not _employee_access_allowed(employee_id):
        return jsonify({"employeeInfo": {}}), 403

    db = Databaze()
    return jsonify({"employeeInfo": db.get_employee_info_by_id(employee_id)})


@app.route("/insertRezervace", methods=["POST"])
@login_required
def insert_rezervace():
    fields = [
        "idZamestnance",
        "spz",
        "stavRezervace",
        "kmPredJizdou",
        "kmPoJizde",
        "najetoKm",
        "poskozeni",
        "prevzetiDne",
        "odevzdaniDne",
        "divize",
        "oddeleni",
    ]
    form_data = {field: request.form.get(field, "").strip() for field in fields}
    required_fields = [
        "idZamestnance",
        "spz",
        "stavRezervace",
        "prevzetiDne",
        "odevzdaniDne",
    ]
    missing = _missing_fields(form_data, required_fields)

    if missing:
        return (
            render_template(
                "rezervace.html",
                **_reservation_context(
                    employee_info=form_data,
                    error=f"Missing required fields: {', '.join(missing)}",
                ),
            ),
            400,
        )

    if not _employee_access_allowed(form_data["idZamestnance"]):
        flash("Access denied.", "error")
        return redirect(url_for("rezervace"))

    try:
        prevzeti_dne = date.fromisoformat(form_data["prevzetiDne"])
        odevzdani_dne = date.fromisoformat(form_data["odevzdaniDne"])
        if odevzdani_dne < prevzeti_dne:
            raise ValueError("End date must not be before start date")
    except ValueError:
        return (
            render_template(
                "rezervace.html",
                **_reservation_context(
                    employee_info=form_data,
                    error="Invalid reservation date range.",
                ),
            ),
            400,
        )

    db = Databaze()
    employee = db.get_employee_info_by_id(form_data["idZamestnance"])
    car = db.get_car_info_by_spz(form_data["spz"])

    if not employee:
        return (
            render_template(
                "rezervace.html",
                **_reservation_context(
                    employee_info=form_data,
                    error="Selected employee does not exist.",
                ),
            ),
            400,
        )

    if not car:
        return (
            render_template(
                "rezervace.html",
                **_reservation_context(
                    employee_info=form_data,
                    error="Selected car does not exist.",
                ),
            ),
            400,
        )

    saved, reason = db.insert_rezervace_if_available(
        employee["idZamestnance"],
        employee["jmeno"],
        employee["prijmeni"],
        employee.get("divize", ""),
        employee.get("oddeleni", ""),
        car.get("idAuta"),
        car["spz"],
        form_data["stavRezervace"],
        form_data["prevzetiDne"],
        form_data["odevzdaniDne"],
        form_data["kmPredJizdou"],
        form_data["kmPoJizde"],
        form_data["najetoKm"],
        form_data["poskozeni"],
    )

    if reason == "conflict":
        return render_template(
            "rezervace.html",
            **_reservation_context(
                employee_info=form_data,
                error="Reservation already exists for the specified period.",
            ),
        )

    if not saved:
        return (
            render_template(
                "rezervace.html",
                **_reservation_context(
                    employee_info=form_data,
                    error="Reservation could not be saved.",
                ),
            ),
            500,
        )

    flash("Reservation saved.", "success")
    return redirect(url_for("rezervace"))


@app.route("/submit", methods=["POST"])
@admin_required
def submit():
    required_fields = ["vin", "spz", "znacka", "model", "rokVyroby", "najetoKm"]
    form_data = {field: request.form.get(field, "").strip() for field in required_fields}
    missing = _missing_fields(form_data, required_fields)

    if missing:
        flash(f"Missing required fields: {', '.join(missing)}", "error")
        return render_template("auta.html", data=form_data), 400

    try:
        rok_vyroby = int(form_data["rokVyroby"])
        najeto_km = int(form_data["najetoKm"])
        if rok_vyroby < 1886 or najeto_km < 0:
            raise ValueError("Invalid car data")
    except ValueError:
        flash("Invalid car year or mileage.", "error")
        return render_template("auta.html", data=form_data), 400

    db = Databaze()
    saved = db.insert_car(
        form_data["vin"],
        form_data["spz"],
        form_data["znacka"],
        form_data["model"],
        rok_vyroby,
        najeto_km,
    )

    if not saved:
        flash("Car could not be saved.", "error")
        return render_template("auta.html", data=form_data), 500

    flash("Car saved.", "success")
    return redirect(url_for("auta"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug_mode)
