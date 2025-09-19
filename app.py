import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import sqlite3
import hashlib
import time

# Set page configuration
st.set_page_config(
    page_title="Loan Application System",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database setup
def init_db():
    conn = sqlite3.connect('loan_app.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE,
                 password TEXT,
                 full_name TEXT,
                 email TEXT,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # User profiles table
    c.execute('''CREATE TABLE IF NOT EXISTS user_profiles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 age INTEGER,
                 income REAL,
                 employment_status TEXT,
                 credit_score INTEGER,
                 civil_score INTEGER,
                 last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Loans table
    c.execute('''CREATE TABLE IF NOT EXISTS loans
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 amount REAL,
                 interest_rate REAL,
                 term_months INTEGER,
                 status TEXT,
                 application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 approved_date TIMESTAMP,
                 due_date TIMESTAMP,
                 penalty_rate REAL DEFAULT 0.05,
                 FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Payments table
    c.execute('''CREATE TABLE IF NOT EXISTS payments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 loan_id INTEGER,
                 amount REAL,
                 payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY (loan_id) REFERENCES loans (id))''')
    
    # Insert default admin user if not exists
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        hashed_password = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, full_name, email) VALUES (?, ?, ?, ?)",
                 ('admin', hashed_password, 'Administrator', 'admin@loansystem.com'))
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Utility functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def get_user_id(username):
    conn = sqlite3.connect('loan_app.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_user_profile(user_id):
    conn = sqlite3.connect('loan_app.db')
    c = conn.cursor()
    c.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def get_user_loans(user_id):
    conn = sqlite3.connect('loan_app.db')
    c = conn.cursor()
    c.execute("SELECT * FROM loans WHERE user_id = ?", (user_id,))
    result = c.fetchall()
    conn.close()
    return result

def calculate_credit_score(income, employment_status, payment_history):
    # Simple credit score calculation
    base_score = 600
    
    # Income factor
    if income >= 100000:
        base_score += 100
    elif income >= 70000:
        base_score += 70
    elif income >= 50000:
        base_score += 40
    elif income >= 30000:
        base_score += 20
    
    # Employment status factor
    employment_factors = {
        "employed": 50,
        "self-employed": 30,
        "unemployed": -50,
        "student": 10,
        "retired": 20
    }
    base_score += employment_factors.get(employment_status.lower(), 0)
    
    # Payment history factor (simulated)
    payment_factor = 50 if payment_history > 0.9 else 0 if payment_history > 0.7 else -50
    base_score += payment_factor
    
    # Ensure score is within 300-850 range
    return max(300, min(850, base_score))

def calculate_civil_score(age, employment_status, credit_score):
    # Simple civil score calculation
    base_score = 50
    
    # Age factor
    if age >= 25 and age <= 60:
        base_score += 30
    elif age > 60:
        base_score += 20
    else:
        base_score += 10
    
    # Employment factor
    if employment_status.lower() == "employed":
        base_score += 30
    elif employment_status.lower() == "self-employed":
        base_score += 20
    else:
        base_score += 10
    
    # Credit score influence
    if credit_score >= 700:
        base_score += 20
    elif credit_score >= 600:
        base_score += 10
    
    return max(0, min(100, base_score))

# Authentication functions
def login_user(username, password):
    conn = sqlite3.connect('loan_app.db')
    c = conn.cursor()
    c.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and verify_password(password, user[2]):
        return True, user[1]
    return False, None

def register_user(username, password, full_name, email):
    try:
        conn = sqlite3.connect('loan_app.db')
        c = conn.cursor()
        hashed_password = hash_password(password)
        c.execute("INSERT INTO users (username, password, full_name, email) VALUES (?, ?, ?, ?)",
                 (username, hashed_password, full_name, email))
        conn.commit()
        conn.close()
        return True, "Registration successful"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except Exception as e:
        return False, f"Error: {str(e)}"

# Main application
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_id = None
    
    # Sidebar for navigation
    st.sidebar.title("Loan Application System")
    
    if not st.session_state.logged_in:
        menu = ["Login", "Register"]
        choice = st.sidebar.selectbox("Menu", menu)
        
        if choice == "Login":
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login"):
                success, user = login_user(username, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.session_state.user_id = get_user_id(user)
                    st.success(f"Logged in as {user}")
                    st.rerun()
                else:
                    st.error("Invalid username/password")
        
        elif choice == "Register":
            st.subheader("Create New Account")
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            
            if st.button("Register"):
                if new_password == confirm_password:
                    success, message = register_user(new_username, new_password, full_name, email)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("Passwords do not match")
    
    else:
        st.sidebar.write(f"Logged in as: **{st.session_state.username}**")
        menu = ["Dashboard", "Credit Score", "Civil Score", "Apply for Loan", "My Loans", "Admin Panel"]
        choice = st.sidebar.selectbox("Menu", menu)
        
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.user_id = None
            st.rerun()
        
        # Dashboard
        if choice == "Dashboard":
            st.title("Loan Application Dashboard")
            
            # Get user profile
            profile = get_user_profile(st.session_state.user_id)
            loans = get_user_loans(st.session_state.user_id)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("Credit Score")
                if profile and profile[4] is not None:
                    # Fix: Safely convert credit score to int
                    try:
                        credit_score = int(profile[4])
                        st.metric("Score", f"{credit_score}/850")
                    except (ValueError, TypeError):
                        st.write("Credit score not available")
                else:
                    st.write("Complete your profile to get a credit score")
            
            with col2:
                st.subheader("Civil Score")
                if profile and profile[5] is not None:
                    # Fix: Safely convert civil score to int
                    try:
                        civil_score = int(profile[5])
                        st.metric("Score", f"{civil_score}/100")
                    except (ValueError, TypeError):
                        st.write("Civil score not available")
                else:
                    st.write("Complete your profile to get a civil score")
            
            with col3:
                st.subheader("Active Loans")
                active_loans = len([loan for loan in loans if loan[5] == "approved"]) if loans else 0
                st.metric("Count", active_loans)
            
            # Loan status chart
            if loans:
                st.subheader("Loan Overview")
                loan_data = []
                for loan in loans:
                    loan_data.append({
                        "Amount": loan[2],
                        "Interest Rate": loan[3],
                        "Status": loan[5],
                        "Application Date": loan[6]
                    })
                
                df = pd.DataFrame(loan_data)
                st.bar_chart(df.groupby("Status")["Amount"].sum())
            
            # Recent activity
            st.subheader("Recent Activity")
            if loans:
                for loan in loans[-5:]:
                    status_color = "green" if loan[5] == "approved" else "orange" if loan[5] == "pending" else "red"
                    st.write(f"**{loan[6].split()[0]}**: Applied for ${loan[2]:,.2f} - :{status_color}[{loan[5]}]")
            else:
                st.info("No loan applications yet")
        
        # Credit Score
        elif choice == "Credit Score":
            st.title("Credit Score Checker")
            
            profile = get_user_profile(st.session_state.user_id)
            
            if profile and profile[4] is not None:
                # Fix: Safely convert credit score to int
                try:
                    credit_score = int(profile[4])
                    st.metric("Your Credit Score", f"{credit_score}/850")
                except (ValueError, TypeError):
                    st.error("Credit score data is invalid")
                    st.stop()
                
                # Credit score factors
                st.subheader("Factors affecting your credit score")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Income**: ${profile[2]:,.2f}")
                    st.progress(min(profile[2] / 100000, 1.0))
                    
                    employment_status = profile[3]
                    st.write(f"**Employment**: {employment_status}")
                    employment_values = {
                        "employed": 1.0,
                        "self-employed": 0.8,
                        "retired": 0.6,
                        "student": 0.4,
                        "unemployed": 0.2
                    }
                    if employment_status and isinstance(employment_status, str):
                        st.progress(employment_values.get(employment_status.lower(), 0.5))
                    else:
                        st.progress(0.5)
                
                with col2:
                    # Simulated payment history
                    payment_history = random.uniform(0.7, 1.0)
                    st.write(f"**Payment History**: {payment_history*100:.1f}%")
                    st.progress(payment_history)
                    
                    # Age factor
                    age = profile[1]
                    st.write(f"**Age**: {age} years")
                    age_factor = min(age / 40, 1.0) if age > 25 else 0.5
                    st.progress(age_factor)
                
                # Credit score explanation
                st.info("""
                Your credit score is calculated based on:
                - Income level
                - Employment status
                - Payment history
                - Age and financial stability
                """)
            
            else:
                st.warning("Please complete your profile to view your credit score")
                with st.form("profile_form"):
                    st.subheader("Complete Your Profile")
                    age = st.number_input("Age", min_value=18, max_value=100, value=25)
                    income = st.number_input("Annual Income ($)", min_value=0, value=50000)
                    employment_status = st.selectbox(
                        "Employment Status",
                        ["Employed", "Self-Employed", "Unemployed", "Student", "Retired"]
                    )
                    
                    if st.form_submit_button("Save Profile"):
                        # Calculate credit score (simulated)
                        payment_history = random.uniform(0.7, 1.0)  # Simulated payment history
                        credit_score = calculate_credit_score(income, employment_status, payment_history)
                        civil_score = calculate_civil_score(age, employment_status, credit_score)
                        
                        conn = sqlite3.connect('loan_app.db')
                        c = conn.cursor()
                        c.execute(
                            "INSERT INTO user_profiles (user_id, age, income, employment_status, credit_score, civil_score) VALUES (?, ?, ?, ?, ?, ?)",
                            (st.session_state.user_id, age, income, employment_status, credit_score, civil_score)
                        )
                        conn.commit()
                        conn.close()
                        st.success("Profile saved successfully!")
                        st.rerun()
        
        # Civil Score
        elif choice == "Civil Score":
            st.title("Civil Score Checker")
            
            profile = get_user_profile(st.session_state.user_id)
            
            if profile and profile[5] is not None:
                # Fix: Handle None values for civil score
                try:
                    civil_score = int(profile[5]) if profile[5] is not None else 0
                    st.metric("Your Civil Score", f"{civil_score}/100")
                except (ValueError, TypeError):
                    st.error("Civil score data is invalid")
                    st.stop()
                
                # Civil score factors
                st.subheader("Factors affecting your civil score")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Age**: {profile[1]} years")
                    age_factor = min(profile[1] / 40, 1.0) if profile[1] > 25 else 0.5
                    st.progress(age_factor)
                    
                    st.write(f"**Employment**: {profile[3]}")
                    employment_values = {
                        "employed": 1.0,
                        "self-employed": 0.8,
                        "retired": 0.7,
                        "student": 0.5,
                        "unemployed": 0.3
                    }
                    # Fix: Check if profile[3] exists and is a string before calling .lower()
                    if profile[3] and isinstance(profile[3], str):
                        st.progress(employment_values.get(profile[3].lower(), 0.5))
                    else:
                        st.progress(0.5)
                
                with col2:
                    # Fix: Handle None values for credit score
                    try:
                        credit_score_value = int(profile[4]) if profile[4] is not None else 300
                        st.write(f"**Credit Score**: {credit_score_value}/850")
                        credit_factor = credit_score_value / 850
                        st.progress(credit_factor)
                    except (ValueError, TypeError):
                        st.write("**Credit Score**: Not available")
                        st.progress(0)
                    
                    # Simulated community involvement
                    community_involvement = random.uniform(0.3, 0.9)
                    st.write(f"**Community Involvement**: {community_involvement*100:.1f}%")
                    st.progress(community_involvement)
                
                # Civil score explanation
                st.info("""
                Your civil score is calculated based on:
                - Age and stability
                - Employment status
                - Creditworthiness
                - Simulated community involvement
                """)
            
            else:
                st.warning("Please complete your profile to view your civil score")
        
        # Apply for Loan
        elif choice == "Apply for Loan":
            st.title("Apply for a Loan")
            
            profile = get_user_profile(st.session_state.user_id)
            
            if not profile:
                st.warning("Please complete your profile before applying for a loan")
                st.stop()
            
            with st.form("loan_application"):
                st.subheader("Loan Application Form")
                
                loan_amount = st.number_input("Loan Amount ($)", min_value=100, max_value=1000000, value=10000)
                loan_term = st.slider("Loan Term (months)", 6, 60, 12)
                purpose = st.selectbox(
                    "Loan Purpose",
                    ["Home Improvement", "Debt Consolidation", "Education", "Business", "Personal", "Other"]
                )
                
                # Display estimated terms based on credit score
                # Fix: Handle None values for credit score
                try:
                    credit_score = int(profile[4]) if profile and profile[4] is not None else 300
                except (ValueError, TypeError):
                    credit_score = 300  # Default to minimum score if conversion fails
                
                if credit_score >= 750:
                    interest_rate = 5.5
                    approval_chance = "Very High"
                elif credit_score >= 700:
                    interest_rate = 6.5
                    approval_chance = "High"
                elif credit_score >= 650:
                    interest_rate = 8.0
                    approval_chance = "Moderate"
                elif credit_score >= 600:
                    interest_rate = 10.5
                    approval_chance = "Low"
                else:
                    interest_rate = 15.0
                    approval_chance = "Very Low"
                
                st.write(f"**Estimated Interest Rate**: {interest_rate}%")
                st.write(f"**Approval Chance**: {approval_chance}")
                
                submitted = st.form_submit_button("Submit Application")
                
                if submitted:
                    # Determine approval based on credit score and other factors
                    # Fix: Handle case where profile[2] (income) might be None
                    income = profile[2] if profile[2] is not None else 0
                    if credit_score >= 650 and loan_amount <= income * 0.5:
                        status = "approved"
                        message = "Congratulations! Your loan application has been approved."
                    else:
                        status = "pending"
                        message = "Your loan application is under review."
                    
                    # Save loan application
                    conn = sqlite3.connect('loan_app.db')
                    c = conn.cursor()
                    application_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    if status == "approved":
                        approved_date = application_date
                        due_date = (datetime.now() + timedelta(days=loan_term*30)).strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        approved_date = None
                        due_date = None
                    
                    c.execute(
                        "INSERT INTO loans (user_id, amount, interest_rate, term_months, status, application_date, approved_date, due_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (st.session_state.user_id, loan_amount, interest_rate, loan_term, status, application_date, approved_date, due_date)
                    )
                    conn.commit()
                    conn.close()
                    
                    st.success(message)
        
        # My Loans
        elif choice == "My Loans":
            st.title("My Loans")
            
            loans = get_user_loans(st.session_state.user_id)
            
            if not loans:
                st.info("You don't have any loan applications yet")
            else:
                for loan in loans:
                    with st.expander(f"Loan #{loan[0]} - ${loan[2]:,.2f} - {loan[5]}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Amount**: ${loan[2]:,.2f}")
                            st.write(f"**Interest Rate**: {loan[3]}%")
                            st.write(f"**Term**: {loan[4]} months")
                        
                        with col2:
                            st.write(f"**Status**: {loan[5]}")
                            st.write(f"**Application Date**: {loan[6]}")
                            
                            if loan[7]:  # Approved date
                                st.write(f"**Approved Date**: {loan[7]}")
                            
                            if loan[8]:  # Due date
                                st.write(f"**Due Date**: {loan[8]}")
                                
                                # Check if loan is overdue
                                if isinstance(loan[8], str):
                                    try:
                                        due_date = datetime.strptime(loan[8], "%Y-%m-%d %H:%M:%S")
                                        if datetime.now() > due_date:
                                            days_overdue = (datetime.now() - due_date).days
                                            penalty = loan[2] * loan[9] * (days_overdue / 365)
                                            st.error(f"**Overdue by {days_overdue} days**")
                                            st.error(f"**Penalty**: ${penalty:,.2f}")
                                    except ValueError:
                                        st.write("Invalid due date format")
                        
                        # Payment section for approved loans
                        if loan[5] == "approved":
                            st.subheader("Make a Payment")
                            payment_amount = st.number_input(
                                f"Payment Amount for Loan #{loan[0]}",
                                min_value=1.0,
                                max_value=float(loan[2]),
                                key=f"payment_{loan[0]}"
                            )
                            
                            if st.button(f"Make Payment", key=f"pay_btn_{loan[0]}"):
                                conn = sqlite3.connect('loan_app.db')
                                c = conn.cursor()
                                c.execute(
                                    "INSERT INTO payments (loan_id, amount) VALUES (?, ?)",
                                    (loan[0], payment_amount)
                                )
                                conn.commit()
                                
                                # Update loan amount
                                new_amount = loan[2] - payment_amount
                                c.execute(
                                    "UPDATE loans SET amount = ? WHERE id = ?",
                                    (new_amount, loan[0])
                                )
                                conn.commit()
                                conn.close()
                                st.success(f"Payment of ${payment_amount:,.2f} processed")
                                st.rerun()
        
        # Admin Panel
        elif choice == "Admin Panel" and st.session_state.username == "admin":
            st.title("Admin Panel")
            
            # Admin functionality
            tab1, tab2, tab3 = st.tabs(["Users", "Loans", "Analytics"])
            
            with tab1:
                st.subheader("User Management")
                conn = sqlite3.connect('loan_app.db')
                users = pd.read_sql_query("SELECT id, username, full_name, email, created_at FROM users", conn)
                st.dataframe(users)
                
                # User search
                search_user = st.text_input("Search user by username")
                if search_user:
                    user_data = pd.read_sql_query(
                        f"SELECT * FROM users WHERE username LIKE '%{search_user}%'", 
                        conn
                    )
                    if not user_data.empty:
                        st.write("User Details:")
                        st.dataframe(user_data)
                        
                        # Get user profile
                        user_id = user_data.iloc[0]['id']
                        profile = pd.read_sql_query(
                            f"SELECT * FROM user_profiles WHERE user_id = {user_id}", 
                            conn
                        )
                        
                        if not profile.empty:
                            st.write("User Profile:")
                            st.dataframe(profile)
                        
                        # Get user loans
                        loans = pd.read_sql_query(
                            f"SELECT * FROM loans WHERE user_id = {user_id}", 
                            conn
                        )
                        
                        if not loans.empty:
                            st.write("User Loans:")
                            st.dataframe(loans)
                
                conn.close()
            
            with tab2:
                st.subheader("Loan Management")
                conn = sqlite3.connect('loan_app.db')
                loans = pd.read_sql_query(
                    "SELECT l.*, u.username FROM loans l JOIN users u ON l.user_id = u.id", 
                    conn
                )
                st.dataframe(loans)
                
                # Update loan status
                st.subheader("Update Loan Status")
                loan_id = st.number_input("Loan ID", min_value=1)
                new_status = st.selectbox("New Status", ["pending", "approved", "rejected"])
                
                if st.button("Update Status"):
                    c = conn.cursor()
                    if new_status == "approved":
                        # Set approved date and due date
                        approved_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        loan_term = c.execute(
                            "SELECT term_months FROM loans WHERE id = ?", 
                            (loan_id,)
                        ).fetchone()[0]
                        due_date = (datetime.now() + timedelta(days=loan_term*30)).strftime("%Y-%m-%d %H:%M:%S")
                        
                        c.execute(
                            "UPDATE loans SET status = ?, approved_date = ?, due_date = ? WHERE id = ?",
                            (new_status, approved_date, due_date, loan_id)
                        )
                    else:
                        c.execute(
                            "UPDATE loans SET status = ? WHERE id = ?",
                            (new_status, loan_id)
                        )
                    
                    conn.commit()
                    st.success(f"Loan #{loan_id} status updated to {new_status}")
                
                conn.close()
            
            with tab3:
                st.subheader("System Analytics")
                conn = sqlite3.connect('loan_app.db')
                
                # Loan statistics
                total_loans = pd.read_sql_query("SELECT COUNT(*) as count FROM loans", conn).iloc[0]['count']
                total_approved = pd.read_sql_query("SELECT COUNT(*) as count FROM loans WHERE status = 'approved'", conn).iloc[0]['count']
                total_pending = pd.read_sql_query("SELECT COUNT(*) as count FROM loans WHERE status = 'pending'", conn).iloc[0]['count']
                total_rejected = pd.read_sql_query("SELECT COUNT(*) as count FROM loans WHERE status = 'rejected'", conn).iloc[0]['count']
                total_amount = pd.read_sql_query("SELECT SUM(amount) as total FROM loans WHERE status = 'approved'", conn).iloc[0]['total'] or 0
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Loans", total_loans)
                col2.metric("Approved", total_approved)
                col3.metric("Pending", total_pending)
                col4.metric("Rejected", total_rejected)
                
                st.metric("Total Amount Lent", f"${total_amount:,.2f}")
                
                # Loan status distribution
                status_data = pd.read_sql_query(
                    "SELECT status, COUNT(*) as count FROM loans GROUP BY status", 
                    conn
                )
                st.bar_chart(status_data.set_index("status"))
                
                # Average credit score
                avg_credit = pd.read_sql_query(
                    "SELECT AVG(credit_score) as avg FROM user_profiles", 
                    conn
                ).iloc[0]['avg'] or 0
                
                st.metric("Average Credit Score", f"{avg_credit:.1f}/850")
                
                conn.close()

if __name__ == "__main__":
    main()
