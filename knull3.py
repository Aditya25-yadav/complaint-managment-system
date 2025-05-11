import mysql.connector as connection
import sys
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton, QComboBox,
    QTextEdit, QMessageBox, QDialog, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Database connection
try:
    mydb = connection.connect(
        host="localhost",
        user="root",
        password="Messi2025#",
        database="complaintmanagmentsystem",
        use_pure=True
    )
    cursor = mydb.cursor()
    print("✅ Connected to MySQL: mp11")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    sys.exit(1)

# Back-end functions
def sign_up_user(role, name, email, phone, password, address=None, department=None):
    table = "Citizens" if role == "citizen" else "Authority"
    if not all([name, email, phone, password]) or (role == "citizen" and not address) or (role == "authority" and not department):
        return "⚠ All fields are required."
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "⚠ Invalid email format."
    
    try:
        cursor.execute(f"SELECT * FROM {table} WHERE Email = %s", (email,))
        if cursor.fetchone():
            return "⚠ Email already registered."
        
        if role == "citizen":
            query = "INSERT INTO Citizens (Name, Email, Phone, Address, Password) VALUES (%s, %s, %s, %s, %s)"
            params = (name, email, phone, address, password)
        else:
            query = "INSERT INTO Authority (Name, Department, Email, Phone, Password) VALUES (%s, %s, %s, %s, %s)"
            params = (name, department, email, phone, password)
            print(f"Debug: Executing query: {query} with params: {params}")
        
        cursor.execute(query, params)
        mydb.commit()
        user_id = cursor.lastrowid
        return f"✅ Sign-up successful. Your {'Citizen' if role == 'citizen' else 'Authority'} ID: {user_id}"
    except Exception as e:
        mydb.rollback()
        print(f"Debug: Error during signup: {e}")
        return f"❌ Error during signup: {e}"

def login_user(email, password, role):
    table = "Citizens" if role == "citizen" else "Authority"
    try:
        cursor.execute(f"SELECT * FROM {table} WHERE Email = %s AND Password = %s", (email, password))
        result = cursor.fetchone()
        if result:
            return result[0], f"✅ Welcome back, {result[1]}!"
        return None, "❌ Invalid credentials."
    except Exception as e:
        print(f"Debug: Error during login: {e}")
        return None, f"❌ Error during login: {e}"

def log_complaint(citizen_id, category, description, location):
    if not all([category, description, location]):
        return "⚠ All fields are required."
    try:
        cursor.execute("CALL InsertComplaint(%s, %s, %s, %s)", (citizen_id, category, description, location))
        mydb.commit()
        cursor.execute("SELECT MAX(ComplaintID) FROM Complaints WHERE CitizenID = %s", (citizen_id,))
        complaint_id = cursor.fetchone()[0]
        return f"✅ Complaint logged successfully with Complaint ID: {complaint_id}"
    except Exception as e:
        mydb.rollback()
        print(f"Debug: Error logging complaint: {e}")
        return f"❌ Error logging complaint: {e}"

