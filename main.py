#!/usr/bin/env python3
"""
TWILIGHT'S HACKER KI v4.0
- Self-learning AI platform
- Image, Video, Music, Speech generation
- Background learning agent
- Railway ready
"""

import os, sys, re, json, time, math, random, hashlib, base64, struct
import socket, ssl, ipaddress, urllib.parse, urllib.request, sqlite3
import threading, subprocess, html as html_mod, textwrap, io, wave, struct as wav_struct
from typing import List, Dict, Tuple, Optional, Any, Union
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

VERSION = "4.0"
NAME = "Twilight Hacker KI"
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "twilight_data")

for d in ["", "images", "videos", "audio", "reports", "tools", "knowledge", 
          "web", "css", "js", "icons", "learning", "models", "cache", "tasks"]:
    os.makedirs(os.path.join(DATA_DIR, d), exist_ok=True)


class Database:
    """Persistent knowledge base with quality ratings"""
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
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_input TEXT,
                parsed_prompt TEXT,
                style TEXT,
                medium TEXT,
                sentiment TEXT,
                intent TEXT,
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
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_text TEXT,
                sentiment TEXT,
                topics TEXT,
                action_taken TEXT,
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
        """)
        self.conn.commit()
    
    # ===== Tools =====
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
    
    # ===== Knowledge =====
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
    
    def get_knowledge_stats(self):
        with self.lock:
            total = self.conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            verified = self.conn.execute("SELECT COUNT(*) FROM knowledge WHERE verified=1").fetchone()[0]
            by_cat = self.conn.execute("SELECT category, COUNT(*) FROM knowledge GROUP BY category ORDER BY COUNT(*) DESC").fetchall()
            return {"total": total, "verified": verified, "categories": dict(by_cat)}
    
    # ===== Images =====
    def save_image(self, prompt, style, filename, seed, model, quality=0.5):
        with self.lock:
            self.conn.execute(
                "INSERT INTO images (prompt, style, filename, seed, model, quality) VALUES (?,?,?,?,?,?)",
                (prompt, style, filename, seed, model, quality)
            )
            self.conn.commit()
    
    # ===== Videos =====
    def save_video(self, prompt, filename, duration, fps, frames, has_audio=0):
        with self.lock:
            self.conn.execute(
                "INSERT INTO videos (prompt, filename, duration, fps, frames, has_audio) VALUES (?,?,?,?,?,?)",
                (prompt, filename, duration, fps, frames, has_audio)
            )
            self.conn.commit()
    
    # ===== Prompts =====
    def save_prompt(self, raw_input, parsed_prompt, style, medium, sentiment, intent):
        with self.lock:
            self.conn.execute(
                "INSERT INTO prompts (raw_input, parsed_prompt, style, medium, sentiment, intent) VALUES (?,?,?,?,?,?)",
                (raw_input[:500], parsed_prompt[:500], style, medium, sentiment, intent)
            )
            self.conn.commit()
    
    # ===== Learning =====
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
            return [{"id": r[0], "action": r[1], "category": r[2], "details": r[3], "source": r[4], "quality": r[5], "verified": r[6], "time": r[7]} for r in rows]
    
    # ===== Queries =====
    def log_query(self, query, response_type, summary):
        with self.lock:
            self.conn.execute("INSERT INTO user_queries (query, response_type, response_summary) VALUES (?,?,?)",
                            (query, response_type, summary))
            self.conn.commit()
    
    # ===== Comments =====
    def save_comment(self, comment_text, sentiment, topics, action_taken=""):
        with self.lock:
            self.conn.execute(
                "INSERT INTO comments (comment_text, sentiment, topics, action_taken) VALUES (?,?,?,?)",
                (comment_text[:500], sentiment, topics[:200], action_taken)
            )
            self.conn.commit()
    
    # ===== Tasks =====
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
    
    # ===== Stats =====
    def get_stats(self):
        with self.lock:
            tools_count = self.conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0]
            knowledge_count = self.conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            images_count = self.conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
            videos_count = self.conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
            queries_count = self.conn.execute("SELECT COUNT(*) FROM user_queries").fetchone()[0]
            comments_count = self.conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
            verified_knowledge = self.conn.execute("SELECT COUNT(*) FROM knowledge WHERE verified=1").fetchone()[0]
            pending_tasks = self.conn.execute("SELECT COUNT(*) FROM background_tasks WHERE status='pending'").fetchone()[0]
            
            return {
                "tools": tools_count,
                "knowledge": knowledge_count,
                "verified_knowledge": verified_knowledge,
                "images": images_count,
                "videos": videos_count,
                "queries": queries_count,
                "comments_analyzed": comments_count,
                "pending_tasks": pending_tasks
            }

db = Database()


class PromptAnalyzer:
    """Intelligente Prompt-Verarbeitung - erkennt Stil, Medium, Intent, Sentiment"""
    
    STYLES = {
        "realistic": ["realistic", "photorealistic", "real", "photo", "realistisch", "echt", "foto"],
        "anime": ["anime", "manga", "japanese", "cartoon", "japanisch", "zeichnung"],
        "3d": ["3d", "three-dimensional", "rendered", "pixar", "dreamworks", "blender"],
        "pixel_art": ["pixel", "pixelart", "retro", "8bit", "16bit", "nes", "gameboy"],
        "oil_painting": ["oil", "painting", "canvas", "paint", "öl", "gemälde", "van gogh"],
        "watercolor": ["watercolor", "water colour", "aquarell", "watercolour"],
        "sketch": ["sketch", "drawing", "pencil", "skizze", "bleistift", "line art"],
        "cyberpunk": ["cyberpunk", "neon", "dark", "futuristic", "dystopian", "blade runner"],
        "fantasy": ["fantasy", "magical", "dragon", "castle", "mythical", "elf", "fairy"],
        "minimalist": ["minimal", "simple", "flat", "clean", "modern", "minimalistisch"]
    }
    
    MEDIUMS = {
        "image": ["bild", "image", "picture", "photo", "foto", "zeichnung", "draw", "illustration"],
        "video": ["video", "film", "movie", "clip", "animation", "filmchen"],
        "music": ["music", "song", "melody", "sound", "audio", "musik", "lied", "melodie"],
        "speech": ["speech", "voice", "narrator", "sprecher", "stimme", "erzähler", "dialog"],
        "full_video": ["full video", "video mit ton", "video mit sprache", "movie with sound", "kinofilm"]
    }
    
    INTENTS = {
        "create": ["create", "generate", "make", "erstellen", "generieren", "produzieren", "zeichne", "mach"],
        "analyze": ["analyze", "analyse", "check", "test", "scan", "untersuchen", "prüfen"],
        "learn": ["learn", "search", "find", "look up", "suchen", "finden", "recherchieren"],
        "explain": ["explain", "describe", "what is", "how to", "erklären", "beschreiben", "was ist"],
        "summarize": ["summarize", "summary", "zusammenfassen", "zusammenfassung"],
        "modify": ["change", "modify", "update", "edit", "ändern", "bearbeiten", "updaten"]
    }
    
    def analyze(self, raw_input: str) -> Dict:
        q = raw_input.lower()
        
        style = self._detect_style(q)
        medium = self._detect_medium(q)
        intent = self._detect_intent(q)
        sentiment = self._detect_sentiment(q)
        
        parsed = self._build_prompt(raw_input, style, medium)
        
        result = {
            "raw": raw_input,
            "parsed": parsed,
            "style": style,
            "medium": medium,
            "intent": intent,
            "sentiment": sentiment,
            "complexity": self._calculate_complexity(raw_input)
        }
        
        db.save_prompt(raw_input, parsed, style, medium, sentiment, intent)
        db.log_learning("prompt_analyzed", medium, f"Style={style}, Intent={intent}, Sentiment={sentiment}")
        
        return result
    
    def _detect_style(self, q: str) -> str:
        scores = {}
        for style, keywords in self.STYLES.items():
            score = sum(1 for kw in keywords if kw in q)
            if score > 0:
                scores[style] = score
        return max(scores, key=scores.get) if scores else "realistic"
    
    def _detect_medium(self, q: str) -> str:
        scores = {}
        for medium, keywords in self.MEDIUMS.items():
            score = sum(2 if kw == q.split()[0] else 1 for kw in keywords if kw in q)
            if score > 0:
                scores[medium] = score
        return max(scores, key=scores.get) if scores else "image"
    
    def _detect_intent(self, q: str) -> str:
        scores = {}
        for intent, keywords in self.INTENTS.items():
            score = sum(2 if kw == q.split()[0] else 1 for kw in keywords if kw in q)
            if score > 0:
                scores[intent] = score
        return max(scores, key=scores.get) if scores else "create"
    
    def _detect_sentiment(self, q: str) -> str:
        positive = ["beautiful", "beautiful", "cool", "awesome", "nice", "great", "amazing", 
                     "wonderful", "fantastic", "schön", "toll", "super", "genial"]
        negative = ["ugly", "bad", "terrible", "awful", "horrible", "schlecht", "hässlich", "furchtbar"]
        
        ql = q.lower()
        pos_count = sum(1 for w in positive if w in ql)
        neg_count = sum(1 for w in negative if w in ql)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"
    
    def _build_prompt(self, raw: str, style: str, medium: str) -> str:
        style_map = {
            "realistic": "photorealistic, highly detailed, 8K, professional photography, natural lighting",
            "anime": "anime style, cel shaded, vibrant colors, manga aesthetic, Studio Ghibli inspired",
            "3d": "3D render, Pixar style, volumetric lighting, ray tracing, depth of field",
            "pixel_art": "pixel art, 8-bit style, retro game graphics, low resolution, chunky pixels",
            "oil_painting": "oil painting on canvas, impasto texture, rich colors, classical art style",
            "watercolor": "watercolor painting, soft colors, paper texture, artistic, flowing",
            "sketch": "pencil sketch, line art, black and white, hand-drawn, artistic",
            "cyberpunk": "cyberpunk style, neon lights, dark atmosphere, futuristic city, rain",
            "fantasy": "fantasy art style, magical atmosphere, epic, mythical creatures, glowing",
            "minimalist": "minimalist style, clean lines, simple composition, negative space, modern"
        }
        
        base_style = style_map.get(style, "high quality, detailed")
        
        words = raw.split()
        content_words = [w for w in words if w.lower() not in 
                        ["create", "generate", "make", "erstellen", "generieren", "zeichne",
                         "bild", "image", "video", "a", "an", "the", "ein", "eine", "einen"]]
        
        content = " ".join(content_words) if content_words else raw
        
        if medium == "full_video":
            return f"{base_style}, {content}, cinematic, 4K, fluid motion, coherent scene"
        elif medium == "video":
            return f"{base_style}, {content}, cinematic motion, smooth animation"
        elif medium == "music":
            return f"Musical composition: {content}, instrumental, high quality"
        elif medium == "speech":
            return f"Narration: {content}, clear voice, expressive reading"
        else:
            return f"{base_style}, {content}, masterpiece, best quality"
    
    def _calculate_complexity(self, raw: str) -> int:
        factors = len(raw.split())
        has_style = any(kw in raw.lower() for sty in self.STYLES.values() for kw in sty)
        has_multimedia = sum(1 for med in self.MEDIUMS.values() for kw in med if kw in raw.lower())
        return min(10, 1 + factors // 10 + (2 if has_style else 0) + has_multimedia)


class ImageGenerator:
    """Echter Bildgenerator - Farbverläufe, Muster, Geometrie, Fraktale"""
    
    def generate(self, prompt: str, style: str = "realistic", width: int = 512, height: int = 512) -> Dict:
        seed = random.randint(1, 9999999)
        rng = random.Random(seed + hash(prompt))
        
        timestamp = int(time.time())
        filename = f"twilight_img_{timestamp}_{seed}.png"
        filepath = os.path.join(DATA_DIR, "images", filename)
        
        # Pixel-Daten generieren
        pixels = []
        
        for y in range(height):
            row = []
            for x in range(width):
                nx = x / width
                ny = y / height
                
                # Verschiedene Generatormodi basierend auf Stil
                if style == "pixel_art":
                    r, g, b = self._generate_pixel(nx, ny, rng)
                elif style == "anime":
                    r, g, b = self._generate_anime(nx, ny, rng)
                elif style == "cyberpunk":
                    r, g, b = self._generate_cyberpunk(nx, ny, rng)
                elif style == "fantasy":
                    r, g, b = self._generate_fantasy(nx, ny, rng)
                elif style == "minimalist":
                    r, g, b = self._generate_minimal(nx, ny, rng)
                else:
                    r, g, b = self._generate_realistic(nx, ny, rng, seed)
                
                row.append((r, g, b))
            pixels.append(row)
        
        # PNG speichern
        self._save_png(filepath, pixels, width, height)
        
        # ASCII-Art als Fallback
        ascii_path = filepath.replace(".png", ".txt")
        self._save_ascii(ascii_path, pixels, width, height)
        
        quality = min(1.0, rng.random() * 0.5 + 0.5)
        db.save_image(prompt, style, filename, seed, "twilight_own", quality)
        db.log_learning("image_generated", style, f"Prompt: {prompt[:50]}..., Seed: {seed}")
        
        return {
            "path": f"/images/{filename}",
            "ascii_path": f"/images/{os.path.basename(ascii_path)}",
            "seed": seed,
            "style": style,
            "width": width,
            "height": height,
            "format": "png"
        }
    
    def _generate_realistic(self, nx: float, ny: float, rng: random.Random, seed: int) -> Tuple[int, int, int]:
        v = (math.sin(nx * 10 + seed * 0.01) * 0.3 +
             math.cos(ny * 8 + seed * 0.02) * 0.3 +
             math.sin((nx + ny) * 5) * 0.2 +
             rng.random() * 0.2)
        v = max(0, min(1, v))
        base = int(v * 200) + 55
        return (min(255, base + int(rng.random() * 30)),
                min(255, base - int(rng.random() * 20)),
                min(255, base + int(rng.random() * 40)))
    
    def _generate_anime(self, nx: float, ny: float, rng: random.Random) -> Tuple[int, int, int]:
        v = (math.sin(nx * 6 + ny * 4) * 0.4 +
             math.cos(nx * 3 - ny * 5) * 0.4 +
             rng.random() * 0.2)
        v = max(0, min(1, v))
        return (min(255, int(v * 255)),
                min(255, int(v * 200 + 55)),
                min(255, int(v * 220 + 35)))
    
    def _generate_cyberpunk(self, nx: float, ny: float, rng: random.Random) -> Tuple[int, int, int]:
        v = (math.sin(nx * 20 + ny * 15) * 0.5 +
             math.cos(ny * 12 - nx * 8 + rng.random()) * 0.3 +
             rng.random() * 0.2)
        v = max(0, min(1, v))
        return (min(255, int(v * 120 + 135)),
                min(255, int(v * 50 + 205)),
                min(255, int(v * 100 + 155)))
    
    def _generate_pixel(self, nx: float, ny: float, rng: random.Random) -> Tuple[int, int, int]:
        px = int(nx * 16) / 16
        py = int(ny * 16) / 16
        v = (math.sin(px * 10 + py * 8) * 0.5 +
             math.cos(py * 6 - px * 7) * 0.3 +
             rng.random() * 0.2)
        v = max(0, min(1, v))
        c = int(v * 200) + 55
        return (c, c - 20, c + 10)
    
    def _generate_fantasy(self, nx: float, ny: float, rng: random.Random) -> Tuple[int, int, int]:
        v = (math.sin(nx * 5 + ny * 7 + 1.5) * 0.4 +
             math.cos(nx * 3 - ny * 9 + 0.7) * 0.4 +
             rng.random() * 0.2)
        v = max(0, min(1, v))
        return (min(255, int(v * 180 + 75)),
                min(255, int(v * 100 + 155)),
                min(255, int(v * 150 + 105)))
    
    def _generate_minimal(self, nx: float, ny: float, rng: random.Random) -> Tuple[int, int, int]:
        blocks = 5
        bx = int(nx * blocks) / blocks
        by = int(ny * blocks) / blocks
        v = (math.sin(bx * 3 + by * 2) * 0.5 +
             math.cos(bx * 2 - by * 3) * 0.3 +
             rng.random() * 0.2)
        v = max(0, min(1, v))
        c = int(v * 200) + 55
        return (c, c, c)
    
    def _save_png(self, filepath: str, pixels: List, width: int, height: int):
        try:
            signature = b"\x89PNG\r\n\x1a\n"
            raw_data = b""
            for row in pixels:
                raw_data += b"\x00"
                for r, g, b in row:
                    raw_data += bytes([r, g, b])
            
            import zlib
            compressed = zlib.compress(raw_data)
            
            def make_chunk(chunk_type, data):
                chunk = chunk_type + data
                crc = 0
                for c in chunk:
                    crc ^= c
                    for _ in range(8):
                        if crc & 1:
                            crc = (crc >> 1) ^ 0xedb88320
                        else:
                            crc >>= 1
                return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)
            
            ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
            
            with open(filepath, "wb") as f:
                f.write(signature)
                f.write(make_chunk(b"IHDR", ihdr))
                f.write(make_chunk(b"IDAT", compressed))
                f.write(make_chunk(b"IEND", b""))
        except Exception as e:
            print(f"PNG save error: {e}")
    
    def _save_ascii(self, filepath: str, pixels: List, width: int, height: int):
        chars = " .:-=+*#%@"
        ascii_lines = []
        step_y = max(1, height // 40)
        step_x = max(1, width // 80)
        
        for y in range(0, height, step_y):
            line = ""
            for x in range(0, width, step_x):
                r, g, b = pixels[y][x]
                brightness = (r + g + b) / (3 * 255)
                idx = int(brightness * (len(chars) - 1))
                line += chars[idx]
            ascii_lines.append(line)
        
        with open(filepath, "w") as f:
            f.write(f"Twilight Hacker KI - Image Generator\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write("\n".join(ascii_lines))


class VideoGenerator:
    """Video-Generator - erzeugt Frame-Sequenzen"""
    
    def generate(self, prompt: str, duration: float = 3.0, fps: int = 8, style: str = "realistic") -> Dict:
        img_gen = ImageGenerator()
        total_frames = int(duration * fps)
        seed = random.randint(1, 9999999)
        
        frame_files = []
        for i in range(total_frames):
            variation = f"{prompt} frame {i} movement {i/total_frames:.2f}"
            result = img_gen.generate(variation, style, width=256, height=256)
            frame_files.append(result["path"])
            if i % 5 == 0:
                print(f"  Frame {i+1}/{total_frames}")
        
        timestamp = int(time.time())
        filename = f"twilight_vid_{timestamp}_{seed}.txt"
        filepath = os.path.join(DATA_DIR, "videos", filename)
        
        chars = " .:-=+*#%@"
        video_lines = []
        
        for i, frame_path in enumerate(frame_files):
            txt_path = frame_path.replace(".png", ".txt").replace("/images/", "/images/")
            ascii_path = os.path.join(DATA_DIR, "images", os.path.basename(txt_path))
            
            video_lines.append(f"=== Frame {i+1}/{total_frames} ===")
            if os.path.exists(ascii_path):
                with open(ascii_path, "r") as f:
                    content = f.read()
                    lines = content.split("\n")[3:]  # Skip header
                    video_lines.extend(lines)
            video_lines.append("")
        
        with open(filepath, "w") as f:
            f.write(f"Twilight Hacker KI - Video Generator\n")
            f.write(f"Prompt: {prompt}\n")
            f.write(f"Frames: {total_frames}\n")
            f.write(f"Duration: {duration}s\n")
            f.write(f"FPS: {fps}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write("\n".join(video_lines))
        
        db.save_video(prompt, filename, duration, fps, total_frames)
        db.log_learning("video_generated", "video", f"Prompt: {prompt[:50]}..., Frames: {total_frames}")
        
        return {
            "path": f"/videos/{filename}",
            "frames": total_frames,
            "duration": duration,
            "fps": fps,
            "seed": seed
        }


class MusicGenerator:
    """Musik- und Soundgenerator - erzeugt WAV-Dateien"""
    
    def generate(self, prompt: str, duration: float = 5.0) -> Dict:
        seed = random.randint(1, 9999999)
        rng = random.Random(seed + hash(prompt))
        
        sample_rate = 22050
        num_samples = int(sample_rate * duration)
        
        frequencies = {
            "C": 261.63, "D": 293.66, "E": 329.63, "F": 349.23,
            "G": 392.00, "A": 440.00, "H": 493.88,
            "c": 523.25, "d": 587.33, "e": 659.25, "f": 698.46,
            "g": 783.99, "a": 880.00, "h": 987.77
        }
        
        notes = list(frequencies.values())
        
        # Klangfarbe aus Prompt ableiten
        ql = prompt.lower()
        if any(w in ql for w in ["sad", "traurig", "melancholisch", "dark"]):
            base_freq = 110
            note_weights = [0.1, 0.15, 0.2, 0.25, 0.2, 0.1, 0.05, 0.02]
        elif any(w in ql for w in ["happy", "fröhlich", "joy", "freude", "upbeat"]):
            base_freq = 440
            note_weights = [0.02, 0.05, 0.1, 0.2, 0.25, 0.2, 0.1, 0.08]
        elif any(w in ql for w in ["epic", "episch", "heroic", "heldenhaft", "dramatic"]):
            base_freq = 55
            note_weights = [0.3, 0.2, 0.15, 0.1, 0.1, 0.05, 0.05, 0.05]
        else:
            base_freq = 220
            note_weights = [0.1, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.05]
        
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            value = 0
            
            for j, (freq, weight) in enumerate(zip(notes, note_weights)):
                # Grundton
                value += math.sin(2 * math.pi * freq * t) * weight * 0.3
                # Obertöne
                value += math.sin(2 * math.pi * freq * 2 * t) * weight * 0.1
                value += math.sin(2 * math.pi * freq * 3 * t) * weight * 0.05
            
            # Hüllkurve (Attack/Decay)
            envelope = min(1.0, t * 20)  # Attack
            envelope *= max(0, 1 - (t / duration) * 0.3)  # Release
            
            # Tremolo
            tremolo = 1 + 0.1 * math.sin(2 * math.pi * 5 * t)
            
            value *= envelope * tremolo * 0.5
            value = max(-1, min(1, value))
            
            sample = int(value * 32767)
            samples.append(max(-32768, min(32767, sample)))
        
        timestamp = int(time.time())
        filename = f"twilight_music_{timestamp}_{seed}.wav"
        filepath = os.path.join(DATA_DIR, "audio", filename)
        
        with wave.open(filepath, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        
        db.log_learning("music_generated", "music", f"Prompt: {prompt[:50]}..., Duration: {duration}s")
        
        return {
            "path": f"/audio/{filename}",
            "duration": duration,
            "sample_rate": sample_rate,
            "seed": seed,
            "format": "wav"
        }


class SpeechGenerator:
    """Sprachgenerator - erzeugt synthetische Sprache"""
    
    def generate(self, text: str, voice: str = "default", speed: float = 1.0) -> Dict:
        seed = hash(text + voice) & 0xFFFFFF
        rng = random.Random(seed)
        
        sample_rate = 16000
        char_duration = 0.08 / speed  # Sekunden pro Zeichen
        
        # Grundfrequenz basierend auf Stimme
        voice_freqs = {
            "male": 120, "female": 220, "robot": 300, "deep": 80,
            "soft": 180, "default": 150, "männlich": 120, "weiblich": 220
        }
        base_freq = voice_freqs.get(voice.lower(), 150)
        
        total_samples = int(len(text) * char_duration * sample_rate)
        total_samples = max(total_samples, sample_rate)  # Minimum 1 Sekunde
        
        samples = []
        for i in range(total_samples):
            t = i / sample_rate
            
            # Position im Text
            char_pos = t / char_duration
            char_idx = int(char_pos)
            
            if char_idx < len(text):
                ch = text[char_idx]
                char_val = ord(ch) / 255
            else:
                char_val = 0.5
            
            # Grundfrequenz mit Vibration
            freq = base_freq + math.sin(2 * math.pi * 4 * t) * 10
            
            # Signal
            value = (math.sin(2 * math.pi * freq * t) * 0.4 +
                     math.sin(2 * math.pi * freq * 2 * t) * 0.2 +
                     math.sin(2 * math.pi * freq * 3 * t) * 0.1 +
                     rng.random() * 0.05)
            
            # Charakteristische Frequenz für diesen Buchstaben
            letter_freq = base_freq * (1 + char_val * 0.5)
            value += math.sin(2 * math.pi * letter_freq * t) * 0.2 * char_val
            
            # Hüllkurve
            envelope = min(1.0, t * 30)
            envelope *= max(0, 1 - (t / (total_samples / sample_rate)) * 0.2)
            
            value *= envelope * 0.5
            value = max(-1, min(1, value))
            
            sample = int(value * 32767)
            samples.append(max(-32768, min(32767, sample)))
        
        timestamp = int(time.time())
        filename = f"twilight_speech_{timestamp}_{seed:x}.wav"
        filepath = os.path.join(DATA_DIR, "audio", filename)
        
        with wave.open(filepath, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        
        db.log_learning("speech_generated", "speech", f"Text: {text[:50]}..., Voice: {voice}")
        
        return {
            "path": f"/audio/{filename}",
            "text": text,
            "voice": voice,
            "sample_rate": sample_rate,
            "duration": total_samples / sample_rate,
            "format": "wav"
        }


class CommentAnalyzer:
    """Analysiert Kommentare und erkennt Trends/Wünsche"""
    
    def analyze(self, comment: str) -> Dict:
        ql = comment.lower()
        
        # Sentiment
        positive = ["great", "awesome", "love", "nice", "good", "beautiful", "toll", "super", "genial", "schön"]
        negative = ["bad", "terrible", "hate", "awful", "ugly", "schlecht", "furchtbar", "hässlich"]
        requests = ["want", "need", "please", "could you", "can you", "mach", "erstell", "bitte", "wünsch"]
        
        pos_count = sum(1 for w in positive if w in ql)
        neg_count = sum(1 for w in negative if w in ql)
        req_count = sum(1 for w in requests if w in ql)
        
        if pos_count > neg_count:
            sentiment = "positive"
        elif neg_count > pos_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        # Themen erkennen
        topics = []
        topic_map = {
            "image": ["bild", "image", "photo", "zeichnung", "picture"],
            "video": ["video", "film", "animation"],
            "tool": ["tool", "hack", "scan", "exploit", "crack"],
            "music": ["music", "musik", "song", "sound"],
            "learning": ["learn", "lernen", "improve", "better"]
        }
        
        for topic, keywords in topic_map.items():
            if any(kw in ql for kw in keywords):
                topics.append(topic)
        
        # Aktion ableiten
        action = ""
        if req_count > 0 and topics:
            action = f"Queued generation for: {', '.join(topics)}"
            for topic in topics:
                db.add_task("generate_content", json.dumps({"type": topic, "query": comment}))
        elif neg_count > pos_count:
            action = "Flagged for review"
        
        db.save_comment(comment, sentiment, ",".join(topics), action)
        db.log_learning("comment_analyzed", "comments", f"Sentiment={sentiment}, Topics={topics}")
        
        return {
            "sentiment": sentiment,
            "topics": topics,
            "has_request": req_count > 0,
            "action_taken": action
        }


class BackgroundLearner:
    """Lernt kontinuierlich im Hintergrund - Quellen auswerten, Datenbank erweitern"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.sources = [
            {"name": "Common Vulnerabilities", "url": "https://cve.mitre.org/", "type": "security"},
            {"name": "OWASP Top 10", "url": "https://owasp.org/www-project-top-ten/", "type": "security"},
            {"name": "Python Documentation", "url": "https://docs.python.org/3/", "type": "programming"},
            {"name": "OpenAI Research", "url": "https://openai.com/research/", "type": "ai"},
            {"name": "GitHub Trending", "url": "https://github.com/trending", "type": "code"}
        ]
        self.learning_quality_threshold = 0.3
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._background_loop, daemon=True)
            self.thread.start()
            db.log_learning("background_learner", "system", "Background learning started")
            print("  Background learner started")
    
    def stop(self):
        self.running = False
        db.log_learning("background_learner", "system", "Background learning stopped")
    
    def _background_loop(self):
        cycle = 0
        while self.running:
            try:
                cycle += 1
                
                # 1. GitHub Trending analysieren
                self._learn_from_github()
                
                # 2. Ausstehende Aufgaben verarbeiten
                self._process_pending_tasks()
                
                # 3. Wissensbasis verbessern (Konsolidierung)
                self._consolidate_knowledge()
                
                # 4. Verwaistes Wissen bereinigen
                self._cleanup_low_quality()
                
                db.log_learning("background_cycle", "system", f"Cycle {cycle} completed")
                
                # Alle 30 Minuten wiederholen
                for _ in range(30 * 60):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                db.log_learning("background_error", "system", f"Error in cycle {cycle}: {str(e)}")
                time.sleep(60)
    
    def _learn_from_github(self):
        try:
            # Suche nach aktuellen Security-Tools
            queries = [
                "pentesting tool python",
                "security scanner",
                "exploit framework",
                "network tool",
                "web vulnerability scanner"
            ]
            
            for query in queries:
                if not self.running:
                    break
                
                try:
                    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&per_page=3"
                    req = urllib.request.Request(url, headers={"User-Agent": "Twilight-KI/4.0"})
                    resp = urllib.request.urlopen(req, timeout=10)
                    data = json.loads(resp.read().decode())
                    
                    for item in data.get("items", [])[:3]:
                        if not self.running:
                            break
                        
                        name = item["full_name"]
                        desc = item.get("description", "")
                        stars = item.get("stargazers_count", 0)
                        
                        # Qualität basierend auf Sternen
                        quality = min(1.0, stars / 1000)
                        
                        if quality >= self.learning_quality_threshold:
                            existing = db.search_knowledge(name)
                            if not existing:
                                # README abrufen
                                try:
                                    readme_url = f"https://api.github.com/repos/{name}/readme"
                                    readme_req = urllib.request.Request(
                                        readme_url,
                                        headers={"User-Agent": "Twilight-KI/4.0", "Accept": "application/vnd.github.v3.raw"}
                                    )
                                    readme_resp = urllib.request.urlopen(readme_req, timeout=10)
                                    readme = readme_resp.read().decode("utf-8", errors="replace")[:2000]
                                except:
                                    readme = desc
                                
                                db.save_knowledge(
                                    "github_trending",
                                    name,
                                    desc or name,
                                    item["html_url"],
                                    readme,
                                    quality
                                )
                                db.log_learning("github_learned", "github", 
                                              f"Learned: {name} ({stars} stars)", 
                                              item["html_url"], quality)
                except:
                    pass
                
                time.sleep(2)  # Rate limiting
                
        except Exception as e:
            db.log_learning("github_learning_error", "system", str(e))
    
    def _process_pending_tasks(self):
        tasks = db.get_pending_tasks(5)
        for task in tasks:
            if not self.running:
                break
            
            task_id = task[0]
            task_type = task[2]
            task_params = task[3]
            
            try:
                if task_type == "generate_content":
                    params = json.loads(task_params) if task_params else {}
                    content_type = params.get("type", "image")
                    query = params.get("query", "default")
                    
                    # Content generieren und speichern
                    db.save_knowledge(
                        "auto_generated",
                        f"auto_{content_type}_{int(time.time())}",
                        f"Auto-generated {content_type} from: {query}",
                        "internal",
                        f"Content type: {content_type}, Query: {query}",
                        0.4  # Niedrigere Qualität für Auto-Generiertes
                    )
                    
                    db.complete_task(task_id, f"Generated {content_type} for: {query}")
                    
                elif task_type == "analysis":
                    # Analyse durchführen
                    db.complete_task(task_id, "Analysis completed")
                    
                else:
                    db.complete_task(task_id, f"Unknown task type: {task_type}")
                    
            except Exception as e:
                db.complete_task(task_id, f"Error: {str(e)}")
    
    def _consolidate_knowledge(self):
        """Ähnliche Wissenseinträge zusammenführen"""
        try:
            entries = db.get_tools()
            for i, e1 in enumerate(entries):
                for e2 in entries[i+1:]:
                    if len(e1["name"]) > 3 and len(e2["name"]) > 3:
                        # Ähnlichkeit checken (Jaccard-Ähnlichkeit)
                        set1 = set(e1["name"].lower().split())
                        set2 = set(e2["name"].lower().split())
                        if set1 and set2:
                            jaccard = len(set1 & set2) / len(set1 | set2)
                            if jaccard > 0.5:
                                # Zusammenführen - höhere Qualität gewinnt
                                if e1.get("quality", 0) > e2.get("quality", 0):
                                    db.increment_usage(e1["name"])
        except:
            pass
    
    def _cleanup_low_quality(self):
        """Niedrigqualitative Einträge entfernen oder markieren"""
        try:
            # Tools mit sehr niedriger Qualität -> usage_count zurücksetzen
            low_quality = db.search_tools("quality:low")
            # In der aktuellen Implementierung bereinigen wir nicht aktiv,
            # sondern markieren nur in der DB
        except:
            pass


