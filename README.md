# Alpha One Labs Education Platform

A modern, feature-rich education platform built with Django and Tailwind CSS that enables seamless learning experiences through course creation, peer connections, study groups, and interactive forums.

## Project Overview

Alpha One Labs is an education platform designed to facilitate both learning and teaching. The platform provides a comprehensive environment where educators can create and manage courses, while students can learn, collaborate, and engage with peers. With features like study groups, peer connections, and discussion forums, we aim to create a collaborative learning environment that goes beyond traditional online education.

## Features

### For Students

- 📚 Course enrollment and management
- 👥 Peer-to-peer connections and messaging
- 📝 Study group creation and participation
- 💬 Interactive discussion forums
- 📊 Progress tracking and analytics
- 🌟 Submit links and receive grades with feedback
- 🌙 Dark mode support
- 📱 Responsive design for all devices

### For Teachers

- 📝 Course creation and management
- 📊 Student progress monitoring
- 📈 Analytics dashboard
- 📣 Marketing tools for course promotion
- 💯 Grade submitted links and provide feedback
- 💰 Payment integration with Stripe
- 📧 Email marketing capabilities
- 🔔 Automated notifications

### Technical Features

- 🔒 Secure authentication system
- 🌐 Internationalization support
- 🚀 Performance optimized
- 📦 Modular architecture
- ⚡ Real-time updates
- 🔍 Search functionality
- 🎨 Customizable UI
- 🏆 "Get a Grade" system with academic grading scale

## Tech Stack

### Backend

- Python 3.10+
- Django 4.x
- Celery for async tasks
- Redis for caching
- PostgreSQL (production) / SQLite (development)

### Frontend

- Tailwind CSS
- Alpine.js
- Font Awesome icons
- JavaScript (Vanilla)

### Infrastructure

- Docker support
- Nginx
- Gunicorn
- SendGrid for emails
- Stripe for payments

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- pip or poetry for package management
- Git

### Local Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/education-website.git
   cd education-website
   ```

2. Set up a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   # Using pip
   pip install -r requirements.txt

   # Using poetry
   poetry install
   ```

4. Set up environment variables:

   ```bash
   cp .env.sample .env
   # Edit .env with your configuration
   ```

5. Run migrations:

   ```bash
   python manage.py migrate
   ```

6. Create a superuser:

   ```bash
   python manage.py createsuperuser
   ```

7. Create test data:

   ```bash
   python manage.py create_test_data
   ```

8. Run the development server:

   ```bash
   python manage.py runserver
   ```

