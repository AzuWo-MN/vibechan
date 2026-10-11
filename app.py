#!/home/mn-hermes/imageboard/venv/bin/python
"""Tinychan - a 4chan-style imageboard. Flask + SQLite."""
import os, sqlite3, time, hashlib, secrets, html
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, session, redirect, url_for, render_template_string, abort, send_from_directory, flash
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "instance", "chan.db")
UPLOAD = os.path.join(BASE, "uploads")
os.makedirs(UPLOAD, exist_ok=True)

# ---------------------------------------------------------------- templates (import AFTER helpers)
sys.path.insert(0, BASE)
from templates import TPL_HOME, TPL_BOARD, TPL_THREAD, TPL_LOGIN, TPL_ADMIN

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB uploads

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_BOARDS = set("abcdefghijklmnopqrstuvwxyz0123456789")

# ---------------------------------------------------------------- schema
SCHEMA = """
CREATE TABLE IF NOT EXISTS boards (
  slug TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  hidden INTEGER DEFAULT 0,
  created_at INTEGER
);
CREATE TABLE IF NOT EXISTS threads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  board TEXT NOT NULL,
  subject TEXT DEFAULT '',
  author TEXT DEFAULT 'Anonymous',
  body TEXT NOT NULL,
  image TEXT,
  pinned INTEGER DEFAULT 0,
  locked INTEGER DEFAULT 0,
  hidden INTEGER DEFAULT 0,
  report_count INTEGER DEFAULT 0,
  created_at INTEGER,
  bumped_at INTEGER
);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  thread_id INTEGER NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
  author TEXT DEFAULT 'Anonymous',
  body TEXT NOT NULL,
  image TEXT,
  report_count INTEGER DEFAULT 0,
  hidden INTEGER DEFAULT 0,
  created_at INTEGER
);
CREATE TABLE IF NOT EXISTS admins (
  username TEXT PRIMARY KEY,
  password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS news (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at INTEGER
);
CREATE TABLE IF NOT EXISTS bans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_type TEXT,          -- 'thread' or 'post'
  post_id INTEGER,
  ip_hash TEXT,
  reason TEXT,
  created_at INTEGER
);
"""

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init():
    conn = db()
    conn.executescript(SCHEMA)
    # default boards
    for slug, name, desc in [
        ("b", "Random", "The random board. Anything goes (within global rules)."),
        ("g", "Technology", "Computers, code, gadgets."),
        ("a", "Anime & Manga", "Anime and manga discussion."),
    ]:
        conn.execute("INSERT OR IGNORE INTO boards(slug,name,description,created_at) VALUES(?,?,?,?)",
                     (slug, name, desc, int(time.time())))
    # default admin: admin / changeme  (change immediately!)
    if not conn.execute("SELECT 1 FROM admins").fetchone():
        conn.execute("INSERT INTO admins VALUES(?,?)",
                     ("admin", hashlib.sha256(b"changeme").hexdigest()))
    conn.commit(); conn.close()

init()

# ---------------------------------------------------------------- helpers
def now(): return int(time.time())

