import os
import re
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
if app.secret_key == "dev-secret-change-me":
    print("WARNING: using the default SECRET_KEY. Set a real SECRET_KEY env var in production.")

# Render/Neon sometimes hand out "postgres://" — SQLAlchemy 2.x needs "postgresql://".
database_url = os.environ.get("DATABASE_URL", "sqlite:///kaamsathi.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
print(f"KaamSathi is using database: {database_url.split('://')[0]}")

db = SQLAlchemy(app)

CATEGORIES = [
    {"name": "Mason", "icon": "fa-trowel"},
    {"name": "Painter", "icon": "fa-paint-roller"},
    {"name": "Electrician", "icon": "fa-bolt"},
    {"name": "Plumber", "icon": "fa-wrench"},
    {"name": "Loader", "icon": "fa-truck"},
    {"name": "Farm work", "icon": "fa-seedling"},
]

CATEGORY_STYLE = {
    "Mason": {"icon": "fa-trowel", "color": "#1FAE8C"},
    "Painter": {"icon": "fa-paint-roller", "color": "#B87700"},
    "Electrician": {"icon": "fa-bolt", "color": "#5B6EE8"},
    "Plumber": {"icon": "fa-wrench", "color": "#9C2B2E"},
    "Loader": {"icon": "fa-truck", "color": "#3E8AA8"},
    "Farm work": {"icon": "fa-seedling", "color": "#6B8A3A"},
}


# ---------------------------------------------------------------------------
# Database models — replaces the old in-memory lists. Data now survives
# restarts and redeploys. Registration still doesn't verify phone numbers
# with a real OTP; that's the next real feature to add (Message Central,
# same as salary_app), before this goes to real users.
# ---------------------------------------------------------------------------
class Worker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    trade = db.Column(db.String(60), nullable=False)
    locality = db.Column(db.String(120))


class Employer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    locality = db.Column(db.String(120))


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    wage = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(120), nullable=False)
    distance = db.Column(db.Float, default=1.0)
    date_needed = db.Column(db.Date, nullable=False)
    posted_at = db.Column(db.DateTime, default=datetime.utcnow)
    workers_needed = db.Column(db.Integer, default=1)
    urgent = db.Column(db.Boolean, default=False)
    employer_id = db.Column(db.Integer, db.ForeignKey("employer.id"), nullable=False)
    employer = db.relationship("Employer", backref="jobs")


