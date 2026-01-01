import base64
import requests
from flask import Flask, Response, stream_with_context, make_response, redirect
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import urllib.parse
import os

app = Flask(__name__)

# --- 暗号化・復号化ロジック ---
def ob(t): return base64.urlsafe_b64encode(t.encode()).decode().replace('=', '')
def de(t):
    try:
        p = '=' * (4 - len(t) % 4)
        return base64.urlsafe_b64decode(t + p).decode()
    except: return ""

# --- デザイン（CSS） ---
CSS = """
<style>
    :root { --bg: #202124; --text: #e8eaed; --accent: #8ab4f8; --card: #303134; }
    body { font-family: arial, sans-serif; background: var(--bg); color: var(--text); margin: 0; }
    .hero { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; }
    .logo-font { font-size: 80px; font-weight: bold; margin-bottom: 20px; letter-spacing: -2px; }
    .wide-search { width: 90%; max-width: 600px; padding: 14px 25px; border-radius: 30px; border: 1px solid #5f6368; background: var(--card); color: white; font-size: 18px; outline: none; }
    .header { position: sticky; top: 0; background: var(--bg); padding: 15px; border-bottom: 1px solid #3c4043; z-index: 1000; display: flex; align-items: center; gap: 15px; }
    .header input { flex: 1; max-width: 700px; padding: 10px 20px; border-radius: 24px; border: 1px solid #5f6368; background: var(--card); color: white; outline: none; }
    .tabs { display: flex; gap: 20px; padding: 10px 100px; border-bottom: 1px solid #3c4043; }
    .tab { color: #9aa0a6; text-decoration: none; font-size: 14px; padding-bottom: 8px; border-bottom: 3px solid transparent; }
    .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
    .container { max-width: 700px; margin: 20px auto; padding-left: 100px; }
    .res-box { margin-bottom: 25px; }
    .res-box a { color: var(--accent); font-size: 18px; text-decoration: none; }
    .res-box p { color: #bdc1c6; font-size: 14px; margin: 5px 0; line-height: 1.5; }
    .image-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; padding: 20px; }
    .image-grid img { width: 100%; height: 160px; object-fit: cover; border-radius: 8px; background: #333; }
</style>
"""

JS = """
<script>
    function s(type) {
        const q = document.getElementById('q').value;
        if(!q) return;
        const b64 = btoa(encodeURIComponent(q).replace(/%([0-9A-F]{2})/g, (m, p) => String.fromCharCode('0x'+p))).replace(/=/g, '');
        window.location.href = '/s/' + b64 + '/' + type;
    }
    function check(e, type) { if(e.key==='Enter') s(type); }
</script>
"""

@app.route('/')
def index():
    logo = '<span style="color:#4285f4">G</span><span style="color:#ea4335">O</span><span style="color:#fbbc05">O</span><span style="color:#4285f4">G</span><span style="color:#34a853">L</span><span style="color:#ea4335">E</span><span style="color:#777; font-size:30px;">.ry</span>'
    return f"<html><head>{CSS}{JS}</head><body><div class='hero'><div class='logo-font'>{logo}</div><input type='text' id='q' class='wide-search' onkeypress='check(event, \"text\")' placeholder='Googleで検索、またはURLを入力'></div></body></html>"

@app.route('/s/<q>/<t>')
def results(q, t):
    query = de(q)
    if query.startswith(('http://', 'https://')): return redirect(f'/p/{ob(query)}')
    c_t, c_i = ("tab active", "tab") if t == "text" else ("tab", "tab active")
    html = f"<html><head>{CSS}{JS}</head><body><div class='header'><a href='/' style='text-decoration:none; font-size:20px; font-weight:bold;'><span style='color:#4285f4'>G</span></a><input type='text' id='q' value='{query}' onkeypress='check(event, \"{t}\")'></div><div class='tabs'><a href='javascript:s(\"text\")' class='{c_t}'>すべて</a><a href='javascript:s(\"img\")' class='{c_i}'>画像</a></div><div class='container'>"
    if t == 'img':
        try:
            r = requests.get(f"https://www.google.com/search?q={query}&tbm=isch", headers={"User-Agent":"Mozilla/5.0"}, timeout=5)
            soup = BeautifulSoup(r.text, 'html.parser')
            html += "<div class='image-grid'>"
            for img in soup.find_all("img")[1:25]:
                src = img.get("src") or img.get("data-src")
                if src: html += f"<a href='/p/{ob(src)}' target='_blank'><img src='/p/{ob(src)}' loading='lazy'></a>"
            html += "</div>"
        except: html += "Error"
    else:
        try:
            with DDGS() as ddgs:
                for r in list(ddgs.text(query, max_results=12)):
                    html += f"<div class='res-box'><a href='/p/{ob(r['href'])}'>{r['title']}</a><p>{r['body']}</p></div>"
        except: html += "Error"
    return html + "</div></body></html>"

@app.route('/p/<u>')
def proxy(u):
    url = de(u)
    if not url: return "Invalid URL", 400
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15, stream=True)
        def generate():
            if "text/html" in r.headers.get("Content-Type", "").lower():
                soup = BeautifulSoup(r.content, "html.parser")
                for tag, attr in {'a':'href', 'img':'src', 'link':'href', 'script':'src', 'form':'action'}.items():
                    for el in soup.find_all(tag, **{attr: True}):
                        el[attr] = f"/p/{ob(urllib.parse.urljoin(url, el[attr]))}"
                yield str(soup).encode('utf-8')
            else:
                for chunk in r.iter_content(chunk_size=16384): yield chunk
        res = Response(stream_with_context(generate()), content_type=r.headers.get("Content-Type"))
        res.headers["Cache-Control"] = "no-store"
        return res
    except: return "Error", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
