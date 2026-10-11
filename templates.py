# Jinja2 templates for Tinychan, imported by app.py as TPL_* constants.

TPL_BASE_HEAD = """
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tinychan</title>
<link rel="stylesheet" href="/static/style.css">
</head><body>
{% with msgs = get_flashed_messages() %}
  {% for m in msgs %}<div class="flash">{{ m }}</div>{% endfor %}
{% endwith %}
"""

TPL_HOME = TPL_BASE_HEAD + """
<body class="yotsubula">
<div class="logo">tinychan</div>
<div class="tagline">an imageboard for grown-ups</div>
<hr>
{% if news %}
<div class="news-box">
  <h2>News</h2>
  {% for n in news %}
    <div class="news-item">
      <span class="news-title">{{ n.title }}</span>
      <span class="poster">{{ fmt_time(n.created_at) }}</span>
      <p>{{ n.body }}</p>
    </div>
  {% endfor %}
</div>
<hr>
{% endif %}
<h2>Boards</h2>
<table class="board-list">
{% for b in boards %}
  <tr><td><a href="/{{ b.slug }}/">/{{ b.slug }}/</a></td>
      <td>{{ b.name }}</td><td class="dim">{{ b.description }}</td></tr>
{% endfor %}
</table>
<hr>
<div class="footer">Tinychan &mdash; <a href="/admin/login">admin</a></div>
</body></html>
"""

TPL_BOARD = TPL_BASE_HEAD + """
<div class="logo small"><a href="/">tinychan</a></div>
<h1 class="board-title">/{{ board.slug }}/ - {{ board.name }}</h1>
<p class="dim">{{ board.description }}</p>
<hr>
<div class="post-form">
  <h2>Start a new thread</h2>
  <form method="post" action="/{{ board.slug }}/post" enctype="multipart/form-data">
    <input name="subject" placeholder="Subject" maxlength="100">
    <input name="author" placeholder="Anonymous" maxlength="30"><br>
    <textarea name="body" rows="5" cols="50" required placeholder="Comment"></textarea><br>
    <input type="file" name="image" accept=".png,.jpg,.jpeg,.gif,.webp">
    <button type="submit">Post</button>
  </form>
</div>
<hr>
{% for t, n_replies, replies in threads %}
<div class="thread-preview {% if t.pinned %}pinned{% endif %}" id="t{{ t.id }}">
  {% if t.pinned %}<span class="pin">📌 pinned</span>{% endif %}
  {% if t.subject %}<span class="subject">{{ t.subject }}</span>{% endif %}
  <span class="poster">{{ t.author }}</span>
  <span class="dim">{{ fmt_time(t.created_at) }}</span>
  <span class="dim">No.<a href="/{{ board.slug }}/thread/{{ t.id }}">{{ t.id }}</a></span>
  {% if t.image %}<div><a href="/uploads/{{ t.image }}" target="_blank"><img class="thumb" src="/uploads/{{ t.image }}"></a></div>{% endif %}
  <div class="body">{{ t.body_html }}</div>
  {% if n_replies > 0 %}<span class="replies-count">{{ n_replies }} replies <a href="/{{ board.slug }}/thread/{{ t.id }}">[View thread]</a></span>{% endif %}
  <div class="omitted">
  {% for r in replies %}
    <div class="reply">
      <span class="poster">{{ r.author }}</span> <span class="dim">{{ fmt_time(r.created_at) }} No.{{ r.id }}</span>
      {% if r.image %}<div><img class="thumb small" src="/uploads/{{ r.image }}"></div>{% endif %}
      <div class="body">{{ r.body_html }}</div>
    </div>
  {% endfor %}
  </div>
</div>
<hr>
{% else %}
<p class="dim">No threads yet. Be the first!</p>
{% endfor %}
</body></html>
"""

TPL_THREAD = TPL_BASE_HEAD + """
<div class="logo small"><a href="/">tinychan</a> &rarr; <a href="/{{ board.slug }}/">/{{ board.slug }}/</a></div>
<hr>
<div class="thread" id="t{{ thread.id }}">
  {% if thread.subject %}<span class="subject">{{ thread.subject }}</span>{% endif %}
  <span class="poster">{{ thread.author }}</span>
  <span class="dim">{{ fmt_time(thread.created_at) }} No.{{ thread.id }}</span>
  {% if thread.locked %}<span class="pin">🔒 locked</span>{% endif %}
  {% if thread.image %}<div><a href="/uploads/{{ thread.image }}" target="_blank"><img class="thumb" src="/uploads/{{ thread.image }}"></a></div>{% endif %}
  <div class="body">{{ thread.body_html }}</div>
  <form method="post" action="/{{ board.slug }}/thread/{{ thread.id }}/report" class="inline">
    <button class="linkbtn">Report</button>
  </form>
</div>
<hr>
{% for p in posts %}
<div class="reply" id="p{{ p.id }}">
  <span class="poster">{{ p.author }}</span>
  <span class="dim">{{ fmt_time(p.created_at) }} No.{{ p.id }}</span>
  {% if p.image %}<div><a href="/uploads/{{ p.image }}" target="_blank"><img class="thumb small" src="/uploads/{{ p.image }}"></a></div>{% endif %}
  <div class="body">{{ p.body_html }}</div>
  <form method="post" action="/post/{{ p.id }}/report" class="inline">
    <button class="linkbtn">Report</button>
  </form>
</div>
{% endfor %}
<hr>
{% if not thread.locked %}
<div class="post-form">
  <h2>Reply to thread</h2>
  <form method="post" action="/{{ board.slug }}/thread/{{ thread.id }}/reply" enctype="multipart/form-data">
    <input name="author" placeholder="Anonymous" maxlength="30"><br>
    <textarea name="body" rows="5" cols="50" required></textarea><br>
    <input type="file" name="image" accept=".png,.jpg,.jpeg,.gif,.webp">
    <button type="submit">Reply</button>
  </form>
</div>
{% else %}<p class="dim">Thread locked.</p>{% endif %}
</body></html>
"""

