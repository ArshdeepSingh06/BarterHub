import re
import sqlite3

import streamlit as st

DATABASE = "barterhub.db"


def connect_db():
    return sqlite3.connect(DATABASE)


def setup_auth_database():
    with connect_db() as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL)"""
        )


def valid_email(email):
    return re.match(r"^[\w.+-]+@[\w-]+(\.[\w-]+)*\.\w+$", email) is not None


def create_user(name, email, password):
    try:
        with connect_db() as db:
            db.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email.lower(), password),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def login_user(email, password):
    with connect_db() as db:
        row = db.execute(
            "SELECT id, name, email FROM users WHERE email = ? AND password = ?",
            (email.lower(), password),
        ).fetchone()
    if row:
        return {"id": row[0], "name": row[1], "email": row[2]}
    return None


def auth_page():
    setup_auth_database()
    st.title("🔄 BarterHub")
    st.write("Trade what you have for what you need.")
    login, signup = st.tabs(["Login", "Sign Up"])

    with login:
        st.subheader("Welcome Back!")
        email = st.text_input("Email", key="login_email").strip()
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if not email or not password:
                st.error("Please fill in all fields.")
            elif not valid_email(email):
                st.error("Enter a valid email address.")
            elif user := login_user(email, password):
                st.session_state.logged_in = True
                st.session_state.user_id = user["id"]
                st.session_state.user_name = user["name"]
                st.session_state.user_email = user["email"]
                st.rerun()
            else:
                st.error("Invalid email or password.")

    with signup:
        st.subheader("Create Your Account")
        name = st.text_input("Full Name", key="signup_name").strip()
        email = st.text_input("Email", key="signup_email").strip()
        password = st.text_input("Password", type="password", key="signup_password")
        confirm = st.text_input("Confirm Password", type="password", key="confirm_password")
        if st.button("Create Account"):
            if not (name and email and password and confirm):
                st.error("Please fill in all fields.")
            elif not valid_email(email):
                st.error("Enter a valid email address.")
            elif password != confirm:
                st.error("Passwords do not match.")
            elif len(password) < 8:
                st.error("Password must contain at least 8 characters.")
            elif create_user(name, email, password):
                st.success("Account created successfully! You can now login.")
            else:
                st.error("An account with this email already exists.")