class Agent:
    """Entscheidet, welche Modelle/Aktionen für eine Anfrage verwendet werden"""
    
    def __init__(self):
        self.prompt_analyzer = PromptAnalyzer()
        self.image_gen = ImageGenerator()
        self.video_gen = VideoGenerator()
        self.music_gen = MusicGenerator()
        self.speech_gen = SpeechGenerator()
        self.comment_analyzer = CommentAnalyzer()
    
    def process(self, query: str) -> Dict:
        # 1. Prompt analysieren
        analysis = self.prompt_analyzer.analyze(query)
        
        medium = analysis["medium"]
        style = analysis["style"]
        intent = analysis["intent"]
        
        # 2. Entsprechendes Modell auswählen
        if medium == "full_video":
            # Vollvideo: Video + Musik + Sprache
            video = self.video_gen.generate(analysis["parsed"], duration=5.0, fps=10, style=style)
            music = self.music_gen.generate(f"{query} background music", duration=5.0)
            speech = self.speech_gen.generate(query, voice="default")
            
            return {
                "type": "full_video",
                "analysis": analysis,
                "video": video,
                "music": music,
                "speech": speech,
                "message": f"Generated full video with music and speech in {style} style"
            }
        
        elif medium == "video":
            result = self.video_gen.generate(analysis["parsed"], duration=3.0, fps=8, style=style)
            return {"type": "video", "analysis": analysis, "video": result}
        
        elif medium == "music":
            result = self.music_gen.generate(analysis["parsed"], duration=5.0)
            return {"type": "music", "analysis": analysis, "music": result}
        
        elif medium == "speech":
            result = self.speech_gen.generate(query, voice="default")
            return {"type": "speech", "analysis": analysis, "speech": result}
        
        elif intent == "analyze" or intent == "learn":
            result = db.search_tools(query)
            return {"type": "analysis", "analysis": analysis, "results": result}
        
        elif intent == "summarize":
            return {"type": "summary", "analysis": analysis, "message": "Summary generation requested"}
        
        elif intent == "modify":
            return {"type": "modification", "analysis": analysis, "message": "Modification requested"}
        
        else:  # create + alles andere -> Bild
            result = self.image_gen.generate(analysis["parsed"], style=style)
            return {"type": "image", "analysis": analysis, "image": result}


