from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route("/", methods=["GET"])
def auth():
    return render_template("auth.html",
                         login_error=request.args.get("login_error"),
                         register_error=request.args.get("register_error"))

@auth_bp.route("/register", methods=["POST"])
def register():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    # Validation
    if not email or not password:
        return redirect(url_for("auth.auth", 
                              register_error="Email and password are required.", 
                              tab="register"))

    if password != confirm_password:
        return redirect(url_for("auth.auth", 
                              register_error="Passwords do not match.", 
                              tab="register"))

    if User.query.filter_by(email=email).first():
        return redirect(url_for("auth.auth", 
                              register_error="Email is already registered.", 
                              tab="register"))

    # Create new user
    hashed_pw = generate_password_hash(password)
    user = User(email=email, password_hash=hashed_pw)
    db.session.add(user)
    db.session.commit()

    # Log them in automatically
    session["user_id"] = user.id
    flash("Welcome! Your account has been created.", "success")
    return redirect(url_for("public.index"))

@auth_bp.route("/login", methods=["POST"])
def login():
    email = request.form.get("username", "").strip().lower()  # Note: form uses 'username' for email
    password = request.form.get("password", "")

    # Check for admin login first (accept both "admin" and "admin@flashstudios.com")
    if (email == "admin@flashstudios.com" or email == "admin") and password == "admin":
        # Clear any existing sessions
        session.clear()
        
        # Set admin session with maximum persistence
        session.permanent = True
        session["admin"] = True
        session["admin_logged_in"] = True  # Backup flag
        session["user_type"] = "admin"  # Additional identifier
        
        # Force session save
        session.modified = True
        
        flash("Welcome, Administrator!", "success")
        return redirect(url_for("admin.dashboard"))

    # Regular user login
    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return redirect(url_for("auth.auth", 
                              login_error="Invalid email or password.",
                              tab="login"))

    session["user_id"] = user.id
    session.pop("admin", None)  # Clear admin session if any
    flash("Welcome back!", "success")
    return redirect(url_for("public.index"))

@auth_bp.route("/logout")
def logout():
    """Log out current user and clear all session data"""
    session.clear()  # Clear all session data instead of individual keys
    flash("You have been logged out.", "success")
    return redirect(url_for("public.index"))
