import base64
import requests
from flask import Flask, Response, stream_with_context, redirect, request
from bs4 import BeautifulSoup
import urllib.parse
import os

app = Flask(__name__)

def ob(t): return base64.urlsafe_b64encode(t.encode()).decode().replace('=', '')
def de(t):
    try:
        p = '=' * (4 - len(t) % 4)
        return base64.urlsafe_b64decode(t + p).decode()
    except: return ""

# --- デザイン ---
CSS = """
<style>
    :root { --bg: #1a1a1a; --text: #f1f1f1; --accent: #8ab4f8; --card: #303134; }
    body { font-family: sans-serif; background: var(--bg); color: var(--text); margin: 0; }
    
    /* 上に配置 */
    .hero { display: flex; flex-direction: column; align-items: center; padding-top: 50px; height: auto; }
    
    .logo-container { display: flex; align-items: center; justify-content: center; gap: 20px; margin-bottom: 25px; }
    .logo-font { font-size: 40px; font-weight: bold; color: var(--accent); }
    
    /* GIF設定 */
    .char-gif { height: 90px; width: auto; display: block; }
    
    /* 検索窓（文字なし） */
    .search-box { width: 85%; max-width: 500px; padding: 12px 25px; border-radius: 30px; border: 1px solid #5f6368; background: var(--card); color: white; font-size: 18px; outline: none; }
    
    .header { position: sticky; top: 0; background: var(--bg); padding: 10px; border-bottom: 1px solid #3c4043; display: flex; align-items: center; gap: 15px; }
    .header img { height: 30px; }
    .header input { flex: 1; padding: 8px 15px; border-radius: 20px; border: 1px solid #5f6368; background: var(--card); color: white; outline: none; }
    
    .container { max-width: 750px; margin: 20px auto; padding: 0 20px; }
    .res-box { margin-bottom: 25px; }
    .res-box a { color: var(--accent); font-size: 18px; text-decoration: none; }
    .res-box p { color: #bdc1c6; font-size: 14px; margin-top: 5px; }
</style>
"""

# GIF URL (直リンク)
GIF_LEFT = "https://media1.tenor.com/m/T0_m-h8W-vQAAAAC/el-gato-dance.gif" # 猫
GIF_RIGHT = "https://media1.tenor.com/m/C7YIu5A0S_kAAAAC/line-friends-rabbit.gif" # ウサギ

JS = """
<script>
    function s() {
        const q = document.getElementById('q').value;
        if(!q) return;
        const b64 = btoa(encodeURIComponent(q).replace(/%([0-9A-F]{2})/g, (m, p) => String.fromCharCode('0x'+p))).replace(/=/g, '');
        window.location.href = '/s/' + b64;
    }
    function check(e) { if(e.key==='Enter') s(); }
</script>
"""

@app.route('/')
def index():
    return f"""<html><head><title>プロキシ.pro</title>{CSS}{JS}</head><body>
    <div class='hero'>
        <div class='logo-container'>
            <img src='{GIF_LEFT}' class='char-gif'>
            <div class='logo-font'>プロキシ.pro</div>
            <img src='{GIF_RIGHT}' class='char-gif'>
        </div>
        <input type='text' id='q' class='search-box' onkeypress='check(event)' placeholder='' autofocus>
    </div></body></html>"""

@app.route('/s/<q>')
def results(q):
    query = de(q)
    if query.startswith(('http://', 'https://')): return redirect(f'/p/{{ob(query)}}')
    html = f"<html><head><title>{query} - プロキシ.pro</title>{CSS}{JS}</head><body>"
    html += f"<div class='header'><a href='/'><img src='{GIF_LEFT}'></a><input type='text' id='q' value='{query}' onkeypress='check(event)'></div>"
    html += "<div class='container'>"
    try:
        headers = {{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}}
        r = requests.get(f"https://www.google.com/search?q={{urllib.parse.quote(query)}}", headers=headers, timeout=5)
        soup = BeautifulSoup(r.text, 'lxml')
        for g in soup.select('.tF2Cxc'):
            t = g.select_one('h3').text
            l = g.select_one('a')['href']
            s = g.select_one('.VwiC3b').text if g.select_one('.VwiC3b') else ""
            html += f"<div class='res-box'><a href='/p/{{ob(l)}}'>{{t}}</a><p>{{s}}</p></div>"
    except: html += "<p>検索エラーが発生しました。リロードしてください。</p>"
    return html + "</div></body></html>"

@app.route('/p/<u>')
def proxy(u):
    url = de(u)
    try:
        r = requests.get(url, headers={{"User-Agent": "Mozilla/5.0"}}, timeout=10, stream=True)
        def generate():
            if "text/html" in r.headers.get("Content-Type", "").lower():
                soup = BeautifulSoup(r.content, "lxml")
                for tag, attr in {{'a':'href', 'img':'src', 'link':'href', 'script':'src'}}.items():
                    for el in soup.find_all(tag, **{{attr: True}}):
                        el[attr] = f"/p/{{ob(urllib.parse.urljoin(url, el[attr]))}}"
                yield str(soup).encode('utf-8')
            else:
                for chunk in r.iter_content(chunk_size=8192): yield chunk
        return Response(stream_with_context(generate()), content_type=r.headers.get("Content-Type"))
    except: return "Proxy Error", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