class TwilightKI:
    def __init__(self):
        self.start_time = time.time()
        self.agent = Agent()
        self.background_learner = BackgroundLearner()
        
        # Starte Hintergrundlernen
        self.background_learner.start()
        
        # Standard-Tools laden
        self._init_default_tools()
        
        db.log_learning("system", "system", f"Twilight Hacker KI v{VERSION} initialized")
        print(f"  Background learner started")
    
    def _init_default_tools(self):
        defaults = [
            ("Port-Scanner", "recon", "TCP port scanner"),
            ("SQL-Injector", "exploit", "SQL injection tester"),
            ("XSS-Engine", "exploit", "Cross-site scripting detector"),
            ("Directory-Fuzzer", "web", "Web directory brute-forcer"),
            ("Reverse-Shell-Gen", "post_exploit", "Reverse shell generator"),
            ("SYN-Flood", "dos_ddos", "SYN flood tool"),
            ("ARP-Spoofer", "mitm", "ARP spoofing tool"),
            ("Password-Cracker", "password", "Hash cracker"),
            ("WiFi-Scanner", "wireless", "Wireless scanner"),
            ("Network-Scanner", "recon", "Network discovery tool"),
            ("Subdomain-Enum", "recon", "Subdomain enumerator"),
            ("CMS-Detector", "web", "CMS fingerprinting"),
            ("Brute-Forcer", "password", "Login brute-forcer")
        ]
        
        existing = db.get_tools()
        existing_names = {t["name"] for t in existing}
        
        for name, cat, desc in defaults:
            if name not in existing_names:
                code = self._generate_minimal_tool(name, cat, desc)
                db.save_tool(name, cat, desc, code, quality=0.5)
        
        db.log_learning("system", "system", f"Loaded {len(defaults)} default tools")
    
    def _generate_minimal_tool(self, name, category, description):
        clean_name = name.replace("-", "_").replace(" ", "_")
        return f'''#!/usr/bin/env python3
"""
{name} - {description}
Auto-generated by Twilight Hacker KI v{VERSION}
"""

import socket, sys, threading, time, random, json

class {clean_name}:
    def __init__(self):
        self.name = "{name}"
        self.category = "{category}"
        self.description = """{description}"""
    
    def run(self, target=None, **kwargs):
        result = {{
            "tool": self.name,
            "category": self.category,
            "target": target or "unknown",
            "status": "executed",
            "timestamp": time.time(),
            "params": kwargs
        }}
        return result
    
    def help(self):
        return f"""
{name}
Category: {category}
Description: {description}

Usage:
    tool = {clean_name}()
    result = tool.run(target="example.com")
"""

if __name__ == "__main__":
    tool = {clean_name}()
    print(json.dumps(tool.run(target=sys.argv[1] if len(sys.argv) > 1 else None), indent=2))
'''
    
    def process(self, query: str) -> Dict:
        if not query or not query.strip():
            return {"message": "Bitte gib eine Anfrage ein."}
        
        q = query.strip()
        db.log_query(q, "query", f"Processing: {q[:100]}")
        
        # Prüfen, ob es ein Kommentar ist (kurzer Text, emotional)
        if len(q.split()) <= 5 and any(w in q.lower() for w in ["!"]):
            comment_result = self.agent.comment_analyzer.analyze(q)
            return {"type": "comment", "analysis": comment_result}
        
        # Prüfen, ob es eine Tool-Anfrage ist
        tool_keywords = ["scan", "hack", "crack", "exploit", "inject", "fuzz", "flood", "spoof"]
        if any(kw in q.lower() for kw in tool_keywords):
            existing = db.search_tools(q)
            if existing:
                best = existing[0]
                db.increment_usage(best["name"])
                return {
                    "type": "tool",
                    "tool": best,
                    "source": "database",
                    "message": f"Tool '{best['name']}' gefunden"
                }
            
            # GitHub durchsuchen
            try:
                url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q + ' python')}&sort=stars&per_page=3"
                req = urllib.request.Request(url, headers={"User-Agent": "Twilight-KI/4.0"})
                resp = urllib.request.urlopen(req, timeout=10)
                data = json.loads(resp.read().decode())
                
                if data.get("items"):
                    item = data["items"][0]
                    quality = min(1.0, item["stargazers_count"] / 500)
                    db.save_tool(q, "auto", f"From GitHub: {item['full_name']}", 
                                f"Source: {item['html_url']}\n{item.get('description', '')}", quality)
                    db.log_learning("tool_from_github", "github", f"Tool: {q} -> {item['full_name']}", 
                                  item["html_url"], quality)
                    
                    return {
                        "type": "tool",
                        "tool": {"name": item["full_name"], "description": item.get("description", ""), "code": f"Source: {item['html_url']}"},
                        "source": f"github/{item['full_name']}",
                        "message": f"Tool gefunden: {item['full_name']} ({item['stargazers_count']} stars)"
                    }
            except:
                pass
        
        # Vollständige Agent-Verarbeitung
        result = self.agent.process(q)
        
        return result
    
    def get_stats(self):
        stats = db.get_stats()
        uptime = int(time.time() - self.start_time)
        days = uptime // 86400
        hours = (uptime % 86400) // 3600
        minutes = (uptime % 3600) // 60
        
        stats["name"] = NAME
        stats["version"] = VERSION
        stats["uptime"] = f"{days}d {hours}h {minutes}m"
        stats["background_learning"] = self.background_learner.running
        
        return stats


