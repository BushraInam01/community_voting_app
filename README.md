
# Community Voting & Polling App

A Django-based Community Voting & Polling Application that allows users to create polls, participate in voting, and view live results.

## Features

- Create polls with multiple-choice or ranked voting.
- Ranked polls are tallied with instant-runoff voting (round-by-round view).
- Support anonymous and authenticated voting.
- Prevent duplicate votes using database constraints.
- Automatically generate unique, readable poll slugs (non-Latin titles are transliterated; names that would clash with fixed routes are avoided).
- Display live poll results using HTMX (self-hosted, no third-party scripts).
- Polls stop accepting votes at their expiry date; creators can also close a poll early.
- Embed polls read-only in an iframe on other sites (`/polls/embed/<slug>/`).
- Generate anonymous voter tokens using Django signing.
- Rate limiting for anonymous votes and login attempts (per IP + username, per IP, and per username).
- Polls need 2 to 10 different options (duplicates such as "Yes" / "yes" are rejected).
- Votes are protected in the admin: options cannot be added, edited or deleted, and the voting mode cannot be changed, once a poll has votes.
- Content Security Policy (CSP) enforcement.

## Technologies Used

- Python **3.12 or newer** (required by Django 6.1)
- Django 6.1
- SQLite
- HTML and CSS
- HTMX
- django-autoslug (with Unidecode for transliteration)

## Project Setup

**Requirements:** Python 3.12+ (check with `python3 --version`). On older Python versions `pip install -r requirements.txt` fails with a confusing "no matching distribution found" error, because Django 6.1 does not support them.

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

Copy the example file and edit it:

```bash
cp .env.example .env
```

At minimum set `DJANGO_SECRET_KEY`, `DEBUG` and `ALLOWED_HOSTS`. Generate a new secret key for your own environment. Never commit your `.env` file. `.env.example` documents every optional setting (time zone, embed origins, rate limits, HTTPS/email options).

`TIME_ZONE` controls how the expiry time typed into the create-poll form is interpreted (the form displays the zone). It defaults to `UTC`; set it to e.g. `Asia/Karachi` for local times.

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

The suite covers the database constraints, the voting flows (named, anonymous and ranked), instant-runoff tallying, results, poll creation/closing, the embed headers, slug generation, registration and login lockout. The same tests run in GitHub Actions on every push.

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
- Content Security Policy is enforced. All scripts (including htmx) are served from this site; only the embed view relaxes `frame-ancestors` (see `EMBED_FRAME_ANCESTORS`).
- Session and CSRF cookies are `Secure` when `DEBUG=False`; HTTPS redirect and HSTS are configurable (run `python manage.py check --deploy` before deploying).
- Failed logins are throttled three ways: per IP + username (5 failures, 15-minute lockout), per IP (50 failures per hour) and per username (30 failures per hour). The per-username limit is deliberately loose, because someone could use it to temporarily lock another person's account.

### Known limitation: anonymous voting

An anonymous voter is identified by a signed cookie, which identifies a *browser*, not a *person*. Clearing cookies or using a private window yields a new identity, so anonymous polls cannot guarantee one vote per person. As a mitigation, anonymous votes are limited per poll per network address (`ANONYMOUS_VOTES_PER_IP`, default 10 per day). This slows ballot stuffing but is not a guarantee, and it can affect many legitimate voters behind one shared address (offices, campuses, mobile carriers), so tune it to your audience. If one-person-one-vote matters, create the poll with anonymous voting turned off so that login is required.

Rate-limit counters use Django's cache. The default per-process memory cache is fine for development; use a shared cache (e.g. Redis) when running several workers. Clients are identified by `REMOTE_ADDR`, so behind a reverse proxy make sure the proxy/WSGI server passes the real client address.

## License

This project was developed as a Django learning assignment.
