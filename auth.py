import streamlit as st
import hashlib
import secrets
import re

# Password hashing
def hash_password(password, salt=None):

    if salt is None:
        salt = secrets.token_hex(16)

    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        bytes.fromhex(salt),
        100000
    ).hex()

    return hashed, salt


# Verify password
def verify_password(password, stored_hash, salt):

    hashed, _ = hash_password(password, salt)

    return secrets.compare_digest(hashed, stored_hash)


# Validate email
def valid_email(email):

    pattern = r'^[\w.-]+@[\w.-]+\.\w+$'

    return re.match(pattern, email) is not None


# Authentication page
def auth_page():

    st.title("🔄 BarterHub")

    login, signup = st.tabs(["Login", "Sign Up"])

    # LOGIN
    with login:

        st.subheader("Welcome Back!")

        email = st.text_input("Email", key="login_email")
        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button("Login"):

            if not email or not password:
                st.error("Please fill in all fields.")

            else:
                st.info("Login database integration is pending.")


    # SIGNUP
    with signup:

        st.subheader("Create Your Account")

        name = st.text_input("Full Name", key="signup_name")
        email = st.text_input("Email", key="signup_email")

        password = st.text_input(
            "Password",
            type="password",
            key="signup_password"
        )

        confirm = st.text_input(
            "Confirm Password",
            type="password",
            key="confirm_password"
        )

        if st.button("Create Account"):

            if not name or not email or not password or not confirm:
                st.error("Please fill in all fields.")

            elif not valid_email(email):
                st.error("Enter a valid email address.")

            elif password != confirm:
                st.error("Passwords do not match.")

            elif len(password) < 8:
                st.error("Password must contain at least 8 characters.")

            else:
                hashed, salt = hash_password(password)

                st.success("Input validated! Ready for database integration.")