def fmt_time(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def esc(s): return html.escape(s or "", quote=True)

def greentext(s):
    """Escape + turn >lines green, >>links handled in template."""
    out = []
    for line in esc(s).splitlines():
        if line.startswith(">") and not line.startswith(">>"):
            out.append(f'<span class="quote">{line}</span>')
        else:
            out.append(line)
    return "<br>".join(out)

def ip_hash():
    key = app.secret_key
    if isinstance(key, str):
        key = key.encode()
    return hashlib.sha256((request.remote_addr or "x").encode() + key).hexdigest()[:16]

def is_banned():
    conn = db()
    row = conn.execute("SELECT 1 FROM bans WHERE ip_hash=? LIMIT 1", (ip_hash(),)).fetchone()
    conn.close()
    return bool(row)

def login_required(f):
    @wraps(f)
    def wrapped(*a, **kw):
        if not session.get("admin"):
            return redirect(url_for("admin_login", next=request.path))
        return f(*a, **kw)
    return wrapped

def get_board(slug):
    conn = db()
    b = conn.execute("SELECT * FROM boards WHERE slug=?", (slug,)).fetchone()
    conn.close()
    return b

def save_image(fileobj):
    if not fileobj or not fileobj.filename:
        return None
    filename = fileobj.filename
    if isinstance(filename, bytes):
        filename = filename.decode("utf-8", "replace")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXT:
        abort(400, "Unsupported file type")
    fname = f"{int(time.time()*1000)}_{secrets.token_hex(4)}{ext}"
    fileobj.save(os.path.join(UPLOAD, fname))
    return fname

# ---------------------------------------------------------------- template helpers
app.jinja_env.globals.update(fmt_time=fmt_time)

def with_body(post_or_thread):
    d = dict(post_or_thread)
    d["body_html"] = greentext(d["body"])
    return d

# ---------------------------------------------------------------- public routes
@app.route("/")
def home():
    conn = db()
    boards = conn.execute("SELECT * FROM boards WHERE hidden=0 ORDER BY slug").fetchall()
    news = conn.execute("SELECT * FROM news ORDER BY created_at DESC LIMIT 5").fetchall()
    conn.close()
    return render_template_string(TPL_HOME, boards=boards, news=news)

@app.route("/<slug>/", endpoint="board")
def board_page(slug):
    b = get_board(slug)
    if not b or b["hidden"]:
        abort(404)
    conn = db()
    threads = conn.execute(
        "SELECT * FROM threads WHERE board=? AND hidden=0 ORDER BY pinned DESC, bumped_at DESC LIMIT 30",
        (slug,)).fetchall()
    # OP + last 3 replies of each thread (catalog-lite style)
    data = []
    for t in threads:
        replies = conn.execute(
            "SELECT * FROM posts WHERE thread_id=? AND hidden=0 ORDER BY id DESC LIMIT 3",
            (t["id"],)).fetchall()
        n = conn.execute("SELECT COUNT(*) c FROM posts WHERE thread_id=? AND hidden=0",
                         (t["id"],)).fetchone()["c"]
        data.append((t, n, [with_body(r) for r in reversed(replies)]))
    conn.close()
    return render_template_string(TPL_BOARD, board=b, threads=data)

@app.route("/<slug>/thread/<int:tid>")
def thread_page(slug, tid):
    b = get_board(slug)
    if not b:
        abort(404)
    conn = db()
    t = conn.execute("SELECT * FROM threads WHERE id=? AND board=? AND hidden=0", (tid, slug)).fetchone()
    if not t:
        abort(404)
    posts = conn.execute("SELECT * FROM posts WHERE thread_id=? AND hidden=0 ORDER BY id",
                         (tid,)).fetchall()
    conn.close()
    return render_template_string(TPL_THREAD, board=b, thread=with_body(t),
                                  posts=[with_body(p) for p in posts])

@app.route("/<slug>/post", methods=["POST"])
def new_thread(slug):
    b = get_board(slug)
    if not b or b["hidden"] or is_banned():
        abort(403)
    body = request.form.get("body", "").strip()
    if not body:
        abort(400, "Empty post")
    conn = db()
    t = now()
    cur = conn.execute(
        "INSERT INTO threads(board,subject,author,body,image,created_at,bumped_at) VALUES(?,?,?,?,?,?,?)",
        (slug, request.form.get("subject", "").strip()[:100],
         request.form.get("author", "").strip()[:30] or "Anonymous",
         body[:4000], save_image(request.files.get("image")), t, t))
    conn.commit(); conn.close()
    return redirect(f"/{slug}/thread/{cur.lastrowid}")

@app.route("/<slug>/thread/<int:tid>/reply", methods=["POST"])
def reply(slug, tid):
    if is_banned():
        abort(403)
    body = request.form.get("body", "").strip()
    if not body:
        abort(400, "Empty post")
    conn = db()
    conn.execute("INSERT INTO posts(thread_id,author,body,image,created_at) VALUES(?,?,?,?,?)",
                 (tid, request.form.get("author", "").strip()[:30] or "Anonymous",
                  body[:4000], save_image(request.files.get("image")), now()))
    conn.execute("UPDATE threads SET bumped_at=? WHERE id=?", (now(), tid))
    conn.commit(); conn.close()
    return redirect(f"/{slug}/thread/{tid}")

@app.route("/<slug>/thread/<int:tid>/report", methods=["POST"])
@app.route("/post/<int:pid>/report", methods=["POST"])
def report(slug=None, tid=None, pid=None):
    conn = db()
    if pid:
        conn.execute("UPDATE posts SET report_count=report_count+1 WHERE id=?", (pid,))
    else:
        conn.execute("UPDATE threads SET report_count=report_count+1 WHERE id=?", (tid,))
    conn.commit(); conn.close()
    return redirect(request.referrer or "/")

# ---------------------------------------------------------------- admin
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        h = hashlib.sha256(request.form["password"].encode()).hexdigest()
        conn = db()
        row = conn.execute("SELECT 1 FROM admins WHERE username=? AND password_hash=?",
                           (request.form["username"], h)).fetchone()
        conn.close()
        if row:
            session["admin"] = request.form["username"]
            return redirect(request.args.get("next") or "/admin")
        flash("Bad credentials")
    return render_template_string(TPL_LOGIN)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/")

@app.route("/admin")
@login_required
def admin_home():
    conn = db()
    boards = conn.execute("SELECT * FROM boards ORDER BY slug").fetchall()
    reported_threads = conn.execute(
        "SELECT * FROM threads WHERE report_count>0 ORDER BY report_count DESC").fetchall()
    reported_posts = conn.execute(
        """SELECT p.*, t.board FROM posts p JOIN threads t ON p.thread_id=t.id
           WHERE p.report_count>0 ORDER BY p.report_count DESC""").fetchall()
    news = conn.execute("SELECT * FROM news ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template_string(TPL_ADMIN, boards=boards,
                                  reported_threads=reported_threads,
                                  reported_posts=reported_posts, news=news,
                                  username=session["admin"])

@app.route("/admin/boards", methods=["POST"])
@login_required
def admin_boards():
    conn = db()
    action = request.form["action"]
    if action == "create":
        slug = request.form["slug"].strip().lower()
        if slug and set(slug) <= ALLOWED_BOARDS:
            conn.execute("INSERT OR IGNORE INTO boards(slug,name,description,created_at) VALUES(?,?,?,?)",
                         (slug, request.form["name"].strip()[:60],
                          request.form["description"].strip()[:200], now()))
    elif action == "hide":
        conn.execute("UPDATE boards SET hidden=1 WHERE slug=?", (request.form["slug"],))
    elif action == "unhide":
        conn.execute("UPDATE boards SET hidden=0 WHERE slug=?", (request.form["slug"],))
    elif action == "delete":
        slug = request.form["slug"]
        conn.execute("""DELETE FROM posts WHERE thread_id IN (SELECT id FROM threads WHERE board=?)""", (slug,))
        conn.execute("DELETE FROM threads WHERE board=?", (slug,))
        conn.execute("DELETE FROM boards WHERE slug=?", (slug,))
    conn.commit(); conn.close()
    return redirect("/admin")

@app.route("/admin/news", methods=["POST"])
@login_required
def admin_news():
    conn = db()
    if request.form["action"] == "create":
        conn.execute("INSERT INTO news(title,body,created_at) VALUES(?,?,?)",
                     (request.form["title"].strip()[:120], request.form["body"].strip()[:5000], now()))
    elif request.form["action"] == "delete":
        conn.execute("DELETE FROM news WHERE id=?", (request.form["id"],))
    conn.commit(); conn.close()
    return redirect("/admin")

@app.route("/admin/thread/<int:tid>/<action>", methods=["POST"])
@login_required
def admin_thread(tid, action):
    conn = db()
    if action == "pin": conn.execute("UPDATE threads SET pinned=1-pinned WHERE id=?", (tid,))
    elif action == "lock": conn.execute("UPDATE threads SET locked=1-locked WHERE id=?", (tid,))
    elif action == "hide": conn.execute("UPDATE threads SET hidden=1 WHERE id=?", (tid,))
    elif action == "unhide": conn.execute("UPDATE threads SET hidden=0 WHERE id=?", (tid,))
    elif action == "delete": conn.execute("DELETE FROM threads WHERE id=?", (tid,))
    elif action == "ban":
        t = conn.execute("SELECT * FROM threads WHERE id=?", (tid,)).fetchone()
        if t:
            conn.execute("INSERT INTO bans(post_type,post_id,ip_hash,reason,created_at) VALUES(?,?,?,?,?)",
                         ("thread", tid, "", request.form.get("reason", "banned post"), now()))
            conn.execute("DELETE FROM threads WHERE id=?", (tid,))
    elif action == "clearreports": conn.execute("UPDATE threads SET report_count=0 WHERE id=?", (tid,))
    conn.commit(); conn.close()
    return redirect(request.referrer or "/admin")

@app.route("/admin/post/<int:pid>/<action>", methods=["POST"])
@login_required
def admin_post(pid, action):
    conn = db()
    if action == "hide": conn.execute("UPDATE posts SET hidden=1 WHERE id=?", (pid,))
    elif action == "unhide": conn.execute("UPDATE posts SET hidden=0 WHERE id=?", (pid,))
    elif action == "delete": conn.execute("DELETE FROM posts WHERE id=?", (pid,))
    elif action == "ban":
        conn.execute("INSERT INTO bans(post_type,post_id,ip_hash,reason,created_at) VALUES(?,?,?,?,?)",
                     ("post", pid, "", request.form.get("reason", "banned post"), now()))
        conn.execute("DELETE FROM posts WHERE id=?", (pid,))
    elif action == "clearreports": conn.execute("UPDATE posts SET report_count=0 WHERE id=?", (pid,))
    conn.commit(); conn.close()
    return redirect(request.referrer or "/admin")

@app.route("/uploads/<fname>")
def uploaded(fname):
    return send_from_directory(UPLOAD, fname)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()
    app.run(host=args.host, port=args.port, debug=False)
