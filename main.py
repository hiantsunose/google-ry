import base64
import requests
from flask import Flask, Response, stream_with_context, make_response, redirect, request
from bs4 import BeautifulSoup
import urllib.parse
import os

app = Flask(__name__)

# --- ロジック ---
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
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); margin: 0; }
    .hero { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 25px; }
    .logo-font { font-size: 50px; font-weight: bold; color: var(--accent); }
    .cat-gif { height: 80px; }
    .wide-search { width: 90%; max-width: 600px; padding: 14px 25px; border-radius: 30px; border: 1px solid #5f6368; background: var(--card); color: white; font-size: 18px; outline: none; }
    .header { position: sticky; top: 0; background: var(--bg); padding: 15px; border-bottom: 1px solid #3c4043; z-index: 1000; display: flex; align-items: center; gap: 15px; }
    .header input { flex: 1; max-width: 700px; padding: 10px 20px; border-radius: 24px; border: 1px solid #5f6368; background: var(--card); color: white; outline: none; }
    .container { max-width: 750px; margin: 20px auto; padding: 0 20px; }
    .res-box { margin-bottom: 30px; }
    .res-box a { color: var(--accent); font-size: 20px; text-decoration: none; display: block; margin-bottom: 5px; }
    .res-box .url { color: #81c995; font-size: 14px; margin-bottom: 5px; }
    .res-box p { color: #bdc1c6; font-size: 15px; line-height: 1.5; margin: 0; }
</style>
"""

CAT_IMG = "https://media.tenor.com/T0_m-h8W-vQAAAAi/el-gato-dance.gif" # 送っていただいた猫の動くイメージ

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
            <div class='logo-font'>プロキシ.pro</div>
            <img src='{CAT_IMG}' class='cat-gif'>
        </div>
        <input type='text' id='q' class='wide-search' onkeypress='check(event)' placeholder='Google検索またはURLを入力'>
    </div></body></html>"""

@app.route('/s/<q>')
def results(q):
    query = de(q)
    if query.startswith(('http://', 'https://')): return redirect(f'/p/{ob(query)}')
    
    html = f"<html><head><title>{query} - プロキシ.pro</title>{CSS}{JS}</head><body>"
    html += f"<div class='header'><a href='/' style='text-decoration:none; font-size:24px;'><img src='{CAT_IMG}' style='height:30px;'></a><input type='text' id='q' value='{query}' onkeypress='check(event)'></div>"
    html += "<div class='container'>"
    
    try:
        # Google検索をシミュレート
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        r = requests.get(f"https://www.google.com/search?q={urllib.parse.quote(query)}", headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        for g in soup.find_all('div', class_='tF2Cxc'):
            title = g.find('h3').text
            link = g.find('a')['href']
            snippet = g.find('div', class_='VwiC3b').text if g.find('div', class_='VwiC3b') else ""
            html += f"<div class='res-box'><a href='/p/{ob(link)}'>{title}</a><div class='url'>{link}</div><p>{snippet}</p></div>"
    except Exception as e:
        html += f"<p>Error: {str(e)}</p>"
    
    return html + "</div></body></html>"

@app.route('/p/<u>')
def proxy(u):
    url = de(u)
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, stream=True)
        def generate():
            if "text/html" in r.headers.get("Content-Type", "").lower():
                soup = BeautifulSoup(r.content, "html.parser")
                for tag, attr in {'a':'href', 'img':'src', 'link':'href', 'script':'src'}.items():
                    for el in soup.find_all(tag, **{attr: True}):
                        original = el[attr]
                        el[attr] = f"/p/{ob(urllib.parse.urljoin(url, original))}"
                yield str(soup).encode('utf-8')
            else:
                for chunk in r.iter_content(chunk_size=8192): yield chunk
        return Response(stream_with_context(generate()), content_type=r.headers.get("Content-Type"))
    except: return "Access Error", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