def view_status(complaint_id, citizen_id=None, view_all=False):
    try:
        if view_all and citizen_id:
            query = """
                SELECT c.ComplaintID, c.Category, c.Location, c.DateSubmitted, c.Status, 
                       r.ResolutionDetails, r.DateResolved
                FROM Complaints c
                LEFT JOIN Resolutions r ON c.ResolutionID = r.ResolutionID
                WHERE c.CitizenID = %s
                ORDER BY c.DateSubmitted DESC
            """
            cursor.execute(query, (citizen_id,))
            results = cursor.fetchall()
            if not results:
                return "❌ No complaints found for this citizen."
            
            result_text = ""
            for result in results:
                status = result[4]
                resolution_text = result[5] if result[5] else "No resolution provided yet."
                date_resolved = result[6] if result[6] else "Not resolved yet."
                result_text += (
                    f"📌 Complaint ID     : {result[0]}\n"
                    f"📂 Category         : {result[1]}\n"
                    f"📍 Location         : {result[2]}\n"
                    f"📅 Date Submitted   : {result[3]}\n"
                    f"✅ Current Status   : {status}\n"
                    f"📝 Resolution       : {resolution_text}\n"
                    f"🕒 Date Resolved    : {date_resolved}\n"
                    f"{'-'*50}\n"
                )
            return result_text
        else:
            cursor.execute("SELECT GetComplaintStatus(%s)", (complaint_id,))
            status = cursor.fetchone()[0]
            if not status:
                return "❌ Complaint not found."
            
            query = """
                SELECT c.ComplaintID, c.Category, c.Location, c.DateSubmitted, c.Status, 
                       r.ResolutionDetails, r.DateResolved
                FROM Complaints c
                LEFT JOIN Resolutions r ON c.ResolutionID = r.ResolutionID
                WHERE c.ComplaintID = %s
            """
            cursor.execute(query, (complaint_id,))
            result = cursor.fetchone()
            if result:
                resolution_text = result[5] if result[5] else "No resolution provided yet."
                date_resolved = result[6] if result[6] else "Not resolved yet."
                return (
                    f"📌 Complaint ID     : {result[0]}\n"
                    f"📂 Category         : {result[1]}\n"
                    f"📍 Location         : {result[2]}\n"
                    f"📅 Date Submitted   : {result[3]}\n"
                    f"✅ Current Status   : {status}\n"
                    f"📝 Resolution       : {resolution_text}\n"
                    f"🕒 Date Resolved    : {date_resolved}"
                )
            return "❌ Complaint not found."
    except Exception as e:
        print(f"Debug: Error viewing status: {e}")
        return f"❌ Error viewing status: {e}"

def give_feedback(complaint_id, citizen_id, rating, comments):
    if not all([complaint_id, citizen_id, rating, comments]):
        return "⚠ All fields are required."
    try:
        complaint_id = int(complaint_id)
        citizen_id = int(citizen_id)
        rating = int(rating)
        if rating not in range(1, 6):
            return "⚠ Rating must be between 1 and 5."
        
        cursor.execute("SELECT * FROM Complaints WHERE ComplaintID = %s AND CitizenID = %s", (complaint_id, citizen_id))
        if not cursor.fetchone():
            return "❌ Complaint does not match your ID."
        
        cursor.execute(
            "INSERT INTO Feedback (ComplaintID, CitizenID, Rating, Comments) "
            "VALUES (%s, %s, %s, %s)",
            (complaint_id, citizen_id, rating, comments)
        )
        mydb.commit()
        return "✅ Feedback submitted."
    except Exception as e:
        mydb.rollback()
        print(f"Debug: Error submitting feedback: {e}")
        return f"❌ Error submitting feedback: {e}"

def view_complaints(authority_id):
    try:
        cursor.execute("SELECT Department FROM Authority WHERE AuthorityID = %s", (authority_id,))
        result = cursor.fetchone()
        if not result:
            return "❌ Authority not found."
        
        department = result[0]
        
        query = """
            SELECT c.ComplaintID, c.CitizenID, c.AuthorityID, c.Category, c.Description, 
                   c.Location, c.DateSubmitted, c.Status, r.ResolutionDetails
            FROM Complaints c
            LEFT JOIN Resolutions r ON c.ResolutionID = r.ResolutionID
            WHERE c.Category = %s
            ORDER BY c.DateSubmitted DESC
        """
        cursor.execute(query, (department,))
        complaints = cursor.fetchall()
        if not complaints:
            return f"❌ No complaints found for {department} department."
        
        result = ""
        for comp in complaints:
            resolution_text = comp[8] if comp[8] else "No resolution provided."
            result += (
                f"Complaint ID   : {comp[0]}\n"
                f"Citizen ID     : {comp[1]}\n"
                f"Authority ID   : {comp[2] if comp[2] else 'Not Assigned'}\n"
                f"Category       : {comp[3]}\n"
                f"Description    : {comp[4]}\n"
                f"Location       : {comp[5]}\n"
                f"Date Submitted : {comp[6]}\n"
                f"Status         : {comp[7]}\n"
                f"Resolution     : {resolution_text}\n"
                f"{'-'*50}\n"
            )
        return result
    except Exception as e:
        print(f"Debug: Error viewing complaints: {e}")
        return f"❌ Error viewing complaints: {e}"

