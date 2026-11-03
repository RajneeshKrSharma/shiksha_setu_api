# Shiksha Setu APIs

Django REST backend for the Shiksha Setu Flutter app (single school).
Lives beside the app so both are developed in one context.

## Architecture
Every app has three layers and depends in one direction: `api → domain ← data`.

```
apps/<app>/
├── domain/   pure Python: entities, repository and port interfaces, services, usecases/
├── data/     Django models, repository implementations, framework adapters
└── api/      serializers, views, permissions, urls (thin: no business rules)
```

`config/container.py` is the only place that picks the implementation behind each
interface. Business rules live in domain use cases; views only call them.

Built so far: `core` (entity/usecase/repository bases, generic member CRUD, error handling,
audit log, throttling, field encryption), `accounts` (sign-in, roles, Vice Principal
permissions), `school` (name, season timings and periods, holidays, notices) and `students`
(classes, students, dress and books, fees) and `teachers` (teachers, class allotment, daily
lessons), `staff` (staff, vans, fuel bills) and `attendance` (students, and teachers and
staff with login and logout time), `requests` (leaves and meeting queries) and `exams`
(schedule, question bank, papers, marks, results) and `payments` (salaries and payments for
teachers and staff) and `analytics` (data for the Principal's graphs). All ten apps are built.

## Analytics
Read-only data for graphs, for the Principal (or a Vice Principal given `view_analytics`).
Nothing is stored; each graph is worked out from the other modules. Every graph answers with a
`period` and the `points` to draw. Dates are `from` and `to` (YYYY-MM-DD); left out, a daily
graph covers the last 30 days (at most 92) and a monthly graph the last 6 months (at most 24).
- Student attendance: per day, present, late, absent and the percentage who came (present plus
  late); days nobody was marked are left out. One class or the whole school.
- Fees: collected per month by fee, and what each class still owes.
- Exam averages: per exam, students marked, absent, average marks and percentage.
- Teacher and staff attendance: per day, present, late, absent, leave, not in yet; on a
  holiday only those who came are counted.
- Payments: paid out per month (salary and fuel), and what teachers and staff are still owed.
- Fuel: per month and van, bills, litres, money, distance and kilometres per litre.
- Lessons: per day, lessons recorded out of those expected. The expected number is today's
  allotments, since the school keeps no history of them.

## Payments
- Teachers and staff are paid. A salary is a monthly amount from a month onwards; a raise
  applies from its month and earlier months keep the old rate. A month is owed from the first
  salary month up to the current month. The Principal is not paid here, nor the Vice Principal.
- A payment goes towards one month's salary or one approved fuel bill (staff only). It can be
  part of what is owed (an instalment) but never more. Each has a receipt number (`P-000001`),
  a date, a way (cash, bank, upi) and an optional note.
- A fuel bill is owed to the van's driver once approved: the person who submitted it for their
  own van, or the van's driver when the Principal entered it. A bill of a van with no driver
  is owed to nobody.
- A salary cannot start in, or before, a month that already has a salary payment.
- The Principal manages teachers (`manage_teacher_payments`) and staff
  (`manage_staff_payments`); the Vice Principal can be given either. Every teacher and staff
  member sees only their own account (`view_own_payments`).
- Nothing is deducted for absence or leave; the salary is the amount set.

## Exams
- The Principal schedules an exam: type (unit test, mid term, annual), class, subject, day and
  total marks. The class and subject must already have a teacher (allotment), who conducts
  it; the subject takes the spelling of the allotment. Marks are whole numbers.
- Question bank: each teacher has their own, split into units per class and subject they
  take. A question has text, marks and a type (mcq, short, long). Only the owner changes a
  bank; the Principal can read every bank.
- Paper: the exam's teacher picks questions from their own bank for that class and subject.
  The marks must add up to the exam's total before it can be sent. The Principal approves
  it, or rejects it with a reason and the teacher fixes and sends it again. An approved paper
  is final, and each paper keeps its own copy of the questions.
- Marks: the exam's teacher (or the Principal) enters each student's marks, or marks them
  absent, once the exam day has come. The total cannot change after marks are entered or the
  paper is sent, and an exam with marks cannot be cancelled.
- Results: marks and percentage per student in each exam, with the class's average, highest
  and lowest (absent students left out); and each student's exams with a total over those
  they have marks in. There is no pass mark or grade yet. A teacher sees only the exams of the
  subjects they take.

## Requests
- A leave is a first day, a last day and a reason. It can start today or later, and not
  overlap another pending or approved leave of the same person. Teachers, staff and the
  Vice Principal can ask. The Principal (or a Vice Principal given `approve_leaves`) approves
  or rejects it. An approved leave shows as `leave` on the attendance board, unless the
  person checks in anyway.
- A meeting query is a subject, optional details and an optional preferred day. The Principal
  (or a Vice Principal given `decide_requests`) approves it by fixing the meeting's day and
  time, or rejects it.
- Rejecting needs a reason. Nobody can decide their own request. The person who asked can
  withdraw it while it waits. Everyone sees their own requests; whoever may decide a kind
  also sees everyone's of that kind.
- All kinds share one table and one set of rules; a new kind is a new class and a mapper.

## Attendance
- Students: present, absent or late, once a day for a class (not per period). A teacher marks
  the classes allotted to them, for today only; the Principal can mark any class and fix a
  past day (`correct_attendance`). Students left out of a list stay unmarked; marking a
  student again replaces the mark. A report gives each student's present, late and absent
  days between two dates.
- Teachers, staff and the Vice Principal log in and out themselves; the server records the
  time. A check-in after the school opens (the active season's opening time) is late; with no
  timing set, nobody is late. The Principal's own check-in is kept but not on the board.
- The Principal's board shows each person for a day: present, late, absent (a past day with
  no check-in, not a holiday), holiday, or not in yet (today). It does not know weekends.
- The Principal (or a Vice Principal given `correct_attendance`) can fill in or fix a day's
  check-in and check-out times; this is audited.

## Staff
- A staff member (driver, helper, ...) is a sign-in account with the staff role, a name, an
  email and a job title, added by the Principal like a teacher. Removing makes them inactive.
- A van has a name and one driver, who is one staff member. A driver drives one van at a time,
  and a person who drives a van cannot be removed until the van has another driver.
- Fuel bills: a driver submits a bill for their own van (date, petrol or diesel, litres, rate,
  odometer reading). The amount is litres times rate. The Principal approves, or rejects with
  a reason; a driver can withdraw a bill while it is waiting. Whoever approves bills can also
  submit one for any van.
- The odometer must rise from one bill to the next. The distance covered is this reading
  minus the van's previous reading, and the mileage is that distance over this bill's litres.
  Rejected and withdrawn bills do not count. The first bill of a van has no estimate.
- No photo of the bill yet: the app has no file storage so far.

## Teachers
- A teacher is a sign-in account with the teacher role: the Principal adds one with a name,
  email and starting password, and the teacher signs in with that email. The email does not
  change. Removing a teacher makes them inactive and they can no longer sign in; the
  Principal can bring them back or set a new password.
- Allotment gives a teacher a class and a subject (`5-A Maths`). A class and subject has one
  teacher at a time (letter case ignored); take it back before giving it to someone else.
  The Principal can be allotted too, because the Principal also teaches.
- A teacher sees only their own allotments, and in the students module only the classes
  and students they are allotted. Whoever manages classes or students sees all.
- Each day a teacher records what they taught in each of their allotments: one lesson per
  allotment per day, today by default, past days allowed, future days not. They can change
  their own lesson; nobody else can.
- The lesson board lists, for a day, every active allotment and whether its lesson is
  recorded or still pending (teachers who are inactive are left out). It does not yet know
  about holidays or weekends.

## Students
- Classes are a level (Nursery, LKG, UKG, 1 to 8) and an optional section, so `5-A`, or just
  `5` for a school with one class per level. Leave `section` out (or send `""` or `null`) for
  none; on a change, `""` or `null` removes it and leaving it out keeps it. A class with
  students cannot be removed. Removing means inactive.
- A student has a name, roll number (unique in the class), class, guardian's name and whether
  they use the van. Removing a student makes them inactive; their fees stay.
- Dress and books are items with a price (for one class or every class). Selling one to a
  student copies the price at that moment and adds it to what the student owes.
- Fees have four heads. Tuition and van have an amount per class set by the Principal
  (van is owed only by students marked `uses_van`). Dress and books are owed as the items
  sold. A payment can be part of what is due (an instalment) but never more, and gets a
  receipt number (`R-000001`, ...).
- Teachers can see classes and students. Fees and dress/books are for the Principal, or the
  Vice Principal once given `manage_fees` / `manage_accessories`. Staff see none of it.

## School
- One school. The Principal sets its name and which season (summer / winter) is in use.
- Each season has its own school day: opening and closing time, and its periods. Setting a
  season replaces its whole day; periods are numbered by start time and must not overlap or
  fall outside the school hours.
- Holidays are a name plus a first and last day (a one-day holiday has the same day twice).
  Removing one hides it; the record stays.
- Notices come in two kinds, `notice` and `announcement`. Withdrawing one hides it.
- Everyone signed in can read all of this. Changing it needs `manage_school` (name, timings,
  holidays) or `post_notices`, which the Principal always has and can give the Vice Principal.

## Roles
Principal, Vice Principal (if appointed), Teacher, Staff. The Principal also teaches and holds
every permission. The Vice Principal starts with no management rights; the Principal gives
them one at a time, each with a written reason. The Principal can list, rename, reset the
password of, remove (inactive) and bring back a Vice Principal; removing one takes back all
their permissions. No sign-up: the Principal creates the others.
The first Principal comes from `python manage.py create_principal`; an admin-portal
administrator comes from `python manage.py createsuperuser` and has no school role.

No phone number, address, affiliation number or Aadhaar number is stored.

## Errors
Every error has the same shape, and `message` is meant to be shown to the person as it is:
`{"message": "...", "code": "...", "errors": {"field": ["..."]}}`

## Run locally
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # then set DJANGO_SECRET_KEY
.venv/bin/python manage.py migrate
.venv/bin/python manage.py create_principal --email you@school.in --name "Name" --password '...'
.venv/bin/python manage.py runserver
```

## Postman
Import `postman/Shiksha_Setu_API.postman_collection.json`: every endpoint, grouped by module,
with example bodies. `Login` saves the token; requests that create something save its id for
the next one.

## Endpoints (so far)
| Method | Path | Who |
|---|---|---|
| GET | `/api/health/` | anyone |
| GET/PATCH | `/api/school/` | read: signed in, edit: `manage_school` (`school_name`, `active_season`) |
| GET | `/api/school/timings/` | signed in: both seasons, with periods |
| PUT | `/api/school/timings/{summer\|winter}/` | `manage_school`: hours and the full list of periods |
| GET/POST | `/api/school/holidays/` | read: signed in (`?from=&to=`), add: `manage_school` |
| PATCH/DELETE | `/api/school/holidays/{id}/` | `manage_school` |
| GET/POST | `/api/notices/` | read: signed in (`?kind=&limit=`), post: `post_notices` |
| DELETE | `/api/notices/{id}/` | `post_notices`: withdraws it |
| POST | `/api/auth/login/` | anyone (throttled, locks out after 5 bad tries) |
| POST | `/api/auth/refresh/` | refresh token |
| GET/PATCH | `/api/auth/me/` | signed-in user (PATCH: name only); returns `capabilities` |
| POST | `/api/auth/change-password/` | signed-in user |
| GET | `/api/auth/capabilities/` | signed-in user: permissions the Principal can give |
| GET/POST | `/api/classes/` | read: `view_students`, add: `manage_classes` (`?active=true\|false\|all`) |
| GET/PATCH/DELETE | `/api/classes/{id}/` | same; delete = inactive |
| GET/POST | `/api/students/` | read: `view_students`, add: `manage_students` (`?class_id=&query=&active=`) |
| GET/PATCH/DELETE | `/api/students/{id}/` | same; `is_active: true` restores |
| GET | `/api/students/{id}/fees/` | `manage_fees`: dues, paid, balance per head, and payments |
| GET/POST | `/api/accessories/items/` | `manage_accessories` (`?kind=&class_id=`) |
| PATCH/DELETE | `/api/accessories/items/{id}/` | `manage_accessories` |
| GET/POST | `/api/accessories/issues/` | `manage_accessories`: sell to a student (`?student_id=&kind=`) |
| GET | `/api/fees/structure/?class_id=` | `manage_fees`: tuition and van amounts of a class |
| PUT | `/api/fees/structure/{class_id}/{tuition\|van}/` | `manage_fees` |
| GET | `/api/fees/accounts/` | `manage_fees` (`?class_id=&query=&only_due=true`) |
| GET/POST | `/api/fees/payments/` | `manage_fees` (`?student_id=&from=&to=`) |
| GET/POST | `/api/teachers/` | `manage_teachers` or `allot_classes` read, `manage_teachers` add (`?query=&active=`) |
| GET/PATCH/DELETE | `/api/teachers/{id}/` | PATCH: `name`, `is_active`, `password`; delete = inactive |
| GET/POST | `/api/teaching/allotments/` | teacher: own; Principal: any (`?teacher_id=&class_id=`); add: `allot_classes` |
| DELETE | `/api/teaching/allotments/{id}/` | `allot_classes` |
| GET/POST | `/api/teaching/lessons/` | teacher: own, post: `record_daily_lesson`; Principal: any (`?teacher_id=&class_id=&from=&to=`) |
| PATCH | `/api/teaching/lessons/{id}/` | the teacher who wrote it |
| GET | `/api/teaching/lessons/board/?day=` | `manage_teachers` or `allot_classes`: recorded and pending |
| GET/POST | `/api/staff/` | read: `manage_staff` or `allot_vans`, add: `manage_staff` (`?query=&active=`) |
| GET/PATCH/DELETE | `/api/staff/{id}/` | PATCH: `name`, `job_title`, `is_active`, `password`; delete = inactive |
| GET/POST | `/api/vans/` | driver: own van; Principal: all; add: `allot_vans` |
| PATCH/DELETE | `/api/vans/{id}/` | `allot_vans`: rename, `driver_id` (null takes it back) |
| GET/POST | `/api/fuel-bills/` | driver: own; approvers: all (`?van_id=&status=&from=&to=`); post: `submit_fuel_bill` |
| DELETE | `/api/fuel-bills/{id}/` | the submitter, while pending |
| POST | `/api/fuel-bills/{id}/approve/` or `/reject/` | `approve_fuel_bills` (reject needs `reason`) |
| GET/PUT | `/api/attendance/students/` | roster (`?class_id=&day=`); PUT `{class_id, day?, marks:[{student_id, status}]}` marks it |
| GET | `/api/attendance/students/report/` | `?class_id=&from=&to=`: present, late, absent per student |
| POST | `/api/attendance/check-in/`, `/check-out/` | `record_own_attendance`: teacher, staff, Vice Principal |
| GET | `/api/attendance/me/` | own days (`?from=&to=`, today by default) |
| GET | `/api/attendance/people/` | `view_attendance`: the board (`?day=&role=`) |
| GET/PUT | `/api/attendance/records/` | read: `view_attendance` (`?person_id=&from=&to=`); PUT corrects: `correct_attendance` |
| GET | `/api/requests/` | own requests, plus every request of a kind you may decide (`?kind=&status=&requester_id=`) |
| POST | `/api/requests/leaves/` | `record_own_attendance`: `{starts_on, ends_on, reason}` |
| POST | `/api/requests/meetings/` | `raise_meeting_query`: `{subject, details?, preferred_on?}` |
| DELETE | `/api/requests/{id}/` | the person who asked, while pending |
| POST | `/api/requests/{id}/approve/` | `approve_leaves` (leave) or `decide_requests` (meeting: `{meeting_on, meeting_at}`) |
| POST | `/api/requests/{id}/reject/` | same rights; `{reason}` |
| GET/POST | `/api/exams/` | read: teacher (own subjects) or Principal (`?class_id=&type=&from=&to=`); schedule: `schedule_exams` |
| PATCH/DELETE | `/api/exams/{id}/` | `schedule_exams` |
| GET/PUT | `/api/exams/{id}/marks/` | results of the exam; PUT `{marks:[{student_id, marks, absent}]}` enters marks |
| GET | `/api/students/{id}/results/` | a student's exams and totals |
| GET/PUT | `/api/exams/{id}/paper/` | the paper; PUT `{question_ids}` builds it (the exam's teacher) |
| POST | `/api/exams/{id}/paper/send/`, `/approve/`, `/reject/` | teacher sends; `schedule_exams` approves or rejects (`reason`) |
| GET | `/api/exams/papers/?status=` | `schedule_exams`: papers waiting |
| GET/POST | `/api/question-bank/units/` | own units (`?teacher_id=` for the Principal); add: `manage_question_bank` |
| PATCH/DELETE | `/api/question-bank/units/{id}/` | the owner |
| GET/POST | `/api/question-bank/units/{id}/questions/` | the owner reads and adds; the Principal reads |
| PATCH/DELETE | `/api/question-bank/questions/{id}/` | the owner |
| GET | `/api/payments/people/` | the teachers/staff you may pay, with what each is owed (`?role=&query=&active=`) |
| GET | `/api/payments/people/{id}/` | one person's salary months, fuel bills and payments (managers, or the person) |
| GET/PUT | `/api/payments/people/{id}/salary/` | salary history; PUT `{amount, effective_from: "YYYY-MM"}` sets it |
| GET/POST | `/api/payments/` | payments (`?person_id=&from=&to=`); POST `{person_id, kind, amount, mode, month \| fuel_bill_id, paid_on?, note?}` |
| GET | `/api/payments/me/` | `view_own_payments`: my own account |
| GET | `/api/analytics/students/attendance/` | `view_analytics`: `?from=&to=&class_id=` |
| GET | `/api/analytics/students/fees/` | collected per month, owed per class (`?from=&to=`) |
| GET | `/api/analytics/students/exams/` | `?from=&to=&class_id=&type=` |
| GET | `/api/analytics/staff/attendance/` | `?from=&to=&role=` |
| GET | `/api/analytics/staff/payments/` | paid out per month, still owed (`?from=&to=`) |
| GET | `/api/analytics/staff/fuel/` | `?from=&to=&van_id=` |
| GET | `/api/analytics/teachers/lessons/` | `?from=&to=` |
| GET/POST | `/api/auth/vice-principal/` | Principal (`appoint_vice_principal`): list (`?query=&active=`), appoint |
| GET/PATCH/DELETE | `/api/auth/vice-principal/{id}/` | PATCH: `name`, `is_active`, `password`; delete = inactive, and their permissions are taken back |
| GET/POST | `/api/auth/grants/` | Principal (`grant_permissions`) |
| DELETE | `/api/auth/grants/{id}/` | Principal: takes a permission back (the record stays) |
| POST | `/api/auth/vice-principal/` | Principal (`appoint_vice_principal`) |

## Database
`DB_ENGINE` in `.env`: `sqlite` (local only), `mysql`, `postgres`.
Never use sqlite for real school data. Back up before every migration.

## Security on by default
Short-lived JWTs, login lockout, throttling, HTTPS/HSTS when `DJANGO_DEBUG` is off,
server-side permission checks (in the view and again in the use case), an audit log of
account, password and permission changes, no secrets in code. Set `FIELD_ENCRYPTION_KEY`
before encrypting any field with `core/security/crypto.py`.

## Deploy on Railway
Files for it: `railway.json` (start command and health check), `Procfile`, `.python-version`,
and the extra lines in `requirements.txt` (gunicorn, whitenoise, psycopg).

1. New project on railway.com, then **Add > Database > PostgreSQL**.
2. Add the API as a service (GitHub repo, or `railway up` from this folder).
3. On the API service set these variables (Variables tab):
   - `DJANGO_DEBUG=false`
   - `DJANGO_SECRET_KEY` a long random string
   - `FIELD_ENCRYPTION_KEY` the same key you use now (data already encrypted needs it)
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` (reference to the database service)
   - `CORS_ALLOWED_ORIGINS` the app's web address(es), no trailing slash
   - `GEMINI_API_KEY` for the handwriting reader (optional)
4. Settings > Networking > **Generate Domain**. The app reads that name from
   `RAILWAY_PUBLIC_DOMAIN` by itself, so no host variable is needed.
5. Each deploy runs `migrate` and `collectstatic`, then starts gunicorn. Railway's health check calls
   `/api/health/`.
6. Create the Principal account once, from this folder with the Railway CLI linked to the project:
   `railway run python manage.py create_principal --email you@school.in --name "Your Name" --password '<strong password>'`
   (`DATABASE_URL` points at Railway's private network, which your computer cannot reach: run it inside
   the service with `railway ssh`, or run it locally with `DATABASE_URL` set to the Postgres service's `DATABASE_PUBLIC_URL`.)
   Then point the Flutter app at `https://<domain>/api` (`API_BASE_URL`).

Do not use the sqlite file on Railway: the disk is wiped on every deploy.
