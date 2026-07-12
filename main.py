#!/usr/bin/env python3
"""
TWILIGHT HACKER KI v4.1
- ChatGPT-style interface
- Direct media preview in chat
- Background learning
"""

import os, sys, re, json, time, math, random, hashlib, base64, struct
import socket, ssl, ipaddress, urllib.parse, urllib.request, sqlite3
import threading, subprocess, html as html_mod, textwrap, io, wave, struct as wav_struct
from typing import List, Dict, Tuple, Optional, Any, Union
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

VERSION = "4.1"
NAME = "Twilight Hacker KI"
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "twilight_data")

for d in ["", "images", "videos", "audio", "reports", "tools", "knowledge", 
          "web", "css", "js", "icons", "learning", "models", "cache", "tasks"]:
    os.makedirs(os.path.join(DATA_DIR, d), exist_ok=True)


class Database:
    def __init__(self):
        self.db_path = os.path.join(DATA_DIR, "twilight.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._init_tables()
    
    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                category TEXT,
                description TEXT,
                code TEXT,
                version TEXT,
                usage_count INTEGER DEFAULT 0,
                quality REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                name TEXT UNIQUE,
                description TEXT,
                source TEXT,
                code TEXT,
                quality REAL DEFAULT 0.5,
                verified INTEGER DEFAULT 0,
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT,
                style TEXT,
                filename TEXT,
                seed INTEGER,
                model TEXT,
                quality REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT,
                filename TEXT,
                duration REAL,
                fps INTEGER,
                frames INTEGER,
                has_audio INTEGER DEFAULT 0,
                quality REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS audio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT,
                filename TEXT,
                duration REAL,
                sample_rate INTEGER,
                voice TEXT,
                type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS learning_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                category TEXT,
                details TEXT,
                source_url TEXT,
                quality REAL DEFAULT 0.5,
                verified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS user_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                response_type TEXT,
                response_summary TEXT,
                satisfaction REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS background_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT,
                status TEXT DEFAULT 'pending',
                params TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                content_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()
    
    def save_tool(self, name, category, description, code, quality=0.5):
        with self.lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO tools (name, category, description, code, version, quality) VALUES (?,?,?,?,?,?)",
                (name, category, description, code, VERSION, quality)
            )
            self.conn.commit()
    
    def get_tools(self, category=None):
        with self.lock:
            if category:
                cur = self.conn.execute("SELECT * FROM tools WHERE category=? ORDER BY quality DESC, usage_count DESC", (category,))
            else:
                cur = self.conn.execute("SELECT * FROM tools ORDER BY quality DESC, usage_count DESC")
            rows = cur.fetchall()
            return [{"id": r[0], "name": r[1], "category": r[2], "description": r[3], "code": r[4], "quality": r[6]} for r in rows]
    
    def search_tools(self, query):
        with self.lock:
            cur = self.conn.execute(
                "SELECT * FROM tools WHERE name LIKE ? OR description LIKE ? OR category LIKE ? ORDER BY quality DESC",
                (f'%{query}%', f'%{query}%', f'%{query}%')
            )
            rows = cur.fetchall()
            return [{"id": r[0], "name": r[1], "category": r[2], "description": r[3], "code": r[4], "quality": r[6]} for r in rows]
    
    def increment_usage(self, name):
        with self.lock:
            self.conn.execute("UPDATE tools SET usage_count = usage_count + 1 WHERE name = ?", (name,))
            self.conn.commit()
    
    def save_knowledge(self, category, name, description, source, code, quality=0.5):
        with self.lock:
            existing = self.conn.execute("SELECT quality, version FROM knowledge WHERE name=?", (name,)).fetchone()
            if existing:
                new_quality = (existing[0] + quality) / 2
                new_version = existing[1] + 1
                self.conn.execute(
                    "UPDATE knowledge SET description=?, source=?, code=?, quality=?, version=?, updated_at=CURRENT_TIMESTAMP WHERE name=?",
                    (description, source, code, new_quality, new_version, name)
                )
            else:
                self.conn.execute(
                    "INSERT INTO knowledge (category, name, description, source, code, quality) VALUES (?,?,?,?,?,?)",
                    (category, name, description, source, code, quality)
                )
            self.conn.commit()
    
    def search_knowledge(self, query):
        with self.lock:
            cur = self.conn.execute(
                "SELECT * FROM knowledge WHERE name LIKE ? OR description LIKE ? OR category LIKE ? ORDER BY quality DESC, verified DESC",
                (f'%{query}%', f'%{query}%', f'%{query}%')
            )
            rows = cur.fetchall()
            return [{"id": r[0], "category": r[1], "name": r[2], "description": r[3], "source": r[4], "code": r[5], "quality": r[6], "verified": r[7], "version": r[8]} for r in rows]
    
    def save_image(self, prompt, style, filename, seed, model, quality=0.5):
        with self.lock:
            self.conn.execute(
                "INSERT INTO images (prompt, style, filename, seed, model, quality) VALUES (?,?,?,?,?,?)",
                (prompt[:200], style, filename, seed, model, quality)
            )
            self.conn.commit()
    
    def save_video(self, prompt, filename, duration, fps, frames, has_audio=0):
        with self.lock:
            self.conn.execute(
                "INSERT INTO videos (prompt, filename, duration, fps, frames, has_audio) VALUES (?,?,?,?,?,?)",
                (prompt[:200], filename, duration, fps, frames, has_audio)
            )
            self.conn.commit()
    
    def save_audio(self, prompt, filename, duration, sample_rate, voice, atype):
        with self.lock:
            self.conn.execute(
                "INSERT INTO audio (prompt, filename, duration, sample_rate, voice, type) VALUES (?,?,?,?,?,?)",
                (prompt[:200], filename, duration, sample_rate, voice, atype)
            )
            self.conn.commit()
    
    def log_learning(self, action, category, details, source_url="", quality=0.5):
        with self.lock:
            self.conn.execute(
                "INSERT INTO learning_log (action, category, details, source_url, quality) VALUES (?,?,?,?,?)",
                (action, category, details[:500], source_url, quality)
            )
            self.conn.commit()
    
    def get_learning_log(self, limit=50):
        with self.lock:
            cur = self.conn.execute("SELECT * FROM learning_log ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            return [{"id": r[0], "action": r[1], "category": r[2], "details": r[3], "source": r[4], "quality": r[5], "verified": r[6], "time": str(r[7])} for r in rows]
    
    def log_query(self, query, response_type, summary):
        with self.lock:
            self.conn.execute("INSERT INTO user_queries (query, response_type, response_summary) VALUES (?,?,?)",
                            (query, response_type, summary[:200]))
            self.conn.commit()
    
    def add_task(self, task_type, params=""):
        with self.lock:
            self.conn.execute(
                "INSERT INTO background_tasks (task_type, params) VALUES (?,?)",
                (task_type, params)
            )
            self.conn.commit()
    
    def get_pending_tasks(self, limit=5):
        with self.lock:
            cur = self.conn.execute(
                "SELECT * FROM background_tasks WHERE status='pending' ORDER BY created_at ASC LIMIT ?", (limit,)
            )
            return cur.fetchall()
    
    def complete_task(self, task_id, result=""):
        with self.lock:
            self.conn.execute(
                "UPDATE background_tasks SET status='completed', result=?, completed_at=CURRENT_TIMESTAMP WHERE id=?",
                (result[:500], task_id)
            )
            self.conn.commit()
    
    def add_chat(self, role, content, content_type="text"):
        with self.lock:
            self.conn.execute(
                "INSERT INTO chat_history (role, content, content_type) VALUES (?,?,?)",
                (role, content[:1000], content_type)
            )
            self.conn.commit()
    
    def get_chat(self, limit=50):
        with self.lock:
            cur = self.conn.execute(
                "SELECT * FROM chat_history ORDER BY created_at ASC"
            )
            rows = cur.fetchall()
            return [{"id": r[0], "role": r[1], "content": r[2], "content_type": r[3], "time": str(r[4])} for r in rows[-limit:]]
    
    def clear_chat(self):
        with self.lock:
            self.conn.execute("DELETE FROM chat_history")
            self.conn.commit()
    
    def get_stats(self):
        with self.lock:
            tools_count = self.conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0]
            knowledge_count = self.conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            images_count = self.conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
            videos_count = self.conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
            audio_count = self.conn.execute("SELECT COUNT(*) FROM audio").fetchone()[0]
            queries_count = self.conn.execute("SELECT COUNT(*) FROM user_queries").fetchone()[0]
            verified_knowledge = self.conn.execute("SELECT COUNT(*) FROM knowledge WHERE verified=1").fetchone()[0]
            pending_tasks = self.conn.execute("SELECT COUNT(*) FROM background_tasks WHERE status='pending'").fetchone()[0]
            return {
                "tools": tools_count,
                "knowledge": knowledge_count,
                "verified_knowledge": verified_knowledge,
                "images": images_count,
                "videos": videos_count,
                "audio": audio_count,
                "queries": queries_count,
                "pending_tasks": pending_tasks,
                "version": VERSION,
                "name": NAME
            }

