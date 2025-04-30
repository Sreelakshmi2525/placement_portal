# 🎓 Placement Portal

A web-based Placement Portal developed using Django. This application serves as a platform to manage student profiles, placement activities, job postings, and more. It supports both admin and student functionalities.

---

##  Features

- Student login and registration
- Admin dashboard to manage jobs and users
- Static frontend using Bootstrap and custom styles
- SQLite3 as the default database
- Organized static resources (CSS, images, banners)

---

##  Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/placement_portal.git
cd placement_portal
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```
Here is the updated section of the `README.md` that instructs users to create the `.env` file with the specific variables:

---

### 4. Create a `.env` File

For security reasons, store sensitive credentials (like your LinkedIn credentials, email configuration, etc.) in a `.env` file. Follow these steps:

1. **Create a `.env` file** in the root directory of the project.
   
2. **Add your credentials to the `.env` file** in the following format:

```
LINKEDIN_EMAIL="your-linkedin-email"
LINKEDIN_PASSWORD="your-linkedin-password"
EMAIL_HOST="smtp.gmail.com"
EMAIL_PORT="587"
EMAIL_USE_TLS="True"
EMAIL_HOST_USER="your-email@gmail.com"  # Your email
EMAIL_HOST_PASSWORD="your-email-password-or-app-password"  # Your email password or app password
DEFAULT_FROM_EMAIL="your-email@gmail.com"
INSTITUTION_NAME="Your Institution Name"
```

3. Ensure that the `.env` file is added to `.gitignore` to prevent it from being pushed to the repository.
By creating this `.env` file and adding the necessary credentials, you will be able to securely configure the application and ensure sensitive data is not exposed.

---

### 5. Run the Server

```bash
python manage.py migrate
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

- **Backend**: Django (Python)
- **Database**: SQLite (can be switched to PostgreSQL/MySQL)
- **Frontend**: HTML, CSS (Bootstrap), static files


---

##  Author  
🔗 [GitHub Profile](https://github.com/Sreelakshmi2525)

```
