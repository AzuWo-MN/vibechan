# vibechan

A 4chan-style imageboard, vibe coded by [Hermes Agent](https://github.com/NousResearch/hermes-agent) in one evening.

## Features

- **Boards** — homepage lists all boards; each board has a catalog-style thread list (OP + last 3 replies)
- **Threads & posts** — greentext (`>lines`), Anonymous by default, optional name/subject
- **Image uploads** — PNG/JPG/GIF/WebP, 8MB max
- **Reporting** — anonymous users can report posts/threads; counts surface in the admin panel
- **Admin panel** — delete/hide/pin/lock threads, delete/hide posts, ban, publish homepage news articles, create/hide/delete boards
- **Auth** — admin login required for moderation; regular users are anonymous

## Stack

- Python 3 + Flask
- SQLite (zero-config)
- Server-rendered Jinja2 templates, Yotsuba-inspired CSS

## Setup

```bash
python3 -m venv venv
venv/bin/pip install flask
venv/bin/python app.py            # serves on 127.0.0.1:8080
```

Default admin: `admin` / `changeme` — **change it immediately** (edit the hash in the `admins` table, SHA-256).

## Structure

```
app.py         # routes, DB schema, helpers
templates.py   # all Jinja2 templates (TPL_* constants)
static/style.css
uploads/       # user image uploads (gitignored)
instance/      # SQLite DB (gitignored)
```