db = Database()


class ImageGenerator:
    def generate(self, prompt, style="realistic", width=512, height=512):
        seed = random.randint(1, 9999999)
        rng = random.Random(seed + hash(prompt))
        ts = int(time.time())
        filename = f"twilight_img_{ts}_{seed}.png"
        filepath = os.path.join(DATA_DIR, "images", filename)
        
        pixels = []
        for y in range(height):
            row = []
            for x in range(width):
                nx, ny = x/width, y/height
                if style == "pixel_art":
                    r,g,b = self._pixel(nx,ny,rng)
                elif style == "anime":
                    r,g,b = self._anime(nx,ny,rng)
                elif style == "cyberpunk":
                    r,g,b = self._cyberpunk(nx,ny,rng)
                elif style == "fantasy":
                    r,g,b = self._fantasy(nx,ny,rng)
                elif style == "minimalist":
                    r,g,b = self._minimal(nx,ny,rng)
                else:
                    r,g,b = self._realistic(nx,ny,rng,seed)
                row.append((r,g,b))
            pixels.append(row)
        
        self._save_png(filepath, pixels, width, height)
        quality = min(1.0, rng.random() * 0.5 + 0.5)
        db.save_image(prompt, style, filename, seed, "twilight_own", quality)
        return {"path": f"/images/{filename}", "seed": seed, "style": style}
    
    def _realistic(self, nx, ny, rng, seed):
        v = (math.sin(nx*10+seed*0.01)*0.3 + math.cos(ny*8+seed*0.02)*0.3 + math.sin((nx+ny)*5)*0.2 + rng.random()*0.2)
        v = max(0, min(1, v))
        base = int(v*200) + 55
        return (min(255,base+int(rng.random()*30)), min(255,base-int(rng.random()*20)), min(255,base+int(rng.random()*40)))
    
    def _anime(self, nx, ny, rng):
        v = (math.sin(nx*6+ny*4)*0.4 + math.cos(nx*3-ny*5)*0.4 + rng.random()*0.2)
        v = max(0, min(1, v))
        return (min(255,int(v*255)), min(255,int(v*200+55)), min(255,int(v*220+35)))
    
    def _cyberpunk(self, nx, ny, rng):
        v = (math.sin(nx*20+ny*15)*0.5 + math.cos(ny*12-nx*8+rng.random())*0.3 + rng.random()*0.2)
        v = max(0, min(1, v))
        return (min(255,int(v*120+135)), min(255,int(v*50+205)), min(255,int(v*100+155)))
    
    def _pixel(self, nx, ny, rng):
        px, py = int(nx*16)/16, int(ny*16)/16
        v = (math.sin(px*10+py*8)*0.5 + math.cos(py*6-px*7)*0.3 + rng.random()*0.2)
        v = max(0, min(1, v))
        c = int(v*200)+55
        return (c, c-20, c+10)
    
    def _fantasy(self, nx, ny, rng):
        v = (math.sin(nx*5+ny*7+1.5)*0.4 + math.cos(nx*3-ny*9+0.7)*0.4 + rng.random()*0.2)
        v = max(0, min(1, v))
        return (min(255,int(v*180+75)), min(255,int(v*100+155)), min(255,int(v*150+105)))
    
    def _minimal(self, nx, ny, rng):
        v = math.sin(int(nx*5)/5*3+int(ny*5)/5*2)*0.5 + rng.random()*0.2
        v = max(0, min(1, v))
        c = int(v*200)+55
        return (c,c,c)
    
    def _save_png(self, filepath, pixels, width, height):
        try:
            sig = b"\x89PNG\r\n\x1a\n"
            raw = b""
            for row in pixels:
                raw += b"\x00"
                for r,g,b in row:
                    raw += bytes([r,g,b])
            import zlib
            compressed = zlib.compress(raw)
            def chunk(t, d):
                c = t+d
                crc = 0
                for cc in c:
                    crc ^= cc
                    for _ in range(8):
                        if crc & 1: crc = (crc>>1)^0xedb88320
                        else: crc >>= 1
                return struct.pack(">I",len(d))+c+struct.pack(">I",crc)
            ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
            with open(filepath, "wb") as f:
                f.write(sig)
                f.write(chunk(b"IHDR", ihdr))
                f.write(chunk(b"IDAT", compressed))
                f.write(chunk(b"IEND", b""))
        except Exception as e:
            print(f"PNG error: {e}")


