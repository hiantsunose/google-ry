import base64
import requests
from flask import Flask, Response, stream_with_context, redirect, request
from bs4 import BeautifulSoup
import urllib.parse
import os

app = Flask(__name__)

# --- 暗号化ロジック ---
def ob(t): return base64.urlsafe_b64encode(t.encode()).decode().replace('=', '')
def de(t):
    try:
        p = '=' * (4 - len(t) % 4)
        return base64.urlsafe_b64decode(t + p).decode()
    except: return ""

# --- デザイン (CSS) ---
CSS = """
<style>
    :root { --bg: #1a1a1a; --text: #f1f1f1; --accent: #8ab4f8; --card: #303134; }
    body { font-family: 'Helvetica Neue', Arial, sans-serif; background: var(--bg); color: var(--text); margin: 0; }
    
    /* レイアウトを上に寄せる設定 */
    .hero { display: flex; flex-direction: column; align-items: center; padding-top: 10vh; height: 90vh; }
    
    .logo-container { display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 20px; }
    .logo-font { font-size: 45px; font-weight: bold; color: var(--accent); white-space: nowrap; }
    
    /* GIFのサイズ設定 */
    .char-gif { height: 80px; width: auto; object-fit: contain; }
    
    /* 検索欄の設定（placeholderなし） */
    .search-box { width: 90%; max-width: 550px; padding: 12px 20px; border-radius: 24px; border: 1px solid #5f6368; background: var(--card); color: white; font-size: 18px; outline: none; }
    .search-box:focus { border-color: var(--accent); }

    .header { position: sticky; top: 0; background: var(--bg); padding: 10px; border-bottom: 1px solid #3c4043; display: flex; align-items: center; gap: 15px; }
    .header .mini-gif { height: 35px; }
    .header input { flex: 1; max-width: 600px; padding: 8px 15px; border-radius: 20px; border: 1px solid #5f6368; background: var(--card); color: white; outline: none; }
    
    .container { max-width: 750px; margin: 20px auto; padding: 0 20px; }
    .res-box { margin-bottom: 30px; }
    .res-box a { color: var(--accent); font-size: 19px; text-decoration: none; }
    .res-box .url { color: #81c995; font-size: 13px; margin: 3px 0; overflow: hidden; text-overflow: ellipsis; }
    .res-box p { color: #bdc1c6; font-size: 14px; line-height: 1.4; }
</style>
"""

# 画像URL
CAT_GIF = "https://media.tenor.com/T0_m-h8W-vQAAAAi/el-gato-dance.gif" # メキシコ猫
RABBIT_GIF = "https://media.tenor.com/C7YIu5A0S_kAAAAi/line-friends-rabbit.gif" # お送りいただいたウサギ(類似)

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
            <img src='{CAT_GIF}' class='char-gif'> <div class='logo-font'>プロキシ.pro</div>
            <img src='{RABBIT_GIF}' class='char-gif'> </div>
        <input type='text' id='q' class='search-box' onkeypress='check(event)' placeholder='' autofocus>
    </div></body></html>"""

@app.route('/s/<q>')
def results(q):
    query = de(q)
    if query.startswith(('http://', 'https://')): return redirect(f'/p/{ob(query)}')
    html = f"<html><head><title>{query} - プロキシ.pro</title>{CSS}{JS}</head><body>"
    html += f"<div class='header'><a href='/'><img src='{CAT_GIF}' class='mini-gif'></a><input type='text' id='q' value='{query}' onkeypress='check(event)'></div>"
    html += "<div class='container'>"
    try:
        headers = {{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}}
        r = requests.get(f"https://www.google.com/search?q={{urllib.parse.quote(query)}}", headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        results_found = False
        for g in soup.find_all('div', class_='tF2Cxc'):
            title_tag = g.find('h3')
            link_tag = g.find('a')
            if title_tag and link_tag:
                results_found = True
                title = title_tag.text
                link = link_tag['href']
                snippet = g.find('div', class_='VwiC3b').text if g.find('div', class_='VwiC3b') else ""
                html += f"<div class='res-box'><a href='/p/{{ob(link)}}'>{{title}}</a><div class='url'>{{link}}</div><p>{{snippet}}</p></div>"
        if not results_found: html += "<p>結果が見つかりませんでした。</p>"
    except Exception as e: html += f"<p>Error: {{str(e)}}</p>"
    return html + "</div></body></html>"

@app.route('/p/<u>')
def proxy(u):
    url = de(u)
    try:
        r = requests.get(url, headers={{"User-Agent": "Mozilla/5.0"}}, timeout=10, stream=True)
        def generate():
            if "text/html" in r.headers.get("Content-Type", "").lower():
                soup = BeautifulSoup(r.content, "html.parser")
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