def update_complaint(complaint_id, new_status, resolution, authority_id):
    if new_status not in ["Pending", "In Progress", "Resolved"]:
        return "❌ Invalid status."
    if resolution is None or resolution.strip() == "":
        resolution = "No resolution provided."
    try:
        cursor.execute("SELECT Department FROM Authority WHERE AuthorityID = %s", (authority_id,))
        auth_dept = cursor.fetchone()
        if not auth_dept:
            return "❌ Authority not found."
        auth_dept = auth_dept[0]

        cursor.execute("SELECT Category FROM Complaints WHERE ComplaintID = %s", (complaint_id,))
        complaint = cursor.fetchone()
        if not complaint:
            return "❌ Complaint not found."
        if complaint[0] != auth_dept:
            return f"❌ You can only update complaints in the {auth_dept} department."

        cursor.execute("SELECT ResolutionID FROM Resolutions WHERE ComplaintID = %s", (complaint_id,))
        existing_resolution = cursor.fetchone()
        
        if existing_resolution:
            cursor.execute(
                "UPDATE Resolutions SET ResolutionDetails = %s, DateResolved = CURRENT_TIMESTAMP, AssignedTo = %s "
                "WHERE ComplaintID = %s",
                (resolution, authority_id, complaint_id)
            )
        else:
            cursor.execute(
                "INSERT INTO Resolutions (ComplaintID, ResolutionDetails, AssignedTo) "
                "VALUES (%s, %s, %s)",
                (complaint_id, resolution, authority_id)
            )
            cursor.execute("SELECT LAST_INSERT_ID()")
            resolution_id = cursor.fetchone()[0]
            
            cursor.execute(
                "UPDATE Complaints SET Status = %s, ResolutionID = %s, AuthorityID = %s WHERE ComplaintID = %s",
                (new_status, resolution_id, authority_id, complaint_id)
            )
        mydb.commit()
        return f"✅ Complaint {complaint_id} updated to {new_status} with resolution provided."
    except Exception as e:
        mydb.rollback()
        print(f"Debug: Error updating complaint: {e}")
        return f"❌ Error updating complaint: {e}"

def view_feedback(complaint_id):
    try:
        cursor.execute(
            "SELECT FeedbackID, CitizenID, Rating, Comments, DateSubmitted "
            "FROM Feedback WHERE ComplaintID = %s ORDER BY DateSubmitted DESC",
            (complaint_id,)
        )
        feedbacks = cursor.fetchall()
        if not feedbacks:
            return "❌ No feedback found."
        
        result = ""
        for fb in feedbacks:
            result += (
                f"Feedback ID   : {fb[0]}\n"
                f"Citizen ID    : {fb[1]}\n"
                f"Rating        : {fb[2]}\n"
                f"Comments      : {fb[3]}\n"
                f"Date Submitted: {fb[4]}\n"
                f"{'-'*40}\n"
            )
        return result
    except Exception as e:
        print(f"Debug: Error viewing feedback: {e}")
        return f"❌ Error viewing feedback: {e}"