9. Visit [http://localhost:8000](http://localhost:8000) in your browser.

### Docker Setup

1. Build the Docker image:

   ```bash
   docker build -t education-website .
   ```

2. Run the Docker container:

   ```bash
   docker run -d -p 8000:8000 education-website
   ```

3. Visit [http://localhost:8000](http://localhost:8000) in your browser.

### Admin Credentials:

- **Email:** `admin@example.com`
- **Password:** `adminpassword`

## Environment Variables Configuration

Copy `.env.sample` to `.env` and configure the variables.

## Development Guidelines

### Code Style

- Follow PEP 8 guidelines for Python code.
- Use **Black** for code formatting.
- Use **isort** for import sorting.
- Follow Django's coding style guide.
- Use **ESLint** for JavaScript code.

### Git Workflow

1. Create a new branch for each feature/bugfix.
2. Follow **conventional commits** for commit messages.
3. Submit **pull requests** for review.
4. Ensure all **tests pass** before merging.

### Testing

- Write unit tests for new features.
- Run tests before committing:

  ```bash
  python manage.py test
  ```

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality:

```bash
pre-commit install
pre-commit run --all-files
```

### Documentation

- Document all new features and API endpoints
- Update README.md when adding major features
- Use docstrings for Python functions and classes
- Comment complex logic

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and contribute to the project.

## Support

If you encounter any issues or need support, please:

1. Search existing [Issues](https://github.com/alphaonelabs/education-website/issues)
2. Create a new issue if your problem persists

## Feature Guides

### Get a Grade Feature

The "Get a Grade" feature allows users to submit links (URLs) for review and grading by other members of the platform. This feature enhances collaborative learning by enabling peer feedback and assessment.

#### Core Functionality

1. **Link Submission**:
   - Users can submit URLs (articles, projects, resources) for grading
   - Links can be categorized by type (e.g., blog post, project, documentation)
   - Optional description field for providing context
   - Submitted links are stored with metadata including submission date and submitter

2. **Grading System**:
   - Standard academic grading scale (A+, A, A-, B+, B, B-, C+, C, C-, D, F)
   - Color-coded grade display for visual clarity
   - Comment requirement for grades below A to ensure constructive feedback
   - Support for multiple grades from different users

3. **User Interface**:
   - List view of all gradeable links with filtering options
   - Detailed view of individual links with submission metadata
   - Grading form with intuitive grade selection and comment field
   - Responsive design supporting both desktop and mobile access

#### Implementation Details

1. **Models**:
   - `GradeableLink`: Stores link information (URL, title, description, submission date, user)
   - `LinkGrade`: Stores grade information (grade value, comments, grader, timestamp)
   - Relationship mapping between users, links, and grades

2. **Views**:
   - `gradeable_link_list`: Displays all links available for grading
   - `gradeable_link_detail`: Shows detailed information about a specific link
   - `grade_link`: Provides interface for submitting grades
   - `my_submitted_links`: Shows links submitted by the current user
   - `my_graded_links`: Shows links graded by the current user

3. **Templates**:
   - `grade_links/list.html`: List of gradeable links
   - `grade_links/detail.html`: Detailed view of a link
   - `grade_links/grade_link.html`: Form for grading a link
   - `grade_links/my_submitted.html`: User's submitted links
   - `grade_links/my_graded.html`: Links graded by the user

4. **Forms**:
   - `GradeLinkForm`: Form for submitting grades with validation

5. **Workflow**:
   - User submits a link for grading
   - Link appears in the gradeable links list
   - Other users can view and grade the link
   - Grades and comments are displayed on the link detail page
   - Original submitter receives notifications of new grades

#### Security and Validation

1. **Authentication**:
   - All grading features require user authentication
   - Users cannot grade their own submissions
   - Audit trail of who submitted grades and when

2. **Validation**:
   - URL validity checking
   - Required comments for lower grades
   - Protection against duplicate submissions
   - Rate limiting to prevent spam

#### Usage Example

1. **Submitting a Link**:
   - Navigate to "Get a Grade" in the main navigation
   - Click "Submit a Link" button
   - Fill in the URL, title, optional description, and select link type
   - Submit the form

2. **Grading a Link**:
   - Browse the list of gradeable links
   - Select a link to grade
   - On the link detail page, click "Grade This Link"
   - Select a grade (A+ through F)
   - Provide comments (required for grades below A)
   - Submit the grade

3. **Viewing Grades**:
   - Access the link detail page to see all grades
   - Visit "My Submitted Links" to see grades for your submissions
   - Check "My Graded Links" to see links you've graded

#### Technical Notes for Maintainers

1. **JavaScript Functionality**:
   - `grade_link.html` includes JS to dynamically require comments for grades below A
   - Form validation occurs both client-side and server-side

2. **Styling**:
   - Grade colors are consistently applied across the application
   - Tailwind CSS classes are used for responsive design
   - Dark mode support is implemented

3. **Future Enhancements**:
   - Analytics dashboard for grading patterns
   - Advanced filtering options
   - Integration with notification system
   - Grading rubrics for specific link types

4. **Troubleshooting**:
   - If grades aren't displaying, check for proper relationship between `GradeableLink` and `LinkGrade` models
   - For form submission issues, verify CSRF token is properly included
   - JavaScript issues may occur if the comment field ID doesn't match the form field ID

## Acknowledgments

- Thanks to all contributors who have helped shape this project
- Built with ❤️ by the Alpha One Labs team