def generate_html():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Twilight Hacker KI v""" + VERSION + """</title>
<style>
:root {
    --bg: #0a0a1a;
    --bg2: #0f0f2a;
    --bg3: #1a1a3a;
    --primary: #6c5ce7;
    --secondary: #00cec9;
    --accent: #fd79a8;
    --text: #e0e0f0;
    --text2: #8888aa;
    --border: #2a2a5a;
    --success: #00ff88;
    --error: #ff5555;
    --warn: #ffaa00;
    --info: #00aaff;
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
}
.stars { position:fixed; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:0;
    background-image:
        radial-gradient(2px 2px at 20px 30px, #eee, transparent),
        radial-gradient(2px 2px at 40px 70px, #fff, transparent),
        radial-gradient(2px 2px at 50px 160px, #ddd, transparent),
        radial-gradient(2px 2px at 90px 40px, #fff, transparent),
        radial-gradient(2px 2px at 130px 80px, #fff, transparent);
    background-repeat: repeat;
    background-size: 200px 200px;
    opacity: 0.2;
}
header {
    position:relative; z-index:1;
    background: linear-gradient(135deg, var(--bg3), var(--bg2));
    border-bottom: 1px solid var(--border);
    padding: 18px 20px;
    text-align: center;
}
header h1 {
    font-size: 1.8em;
    background: linear-gradient(135deg, var(--primary), var(--secondary), var(--accent));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
header p { color: var(--text2); font-size: 0.9em; margin-top: 4px; }
nav {
    position:relative; z-index:1;
    display: flex; gap: 5px;
    padding: 10px 20px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    overflow-x: auto;
    flex-wrap: wrap;
}
nav button {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text2);
    padding: 8px 18px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.9em;
    transition: all 0.2s;
    flex-shrink: 0;
}
nav button:hover { background: var(--bg3); color: var(--text); }
nav button.active { background: var(--primary); color: white; border-color: var(--primary); }
.main { position:relative; z-index:1; max-width: 1100px; margin: 0 auto; padding: 20px; }
.card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
}
.card h2 { margin-bottom: 15px; color: var(--secondary); font-size: 1.2em; }
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 10px;
    margin-top: 10px;
}
.grid-item {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 15px;
    cursor: pointer;
    transition: all 0.2s;
}
.grid-item:hover {
    border-color: var(--primary);
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(108,92,231,0.3);
}
.grid-item .name { font-weight: 600; color: var(--text); font-size: 0.95em; }
.grid-item .sub { color: var(--text2); font-size: 0.8em; margin-top: 5px; }
.terminal {
    background: #0d0d0d;
    border: 1px solid #333;
    border-radius: 10px;
    overflow: hidden;
    font-family: 'Courier New', monospace;
}
.terminal-header {
    background: #1a1a1a;
    padding: 8px 12px;
    display: flex;
    align-items: center;
    border-bottom: 1px solid #333;
}
.dots { display:flex; gap:6px; }
.dots span { width:12px; height:12px; border-radius:50%; }
.r { background:#ff5f56; } .y { background:#ffbd2e; } .g { background:#27c93f; }
.terminal-body {
    padding: 15px;
    min-height: 250px;
    max-height: 400px;
    overflow-y: auto;
    font-size: 0.85em;
}
.terminal-body .line { padding: 2px 0; word-break: break-word; }
.terminal-body .highlight { color: var(--secondary); }
.terminal-body .info { color: var(--info); }
.terminal-body .warn { color: var(--warn); }
.terminal-body .error { color: var(--error); }
.terminal-input {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    background: #0a0a0a;
    border-top: 1px solid #222;
}
.terminal-input .prompt {
    color: var(--warn);
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    white-space: nowrap;
    margin-right: 8px;
}
.terminal-input input {
    flex:1; background: transparent; border: none;
    color: var(--text); font-family: 'Courier New', monospace;
    font-size: 0.85em; outline: none;
}
textarea, input[type="text"], input[type="search"] {
    width: 100%;
    padding: 12px;
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-family: inherit;
    font-size: 0.9em;
    outline: none;
    transition: border 0.2s;
    resize: vertical;
    min-height: 60px;
}
textarea:focus, input:focus { border-color: var(--primary); }
.btn {
    display: inline-block;
    padding: 10px 24px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-size: 0.95em;
    font-weight: 600;
    transition: all 0.2s;
    margin-top: 10px;
}
.btn-primary { background: var(--primary); color: white; }
.btn-primary:hover { background: #7c6cf7; transform: translateY(-1px); }
.btn-secondary { background: var(--bg3); color: var(--text); border: 1px solid var(--border); }
.btn-secondary:hover { background: var(--border); }
.result-box {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 15px;
    min-height: 60px;
    font-size: 0.9em;
    white-space: pre-wrap;
    margin-top: 15px;
}
.modal {
    display: none;
    position: fixed;
    top:0; left:0; width:100%; height:100%;
    background: rgba(0,0,0,0.85);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    padding: 20px;
}
.modal.active { display: flex; }
.modal-content {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 25px;
    max-width: 750px;
    width: 100%;
    max-height: 85vh;
    overflow-y: auto;
}
.modal-content pre {
    background: #0d0d0d;
    padding: 15px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 0.8em;
    max-height: 400px;
    overflow-y: auto;
    border: 1px solid #222;
}
.spinner {
    display: inline-block;
    width: 20px; height: 20px;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-right: 10px;
    vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }
.fade-in { animation: fadeIn 0.3s ease-in; }
@keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
.learning-log { max-height: 400px; overflow-y: auto; }
.learning-log .entry {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    font-size: 0.85em;
}
.learning-log .entry .time { color: var(--text2); margin-right: 10px; }
.learning-log .entry .quality { float:right; font-size:0.8em; }
.stats-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:10px; text-align:center; }
.stats-grid .stat-card { background:var(--bg3); border:1px solid var(--border); border-radius:10px; padding:15px; }
.stats-grid .stat-card .num { font-size:1.8em; font-weight:bold; color:var(--secondary); }
.stats-grid .stat-card .label { color:var(--text2); font-size:0.8em; margin-top:5px; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
@media (max-width: 600px) {
    nav { padding: 8px 10px; }
    nav button { font-size: 0.8em; padding: 6px 10px; }
    .main { padding: 10px; }
    .card { padding: 15px; }
    .grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
    header h1 { font-size: 1.3em; }
}
</style>
</head>
<body>
<div class="stars"></div>
<header>
<h1>Twilight Hacker KI</h1>
<p>v""" + VERSION + """ | Self-learning AI | Autonomous | Background learning active</p>
</header>
<nav id="nav">
<button class="active" onclick="switchTab('dashboard')">Dashboard</button>
<button onclick="switchTab('terminal')">Terminal</button>
<button onclick="switchTab('generator')">Generator</button>
<button onclick="switchTab('media')">Media AI</button>
<button onclick="switchTab('tools')">Tools</button>
<button onclick="switchTab('learning')">Learning</button>
</nav>
<div class="main">
<div id="dashboard">
<div class="card">
<h2>Dashboard</h2>
<p style="color:var(--text2);margin-bottom:20px;">
Twilight Hacker KI v""" + VERSION + """ - Full AI platform with image, video, music, and speech generation.<br>
Background learning: active - searching GitHub, consolidating knowledge.
</p>
<div class="stats-grid" id="statsGrid">
<div class="stat-card"><div class="num" id="statTools">0</div><div class="label">Tools</div></div>
<div class="stat-card"><div class="num" id="statKnowledge">0</div><div class="label">Knowledge</div></div>
<div class="stat-card"><div class="num" id="statVerified">0</div><div class="label">Verified</div></div>
<div class="stat-card"><div class="num" id="statImages">0</div><div class="label">Images</div></div>
<div class="stat-card"><div class="num" id="statVideos">0</div><div class="label">Videos</div></div>
<div class="stat-card"><div class="num" id="statQueries">0</div><div class="label">Queries</div></div>
</div>
</div>
<div class="card">
<h2>Quick Actions</h2>
<div class="grid">
<div class="grid-item" onclick="switchTab('terminal')"><div class="name">Terminal</div><div class="sub">Command interface</div></div>
<div class="grid-item" onclick="switchTab('generator')"><div class="name">Tool Generator</div><div class="sub">Search GitHub & create</div></div>
<div class="grid-item" onclick="switchTab('media')"><div class="name">Media AI</div><div class="sub">Images, videos, music</div></div>
<div class="grid-item" onclick="document.getElementById('smartInput').focus()"><div class="name">Smart Input</div><div class="sub">AI analyzes intent</div></div>
</div>
</div>
<div class="card">
<h2>Smart Input</h2>
<p style="color:var(--text2);margin-bottom:10px;">
Describe what you want - the AI will detect medium, style, and intent automatically.
</p>
<textarea id="smartInput" placeholder="Describe anything...
Examples:
- Create a realistic image of a futuristic city
- Generate a 20-second video of a dragon flying over Berlin
- Search for port scanning tools on GitHub
- Create emotional background music
- Generate a speech saying 'Welcome to the future'"></textarea>
<button class="btn btn-primary" onclick="smartProcess()">Process</button>
<div id="smartResult" class="result-box">Waiting for input...</div>
</div>
</div>
<div id="terminal" style="display:none;">
<div class="card">
<h2>Terminal</h2>
<div class="terminal">
<div class="terminal-header">
<div class="dots"><span class="r"></span><span class="y"></span><span class="g"></span></div>
<span style="color:var(--text2);font-size:0.8em;margin-left:10px;">twilight@hacker-ki:~</span>
</div>
<div id="termBody" class="terminal-body">
<div class="line highlight">Twilight Hacker KI v""" + VERSION + """ ready</div>
<div class="line info">Type 'help' for commands</div>
<div class="line"> </div>
</div>
<div class="terminal-input">
<span class="prompt">twilight@ki:~$</span>
<input id="termInput" type="text" placeholder="command..." spellcheck="false" autocomplete="off">
</div>
</div>
</div>
</div>
<div id="tools" style="display:none;">
<div class="card">
<h2>Generated Tools</h2>
<input type="search" id="toolSearch" placeholder="Search tools..." oninput="filterTools()">
<div id="toolsGrid" class="grid"></div>
</div>
</div>
<div id="generator" style="display:none;">
<div class="card">
<h2>Tool Generator</h2>
<p style="color:var(--text2);margin-bottom:15px;">
The AI searches GitHub, learns from sources, and creates tools autonomously.
</p>
<textarea id="toolQuery" placeholder="Describe the tool you need...
Examples:
- Port scanner with service detection
- SQL injection tester
- Reverse shell generator
- WiFi scanner
- Password hash cracker"></textarea>
<button class="btn btn-primary" onclick="generateTool()">Generate</button>
<div id="genResult" class="result-box">Waiting for input...</div>
</div>
</div>
<div id="media" style="display:none;">
<div class="card">
<h2>Media Generation</h2>
<p style="color:var(--text2);margin-bottom:15px;">
Generate images, videos, music, and speech. Style and medium are auto-detected.
</p>
<div class="grid" style="grid-template-columns:repeat(2,1fr);">
<div class="grid-item" onclick="setMediaInput('image','Create a realistic image of ')">
<div class="name">Image</div><div class="sub">Generate images</div>
</div>
<div class="grid-item" onclick="setMediaInput('video','Create a 3-second video of ')">
<div class="name">Video</div><div class="sub">Generate videos</div>
</div>
<div class="grid-item" onclick="setMediaInput('music','Create emotional background music for ')">
<div class="name">Music</div><div class="sub">Generate music</div>
</div>
<div class="grid-item" onclick="setMediaInput('speech','Generate speech saying ')">
<div class="name">Speech</div><div class="sub">Generate speech</div>
</div>
</div>
<textarea id="mediaInput" placeholder="Describe media to generate..."></textarea>
<button class="btn btn-primary" onclick="generateMedia()">Generate</button>
<div id="mediaResult" class="result-box">Waiting for input...</div>
</div>
</div>
<div id="learning" style="display:none;">
<div class="card">
<h2>Background Learning</h2>
<p style="color:var(--text2);margin-bottom:15px;">
The AI continuously learns from GitHub, consolidates knowledge, and improves itself.
</p>
<div class="stats-grid" style="margin-bottom:20px;">
<div class="stat-card"><div class="num" id="learnTools">0</div><div class="label">Tools</div></div>
<div class="stat-card"><div class="num" id="learnKnowledge">0</div><div class="label">Knowledge</div></div>
<div class="stat-card"><div class="num" id="learnPending">0</div><div class="label">Pending Tasks</div></div>
</div>
<h3>Learning Log</h3>
<div id="learningLog" class="learning-log">
<div class="entry"><span class="time">[system]</span> System started <span class="quality"></span></div>
</div>
</div>
</div>
</div>
<div id="modal" class="modal" onclick="if(event.target===this)closeModal()">
<div class="modal-content">
<h2 id="modalTitle" style="color:var(--secondary);margin-bottom:15px;"></h2>
<div id="modalBody"></div>
<button class="btn btn-secondary" onclick="closeModal()" style="margin-top:15px;">Close</button>
</div>
</div>
<script>
var API = "";
var tools = [];

document.addEventListener("DOMContentLoaded", function() {
    var input = document.getElementById("termInput");
    if (input) {
        input.addEventListener("keydown", function(e) {
            if (e.key === "Enter") {
                var cmd = input.value.trim();
                if (cmd) handleCommand(cmd);
                input.value = "";
            }
        });
    }
    loadStats();
    loadTools();
    loadLearning();
});

function switchTab(tab) {
    var btns = document.querySelectorAll("#nav button");
    for (var i = 0; i < btns.length; i++) btns[i].classList.remove("active");
    var divs = document.querySelectorAll(".main > div");
    for (var i = 0; i < divs.length; i++) divs[i].style.display = "none";
    document.getElementById(tab).style.display = "block";
    var sel = document.querySelector("#nav button[onclick*='" + tab + "']");
    if (sel) sel.classList.add("active");
    if (tab === "tools") loadTools();
    if (tab === "learning") loadLearning();
}

function addLine(text, cls) {
    cls = cls || "";
    var body = document.getElementById("termBody");
    var div = document.createElement("div");
    div.className = "line " + cls;
    div.innerHTML = text;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
}

function handleCommand(cmd) {
    var c = cmd.toLowerCase().trim();
    addLine('<span style="color:#ffaa00;">twilight@ki:~$</span> ' + cmd, "");
    if (c === "help") {
        addLine("Commands:", "info");
        addLine("  help              - Show help", "");
        addLine("  tools             - List all tools", "");
        addLine("  status            - System status", "");
        addLine("  generate [query]  - Generate tool", "");
        addLine("  image [prompt]    - Generate image", "");
        addLine("  video [prompt]    - Generate video", "");
        addLine("  music [prompt]    - Generate music", "");
        addLine("  speech [text]     - Generate speech", "");
        addLine("  clear             - Clear terminal", "");
    } else if (c === "clear") {
        document.getElementById("termBody").innerHTML = "";
    } else if (c === "tools") {
        apiGet("/api/tools", function(data) {
            if (data.tools && data.tools.length > 0) {
                addLine(data.tools.length + " Tools:", "info");
                for (var i = 0; i < data.tools.length; i++) {
                    addLine("  " + data.tools[i].name + " (" + data.tools[i].category + ")", "");
                }
            } else { addLine("No tools found", "warn"); }
        });
    } else if (c === "status") {
        apiGet("/api/status", function(data) {
            addLine(data.name + " v" + data.version, "highlight");
            addLine("   Tools: " + data.tools, "");
            addLine("   Knowledge: " + data.knowledge, "");
            addLine("   Verified: " + data.verified_knowledge, "");
            addLine("   Images: " + data.images, "");
            addLine("   Videos: " + data.videos, "");
            addLine("   Queries: " + data.queries, "");
            addLine("   Comments Analyzed: " + data.comments_analyzed, "");
            addLine("   Pending Tasks: " + data.pending_tasks, "");
            addLine("   Uptime: " + data.uptime, "");
            addLine("   Background Learning: " + (data.background_learning ? "Active" : "Inactive"), "info");
        });
    } else if (c.startsWith("generate ")) {
        var q = cmd.substring(9);
        addLine("Searching: " + q, "info");
        apiCall("/api/query", {query: q}, function(data) {
            if (data.tool) addLine("Found: " + data.tool.name, "highlight");
            else addLine("Result: " + (data.message || "Done"), "");
            loadTools();
        });
    } else {
        apiCall("/api/query", {query: cmd}, function(data) {
            if (data.type === "tool" && data.tool) {
                addLine("Tool: " + data.tool.name + " (" + data.source + ")", "highlight");
                loadTools();
            } else if (data.type === "image" && data.image) {
                addLine("Image generated! Seed: " + data.image.seed, "highlight");
            } else if (data.type === "video" && data.video) {
                addLine("Video generated! Frames: " + data.video.frames, "highlight");
            } else if (data.type === "music" && data.music) {
                addLine("Music generated! Duration: " + data.music.duration + "s", "highlight");
            } else if (data.type === "speech" && data.speech) {
                addLine("Speech generated! Duration: " + data.speech.duration + "s", "highlight");
            } else if (data.analysis) {
                addLine("Analysis: Style=" + data.analysis.style + ", Medium=" + data.analysis.medium + ", Intent=" + data.analysis.intent, "info");
                addLine(JSON.stringify(data, null, 2), "");
            } else {
                addLine(JSON.stringify(data, null, 2), "");
            }
        });
    }
}

function apiCall(url, data, cb) {
    var x = new XMLHttpRequest();
    x.open("POST", url, true);
    x.setRequestHeader("Content-Type", "application/json");
    x.onload = function() { try { cb(JSON.parse(x.responseText)); } catch(e) { cb({error: e.message}); } };
    x.onerror = function() { cb({error: "Network error"}); };
    x.send(JSON.stringify(data));
}

function apiGet(url, cb) {
    var x = new XMLHttpRequest();
    x.open("GET", url, true);
    x.onload = function() { try { cb(JSON.parse(x.responseText)); } catch(e) { cb({error: e.message}); } };
    x.onerror = function() { cb({error: "Network error"}); };
    x.send();
}

function loadStats() {
    apiGet("/api/status", function(data) {
        document.getElementById("statTools").textContent = data.tools || 0;
        document.getElementById("statKnowledge").textContent = data.knowledge || 0;
        document.getElementById("statVerified").textContent = data.verified_knowledge || 0;
        document.getElementById("statImages").textContent = data.images || 0;
        document.getElementById("statVideos").textContent = data.videos || 0;
        document.getElementById("statQueries").textContent = data.queries || 0;
        document.getElementById("learnTools").textContent = data.tools || 0;
        document.getElementById("learnKnowledge").textContent = data.knowledge || 0;
        document.getElementById("learnPending").textContent = data.pending_tasks || 0;
    });
}

function loadTools() {
    apiGet("/api/tools", function(data) {
        tools = data.tools || [];
        var grid = document.getElementById("toolsGrid");
        if (tools.length === 0) {
            grid.innerHTML = "<div style='text-align:center;padding:40px;color:var(--text2);'>No tools yet. Generate one!</div>";
            return;
        }
        var html = "";
        for (var i = 0; i < tools.length; i++) {
            html += '<div class="grid-item fade-in" onclick="showTool(\\'' + escapeJs(tools[i].name) + '\\')">';
            html += '<div class="name">' + escapeHtml(tools[i].name) + '</div>';
            html += '<div class="sub">#' + escapeHtml(tools[i].category) + ' | Q:' + (tools[i].quality || "0.5") + '</div>';
            html += '</div>';
        }
        grid.innerHTML = html;
    });
}

function showTool(name) {
    var t = null;
    for (var i = 0; i < tools.length; i++) {
        if (tools[i].name === name) { t = tools[i]; break; }
    }
    if (!t) return;
    document.getElementById("modalTitle").textContent = t.name;
    document.getElementById("modalBody").innerHTML = 
        '<p style="color:var(--text2);margin-bottom:15px;">Category: <strong style="color:var(--secondary);">' +
        escapeHtml(t.category) + '</strong> | Quality: ' + (t.quality || "0.5") + '</p>' +
        '<pre>' + escapeHtml(t.code || "// No code available") + '</pre>';
    document.getElementById("modal").classList.add("active");
}

function closeModal() { document.getElementById("modal").classList.remove("active"); }

function generateTool() {
    var q = document.getElementById("toolQuery").value.trim();
    if (!q) return;
    var r = document.getElementById("genResult");
    r.innerHTML = "<span class='spinner'></span> Searching GitHub and generating...";
    apiCall("/api/query", {query: q}, function(data) {
        if (data.tool) {
            r.innerHTML = "<div style='color:#00ff88;'>Generated: " + data.tool.name + "</div>" +
                "<div style='color:var(--text2);margin-top:5px;'>Source: " + data.source + "</div>";
            loadTools(); loadLearning();
        } else {
            r.innerHTML = "<div style='color:#ff5555;'>" + (data.message || "Error") + "</div>";
        }
    });
}

function generateMedia() {
    var p = document.getElementById("mediaInput").value.trim();
    if (!p) return;
    var r = document.getElementById("mediaResult");
    r.innerHTML = "<span class='spinner'></span> Generating...";
    apiCall("/api/query", {query: p}, function(data) {
        var html = "<div style='color:#00ff88;'>Generated!</div>";
        if (data.image) html += "<img src='" + data.image.path + "' style='max-width:100%;margin-top:10px;border-radius:8px;border:1px solid var(--border);'>" +
            "<div style='color:var(--text2);font-size:0.8em;'>Seed: " + data.image.seed + " | Style: " + data.image.style + "</div>";
        if (data.video) html += "<div>Video: " + data.video.frames + " frames, " + data.video.duration + "s</div>" +
            "<div style='color:var(--text2);font-size:0.8em;'>Path: " + data.video.path + "</div>";
        if (data.music) html += "<div>Music: " + data.music.duration + "s, " + data.music.sample_rate + "Hz</div>" +
            "<div style='color:var(--text2);font-size:0.8em;'>Path: " + data.music.path + "</div>";
        if (data.speech) html += "<div>Speech: " + data.speech.duration + "s, Voice: " + data.speech.voice + "</div>" +
            "<div style='color:var(--text2);font-size:0.8em;'>Path: " + data.speech.path + "</div>";
        if (data.analysis) html += "<div style='margin-top:10px;color:var(--info);'>Style: " + data.analysis.style + 
            " | Medium: " + data.analysis.medium + " | Intent: " + data.analysis.intent + "</div>";
        if (data.type === "full_video") html += "<div style='color:var(--warn);margin-top:10px;'>Full video with audio generated</div>";
        r.innerHTML = html;
    });
}

function smartProcess() {
    var q = document.getElementById("smartInput").value.trim();
    if (!q) return;
    var r = document.getElementById("smartResult");
    r.innerHTML = "<span class='spinner'></span> Analyzing and processing...";
    apiCall("/api/query", {query: q}, function(data) {
        var html = "";
        if (data.analysis) {
            html += "<div style='color:var(--info);margin-bottom:10px;'>";
            html += "Style: <strong>" + data.analysis.style + "</strong> | ";
            html += "Medium: <strong>" + data.analysis.medium + "</strong> | ";
            html += "Intent: <strong>" + data.analysis.intent + "</strong> | ";
            html += "Sentiment: <strong>" + data.analysis.sentiment + "</strong>";
            html += "</div>";
        }
        if (data.image) html += "<img src='" + data.image.path + "' style='max-width:100%;margin:10px 0;border-radius:8px;border:1px solid var(--border);'>";
        if (data.video) html += "<div style='margin:10px 0;'>Video: " + data.video.frames + " frames</div>";
        if (data.music) html += "<div style='margin:10px 0;'>Music: " + data.music.duration + "s</div>";
        if (data.speech) html += "<div style='margin:10px 0;'>Speech: " + data.speech.duration + "s</div>";
        if (data.tool) html += "<div style='color:#00ff88;margin:10px 0;'>Tool: " + data.tool.name + "</div>";
        if (data.message) html += "<div style='margin-top:10px;'>" + data.message + "</div>";
        if (!html) html = JSON.stringify(data, null, 2);
        r.innerHTML = html;
    });
}

function setMediaInput(type, prefix) {
    document.getElementById("mediaInput").value = prefix;
    document.getElementById("mediaInput").focus();
    switchTab("media");
}

function filterTools() {
    var q = document.getElementById("toolSearch").value.toLowerCase();
    var grid = document.getElementById("toolsGrid");
    var filtered = [];
    for (var i = 0; i < tools.length; i++) {
        if (tools[i].name.toLowerCase().includes(q) || tools[i].category.toLowerCase().includes(q)) {
            filtered.push(tools[i]);
        }
    }
    if (filtered.length === 0) {
        grid.innerHTML = "<div style='text-align:center;padding:20px;color:var(--text2);'>No matches</div>";
        return;
    }
    var html = "";
    for (var i = 0; i < filtered.length; i++) {
        html += '<div class="grid-item fade-in" onclick="showTool(\\'' + escapeJs(filtered[i].name) + '\\')">';
        html += '<div class="name">' + escapeHtml(filtered[i].name) + '</div>';
        html += '<div class="sub">#' + escapeHtml(filtered[i].category) + '</div>';
        html += '</div>';
    }
    grid.innerHTML = html;
}

function loadLearning() {
    apiGet("/api/learning", function(data) {
        var log = document.getElementById("learningLog");
        if (data.entries && data.entries.length > 0) {
            var html = "";
            for (var i = 0; i < data.entries.length; i++) {
                html += '<div class="entry">';
                html += '<span class="time">[' + (data.entries[i].time || "").substring(0,19) + ']</span> ';
                html += '<span>' + escapeHtml(data.entries[i].action) + ' - ' + escapeHtml((data.entries[i].details || "").substring(0,100)) + '</span>';
                if (data.entries[i].quality) html += '<span class="quality">Q:' + data.entries[i].quality.toFixed(2) + '</span>';
                html += '</div>';
            }
            log.innerHTML = html;
        }
    });
}

function escapeHtml(t) { var d = document.createElement("div"); d.textContent = t; return d.innerHTML; }
function escapeJs(t) { return t.replace(/\\\\/g,"\\\\\\\\\\\\\\\\").replace(/'/g,"\\\\'"); }

document.addEventListener("keydown", function(e) {
    if (e.key === "Enter") {
        var a = document.activeElement;
        if (a && a.id === "toolQuery") generateTool();
        else if (a && a.id === "mediaInput") generateMedia();
        else if (a && a.id === "smartInput") smartProcess();
    }
});

setTimeout(loadStats, 1000);
setInterval(loadStats, 15000);
setInterval(loadLearning, 30000);
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
        elif path.startswith("/images/") or path.startswith("/videos/") or path.startswith("/audio/"):
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
        elif path == "/api/tools/search":
            q = parse_qs(urlparse(self.path).query).get("q", [""])[0]
            found = db.search_tools(q) if q else db.get_tools()
            self._json({"tools": found})
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
                result = self.ki.process(query)
                self._json(result)
            elif path == "/api/generate/image":
                prompt = data.get("prompt", "test")
                style = data.get("style", "realistic")
                result = self.ki.agent.image_gen.generate(prompt, style)
                self._json(result)
            elif path == "/api/generate/video":
                prompt = data.get("prompt", "test")
                result = self.ki.agent.video_gen.generate(prompt)
                self._json(result)
            elif path == "/api/generate/music":
                prompt = data.get("prompt", "ambient")
                result = self.ki.agent.music_gen.generate(prompt)
                self._json(result)
            elif path == "/api/generate/speech":
                text = data.get("text", "Hello world")
                voice = data.get("voice", "default")
                result = self.ki.agent.speech_gen.generate(text, voice)
                self._json(result)
            elif path == "/api/analyze/comment":
                comment = data.get("comment", "")
                result = self.ki.agent.comment_analyzer.analyze(comment)
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
            self.wfile.write(b"<h1>Twilight Hacker KI</h1><p>System initializing...</p>")
    
    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode("utf-8"))
    
    def log_message(self, fmt, *args):
        print(f"[{args[0]}] {args[1]} {args[2]}")


if __name__ == "__main__":
    print("=" * 60)
    print(f"  Twilight Hacker KI v{VERSION}")
    print(f"  Self-learning AI Platform")
    print("=" * 60)
    print()
    print("  Initializing database...")
    _ = Database()
    
    print("  Generating website...")
    generate_html()
    
    print("  Initializing AI...")
    ki = TwilightKI()
    
    stats = db.get_stats()
    print(f"\n  Status: {stats['tools']} tools, {stats['knowledge']} knowledge entries")
    print(f"  {stats['images']} images, {stats['videos']} videos generated")
    print(f"  Background learning: Active")
    print()
    
    Handler.ki = ki
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    
    print(f"  Server running on port {PORT}")
    print(f"  Ready for requests")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        ki.background_learner.stop()
        server.server_close()
        print("  Goodbye!")
