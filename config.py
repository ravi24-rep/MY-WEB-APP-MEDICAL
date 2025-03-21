# config.py
db_config = {
    'host': '127.0.0.1',  # From your MySQL Workbench connection
    'port': 3306,         # From your MySQL Workbench connection
    'user': 'root',       # From your MySQL Workbench connection
    'password': 'Ravidhiya@1924',       # No password set in your MySQL Workbench connection
    'database': 'medical_fund_db'
}

# Email configuration for Flask-Mail
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'ravidynamo1924@gmail.com'  # Replace with your email
MAIL_PASSWORD = 'Ravidhiya@1924'  # Replace with your app-specific password