class Interest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey("worker.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    job = db.relationship("Job", backref="interests")
    worker = db.relationship("Worker", backref="interests")


def format_work_date(d):
    diff = (d - date.today()).days
    if diff == 0:
        return "Today"
    if diff == 1:
        return "Tomorrow"
    return d.strftime("%a, %d %b")


def date_tag_class(label):
    if label == "Today":
        return "date-today"
    if label == "Tomorrow":
        return "date-tomorrow"
    return "date-later"


def format_posted_ago(dt):
    diff = datetime.utcnow() - dt
    minutes = int(diff.total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hr ago"
    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''} ago"


def wa_digits(phone):
    return re.sub(r"\D", "", phone)


def jobs_for_template(worker_id=None):
    """Query all jobs, newest first, and attach display fields for templates."""
    jobs = Job.query.order_by(Job.posted_at.desc()).all()
    interested_ids = set()
    if worker_id:
        interested_ids = {
            i.job_id for i in Interest.query.filter_by(worker_id=worker_id).all()
        }

    enriched = []
    for job in jobs:
        style = CATEGORY_STYLE.get(job.category, {"icon": "fa-briefcase", "color": "#122340"})
        label = format_work_date(job.date_needed)
        tags = []
        if job.urgent:
            tags.append({"type": "urgent", "label": "Urgent"})
        if job.workers_needed > 1:
            tags.append({"type": "workers", "label": f"{job.workers_needed} workers"})
        if (datetime.utcnow() - job.posted_at) < timedelta(hours=2):
            tags.append({"type": "new", "label": "New"})

        enriched.append({
            "id": job.id,
            "title": job.title,
            "category": job.category,
            "wage": job.wage,
            "location": job.location,
            "distance": job.distance,
            "posted": format_posted_ago(job.posted_at),
            "date_needed": job.date_needed,
            "icon": style["icon"],
            "color": style["color"],
            "date_label": label,
            "date_tag_class": date_tag_class(label),
            "tags": tags,
            "employer_name": job.employer.name,
            "employer_phone": job.employer.phone,
            "employer_phone_wa": wa_digits(job.employer.phone),
            "already_interested": job.id in interested_ids,
        })
    return enriched


def build_calendar_days():
    days = []
    for i in range(7):
        d = date.today() + timedelta(days=i)
        has_jobs = Job.query.filter_by(date_needed=d).first() is not None
        days.append({
            "num": d.day,
            "weekday": d.strftime("%a"),
            "is_today": i == 0,
            "is_tomorrow": i == 1,
            "has_jobs": has_jobs,
        })
    return days


def current_worker():
    wid = session.get("worker_id")
    return Worker.query.get(wid) if wid else None


def current_employer():
    eid = session.get("employer_id")
    return Employer.query.get(eid) if eid else None


def seed_if_empty():
    """Populate demo employers/jobs on first run only — never on top of real data."""
    if Job.query.count() > 0:
        return

    demo_employers = [
        Employer(name="Subrat Nayak", phone="+91 90000 00001", locality="Chandrasekharpur"),
        Employer(name="Priya Mishra", phone="+91 90000 00002", locality="Patia"),
        Employer(name="Ganesh Traders", phone="+91 90000 00003", locality="Old Town"),
        Employer(name="Ananya Patra", phone="+91 90000 00004", locality="Saheed Nagar"),
        Employer(name="Bijay Sahu", phone="+91 90000 00005", locality="Jatni"),
    ]
    db.session.add_all(demo_employers)
    db.session.commit()

    demo_jobs = [
        Job(title="Mason needed — house wall", category="Mason", wage=700,
            location="Chandrasekharpur", distance=1.8, date_needed=date.today(),
            posted_at=datetime.utcnow() - timedelta(minutes=12),
            workers_needed=2, urgent=True, employer_id=demo_employers[0].id),
        Job(title="Painter for 2BHK flat", category="Painter", wage=650,
            location="Patia", distance=3.2, date_needed=date.today() + timedelta(days=1),
            posted_at=datetime.utcnow() - timedelta(minutes=40),
            workers_needed=1, urgent=False, employer_id=demo_employers[1].id),
        Job(title="Loading help — shop stock", category="Loader", wage=500,
            location="Old Town", distance=2.4, date_needed=date.today(),
            posted_at=datetime.utcnow() - timedelta(hours=1),
            workers_needed=3, urgent=False, employer_id=demo_employers[2].id),
        Job(title="Electrician helper", category="Electrician", wage=800,
            location="Saheed Nagar", distance=4.1, date_needed=date.today() + timedelta(days=1),
            posted_at=datetime.utcnow() - timedelta(hours=2),
            workers_needed=1, urgent=False, employer_id=demo_employers[3].id),
        Job(title="Farm hand — harvest help", category="Farm work", wage=550,
            location="Jatni", distance=6.5, date_needed=date.today() + timedelta(days=3),
            posted_at=datetime.utcnow() - timedelta(hours=3),
            workers_needed=4, urgent=False, employer_id=demo_employers[4].id),
    ]
    db.session.add_all(demo_jobs)
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_if_empty()


# ---------------------------------------------------------------------------
# Registration / login
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        role = request.form.get("role", "worker")
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name or not phone:
            flash("Please enter your name and phone number.")
            return redirect(url_for("register", role=role))

        if role == "worker":
            trade = request.form.get("trade", CATEGORIES[0]["name"])
            locality = request.form.get("locality", "").strip()
            worker = Worker.query.filter_by(phone=phone).first()
            if not worker:
                worker = Worker(name=name, phone=phone, trade=trade, locality=locality)
                db.session.add(worker)
                db.session.commit()
            session["worker_id"] = worker.id
            session["worker_name"] = worker.name
            session.pop("employer_id", None)
            session.pop("employer_name", None)
            flash(f"Welcome, {worker.name} — you're registered and visible to employers.")
            return redirect(url_for("home"))

        else:
            locality = request.form.get("locality", "").strip()
            employer = Employer.query.filter_by(phone=phone).first()
            if not employer:
                employer = Employer(name=name, phone=phone, locality=locality)
                db.session.add(employer)
                db.session.commit()
            session["employer_id"] = employer.id
            session["employer_name"] = employer.name
            session.pop("worker_id", None)
            session.pop("worker_name", None)
            flash(f"Welcome, {employer.name} — you can now post jobs.")
            return redirect(url_for("post_job"))

    default_role = request.args.get("role", "worker")
    return render_template("register.html", categories=CATEGORIES, default_role=default_role)


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.")
    return redirect(url_for("home"))


# ---------------------------------------------------------------------------
# Labourer home
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    worker = current_worker()
    all_jobs = jobs_for_template(worker_id=worker.id if worker else None)
    tomorrow = date.today() + timedelta(days=1)
    tomorrow_jobs = [job for job in all_jobs if job["date_needed"] == tomorrow]
    return render_template(
        "home.html",
        worker=worker,
        categories=CATEGORIES,
        jobs=all_jobs,
        calendar_days=build_calendar_days(),
        tomorrow_jobs=tomorrow_jobs,
        tomorrow_label=tomorrow.strftime("%a, %d %b"),
        active_nav="home",
    )


@app.route("/jobs/<int:job_id>/interest", methods=["POST"])
def show_interest(job_id):
    worker = current_worker()
    if not worker:
        flash("Register as a worker first so employers can see your contact details.")
        return redirect(url_for("register", role="worker"))

    job = Job.query.get(job_id)
    if not job:
        flash("That job is no longer available.")
        return redirect(url_for("home"))

    already = Interest.query.filter_by(job_id=job_id, worker_id=worker.id).first()
    if not already:
        db.session.add(Interest(job_id=job_id, worker_id=worker.id))
        db.session.commit()
    flash(f"You're marked interested in \"{job.title}\" — the employer can now call or WhatsApp you.")
    return redirect(url_for("home"))


# ---------------------------------------------------------------------------
# Employer side
# ---------------------------------------------------------------------------
@app.route("/post-job", methods=["GET", "POST"])
def post_job():
    employer = current_employer()

    if request.method == "POST":
        if not employer:
            flash("Register as an employer first so workers can see who's hiring.")
            return redirect(url_for("register", role="employer"))

        category = request.form.get("category", "Mason")
        wage = request.form.get("wage", type=int) or 0
        workers_needed = request.form.get("workers", type=int) or 1
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()
        date_str = request.form.get("date_needed", "")

        try:
            date_needed = date.fromisoformat(date_str) if date_str else date.today()
        except ValueError:
            date_needed = date.today()

        if wage <= 0 or not location:
            flash("Please fill in wage and location before posting.")
            return redirect(url_for("post_job"))

        job = Job(
            title=description or f"{category} needed",
            category=category,
            wage=wage,
            location=location,
            distance=0.5,
            date_needed=date_needed,
            posted_at=datetime.utcnow(),
            workers_needed=workers_needed,
            urgent=(date_needed == date.today()),
            employer_id=employer.id,
        )
        db.session.add(job)
        db.session.commit()
        flash(f"Job posted — {workers_needed} {category.lower()}(s) at ₹{wage}/day, needed {format_work_date(date_needed)}.")
        return redirect(url_for("my_jobs"))

    return render_template(
        "post_job.html",
        categories=CATEGORIES,
        employer=employer,
        active_nav="post",
    )


@app.route("/my-jobs")
def my_jobs():
    employer = current_employer()
    if not employer:
        flash("Register as an employer to see the jobs you've posted.")
        return redirect(url_for("register", role="employer"))

    mine = Job.query.filter_by(employer_id=employer.id).order_by(Job.posted_at.desc()).all()
    enriched = []
    for job in mine:
        style = CATEGORY_STYLE.get(job.category, {"icon": "fa-briefcase", "color": "#122340"})
        interested = []
        for i in Interest.query.filter_by(job_id=job.id).all():
            interested.append({
                "worker_name": i.worker.name,
                "worker_trade": i.worker.trade,
                "worker_phone": i.worker.phone,
                "phone_wa": wa_digits(i.worker.phone),
            })
        enriched.append({
            "title": job.title,
            "wage": job.wage,
            "location": job.location,
            "icon": style["icon"],
            "color": style["color"],
            "date_label": format_work_date(job.date_needed),
            "interested": interested,
        })

    return render_template("my_jobs.html", employer=employer, jobs=enriched, active_nav="post")


# ---------------------------------------------------------------------------
# Earnings / profile
# ---------------------------------------------------------------------------
EARNINGS_HISTORY = [
    {"job": "Mason — house wall", "date": "20 Aug", "amount": 700},
    {"job": "Loading — shop stock", "date": "19 Aug", "amount": 500},
    {"job": "Mason — boundary wall", "date": "17 Aug", "amount": 750},
    {"job": "Painter — 1BHK flat", "date": "15 Aug", "amount": 600},
    {"job": "Mason — house wall", "date": "13 Aug", "amount": 700},
]


@app.route("/earnings")
def earnings():
    worker = current_worker()
    week_total = sum(e["amount"] for e in EARNINGS_HISTORY[:2])
    month_total = sum(e["amount"] for e in EARNINGS_HISTORY)
    avg_wage = round(month_total / len(EARNINGS_HISTORY))
    return render_template(
        "earnings.html",
        worker_name=worker.name if worker else "Guest worker",
        history=EARNINGS_HISTORY,
        week_total=week_total,
        month_total=month_total,
        avg_wage=avg_wage,
        active_nav="earnings",
    )


@app.route("/profile")
def profile():
    worker = current_worker()
    if worker:
        name = worker.name
        phone = worker.phone
        primary_trade = worker.trade
        locality = worker.locality or "Bhubaneswar"
    else:
        name = "Guest worker"
        phone = "Not registered"
        primary_trade = "—"
        locality = "—"

    initials = "".join(part[0] for part in name.split()[:2]).upper() or "?"
    return render_template(
        "profile.html",
        worker=worker,
        worker_name=name,
        initials=initials,
        phone=phone,
        locality=locality,
        primary_trade=primary_trade,
        years_experience=6,
        rating=4.6,
        skills=["Brickwork", "Plastering", "Tiling", "Concrete work"],
        active_nav="profile",
    )


if __name__ == "__main__":
    app.run(debug=True)
