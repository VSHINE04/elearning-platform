# eLearning Platform

A comprehensive eLearning platform built with Flask and MongoDB that allows teachers to create courses, manage assignments, and grade student submissions, while enabling students to enroll in courses, submit assignments, and track their progress.

## Features

- **User Authentication**
  - Separate login for teachers and students
  - Secure password hashing
  - Session management

- **Course Management**
  - Create and manage courses
  - Course enrollment system
  - Course progress tracking

- **Assignment System**
  - Create and manage assignments
  - File upload support
  - Due date management
  - Assignment submission tracking

- **Grading System**
  - Grade student submissions
  - Provide feedback
  - Track student progress
  - Calculate average grades

- **Student Dashboard**
  - View enrolled courses
  - Track assignment progress
  - View grades and feedback
  - Monitor overall performance

- **Teacher Dashboard**
  - Manage courses and assignments
  - Grade submissions
  - Track student progress
  - View submission statistics

## Tech Stack

- **Backend**: Python, Flask
- **Database**: MongoDB
- **Frontend**: HTML, CSS, Bootstrap 5
- **File Storage**: Local file system
- **Authentication**: Flask session management

## Prerequisites

- Python 3.8 or higher
- MongoDB
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/elearning-platform.git
cd elearning-platform
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up MongoDB:
- Install MongoDB on your system
- Start the MongoDB service
- Create a database named 'elearning_db'

5. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
elearning-platform/
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── .gitignore         # Git ignore file
├── README.md          # Project documentation
├── uploads/           # File upload directory
└── templates/         # HTML templates
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── courses.html
    ├── assignments.html
    ├── student_dashboard.html
    └── teacher_dashboard.html
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Bootstrap 5 for the UI components
- Flask documentation for the web framework
- MongoDB documentation for the database 