# PyQt6 Front-end
class ComplaintApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Complaint Management System")
        self.resize(500, 400)
        self.user_id = None
        self.role = None
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 12pt;
                color: #333;
            }
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QRadioButton {
                font-size: 12pt;
                color: #333;
            }
            QGroupBox {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 10px;
                font-size: 12pt;
                color: #333;
            }
        """)
        
        self.show_main_screen()

    def show_main_screen(self):
        self.clear_layout()
        
        header = QLabel("Complaint Management System")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(header)
        
        role_group = QGroupBox("Select Role")
        role_layout = QVBoxLayout(role_group)
        role_layout.setSpacing(10)
        
        self.role_citizen = QRadioButton("Citizen")
        self.role_authority = QRadioButton("Authority")
        self.role_citizen.setChecked(True)
        role_layout.addWidget(self.role_citizen)
        role_layout.addWidget(self.role_authority)
        self.main_layout.addWidget(role_group)
        
        signup_btn = QPushButton("Sign Up")
        login_btn = QPushButton("Login")
        exit_btn = QPushButton("Exit")
        
        signup_btn.clicked.connect(self.open_signup_dialog)
        login_btn.clicked.connect(self.open_login_dialog)
        exit_btn.clicked.connect(self.close_application)
        
        self.main_layout.addWidget(signup_btn)
        self.main_layout.addWidget(login_btn)
        self.main_layout.addWidget(exit_btn)
        self.main_layout.addStretch()

    def clear_layout(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def open_signup_dialog(self):
        self.role = "citizen" if self.role_citizen.isChecked() else "authority"
        dialog = SignupDialog(self.role, self)
        dialog.exec()

    def open_login_dialog(self):
        self.role = "citizen" if self.role_citizen.isChecked() else "authority"
        dialog = LoginDialog(self.role, self)
        if dialog.exec():
            self.show_menu()

    def show_menu(self):
        self.clear_layout()
        
        header = QLabel(f"{self.role.capitalize()} Menu")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(header)
        
        if self.role == "citizen":
            log_btn = QPushButton("Log a Complaint")
            status_btn = QPushButton("View Complaint Status")
            feedback_btn = QPushButton("Give Feedback")
            log_btn.clicked.connect(self.open_log_complaint_dialog)
            status_btn.clicked.connect(self.open_view_status_dialog)
            feedback_btn.clicked.connect(self.open_give_feedback_dialog)
            self.main_layout.addWidget(log_btn)
            self.main_layout.addWidget(status_btn)
            self.main_layout.addWidget(feedback_btn)
        else:
            complaints_btn = QPushButton("View Complaints")
            feedback_btn = QPushButton("View Feedback")
            complaints_btn.clicked.connect(self.open_view_complaints_dialog)
            feedback_btn.clicked.connect(self.open_view_feedback_dialog)
            self.main_layout.addWidget(complaints_btn)
            self.main_layout.addWidget(feedback_btn)
        
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.logout)
        self.main_layout.addWidget(logout_btn)
        self.main_layout.addStretch()

    def open_log_complaint_dialog(self):
        dialog = LogComplaintDialog(self.user_id, self)
        dialog.exec()

    def open_view_status_dialog(self):
        dialog = ViewStatusDialog(self)
        dialog.exec()

    def open_give_feedback_dialog(self):
        dialog = GiveFeedbackDialog(self.user_id, self)
        dialog.exec()

    def open_view_complaints_dialog(self):
        dialog = ViewComplaintsDialog(self.user_id, self)
        dialog.exec()

    def open_view_feedback_dialog(self):
        dialog = ViewFeedbackDialog(self)
        dialog.exec()

    def logout(self):
        self.user_id = None
        self.role = None
        self.show_main_screen()

    def close_application(self):
        try:
            cursor.close()
            mydb.close()
            print("🔌 Database connection closed.")
        except Exception as e:
            print(f"❌ Error closing database: {e}")
        self.close()

# Dialog Classes
class SignupDialog(QDialog):
    def __init__(self, role, parent=None):
        super().__init__(parent)
        self.role = role
        self.setWindowTitle(f"Sign Up - {role.capitalize()}")
        self.resize(400, 500)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                font-size: 12pt;
                color: #333;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 6px;
                font-size: 12pt;
                color: #333;
                background-color: #fff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
            }
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        header = QLabel(f"Sign Up as {role.capitalize()}")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(header)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter your name")
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Enter your email")
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("Enter your phone number")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Enter your password")
        
        self.layout.addWidget(QLabel("Name:"))
        self.layout.addWidget(self.name_edit)
        self.layout.addWidget(QLabel("Email:"))
        self.layout.addWidget(self.email_edit)
        self.layout.addWidget(QLabel("Phone:"))
        self.layout.addWidget(self.phone_edit)
        self.layout.addWidget(QLabel("Password:"))
        self.layout.addWidget(self.password_edit)
        
        if role == "citizen":
            self.address_edit = QLineEdit()
            self.address_edit.setPlaceholderText("Enter your address")
            self.layout.addWidget(QLabel("Address:"))
            self.layout.addWidget(self.address_edit)
            self.department_combo = None
            self.other_dept_edit = None
        else:
            self.department_combo = QComboBox()
            departments = ["Sanitation", "Electricity", "Water Supply", "Public Safety", 
                          "Health", "Transportation", "Other"]
            self.department_combo.addItems(departments)
            self.other_dept_edit = QLineEdit()
            self.other_dept_edit.setPlaceholderText("Specify department")
            self.layout.addWidget(QLabel("Department:"))
            self.layout.addWidget(self.department_combo)
            self.layout.addWidget(QLabel("Other Department (if selected):"))
            self.layout.addWidget(self.other_dept_edit)
            self.address_edit = None
        
        btn_layout = QHBoxLayout()
        submit_btn = QPushButton("Submit")
        cancel_btn = QPushButton("Cancel")
        submit_btn.clicked.connect(self.submit)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(submit_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        self.layout.addStretch()

    def submit(self):
        name = self.name_edit.text().strip()
        email = self.email_edit.text().strip()
        phone = self.phone_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if self.role == "citizen":
            address = self.address_edit.text().strip()
            department = None
        else:
            department = self.department_combo.currentText()
            if department == "Other":
                department = self.other_dept_edit.text().strip()
            address = None
        
        result = sign_up_user(self.role, name, email, phone, password, address, department)
        msg = QMessageBox(self)
        msg.setWindowTitle("Result")
        msg.setText(result)
        msg.setStyleSheet("QLabel { font-size: 12pt; color: #333; } QPushButton { font-size: 12pt; color: #333; }")
        if "✅" in result:
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            self.accept()
        else:
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()

class LoginDialog(QDialog):
    def __init__(self, role, parent=None):
        super().__init__(parent)
        self.role = role
        self.main_window = parent
        self.setWindowTitle(f"Login - {role.capitalize()}")
        self.resize(350, 300)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                font-size: 12pt;
                color: #333;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 6px;
                font-size: 12pt;
                color: #333;
                background-color: #fff;
            }
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        header = QLabel(f"Login as {role.capitalize()}")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(header)
        
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Enter your email")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Enter your password")
        
        self.layout.addWidget(QLabel("Email:"))
        self.layout.addWidget(self.email_edit)
        self.layout.addWidget(QLabel("Password:"))
        self.layout.addWidget(self.password_edit)
        
        btn_layout = QHBoxLayout()
        submit_btn = QPushButton("Login")
        cancel_btn = QPushButton("Cancel")
        submit_btn.clicked.connect(self.submit)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(submit_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        self.layout.addStretch()

    def submit(self):
        email = self.email_edit.text().strip()
        password = self.password_edit.text().strip()
        user_id, result = login_user(email, password, self.role)
        msg = QMessageBox(self)
        msg.setWindowTitle("Result")
        msg.setText(result)
        msg.setStyleSheet("QLabel { font-size: 12pt; color: #333; } QPushButton { font-size: 12pt; color: #333; }")
        if user_id:
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            self.main_window.user_id = user_id
            self.accept()
        else:
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()

class LogComplaintDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Log Complaint")
        self.resize(400, 400)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                font-size: 12pt;
                color: #333;
            }
            QComboBox, QTextEdit, QLineEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 6px;
                font-size: 12pt;
                color: #333;
                background-color: #fff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
            }
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        header = QLabel("Log a Complaint")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(header)
        
        self.category_combo = QComboBox()
        categories = ["Sanitation", "Electricity", "Water Supply", "Public Safety", 
                      "Health", "Transportation", "Other"]
        self.category_combo.addItems(categories)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Describe the issue")
        self.loc_edit = QLineEdit()
        self.loc_edit.setPlaceholderText("Enter location")
        
        self.layout.addWidget(QLabel("Category:"))
        self.layout.addWidget(self.category_combo)
        self.layout.addWidget(QLabel("Description:"))
        self.layout.addWidget(self.desc_edit)
        self.layout.addWidget(QLabel("Location:"))
        self.layout.addWidget(self.loc_edit)
        
        btn_layout = QHBoxLayout()
        submit_btn = QPushButton("Submit")
        cancel_btn = QPushButton("Cancel")
        submit_btn.clicked.connect(self.submit)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(submit_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        self.layout.addStretch()

    def submit(self):
        result = log_complaint(
            self.user_id,
            self.category_combo.currentText().strip(),
            self.desc_edit.toPlainText().strip(),
            self.loc_edit.text().strip()
        )
        msg = QMessageBox(self)
        msg.setWindowTitle("Result")
        msg.setText(result)
        msg.setStyleSheet("QLabel { font-size: 12pt; color: #333; } QPushButton { font-size: 12pt; color: #333; }")
        if "✅" in result:
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            self.accept()
        else:
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()

class ViewStatusDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("View Complaint Status")
        self.resize(400, 350)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                font-size: 12pt;
                color: #333;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 6px;
                font-size: 12pt;
                color: #333;
                background-color: #fff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
            }
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        header = QLabel("View Complaint Status")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(header)
        
        self.view_option_combo = QComboBox()
        self.view_option_combo.addItems(["All Complaints", "By Complaint ID"])
        self.view_option_combo.currentIndexChanged.connect(self.toggle_complaint_id_input)
        self.layout.addWidget(QLabel("View Option:"))
        self.layout.addWidget(self.view_option_combo)
        
        self.complaint_id_edit = QLineEdit()
        self.complaint_id_edit.setPlaceholderText("Enter Complaint ID")
        self.complaint_id_label = QLabel("Complaint ID:")
        self.layout.addWidget(self.complaint_id_label)
        self.layout.addWidget(self.complaint_id_edit)
        
        btn_layout = QHBoxLayout()
        check_btn = QPushButton("Check Status")
        cancel_btn = QPushButton("Cancel")
        check_btn.clicked.connect(self.submit)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(check_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        self.layout.addStretch()

        self.toggle_complaint_id_input()

    def toggle_complaint_id_input(self):
        is_by_id = self.view_option_combo.currentText() == "By Complaint ID"
        self.complaint_id_label.setVisible(is_by_id)
        self.complaint_id_edit.setVisible(is_by_id)

    def submit(self):
        view_all = self.view_option_combo.currentText() == "All Complaints"
        complaint_id = self.complaint_id_edit.text().strip() if not view_all else None
        citizen_id = self.main_window.user_id if self.main_window.role == "citizen" else None
        
        if view_all and not citizen_id:
            result = "❌ Only citizens can view all complaints."
        elif not view_all and not complaint_id:
            result = "❌ Please enter a Complaint ID."
        else:
            result = view_status(complaint_id, citizen_id, view_all)
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Complaint Status")
        msg.setText(result)
        msg.setStyleSheet("QLabel { font-size: 12pt; color: #333; } QPushButton { font-size: 12pt; color: #333; }")
        if "❌" in result:
            msg.setIcon(QMessageBox.Icon.Warning)
        else:
            msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

class GiveFeedbackDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Give Feedback")
        self.resize(400, 400)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                font-size: 12pt;
                color: #333;
            }
            QLineEdit, QComboBox, QTextEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 6px;
                font-size: 12pt;
                color: #333;
                background-color: #fff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
            }
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        header = QLabel("Give Feedback")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(header)
        
        self.complaint_id_edit = QLineEdit()
        self.complaint_id_edit.setPlaceholderText("Enter Complaint ID")
        self.rating_combo = QComboBox()
        self.rating_combo.addItems(["1", "2", "3", "4", "5"])
        self.comments_edit = QTextEdit()
        self.comments_edit.setPlaceholderText("Enter your comments")
        
        self.layout.addWidget(QLabel("Complaint ID:"))
        self.layout.addWidget(self.complaint_id_edit)
        self.layout.addWidget(QLabel("Rating (1-5):"))
        self.layout.addWidget(self.rating_combo)
        self.layout.addWidget(QLabel("Comments:"))
        self.layout.addWidget(self.comments_edit)
        
        btn_layout = QHBoxLayout()
        submit_btn = QPushButton("Submit")
        cancel_btn = QPushButton("Cancel")
        submit_btn.clicked.connect(self.submit)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(submit_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        self.layout.addStretch()

    def submit(self):
        result = give_feedback(
            self.complaint_id_edit.text().strip(),
            self.user_id,
            self.rating_combo.currentText().strip(),
            self.comments_edit.toPlainText().strip()
        )
        msg = QMessageBox(self)
        msg.setWindowTitle("Result")
        msg.setText(result)
        msg.setStyleSheet("QLabel { font-size: 12pt; color: #333; } QPushButton { font-size: 12pt; color: #333; }")
        if "✅" in result:
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            self.accept()
        else:
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()

class ViewComplaintsDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("View Complaints")
        self.resize(700, 550)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                font-size: 12pt;
                color: #333;
            }
            QTextEdit, QLineEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 6px;
                font-size: 12pt;
                color: #333;
                background-color: #fff;
            }
            QTextEdit[readOnly="true"] {
                background-color: #f9f9f9;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
            }
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        header = QLabel("View Complaints")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(header)
        
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setText(view_complaints(self.user_id))
        self.layout.addWidget(self.text_area)
        
        self.complaint_id_edit = QLineEdit()
        self.complaint_id_edit.setPlaceholderText("Enter Complaint ID")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Pending", "In Progress", "Resolved"])
        self.resolution_edit = QTextEdit()
        self.resolution_edit.setPlaceholderText("Enter resolution")
        self.resolution_edit.setFixedHeight(80)
        
        self.layout.addWidget(QLabel("Complaint ID to Update:"))
        self.layout.addWidget(self.complaint_id_edit)
        self.layout.addWidget(QLabel("New Status:"))
        self.layout.addWidget(self.status_combo)
        self.layout.addWidget(QLabel("Resolution:"))
        self.layout.addWidget(self.resolution_edit)
        
        btn_layout = QHBoxLayout()
        update_btn = QPushButton("Update Status & Resolution")
        close_btn = QPushButton("Close")
        update_btn.clicked.connect(self.submit)
        close_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(update_btn)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        self.layout.addStretch()

    def submit(self):
        complaint_id = self.complaint_id_edit.text().strip()
        new_status = self.status_combo.currentText()
        resolution = self.resolution_edit.toPlainText().strip()
        result = update_complaint(complaint_id, new_status, resolution, self.user_id)
        msg = QMessageBox(self)
        msg.setWindowTitle("Result")
        msg.setText(result)
        msg.setStyleSheet("QLabel { font-size: 12pt; color: #333; } QPushButton { font-size: 12pt; color: #333; }")
        if "✅" in result:
            msg.setIcon(QMessageBox.Icon.Information)
            self.text_area.setText(view_complaints(self.user_id))
            self.complaint_id_edit.clear()
            self.resolution_edit.clear()
            msg.exec()
        else:
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()

class ViewFeedbackDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("View Feedback")
        self.resize(700, 500)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                font-size: 12pt;
                color: #333;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 6px;
                font-size: 12pt;
                color: #333;
                background-color: #f9f9f9;
            }
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        header = QLabel("View Feedback")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(header)
        
        self.complaint_id_edit = QLineEdit()
        self.complaint_id_edit.setPlaceholderText("Enter Complaint ID")
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.layout.addWidget(QLabel("Complaint ID:"))
        self.layout.addWidget(self.complaint_id_edit)
        self.layout.addWidget(self.text_area)
        
        btn_layout = QHBoxLayout()
        show_btn = QPushButton("Show Feedback")
        close_btn = QPushButton("Cancel")
        show_btn.clicked.connect(self.submit)
        close_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(show_btn)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        self.layout.addStretch()

    def submit(self):
        result = view_feedback(self.complaint_id_edit.text().strip())
        self.text_area.setText(result)
        if "❌" in result:
            msg = QMessageBox(self)
            msg.setWindowTitle("Result")
            msg.setText(result)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setStyleSheet("QLabel { font-size: 12pt; color: #333; } QPushButton { font-size: 12pt; color: #333; }")
            msg.exec()

# Run the application
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        window = ComplaintApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)