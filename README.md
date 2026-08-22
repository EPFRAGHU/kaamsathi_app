# KaamSathi — daily labourer job-matching app (starter)

A Flask MVP for the daily-wage labourer/employer marketplace concept, matching the
UI mockup shown in chat. Two screens are wired up end to end:

- `/` — labourer home: availability switch, trade categories, nearby jobs
- `/post-job` — employer form to post a new job (writes into the in-memory job list)

## Run it locally

```bash
pip install flask
python3 app.py
```

Then open http://127.0.0.1:5000 in your browser (or your phone on the same wifi
network, using your computer's local IP instead of 127.0.0.1, to see it at
actual phone width).

## What's real vs. placeholder

- Job data is in-memory (`JOBS` list in `app.py`) — resets every time you restart
  the server. Swap this for Postgres once you're ready (this matches the pattern
  you've already used in salary_app / the inquiry portal: Flask + Neon Postgres).
- There's no login/auth yet — every visitor sees "Ramesh Sahoo" as the worker.
- The availability switch and category chips are visual only; wiring "available
  today" to actually filter/notify would be the next real feature to build.
- SMS/OTP, e-Shram verification, and payments are intentionally left out — add
  them once the core matching loop is proven with real users at labour chowks.

## File structure

```
kaamsathi_app/
├── app.py                 Flask routes + in-memory job data
├── templates/
│   ├── base.html           shared phone-frame shell, nav, flash messages
│   ├── home.html           labourer home screen
│   └── post_job.html       employer "post a job" form
└── static/
    ├── css/style.css      all styling (design tokens at the top)
    └── js/main.js         switch, chip selection, stepper, form validation
```
