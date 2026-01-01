import base64
import requests
from flask import Flask, Response, stream_with_context, redirect, request, send_from_directory
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

CSS = """
<style>
    :root { --bg: #1a1a1a; --text: #f1f1f1; --accent: #8ab4f8; --card: #303134; }
    body { font-family: sans-serif; background: var(--bg); color: var(--text); margin: 0; }
    
    /* 検索欄とロゴを少し下げる（25vh） */
    .hero { display: flex; flex-direction: column; align-items: center; padding-top: 25vh; min-height: 75vh; }
    
    .logo-container { display: flex; align-items: center; justify-content: center; gap: 20px; margin-bottom: 25px; }
    .logo-font { font-size: 42px; font-weight: bold; color: var(--accent); }
    
    /* GIF画像の設定：背景に馴染ませ、動きを止めない設定 */
    .char-gif { height: 95px; width: auto; background: transparent; mix-blend-mode: lighten; }
    
    .search-box { width: 85%; max-width: 500px; padding: 14px 25px; border-radius: 30px; border: 1px solid #5f6368; background: var(--card); color: white; font-size: 18px; outline: none; }
    .search-box:focus { border-color: var(--accent); }

    .header { position: sticky; top: 0; background: var(--bg); padding: 10px; border-bottom: 1px solid #3c4043; display: flex; align-items: center; gap: 15px; }
    .header img { height: 35px; mix-blend-mode: lighten; }
    .header input { flex: 1; padding: 8px 15px; border-radius: 20px; border: 1px solid #5f6368; background: var(--card); color: white; outline: none; }
    
    .container { max-width: 750px; margin: 20px auto; padding: 0 20px; }
    .res-box { margin-bottom: 25px; border-bottom: 1px solid #333; padding-bottom: 15px; }
    .res-box a { color: var(--accent); font-size: 18px; text-decoration: none; font-weight: bold; }
    .res-box p { color: #bdc1c6; font-size: 14px; margin-top: 8px; line-height: 1.5; }
</style>
"""

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

@app.route('/img/<path:filename>')
def custom_static(filename):
    # キャッシュを有効にして、ウサギが止まらないようにする
    response = send_from_directory(os.getcwd(), filename)
    response.headers['Cache-Control'] = 'public, max-age=31536000'
    return response

@app.route('/')
def index():
    return f"""<html><head><title>プロキシ.pro</title>{CSS}{JS}</head><body>
    <div class='hero'>
        <div class='logo-container'>
            <img src='/img/cat.gif' class='char-gif'>
            <div class='logo-font'>プロキシ.pro</div>
            <img src='/img/rabbit.gif' class='char-gif'>
        </div>
        <input type='text' id='q' class='search-box' onkeypress='check(event)' placeholder='' autofocus>
    </div></body></html>"""

@app.route('/s/<q>')
def results(q):
    query = de(q)
    if query.startswith(('http://', 'https://')): return redirect(f'/p/{ob(query)}')
    
    html = f"<html><head><title>{query} - プロキシ.pro</title>{CSS}{JS}</head><body>"
    html += f"<div class='header'><a href='/'><img src='/img/cat.gif'></a><input type='text' id='q' value='{query}' onkeypress='check(event)'></div>"
    html += "<div class='container'>"
    
    try:
        # DuckDuckGo HTML版（エラーが少ない）を使用
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        for res in soup.select('.result'):
            t_tag = res.select_one('.result__a')
            s_tag = res.select_one('.result__snippet')
            if t_tag:
                title = t_tag.text
                link = t_tag['href']
                snippet = s_tag.text if s_tag else ""
                # DuckDuckGoの外部リダイレクトURLを解除する処理
                if "uddg=" in link:
                    link = urllib.parse.unquote(link.split("uddg=")[1].split("&")[0])
                html += f"<div class='res-box'><a href='/p/{ob(link)}'>{title}</a><p>{snippet}</p></div>"
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
                        el[attr] = f"/p/{ob(urllib.parse.urljoin(url, el[attr]))}"
                yield str(soup).encode('utf-8')
            else:
                for chunk in r.iter_content(chunk_size=8192): yield chunk
        return Response(stream_with_context(generate()), content_type=r.headers.get("Content-Type"))
    except: return "Proxy Error", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
