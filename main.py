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
    body { background: #000; color: #fff; font-family: 'Courier New', monospace; margin: 0; overflow: hidden; }
    .hero { display: flex; flex-direction: column; align-items: center; padding-top: 15vh; }
    .logo-font { font-size: 35px; margin-top: 15px; font-weight: bold; letter-spacing: 2px; }
    .char-gif { height: 110px; cursor: pointer; }
    .search-box { width: 400px; padding: 12px; background: #000; border: 2px solid #fff; color: #fff; margin-top: 20px; outline: none; }

    /* バトルフィールド */
    #battle-screen { display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: #000; z-index: 9999; }
    #field { position: relative; width: 400px; height: 200px; border: 5px solid #fff; margin: 180px auto 0; overflow: hidden; background: #000; }
    
    /* ハート（ソウル） */
    #heart { position: absolute; width: 16px; height: 16px; z-index: 100; transition: background 0.2s; clip-path: polygon(50% 0%, 100% 35%, 80% 100%, 50% 80%, 20% 100%, 0% 35%); }
    .red { background: #f00; }
    .blue { background: #00f; }

    /* 攻撃オブジェクト */
    .bone { position: absolute; background: #fff; z-index: 50; }
    .blaster-line { position: absolute; background: #fff; height: 2px; opacity: 0.5; z-index: 40; }
    .blaster-beam { position: absolute; background: #fff; height: 40px; z-index: 60; box-shadow: 0 0 20px #fff; }

    #ui-box { text-align: center; margin-top: 20px; font-size: 20px; }
    #hp-bar-bg { width: 100px; height: 20px; background: #f00; display: inline-block; vertical-align: middle; margin: 0 10px; }
    #hp-bar-fg { height: 100%; background: #ff0; width: 100%; }
</style>
"""

JS = """
<script>
    let active = false;
    let hp = 92, maxHp = 92;
    let px = 192, py = 100;
    let vx = 0, vy = 0;
    let mode = 'red'; // 'red' or 'blue'
    let keys = {};

    function startBattle() {
        document.getElementById('battle-screen').style.display = 'block';
        active = true;
        gameLoop();
        attackDirector();
    }

    window.onkeydown = (e) => keys[e.code] = true;
    window.onkeyup = (e) => keys[e.code] = false;

    function gameLoop() {
        if(!active) return;

        // 移動ロジック
        if(mode === 'red') {
            if(keys['ArrowUp']) py -= 3;
            if(keys['ArrowDown']) py += 3;
        } else { // 青モード（重力）
            vy += 0.2; // 重力
            py += vy;
            if(keys['ArrowUp'] && py >= 184) vy = -5; // ジャンプ
            if(py > 184) { py = 184; vy = 0; }
        }
        if(keys['ArrowLeft']) px -= 3;
        if(keys['ArrowRight']) px += 3;

        px = Math.max(0, Math.min(384, px));
        py = Math.max(0, Math.min(184, py));

        const h = document.getElementById('heart');
        h.style.left = px + 'px';
        h.style.top = py + 'px';
        h.className = mode;

        checkCollision();
        requestAnimationFrame(gameLoop);
    }

    // Scratchのスクリプト順序を再現したディレクター
    async function attackDirector() {
        while(active) {
            let rand = Math.random();
            if(rand < 0.3) {
                mode = 'blue';
                await spawnBonesLower();
            } else if(rand < 0.6) {
                mode = 'red';
                await spawnBlaster();
            } else {
                await spawnBonesSlide();
            }
            await new Promise(r => setTimeout(r, 1000));
        }
    }

    function createBone(x, y, w, h, vx, vy_b) {
        const b = document.createElement('div');
        b.className = 'bone';
        b.style.left = x+'px'; b.style.top = y+'px'; b.style.width = w+'px'; b.style.height = h+'px';
        document.getElementById('field').appendChild(b);
        let cx = x, cy = y;
        const itv = setInterval(() => {
            cx += vx; cy += vy_b;
            b.style.left = cx+'px'; b.style.top = cy+'px';
            if(cx < -50 || cx > 450) { clearInterval(itv); b.remove(); }
        }, 20);
    }

    async function spawnBonesLower() {
        for(let i=0; i<8; i++) {
            createBone(i*50, 150, 15, 50, 0, 0);
            await new Promise(r => setTimeout(r, 200));
        }
    }

    async function spawnBlaster() {
        const line = document.createElement('div');
        line.className = 'blaster-line';
        line.style.top = py + 8 + 'px'; line.style.width = '400px';
        document.getElementById('field').appendChild(line);
        await new Promise(r => setTimeout(r, 600));
        line.remove();
        const beam = document.createElement('div');
        beam.className = 'blaster-beam';
        beam.style.top = py - 12 + 'px'; beam.style.width = '400px';
        document.getElementById('field').appendChild(beam);
        setTimeout(() => beam.remove(), 200);
    }

    async function spawnBonesSlide() {
        for(let i=0; i<5; i++) {
            createBone(400, 100, 20, 100, -5, 0);
            await new Promise(r => setTimeout(r, 400));
        }
    }

    function checkCollision() {
        const hRect = document.getElementById('heart').getBoundingClientRect();
        document.querySelectorAll('.bone, .blaster-beam').forEach(t => {
            const tRect = t.getBoundingClientRect();
            if(!(hRect.right < tRect.left || hRect.left > tRect.right || hRect.bottom < tRect.top || hRect.top > tRect.bottom)) {
                hp -= 1;
                updateHp();
                if(hp <= 0) location.reload();
            }
        });
    }

    function updateHp() {
        const p = (hp / maxHp) * 100;
        document.getElementById('hp-bar-fg').style.width = p + '%';
        document.getElementById('hp-text').innerText = Math.max(0, Math.ceil(hp));
    }
</script>
"""

@app.route('/')
def index():
    return f"""<html><head><title>猫戦 完全再現</title>{CSS}{JS}</head><body>
    <div id='battle-screen'>
        <div style='text-align:center; padding-top:30px;'>
            <img src='/img/cat.gif' id='boss-cat' style='height:100px;'>
        </div>
        <div id='field'><div id='heart' class='red'></div></div>
        <div id='ui-box'>
            PLAYER LV 19 <div id='hp-bar-bg'><div id='hp-bar-fg'></div></div> <span id='hp-text'>92</span> / 92
        </div>
    </div>
    <div class='hero'>
        <img src='/img/cat.gif' class='char-gif' onclick='startBattle()'>
        <div class='logo-font'>プロキシ.pro</div>
        <input type='text' id='q' class='search-box' onkeypress='if(event.key==="Enter") location.href="/s/"+btoa(this.value)' placeholder=''>
    </div></body></html>"""

@app.route('/img/<path:f>')
def static_img(f): return send_from_directory(os.getcwd(), f)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