class VideoGenerator:
    def generate(self, prompt, duration=3.0, fps=8, style="realistic"):
        img_gen = ImageGenerator()
        frames = int(duration*fps)
        seed = random.randint(1, 9999999)
        frame_files = []
        for i in range(frames):
            r = img_gen.generate(f"{prompt} frame {i}", style, width=256, height=256)
            frame_files.append(r["path"])
        ts = int(time.time())
        filename = f"twilight_vid_{ts}_{seed}.txt"
        filepath = os.path.join(DATA_DIR, "videos", filename)
        with open(filepath, "w") as f:
            f.write(f"Video: {prompt}\nFrames: {frames}\nDuration: {duration}s\n\n")
            for i, fp in enumerate(frame_files):
                f.write(f"=== Frame {i+1}/{frames} ===\n")
                f.write(f"Path: {fp}\n\n")
        db.save_video(prompt, filename, duration, fps, frames)
        return {"path": f"/videos/{filename}", "frames": frames, "duration": duration, "fps": fps, "seed": seed}


class MusicGenerator:
    def generate(self, prompt, duration=5.0):
        seed = random.randint(1, 9999999)
        rng = random.Random(seed + hash(prompt))
        sr = 22050
        ns = int(sr*duration)
        notes = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
        weights = [0.1, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.05]
        ql = prompt.lower()
        if any(w in ql for w in ["sad","traurig","melancholisch","dark"]):
            weights = [0.3,0.2,0.15,0.1,0.1,0.05,0.05,0.05]
        elif any(w in ql for w in ["happy","fröhlich","joy","upbeat"]):
            weights = [0.02,0.05,0.1,0.2,0.25,0.2,0.1,0.08]
        samples = []
        for i in range(ns):
            t = i/sr
            val = 0
            for j,(freq,w) in enumerate(zip(notes,weights)):
                val += math.sin(2*math.pi*freq*t)*w*0.3
                val += math.sin(2*math.pi*freq*2*t)*w*0.1
            env = min(1.0, t*20) * max(0, 1-(t/duration)*0.3)
            val *= env * 0.5
            val = max(-1, min(1, val))
            samples.append(int(val*32767))
        ts = int(time.time())
        filename = f"twilight_music_{ts}_{seed}.wav"
        filepath = os.path.join(DATA_DIR, "audio", filename)
        with wave.open(filepath, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        db.save_audio(prompt, filename, duration, sr, "instrumental", "music")
        return {"path": f"/audio/{filename}", "duration": duration, "seed": seed}


class SpeechGenerator:
    def generate(self, text, voice="default", speed=1.0):
        seed = hash(text+voice) & 0xFFFFFF
        rng = random.Random(seed)
        sr = 16000
        char_dur = 0.08/speed
        ns = int(len(text)*char_dur*sr)
        ns = max(ns, sr)
        voice_freqs = {"male":120,"female":220,"robot":300,"deep":80,"soft":180,"default":150}
        bf = voice_freqs.get(voice.lower(), 150)
        samples = []
        for i in range(ns):
            t = i/sr
            ci = int(t/char_dur)
            cv = ord(text[ci])/255 if ci < len(text) else 0.5
            freq = bf + math.sin(2*math.pi*4*t)*10
            val = (math.sin(2*math.pi*freq*t)*0.4 + math.sin(2*math.pi*freq*2*t)*0.2 + rng.random()*0.05)
            val += math.sin(2*math.pi*bf*(1+cv*0.5)*t)*0.2*cv
            env = min(1.0, t*30) * max(0, 1-(t/(ns/sr))*0.2)
            val *= env * 0.5
            val = max(-1, min(1, val))
            samples.append(int(val*32767))
        ts = int(time.time())
        filename = f"twilight_speech_{ts}_{seed:x}.wav"
        filepath = os.path.join(DATA_DIR, "audio", filename)
        with wave.open(filepath, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        db.save_audio(text, filename, ns/sr, sr, voice, "speech")
        return {"path": f"/audio/{filename}", "text": text, "voice": voice, "duration": ns/sr}


class BackgroundLearner:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            db.log_learning("system", "system", "Background learner started")
    
    def stop(self):
        self.running = False
    
    def _loop(self):
        cycle = 0
        while self.running:
            try:
                cycle += 1
                self._learn_github()
                self._consolidate()
                db.log_learning("background", "system", f"Cycle {cycle} completed")
                for _ in range(30*60):
                    if not self.running: break
                    time.sleep(1)
            except Exception as e:
                db.log_learning("background_error", "system", str(e))
                time.sleep(60)
    
    def _learn_github(self):
        try:
            queries = ["pentesting python","security scanner","exploit tool","network scanner"]
            for q in queries:
                if not self.running: break
                try:
                    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&per_page=3"
                    req = urllib.request.Request(url, headers={"User-Agent":"Twilight-KI/4.0"})
                    resp = urllib.request.urlopen(req, timeout=10)
                    data = json.loads(resp.read().decode())
                    for item in data.get("items",[])[:3]:
                        if not self.running: break
                        name = item["full_name"]
                        stars = item["stargazers_count"]
                        quality = min(1.0, stars/1000)
                        if quality >= 0.3:
                            existing = db.search_knowledge(name)
                            if not existing:
                                try:
                                    ru = f"https://api.github.com/repos/{name}/readme"
                                    rr = urllib.request.Request(ru, headers={"User-Agent":"Twilight-KI/4.0","Accept":"application/vnd.github.v3.raw"})
                                    rresp = urllib.request.urlopen(rr, timeout=10)
                                    readme = rresp.read().decode("utf-8","replace")[:2000]
                                except:
                                    readme = item.get("description","")
                                db.save_knowledge("github", name, item.get("description",""), item["html_url"], readme, quality)
                                db.log_learning("github_learn", "github", f"Learned: {name} ({stars}★)", item["html_url"], quality)
                except:
                    pass
                time.sleep(2)
        except:
            pass
    
    def _consolidate(self):
        try:
            tools = db.get_tools()
            for i, t1 in enumerate(tools):
                for t2 in tools[i+1:]:
                    s1 = set(t1["name"].lower().split())
                    s2 = set(t2["name"].lower().split())
                    if s1 and s2 and len(s1&s2)/len(s1|s2) > 0.5:
                        if t1.get("quality",0) > t2.get("quality",0):
                            db.increment_usage(t1["name"])
        except:
            pass


def generate_html():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Twilight Hacker KI</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
:root{--bg:#212121;--bg2:#171717;--bg3:#2f2f2f;--bg4:#3a3a3a;--primary:#10a37f;--primary-hover:#0e8c6d;--text:#ececf1;--text2:#8e8ea0;--border:#4d4d4f;--user-bg:#343541;--ai-bg:#444654;--font:"Segoe UI",system-ui,sans-serif;}
body{font-family:var(--font);background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column;overflow:hidden;}
/* ChatGPT Sidebar */
.sidebar{width:260px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;overflow:hidden;}
.sidebar-header{padding:12px;border-bottom:1px solid var(--border);}
.sidebar-header h2{font-size:0.95em;color:var(--text);display:flex;align-items:center;gap:8px;}
.sidebar-header h2 .dot{width:8px;height:8px;border-radius:50%;background:var(--primary);display:inline-block;}
.new-chat-btn{width:calc(100%-24px);margin:12px;padding:10px;background:transparent;border:1px solid var(--border);border-radius:6px;color:var(--text);cursor:pointer;font-size:0.85em;transition:all 0.2s;text-align:left;}
.new-chat-btn:hover{background:var(--bg3);border-color:var(--text2);}
.chat-list{flex:1;overflow-y:auto;padding:8px;}
.chat-item{padding:10px 12px;border-radius:6px;cursor:pointer;font-size:0.85em;color:var(--text2);transition:all 0.2s;margin-bottom:2px;}
.chat-item:hover{background:var(--bg3);color:var(--text);}
.chat-item.active{background:var(--bg3);color:var(--text);}
.sidebar-footer{padding:12px;border-top:1px solid var(--border);font-size:0.75em;color:var(--text2);}
/* Main chat area */
.chat-container{flex:1;display:flex;flex-direction:column;overflow:hidden;}
.chat-header{padding:12px 20px;border-bottom:1px solid var(--border);text-align:center;font-size:0.85em;color:var(--text2);background:var(--bg);flex-shrink:0;}
.chat-messages{flex:1;overflow-y:auto;padding:0;}
.message{display:flex;padding:20px 20px;gap:15px;animation:fadeIn 0.3s ease;}
.message.user{background:var(--user-bg);}
.message.ai{background:var(--ai-bg);}
.message-avatar{width:30px;height:30px;border-radius:2px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:0.8em;}
.message-avatar.user{background:#5436da;color:white;}
.message-avatar.ai{background:var(--primary);color:white;}
.message-content{flex:1;font-size:0.95em;line-height:1.6;min-width:0;}
.message-content p{margin-bottom:8px;}
.message-content img{max-width:100%;max-height:400px;border-radius:8px;margin:10px 0;border:1px solid var(--border);}
.message-content audio,.message-content video{width:100%;max-width:500px;margin:10px 0;}
.message-content pre{background:var(--bg);padding:12px;border-radius:6px;overflow-x:auto;font-size:0.85em;margin:8px 0;border:1px solid var(--border);}
.message-content code{background:var(--bg3);padding:2px 4px;border-radius:3px;font-size:0.9em;}
/* Input area */
.input-area{padding:0 20px 20px;background:linear-gradient(transparent,var(--bg) 40%);flex-shrink:0;}
.input-box{display:flex;align-items:flex-end;gap:8px;background:var(--bg3);border:1px solid var(--border);border-radius:12px;padding:10px 15px;max-width:768px;margin:0 auto;}
.input-box textarea{flex:1;background:transparent;border:none;color:var(--text);font-family:var(--font);font-size:0.95em;outline:none;resize:none;min-height:24px;max-height:120px;line-height:1.5;}
.input-box button{background:transparent;border:none;color:var(--text2);cursor:pointer;padding:6px;border-radius:6px;transition:all 0.2s;font-size:1.1em;}
.input-box button:hover{color:var(--text);background:var(--bg4);}
.input-box button.send{background:var(--primary);color:white;width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:6px;}
.input-box button.send:hover{background:var(--primary-hover);}
.input-box button.send:disabled{opacity:0.4;cursor:not-allowed;}
@keyframes fadeIn{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
.typing{display:flex;gap:4px;padding:4px 0;}
.typing span{width:8px;height:8px;border-radius:50%;background:var(--text2);animation:pulse 1.4s ease infinite;}
.typing span:nth-child(2){animation-delay:0.2s}
.typing span:nth-child(3){animation-delay:0.4s}
/* Scrollbar */
::-webkit-scrollbar{width:6px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:var(--text2);}
/* Model selector */
.model-selector{display:flex;gap:8px;padding:10px 20px;background:var(--bg);border-bottom:1px solid var(--border);flex-shrink:0;overflow-x:auto;}
.model-btn{background:transparent;border:1px solid var(--border);color:var(--text2);padding:6px 14px;border-radius:20px;cursor:pointer;font-size:0.8em;transition:all 0.2s;flex-shrink:0;}
.model-btn:hover{border-color:var(--primary);color:var(--text);}
.model-btn.active{background:var(--primary);border-color:var(--primary);color:white;}
/* Responsive */
@media(max-width:768px){
.sidebar{display:none;}
.message{padding:15px 12px;gap:10px;}
}
/* Full layout */
.app{display:flex;height:100vh;overflow:hidden;}
</style>
</head>
<body>
<div class="app">
<!-- Sidebar -->
<div class="sidebar">
<div class="sidebar-header">
<h2><span class="dot"></span> Twilight KI</h2>
</div>
<button class="new-chat-btn" onclick="newChat()">+ New chat</button>
<div class="chat-list">
<div class="chat-item active">Current chat</div>
</div>
<div class="sidebar-footer">
<div style="display:flex;justify-content:space-between;align-items:center;">
<span>v""" + VERSION + """</span>
<span id="sidebarStats">0 tools</span>
</div>
</div>
</div>
<!-- Chat Container -->
<div class="chat-container">
<!-- Model Selector -->
<div class="model-selector">
<button class="model-btn active" onclick="selectModel(this,'default')">Default</button>
<button class="model-btn" onclick="selectModel(this,'image')">Image Gen</button>
<button class="model-btn" onclick="selectModel(this,'video')">Video Gen</button>
<button class="model-btn" onclick="selectModel(this,'music')">Music Gen</button>
<button class="model-btn" onclick="selectModel(this,'speech')">Speech Gen</button>
<button class="model-btn" onclick="selectModel(this,'tool')">Tool Gen</button>
</div>
<!-- Chat Header -->
<div class="chat-header">
<span>Twilight Hacker KI - Background learning active</span>
</div>
<!-- Messages -->
<div class="chat-messages" id="chatMessages">
<div class="message ai">
<div class="message-avatar ai">T</div>
<div class="message-content">
<p>Hello! I'm Twilight Hacker KI. I can help you with:</p>
<ul style="margin-left:20px;margin-bottom:8px;">
<li>Generating images, videos, music, and speech</li>
<li>Creating pentesting tools</li>
<li>Searching GitHub for security tools</li>
<li>Learning in the background</li>
</ul>
<p>What would you like to create?</p>
</div>
</div>
</div>
<!-- Input Area -->
<div class="input-area">
<div class="input-box">
<textarea id="chatInput" placeholder="Send a message..." rows="1" oninput="autoResize(this)" onkeydown="handleKey(event)"></textarea>
<button class="send" id="sendBtn" onclick="sendMessage()">➤</button>
</div>
</div>
</div>
</div>
<script>
var currentModel = "default";
var isGenerating = false;

document.addEventListener("DOMContentLoaded", function() {
    loadStats();
    setInterval(loadStats, 15000);
    document.getElementById("chatInput").focus();
});

function autoResize(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
}

function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function selectModel(btn, model) {
    document.querySelectorAll(".model-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentModel = model;
    addMessage("System", "Switched to " + model + " mode", "ai");
}

function sendMessage() {
    var input = document.getElementById("chatInput");
    var text = input.value.trim();
    if (!text || isGenerating) return;
    
    addMessage("You", text, "user");
    input.value = "";
    input.style.height = "auto";
    
    isGenerating = true;
    document.getElementById("sendBtn").disabled = true;
    
    // Typing indicator
    var typingId = showTyping();
    
    apiCall("/api/query", {query: text, model: currentModel}, function(data) {
        removeTyping(typingId);
        displayResponse(data);
        isGenerating = false;
        document.getElementById("sendBtn").disabled = false;
        document.getElementById("chatInput").focus();
    });
}

function addMessage(role, content, type) {
    var container = document.getElementById("chatMessages");
    var div = document.createElement("div");
    div.className = "message " + type;
    
    var avatar = document.createElement("div");
    avatar.className = "message-avatar " + type;
    avatar.textContent = role === "You" ? "U" : "T";
    
    var contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    
    var p = document.createElement("p");
    p.textContent = content;
    contentDiv.appendChild(p);
    
    div.appendChild(avatar);
    div.appendChild(contentDiv);
    container.appendChild(div);
    scrollToBottom();
}

function showTyping() {
    var container = document.getElementById("chatMessages");
    var div = document.createElement("div");
    div.className = "message ai";
    div.id = "typing-" + Date.now();
    
    var avatar = document.createElement("div");
    avatar.className = "message-avatar ai";
    avatar.textContent = "T";
    
    var contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    contentDiv.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
    
    div.appendChild(avatar);
    div.appendChild(contentDiv);
    container.appendChild(div);
    scrollToBottom();
    return div.id;
}

function removeTyping(id) {
    var el = document.getElementById(id);
    if (el) el.remove();
}

function displayResponse(data) {
    var container = document.getElementById("chatMessages");
    var div = document.createElement("div");
    div.className = "message ai";
    
    var avatar = document.createElement("div");
    avatar.className = "message-avatar ai";
    avatar.textContent = "T";
    
    var contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    
    var html = "";
    
    // Check for different response types
    if (data.type === "image" && data.image) {
        html += '<p>Generated image (' + (data.image.style || "realistic") + ' style):</p>';
        html += '<img src="' + data.image.path + '" alt="Generated image" loading="lazy">';
        html += '<p style="font-size:0.8em;color:var(--text2);">Seed: ' + data.image.seed + '</p>';
    } else if (data.type === "video" && data.video) {
        html += '<p>Generated video (' + data.video.frames + ' frames, ' + data.video.duration + 's):</p>';
        html += '<div style="background:var(--bg);padding:15px;border-radius:8px;border:1px solid var(--border);margin:10px 0;">';
        html += '<p style="font-family:monospace;font-size:0.85em;">📹 Video: ' + data.video.frames + ' frames @ ' + data.video.fps + 'fps</p>';
        html += '<p style="font-size:0.8em;color:var(--text2);">Duration: ' + data.video.duration + 's | Seed: ' + data.video.seed + '</p>';
        html += '<a href="' + data.video.path + '" target="_blank" style="color:var(--primary);font-size:0.85em;">📄 View video file</a>';
        html += '</div>';
    } else if (data.type === "music" && data.music) {
        html += '<p>Generated music:</p>';
        html += '<audio controls><source src="' + data.music.path + '" type="audio/wav">Your browser does not support audio</audio>';
        html += '<p style="font-size:0.8em;color:var(--text2);">Duration: ' + data.music.duration.toFixed(1) + 's | Seed: ' + data.music.seed + '</p>';
    } else if (data.type === "speech" && data.speech) {
        html += '<p>Generated speech (' + data.speech.voice + ' voice):</p>';
        html += '<audio controls><source src="' + data.speech.path + '" type="audio/wav">Your browser does not support audio</audio>';
        html += '<p style="font-size:0.8em;color:var(--text2);">Text: "' + escapeHtml(data.speech.text.substring(0,100)) + '" | Duration: ' + data.speech.duration.toFixed(1) + 's</p>';
    } else if (data.type === "full_video") {
        html += '<p>Generated full video with audio and speech:</p>';
        if (data.video) html += '<div style="background:var(--bg);padding:15px;border-radius:8px;border:1px solid var(--border);margin:10px 0;"><p>📹 ' + data.video.frames + ' frames</p></div>';
        if (data.music) html += '<audio controls style="margin:5px 0;"><source src="' + data.music.path + '" type="audio/wav"></audio>';
        if (data.speech) html += '<audio controls style="margin:5px 0;"><source src="' + data.speech.path + '" type="audio/wav"></audio>';
        html += '<p style="font-size:0.8em;color:var(--text2);">' + (data.message || "") + '</p>';
    } else if (data.type === "tool" && data.tool) {
        html += '<p>Generated tool: <strong>' + escapeHtml(data.tool.name) + '</strong></p>';
        html += '<p style="font-size:0.85em;color:var(--text2);margin-bottom:8px;">Source: ' + escapeHtml(data.source || "database") + '</p>';
        if (data.tool.description) html += '<p style="font-size:0.85em;margin-bottom:8px;">' + escapeHtml(data.tool.description) + '</p>';
        if (data.tool.code) {
            html += '<pre>' + escapeHtml(data.tool.code.substring(0,500)) + '</pre>';
            if (data.tool.code.length > 500) html += '<p style="font-size:0.8em;color:var(--text2);">... (truncated)</p>';
        }
    } else if (data.analysis) {
        html += '<div style="background:var(--bg);padding:10px;border-radius:6px;border:1px solid var(--border);margin:8px 0;font-size:0.85em;">';
        html += '<p>🎯 <strong>Analysis:</strong></p>';
        html += '<p>Style: ' + data.analysis.style + ' | Medium: ' + data.analysis.medium + ' | Intent: ' + data.analysis.intent + '</p>';
        html += '</div>';
    } else if (data.message) {
        html += '<p>' + escapeHtml(data.message) + '</p>';
    } else if (data.error) {
        html += '<p style="color:#ff5555;">Error: ' + escapeHtml(data.error) + '</p>';
    } else {
        var text = JSON.stringify(data, null, 2);
        if (text.length > 1000) text = text.substring(0,1000) + "...";
        html += '<pre>' + escapeHtml(text) + '</pre>';
    }
    
    contentDiv.innerHTML = html;
    div.appendChild(avatar);
    div.appendChild(contentDiv);
    container.appendChild(div);
    scrollToBottom();
    loadStats();
}

function scrollToBottom() {
    var container = document.getElementById("chatMessages");
    container.scrollTop = container.scrollHeight;
}

function loadStats() {
    apiGet("/api/status", function(data) {
        var st = document.getElementById("sidebarStats");
        if (st) st.textContent = (data.tools || 0) + " tools";
    });
}

function newChat() {
    if (confirm("Clear current chat?")) {
        document.getElementById("chatMessages").innerHTML = "";
        addMessage("Twilight", "Chat cleared. What would you like to do?", "ai");
    }
}

function apiCall(url, data, cb) {
    var x = new XMLHttpRequest();
    x.open("POST", url, true);
    x.setRequestHeader("Content-Type", "application/json");
    x.onload = function() {
        try { cb(JSON.parse(x.responseText)); }
        catch(e) { cb({error: e.message}); }
    };
    x.onerror = function() { cb({error: "Network error"}); };
    x.send(JSON.stringify(data));
}

function apiGet(url, cb) {
    var x = new XMLHttpRequest();
    x.open("GET", url, true);
    x.onload = function() {
        try { cb(JSON.parse(x.responseText)); }
        catch(e) { cb({error: e.message}); }
    };
    x.onerror = function() { cb({error: "Network error"}); };
    x.send();
}

function escapeHtml(t) {
    var d = document.createElement("div");
    d.textContent = t;
    return d.innerHTML;
}
</script>
</body>
</html>"""
    
    path = os.path.join(DATA_DIR, "web", "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return html


class Handler(BaseHTTPRequestHandler):
    ki = None
    
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "":
            self._serve_html(os.path.join(DATA_DIR, "web", "index.html"))
        elif any(path.startswith(p) for p in ["/images/","/videos/","/audio/"]):
            local_path = os.path.join(DATA_DIR, path.lstrip("/"))
            if os.path.exists(local_path) and os.path.isfile(local_path):
                ext = os.path.splitext(local_path)[1].lower()
                mime = {".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",
                        ".gif":"image/gif",".mp4":"video/mp4",".wav":"audio/wav",
                        ".txt":"text/plain",".raw":"application/octet-stream"}.get(ext,"application/octet-stream")
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(local_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"Not Found"}')
        elif path == "/api/tools":
            self._json({"tools": db.get_tools()})
        elif path == "/api/status":
            self._json(self.ki.get_stats())
        elif path == "/api/learning":
            entries = db.get_learning_log(100)
            self._json({"entries": entries})
        elif path == "/api/chat":
            chat = db.get_chat()
            self._json({"messages": chat})
        else:
            self._serve_html(os.path.join(DATA_DIR, "web", "index.html"))
    
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        path = urlparse(self.path).path
        
        try:
            if path == "/api/query":
                query = data.get("query", "")
                model = data.get("model", "default")
                result = self.ki.process(query)
                db.add_chat("user", query, "text")
                db.log_query(query, result.get("type","unknown"), json.dumps(result)[:200])
                self._json(result)
            elif path == "/api/generate/image":
                prompt = data.get("prompt", "test")
                style = data.get("style", "realistic")
                result = self.ki.img_gen.generate(prompt, style)
                self._json(result)
            elif path == "/api/generate/video":
                prompt = data.get("prompt", "test")
                result = self.ki.vid_gen.generate(prompt)
                self._json(result)
            elif path == "/api/generate/music":
                prompt = data.get("prompt", "ambient")
                result = self.ki.music_gen.generate(prompt)
                self._json(result)
            elif path == "/api/generate/speech":
                text = data.get("text", "Hello")
                voice = data.get("voice", "default")
                result = self.ki.speech_gen.generate(text, voice)
                self._json(result)
            else:
                self._json({"error": "Unknown endpoint"})
        except Exception as e:
            self._json({"error": str(e)})
    
    def _serve_html(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h1>Twilight Hacker KI</h1><p>Loading...</p>")
    
    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))
    
    def log_message(self, fmt, *args):
        print(f"[{args[0]}] {args[1]} {args[2]}")


class TwilightKI:
    def __init__(self):
        self.start_time = time.time()
        self.img_gen = ImageGenerator()
        self.vid_gen = VideoGenerator()
        self.music_gen = MusicGenerator()
        self.speech_gen = SpeechGenerator()
        self.background = BackgroundLearner()
        self.background.start()
        self._init_defaults()
        db.log_learning("system", "system", f"Twilight Hacker KI v{VERSION} initialized")
    
    def _init_defaults(self):
        defaults = [
            ("Port-Scanner", "recon", "TCP port scanner"),
            ("SQL-Injector", "exploit", "SQL injection tester"),
            ("XSS-Engine", "exploit", "XSS detector"),
            ("Dir-Fuzzer", "web", "Directory brute-forcer"),
            ("Reverse-Shell-Gen", "post_exploit", "Reverse shell generator"),
            ("SYN-Flood", "dos_ddos", "SYN flood tool"),
            ("ARP-Spoofer", "mitm", "ARP spoofer"),
            ("Password-Cracker", "password", "Hash cracker"),
            ("WiFi-Scanner", "wireless", "Wireless scanner")
        ]
        existing = {t["name"] for t in db.get_tools()}
        for name, cat, desc in defaults:
            if name not in existing:
                db.save_tool(name, cat, desc, f"# {name}\n# {desc}\n# Generated by Twilight KI", quality=0.5)
    
    def process(self, query):
        q = query.strip()
        if not q:
            return {"message": "Please enter a query."}
        
        ql = q.lower()
        
        # Model-basierte Verarbeitung
        if "image" in ql or any(w in ql for w in ["bild","zeichne","generate image","create image"]):
            result = self.img_gen.generate(q)
            return {"type": "image", "image": result}
        
        if "video" in ql or any(w in ql for w in ["film","animation"]):
            dur = 3.0
            for w in q.split():
                try:
                    if "sek" in w.lower() or "sec" in w.lower():
                        dur = float(re.search(r"(\d+)", w).group(1))
                except:
                    pass
            result = self.vid_gen.generate(q, duration=dur)
            return {"type": "video", "video": result}
        
        if "music" in ql or "musik" in ql or "song" in ql or any(w in ql for w in ["melodie","sound","klang"]):
            result = self.music_gen.generate(q)
            return {"type": "music", "music": result}
        
        if "speech" in ql or "sprache" in ql or "say" in ql or "sag" in ql or any(w in ql for w in ["sprechen","voice","stimme"]):
            text = q
            for prefix in ["speech","sprache","say","sag","generate speech","sag mir","spreche"]:
                if prefix in ql:
                    idx = ql.index(prefix) + len(prefix)
                    text = q[idx:].strip().strip(":;,. \"'")
                    if not text:
                        text = q
            result = self.speech_gen.generate(text)
            return {"type": "speech", "speech": result}
        
        if any(w in ql for w in ["full","komplett","video mit"]):
            video = self.vid_gen.generate(q, duration=5.0)
            music = self.music_gen.generate(f"{q} background music", duration=5.0)
            speech = self.speech_gen.generate(q)
            return {"type": "full_video", "video": video, "music": music, "speech": speech, "message": "Full video with audio and speech generated"}
        
        # Tool-Suche
        existing = db.search_tools(q)
        if existing:
            best = existing[0]
            db.increment_usage(best["name"])
            return {"type": "tool", "tool": best, "source": "database"}
        
        # GitHub-Suche
        try:
            url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q + ' python')}&sort=stars&per_page=3"
            req = urllib.request.Request(url, headers={"User-Agent":"Twilight-KI/4.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            if data.get("items"):
                item = data["items"][0]
                quality = min(1.0, item["stargazers_count"]/500)
                name = item["full_name"]
                db.save_tool(q, "auto", f"From GitHub: {item['description']}", 
                            f"Source: {item['html_url']}\nStars: {item['stargazers_count']}", quality)
                db.log_learning("tool_github", "github", f"Found: {name}", item["html_url"], quality)
                return {
                    "type": "tool",
                    "tool": {"name": name, "description": item.get("description",""), 
                            "code": f"Source: {item['html_url']}\n{quality:.0%} quality"},
                    "source": "github",
                    "message": f"Found on GitHub: {name} ({item['stargazers_count']}★)"
                }
        except:
            pass
        
        # Fallback: Bild generieren
        result = self.img_gen.generate(q)
        return {"type": "image", "image": result, "message": "Generated image from your description"}
    
    def get_stats(self):
        stats = db.get_stats()
        uptime = int(time.time() - self.start_time)
        d = uptime//86400
        h = (uptime%86400)//3600
        m = (uptime%3600)//60
        stats["uptime"] = f"{d}d {h}h {m}m"
        stats["background_learning"] = self.background.running
        return stats


if __name__ == "__main__":
    print("="*50)
    print(f"  Twilight Hacker KI v{VERSION}")
    print("  ChatGPT-style UI with direct media preview")
    print("="*50)
    
    _ = Database()
    generate_html()
    ki = TwilightKI()
    
    stats = db.get_stats()
    print(f"\n  {stats['tools']} tools loaded")
    print(f"  Background learning: Active")
    print(f"  Server starting on port {PORT}")
    
    Handler.ki = ki
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        ki.background.stop()
        server.server_close()