TPL_LOGIN = TPL_BASE_HEAD + """
<div class="login-box">
  <h2>Admin login</h2>
  <form method="post">
    <input name="username" placeholder="Username" required><br>
    <input name="password" type="password" placeholder="Password" required><br>
    <button type="submit">Login</button>
  </form>
</div>
</body></html>
"""

TPL_ADMIN = TPL_BASE_HEAD + """
<h1>Admin panel <span class="dim">({{ username }})</span> <a href="/admin/logout" class="dim">[logout]</a></h1>
<hr>
<h2>News articles <span class="dim">(homepage)</span></h2>
<form method="post" action="/admin/news">
  <input type="hidden" name="action" value="create">
  <input name="title" placeholder="Title" required maxlength="120">
  <textarea name="body" rows="3" cols="60" placeholder="Body" required></textarea>
  <button type="submit">Publish</button>
</form>
{% for n in news %}
  <div class="admin-item"><b>{{ n.title }}</b> <span class="dim">{{ fmt_time(n.created_at) }}</span>
  <form method="post" action="/admin/news" class="inline">
    <input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{{ n.id }}">
    <button class="linkbtn danger">delete</button>
  </form></div>
{% endfor %}
<hr>
<h2>Boards</h2>
<form method="post" action="/admin/boards">
  <input type="hidden" name="action" value="create">
  <input name="slug" placeholder="slug" maxlength="8" required pattern="[a-z0-9]+">
  <input name="name" placeholder="Name" required maxlength="60">
  <input name="description" placeholder="Description" maxlength="200">
  <button type="submit">Create board</button>
</form>
<table class="board-list">
{% for b in boards %}
  <tr><td>/{{ b.slug }}/ {{ b.name }}</td><td>{% if b.hidden %}<span class="danger">HIDDEN</span>{% else %}visible{% endif %}</td>
  <td>
    <form method="post" action="/admin/boards" class="inline"><input type="hidden" name="slug" value="{{ b.slug }}">
    {% if b.hidden %}<input type="hidden" name="action" value="unhide"><button class="linkbtn">unhide</button>
    {% else %}<input type="hidden" name="action" value="hide"><button class="linkbtn">hide</button>{% endif %}
    </form>
    <form method="post" action="/admin/boards" class="inline"><input type="hidden" name="slug" value="{{ b.slug }}">
      <input type="hidden" name="action" value="delete"><button class="linkbtn danger">DELETE</button></form>
  </td></tr>
{% endfor %}
</table>
<hr>
<h2>Reported threads</h2>
{% for t in reported_threads %}
  <div class="admin-item">
    <b>/{{ t.board }}/{{ t.id }}</b> ({{ t.report_count }} reports) — {{ t.body[:100] }}
    <form method="post" action="/admin/thread/{{ t.id }}/delete" class="inline"><button class="linkbtn danger">delete</button></form>
    <form method="post" action="/admin/thread/{{ t.id }}/ban" class="inline"><input name="reason" placeholder="reason"><button class="linkbtn danger">delete+ban</button></form>
    <form method="post" action="/admin/thread/{{ t.id }}/hide" class="inline"><button class="linkbtn">hide</button></form>
    <form method="post" action="/admin/thread/{{ t.id }}/lock" class="inline"><button class="linkbtn">lock</button></form>
    <form method="post" action="/admin/thread/{{ t.id }}/pin" class="inline"><button class="linkbtn">pin</button></form>
    <form method="post" action="/admin/thread/{{ t.id }}/clearreports" class="inline"><button class="linkbtn">clear reports</button></form>
  </div>
{% else %}<p class="dim">None</p>{% endfor %}
<h2>Reported posts</h2>
{% for p in reported_posts %}
  <div class="admin-item">
    <b>post #{{ p.id }} in /{{ p.board }}/{{ p.thread_id }}</b> ({{ p.report_count }} reports) — {{ p.body[:100] }}
    <form method="post" action="/admin/post/{{ p.id }}/delete" class="inline"><button class="linkbtn danger">delete</button></form>
    <form method="post" action="/admin/post/{{ p.id }}/ban" class="inline"><input name="reason" placeholder="reason"><button class="linkbtn danger">delete+ban</button></form>
    <form method="post" action="/admin/post/{{ p.id }}/hide" class="inline"><button class="linkbtn">hide</button></form>
    <form method="post" action="/admin/post/{{ p.id }}/clearreports" class="inline"><button class="linkbtn">clear reports</button></form>
  </div>
{% else %}<p class="dim">None</p>{% endfor %}
</body></html>
"""
