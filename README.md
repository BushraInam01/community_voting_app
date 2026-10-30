
# Community Voting & Polling App

A Django-based Community Voting & Polling Application that allows users to create polls, participate in voting, and view live results.

## Features

- Create polls with multiple-choice or ranked voting.
- Support anonymous and authenticated voting.
- Prevent duplicate votes using database constraints.
- Automatically generate unique poll slugs.
- Display live poll results using HTMX.
- Automatically freeze polls after their expiry date.
- Embed polls using an iframe-safe view.
- Generate anonymous voter tokens using Django signing.
- Custom template tags for percentage calculations.
- Content Security Policy (CSP) enforcement.

## Technologies Used

- Python
- Django
- SQLite
- HTML and CSS
- HTMX
- django-autoslug

## Project Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd community_voting_app
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
```

### 3. Activate the virtual environment

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file in the project root:

```env
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

Generate a new secret key for your own environment. Never commit your `.env` file.

### 6. Apply migrations

```bash
python3 manage.py migrate
```

### 7. Run the development server

```bash
python3 manage.py runserver
```

Open the application at:

http://127.0.0.1:8000/

## Running Tests

Run the voting tests:

```bash
python3 manage.py test voting
```

These tests verify database-level duplicate-voting and ranked-voting constraints.

Run all project tests:

```bash
python3 manage.py test
```

## Concurrency and Database Locking

The voting submission process uses `transaction.atomic()` and `select_for_update()` to protect voting operations against duplicate submissions and concurrent updates.

The development database is SQLite. Django's SQLite backend does not support row-level locking through `SELECT FOR UPDATE`. Therefore, `select_for_update()` does not acquire a row-level lock when running with SQLite.

Database-level unique constraints provide additional protection against duplicate vote and ranking records.

The SQLite tests verify these database constraints, but they do not prove correct behavior under simultaneous concurrent requests.

For realistic row-level locking and concurrency testing, PostgreSQL is recommended. Such testing should use Django's `TransactionTestCase` with separate database connections.

## Security

- Secret keys are loaded from environment variables.
- `.env` is excluded from version control.
- Authentication is required for non-anonymous polls.
- Anonymous voter tokens are signed using Django's signing framework.
- Duplicate voting is restricted through database constraints.
- Poll expiry and frozen status are checked before accepting votes.
- Content Security Policy is enforced.

## License

This project was developed as a Django learning assignment.
