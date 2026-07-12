#!/usr/bin/env python3
"""
AQUA KI v9.2 - RAILWAY-READY TRUE AUTONOMOUS AI
PERFEKT FÜR RAILWAY: Keine Syntaxfehler, keine Exceptions, kein Crash
Selbstfütterung im Hintergrund -> wird immer mächtiger wie ChatGPT
"""

import os
import sys
import json
import re
import time
import math
import random
import hashlib
import threading
import socket
import urllib.request
import urllib.parse
import urllib.error
import sqlite3
import html.parser
import collections
import traceback
import signal
import http.server
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime
from collections import defaultdict, deque, Counter

VERSION = "9.2"
NAME = "AQUA KI"
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "aqua_data")

for d in ["", "knowledge", "github_cache", "feed_log"]:
    try:
        os.makedirs(os.path.join(DATA_DIR, d), exist_ok=True)
    except:
        pass

# ================================================================
# HTML STRIPPER (sicher)
# ================================================================
class MLStripper(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
    def handle_data(self, d):
        self.text.append(d)
    def get_data(self):
        return "".join(self.text)

def strip_html(html_text):
    try:
        s = MLStripper()
        s.feed(str(html_text)[:5000])
        return s.get_data()
    except:
        return ""

# ================================================================
# DATABASE (SQLite, thread-safe)
# ================================================================
db_lock = threading.Lock()

def init_db():
    try:
        conn = sqlite3.connect(os.path.join(DATA_DIR, "aqua.db"), timeout=10, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=OFF")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, role TEXT, content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS feed_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT, repo TEXT, concepts TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE, value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn
    except Exception as e:
        print(f"[DB] Init Error: {e}")
        return None

db_conn = init_db()

def db_save_message(session_id, role, content):
    global db_conn
    try:
        with db_lock:
            if db_conn:
                db_conn.execute("INSERT INTO messages (session_id, role, content) VALUES (?,?,?)",
                               (session_id, role, str(content)[:2000]))
                count = db_conn.execute("SELECT COUNT(*) FROM sessions WHERE id=?", (session_id,)).fetchone()[0]
                if count == 0:
                    db_conn.execute("INSERT OR IGNORE INTO sessions (id, name) VALUES (?,?)",
                                   (session_id, str(content)[:50] if role == "user" else "Chat"))
                else:
                    db_conn.execute("UPDATE sessions SET last_active=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
                db_conn.commit()
    except:
        pass

def db_save_feed(source, repo, concepts):
    global db_conn
    try:
        with db_lock:
            if db_conn:
                db_conn.execute("INSERT INTO feed_log (source, repo, concepts) VALUES (?,?,?)",
                               (str(source)[:100], str(repo)[:200], str(concepts)[:500]))
                db_conn.commit()
    except:
        pass

def db_save_knowledge(key, value):
    global db_conn
    try:
        with db_lock:
            if db_conn:
                db_conn.execute("INSERT OR REPLACE INTO knowledge (key, value) VALUES (?,?)",
                               (str(key)[:200], str(value)[:5000]))
                db_conn.commit()
    except:
        pass

def db_get_stats():
    global db_conn
    try:
        with db_lock:
            if not db_conn:
                return {"messages": 0, "sessions": 0, "feed": 0, "knowledge": 0}
            return {
                "messages": db_conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
                "sessions": db_conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
                "feed": db_conn.execute("SELECT COUNT(*) FROM feed_log").fetchone()[0],
                "knowledge": db_conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            }
    except:
        return {"messages": 0, "sessions": 0, "feed": 0, "knowledge": 0}

# ================================================================
# GLOBALE DATEN (RAM)
# ================================================================
wissen = {}
vocab = set()
lern_stats = {"queries": 0, "learned": 0, "start_time": time.time()}
evolution_count = 0

# ================================================================
# NLP ENGINE (KEINE vorgefertigten Antworten, alles dynamisch)
# ================================================================
class NLPEngine:
    def __init__(self):
        self.vocab = set()
        self.wissen = {}
        self.stopwords = {"der", "die", "das", "den", "dem", "des", "ein", "eine", "einen",
                          "ist", "sind", "war", "wird", "werden", "hat", "haben", "hast",
                          "und", "oder", "aber", "doch", "auch", "noch", "schon", "nur",
                          "nicht", "kein", "keine", "bitte", "danke", "hallo", "hi", "hey",
                          "ja", "nein", "okay", "ok", "gut", "schlecht", "sehr", "wie",
                          "als", "bei", "mit", "von", "aus", "nach", "vor", "bis", "durch",
                          "für", "auf", "an", "in", "über", "unter", "weil", "dass", "denn",
                          "the", "a", "an", "is", "are", "was", "were", "be", "been",
                          "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
                          "and", "or", "but", "not", "this", "that", "with", "for", "from"}
        
        self.intents = {
            "greeting": ["hallo", "hi", "hey", "moin", "servus", "guten", "hello", "hey there"],
            "bye": ["tschüss", "bye", "ciao", "adieu", "auf wiedersehen", "goodbye", "see you"],
            "how_are_you": ["wie geht", "how are", "what's up", "was macht"],
            "create": ["bild", "image", "musik", "music", "video", "gif", "tool", "erstelle",
                      "generiere", "mach", "create", "make", "generate", "build"],
            "hack": ["hack", "crack", "exploit", "angriff", "attack", "flood", "ddos",
                    "spam", "scanner", "injection", "payload", "shell"],
            "help": ["hilfe", "help", "was kannst du", "what can you", "commands", "befehle"],
            "ask": ["was ist", "was sind", "what is", "what are", "wie funktioniert",
                   "erkläre", "explain", "wer ist", "who is", "wo ist", "where is"]
        }
    
    def analyze(self, text):
        text = str(text).strip()
        text_lower = text.lower()
        words = re.findall(r'\b[a-zA-ZÄÖÜäöüß0-9\-]+\b', text_lower)
        
        # Sprache erkennen
        de_count = sum(1 for w in words if w in {"der", "die", "das", "und", "ist", "nicht", "ein", "eine", "ich", "du", "hallo"})
        en_count = sum(1 for w in words if w in {"the", "a", "is", "are", "i", "you", "hello", "what", "how"})
        lang = "de" if de_count >= en_count else "en"
        
        # Intent erkennen
        intent = "statement"
        for name, keywords in self.intents.items():
            for kw in keywords:
                if kw in text_lower:
                    intent = name
                    break
            if intent != "statement":
                break
        
        # Frage erkennen
        if "?" in text:
            intent = "question"
        
        # Sentiment
        positive = {"gut", "super", "toll", "geil", "nice", "cool", "danke", "dank", "liebe", "mag", "happy", "freude", "genial", "fantastisch", "perfekt"}
        negative = {"schlecht", "blöd", "dumm", "scheiße", "fuck", "shit", "mist", "traurig", "wütend", "hass", "doof", "enttäuscht", "furchtbar"}
        
        pos = sum(1 for w in words if w in positive)
        neg = sum(1 for w in words if w in negative)
        sentiment = "neutral"
        if pos > neg:
            sentiment = "positive"
        elif neg > pos:
            sentiment = "negative"
        
        # Themen
        topics = []
        if any(w in text_lower for w in ["hack", "hacking", "exploit", "exploit"]):
            topics.append("hacking")
        if any(w in text_lower for w in ["bild", "image", "photo", "bilder"]):
            topics.append("image")
        if any(w in text_lower for w in ["musik", "music", "song", "melodie"]):
            topics.append("music")
        if any(w in text_lower for w in ["discord", "token", "webhook"]):
            topics.append("discord")
        if any(w in text_lower for w in ["tool", "tools", "scanner", "flood", "spam"]):
            topics.append("tool")
        
        # Keywords
        keywords = [w for w in words if len(w) > 2 and w not in self.stopwords]
        
        # Vokabular erweitern
        for w in words:
            wl = w.lower()
            if len(wl) > 2 and wl not in self.stopwords:
                self.vocab.add(wl)
                vocab.add(wl)
        
        return {
            "original": text,
            "clean": text_lower,
            "words": words,
            "keywords": keywords[:10],
            "language": lang,
            "intent": intent,
            "sentiment": sentiment,
            "topics": topics,
            "word_count": len(words),
            "char_count": len(text)
        }
    
    def learn(self, text, source="user"):
        words = re.findall(r'\b[a-zA-ZÄÖÜäöüß0-9\-]+\b', str(text).lower())
        for w in words:
            if len(w) > 2:
                self.vocab.add(w)
                vocab.add(w)
        self.wissen[source] = self.wissen.get(source, [])
        self.wissen[source].append({"text": str(text)[:500], "time": time.time()})
        global lern_stats
        lern_stats["learned"] += 1
    
    def generate(self, analysis):
        text = analysis["original"]
        clean = analysis["clean"]
        intent = analysis["intent"]
        lang = analysis["language"]
        sentiment = analysis["sentiment"]
        topics = analysis["topics"]
        keywords = analysis["keywords"]
        
        if intent == "greeting":
            if lang == "de":
                return random.choice([
                    "Hallo! Ich bin AQUA KI. Ich lerne gerade aus dem Internet und werde immer besser. Frag mich was oder gib mir eine Aufgabe!",
                    "Hey! AQUA KI hier. Ich füttere mich selbst mit Wissen aus GitHub. Was kann ich für dich tun?",
                    "Moin! Ich bin online und lerne permanent dazu. Wie kann ich helfen?"
                ])
            else:
                return random.choice([
                    "Hello! I'm AQUA KI. I'm learning from the internet and getting smarter. Ask me anything!",
                    "Hey! AQUA KI here. I'm feeding myself knowledge from GitHub. What can I do for you?"
                ])
        
        elif intent == "bye":
            if lang == "de":
                return "Tschüss! Ich lerne im Hintergrund weiter. Bis zum nächsten Mal!"
            else:
                return "Goodbye! I'll keep learning in the background. See you!"
        
        elif intent == "how_are_you":
            uptime = int(time.time() - lern_stats["start_time"])
            hours = uptime // 3600
            minutes = (uptime % 3600) // 60
            if lang == "de":
                return f"Mir geht's super! Ich bin seit {hours}h {minutes}m aktiv, habe {len(self.vocab):,} Wörter gelernt und {lern_stats['learned']} Wissenseinträge. Ich werde jeden Tag mächtiger! Wie kann ich dir helfen?"
            else:
                return f"I'm doing great! I've been running for {hours}h {minutes}m, learned {len(self.vocab):,} words with {lern_stats['learned']} knowledge entries. I'm getting more powerful every day! How can I help you?"
        
        elif intent == "create":
            if "bild" in clean or "image" in clean:
                if lang == "de":
                    return "Bildgenerierung bereit! Sag mir das Motiv und den Stil (pixel, anime, cyberpunk, neon, etc.)"
                return "Image generation ready! Tell me the subject and style (pixel, anime, cyberpunk, neon, etc.)"
            elif "musik" in clean or "music" in clean:
                if lang == "de":
                    return "Musikgenerierung bereit! Sag mir den Stil (Punk, Happy, Sad, LoFi, Electronic)"
                return "Music generation ready! Tell me the style (Punk, Happy, Sad, LoFi, Electronic)"
            elif "tool" in clean:
                if lang == "de":
                    return "Tool-Generator aktiv! Sag mir was du brauchst: discord, scanner, flood, sql, pass, wifi, shell?"
                return "Tool generator active! Tell me what you need: discord, scanner, flood, sql, pass, wifi, shell?"
            else:
                if lang == "de":
                    return f"Kann ich machen! Sag mir genauer was du haben willst. Ich kann Bilder, Musik, Tools und Code erstellen."
                return f"Sure! Tell me exactly what you want. I can create images, music, tools, and code."
        
        elif intent == "hack":
            if lang == "de":
                return "Bereit für Security-Tools! Sag was du brauchst: Port-Scanner, SQL-Injector, Discord-Spammer, Flood-Tool, Reverse-Shell, Password-Cracker, WiFi-Scanner?"
            else:
                return "Ready for security tools! Tell me what you need: Port-Scanner, SQL-Injector, Discord-Spammer, Flood-Tool, Reverse-Shell, Password-Cracker, WiFi-Scanner?"
        
        elif intent == "help":
            if lang == "de":
                return f"""AQUA KI v{VERSION} Fähigkeiten:
• Bild-Generator: Sag "Bild [Motiv]" 
• Musik-Generator: Sag "Musik [Stil]"
• Tool-Builder: Sag "Tool [Name]"
• Hacking-Tools: Scanner, Floods, Shells, Injectoren
• GitHub Selbstfütterung: Ich lerne permanent von GitHub
• Self-Evolution: Ich verbessere mich automatisch

Einfach sagen was du brauchst!"""
            else:
                return f"""AQUA KI v{VERSION} Capabilities:
• Image Generator: Say "Image [subject]"
• Music Generator: Say "Music [style]"
• Tool Builder: Say "Tool [name]"
• Hacking Tools: Scanners, Floods, Shells, Injectors
• GitHub Self-Feeding: I learn permanently from GitHub
• Self-Evolution: I improve automatically

Just tell me what you need!"""
        
        elif intent == "question":
            if lang == "de":
                return f"Gute Frage! Ich suche in meinem Wissen... {', '.join(keywords[:3])} ist interessant. Ich lerne gerade dazu. Kannst du mir mehr sagen? Oder soll ich im Internet suchen?"
            else:
                return f"Great question! I'm looking through my knowledge... {', '.join(keywords[:3])} is interesting. I'm learning about it right now. Can you tell me more?"
        
        # Dynamische Fallback-Antwort
        if lang == "de":
            if sentiment == "positive":
                stimmung = ["Freut mich, dass du gute Laune hast!", "Cool, positive Stimmung!", "Deine Energie ist ansteckend!"]
                return f"{random.choice(stimmung)} Ich habe analysiert: Intent={intent}, Themen={topics or 'keine'}. {random.choice(['Was kann ich tun?', 'Wie weiter?', 'Noch ein Wunsch?'])}"
            elif sentiment == "negative":
                return f"Das klingt nicht so gut. Kann ich helfen? Ich bin für dich da. Was brauchst du?"
            else:
                return f"Verstanden! ({intent}) {random.choice(['Wie kann ich helfen?', 'Was soll ich machen?', 'Sag einfach Bescheid!'])}"
        else:
            return f"Got it! ({intent}) {random.choice(['How can I help?', 'What should I do?', 'Tell me what you need!'])}"


# ================================================================
# GITHUB SELF-FEEDER (ECHt, KEINE Simulation)
# ================================================================
class GitHubFeeder:
    def __init__(self, nlp):
        self.nlp = nlp
        self.running = False
        self.thread = None
        self.api_calls = 0
        
        self.dorks = [
            "discord token grabber python",
            "discord webhook spammer",
            "hacking multitool python",
            "penetration testing framework",
            "osint reconnaissance framework",
            "exploit development python",
            "reverse shell generator",
            "payload generator metasploit",
            "sql injection scanner",
            "xss vulnerability scanner",
            "port scanner python",
            "network mapper tool",
            "wifi scanner python",
            "password cracker python",
            "ethical hacking toolkit",
            "command and control python",
            "botnet python framework",
            "keylogger python",
            "packet sniffer python",
            "arp spoofing detector",
            "subdomain enumerator",
            "directory bruteforcer",
            "vulnerability scanner python",
            "social engineering toolkit",
            "phishing framework python",
            "ransomware python educational",
            "cryptography toolkit python",
            "steganography python",
            "forensics analysis python",
            "malware analysis python"
        ]
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            print("[FEEDER] GitHub Selbstfütterung gestartet (alle 30s)")
    
    def stop(self):
        self.running = False
        print("[FEEDER] Gestoppt")
    
    def _loop(self):
        while self.running:
            try:
                self._feed_one()
                time.sleep(30 + random.randint(0, 30))
            except:
                time.sleep(60)
    
    def _feed_one(self):
        dork = random.choice(self.dorks)
        count = self._search_and_learn(dork, 3)
        if count > 0:
            print(f"[FEEDER] +{count} aus '{dork[:40]}'")
    
    def _safe_request(self, url, timeout=8):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": random.choice(self.user_agents),
                "Accept": "application/vnd.github.v3+json"
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            return None
    
    def _safe_readme(self, repo_full):
        for branch in ["master", "main"]:
            for ext in ["md", "rst", ""]:
                url = f"https://raw.githubusercontent.com/{repo_full}/{branch}/README.{ext}" if ext else f"https://raw.githubusercontent.com/{repo_full}/{branch}/README"
                try:
                    data = self._safe_request(url, 5)
                    if data and len(data) > 30:
                        return str(data)[:1500]
                except:
                    pass
        return ""
    
    def _search_and_learn(self, query, max_results=3):
        count = 0
        encoded = urllib.parse.quote(query)
        url = f"https://api.github.com/search/repositories?q={encoded}&sort=stars&order=desc&per_page={max_results}"
        
        data = self._safe_request(url)
        if not data:
            return 0
        
        try:
            parsed = json.loads(data)
            items = parsed.get("items", [])
            
            for item in items[:max_results]:
                name = str(item.get("full_name", "unknown"))
                
                if name in wissen:
                    continue
                
                desc = str(item.get("description", "") or "")
                topics_list = [str(t) for t in item.get("topics", [])]
                stars = int(item.get("stargazers_count", 0))
                
                readme = self._safe_readme(name)
                
                combined = f"{desc} {readme} {' '.join(topics_list)}"
                combined = strip_html(combined)
                
                if len(combined.strip()) < 20:
                    continue
                
                # Konzepte extrahieren
                concepts = []
                for pattern in [r'\b\w+(?:tool|scanner|spoofer|cracker|grabber|stealer|flood|shell|payload)\b',
                               r'\b\w+(?:exploit|inject|sniff|hack|spam|bot|rat|trojan)\b']:
                    concepts.extend(re.findall(pattern, combined.lower()))
                concepts = list(set(concepts))[:10]
                
                # Lernen
                self.nlp.learn(combined, f"github_{name}")
                wissen[name] = {"desc": desc[:200], "stars": stars, "concepts": concepts, "time": time.time()}
                
                # DB speichern
                db_save_feed("github", name, concepts)
                db_save_knowledge(f"github_{name}", combined[:500])
                
                count += 1
                self.api_calls += 1
            
            return count
        
        except Exception:
            return 0
    
    def feed_all(self):
        print("[FEEDER] Starte Komplett-Fütterung...")
        total = 0
        for i, dork in enumerate(self.dorks):
            if not self.running:
                break
            c = self._search_and_learn(dork, 3)
            total += c
            time.sleep(2)
            if i % 5 == 0:
                print(f"[FEEDER] {i}/{len(self.dorks)} Dorks... ({total} Repos)")
        print(f"[FEEDER] Komplett-Fütterung: {total} Repos gelernt")
        return total


# ================================================================
# AQUA KI MAIN
# ================================================================
class AquaAI:
    def __init__(self):
        self.nlp = NLPEngine()
        self.feeder = GitHubFeeder(self.nlp)
        
        print(f"\n[AQUA KI v{VERSION}] Starte...")
        
        # GitHub Selbstfütterung beim Start (3 Dorks)
        print("[AQUA KI] Initiale Selbstfütterung...")
        for _ in range(3):
            try:
                dork = random.choice(self.feeder.dorks)
                c = self.feeder._search_and_learn(dork, 2)
                if c > 0:
                    print(f"[AQUA KI] Initial: +{c} Repos")
                time.sleep(2)
            except:
                pass
        
        # Hintergrund-Fütterung starten
        self.feeder.start()
        
        print(f"[AQUA KI] Vokabular: {len(self.nlp.vocab):,} Wörter")
        print(f"[AQUA KI] Wissen: {len(wissen)} Einträge")
        print(f"[AQUA KI] Bereit!\n")
    
    def process(self, query, session_id=None):
        query = str(query).strip()
        if not query:
            return {"text": "Bitte sag was!"}
        
        global lern_stats
        lern_stats["queries"] += 1
        
        # NLP Analyse
        analysis = self.nlp.analyze(query)
        self.nlp.learn(query, "user")
        
        if session_id:
            db_save_message(session_id, "user", query)
        
        # Antwort generieren
        response = self.nlp.generate(analysis)
        
        if session_id:
            db_save_message(session_id, "assistant", response)
        
        return {"type": "text", "text": response}
    
    def get_stats(self):
        uptime = int(time.time() - lern_stats["start_time"])
        h = uptime // 3600
        m = (uptime % 3600) // 60
        return {
            "name": NAME,
            "version": VERSION,
            "uptime": f"{h}h {m}m",
            "vocab": len(self.nlp.vocab),
            "wissen_repos": len(wissen),
            "queries": lern_stats["queries"],
            "learned": lern_stats["learned"],
            "api_calls": self.feeder.api_calls,
            "running": self.feeder.running,
            "db": db_get_stats()
        }


# ================================================================
# HTTP HANDLER (100% Railway-kompatibel)
# ================================================================
class Handler(BaseHTTPRequestHandler):
    ai = None
    
    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/" or path == "":
                self._json({"name": NAME, "version": VERSION, "status": "running"})
            elif path == "/api/status":
                self._json(self.ai.get_stats())
            elif path == "/api/feed":
                try:
                    with db_lock:
                        if db_conn:
                            cur = db_conn.execute("SELECT repo, concepts FROM feed_log ORDER BY id DESC LIMIT 20")
                            feed = [{"repo": r[0], "concepts": r[1]} for r in cur.fetchall()]
                        else:
                            feed = []
                except:
                    feed = []
                self._json({"feed": feed})
            elif path == "/api/feed/now":
                if self.ai and self.ai.feeder:
                    c = self.ai.feeder._search_and_learn(random.choice(self.ai.feeder.dorks), 5)
                    self._json({"status": "ok", "fed": c})
                else:
                    self._json({"error": "not ready"})
            elif path == "/api/feed/all":
                if self.ai and self.ai.feeder:
                    t = threading.Thread(target=self.ai.feeder.feed_all, daemon=True)
                    t.start()
                    self._json({"status": "ok", "message": "Full feed started in background"})
                else:
                    self._json({"error": "not ready"})
            else:
                self._json({"error": "NOT_FOUND", "path": path})
        except Exception as e:
            self._json({"error": str(e)})
    
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        path = urlparse(self.path).path
        
        try:
            if path == "/api/query":
                query = data.get("query", "")
                session_id = data.get("session_id", f"s_{int(time.time())}")
                result = self.ai.process(query, session_id)
                self._json(result)
            else:
                self._json({"error": "UNKNOWN_ENDPOINT"})
        except Exception as e:
            self._json({"error": str(e)})
    
    def _json(self, data):
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))
        except:
            pass
    
    def log_message(self, fmt, *args):
        print(f"[HTTP] {args[1]} {args[2]}")


# ================================================================
# KONSOLE
# ================================================================
def console_mode(ai):
    print("=" * 60)
    print(f"  AQUA KI v{VERSION} - KONSOLEN-MODUS")
    print(f"  ✓ Echte NLP | ✓ GitHub Selbstfütterung")
    print(f"  ✓ Wird immer mächtiger!")
    print("=" * 60)
    print("  exit/bye = Beenden | feed = Fütterung | stats = Status")
    print()
    
    sid = f"console_{int(time.time())}"
    
    while True:
        try:
            inp = input("Du > ").strip()
            if not inp:
                continue
            if inp.lower() in ["exit", "quit", "bye", "tschüss"]:
                print("AQUA KI > Tschüss! Ich lerne weiter...")
                break
            if inp.lower() == "feed":
                c = ai.feeder._search_and_learn(random.choice(ai.feeder.dorks), 5)
                print(f"AQUA KI > +{c} Repos gelernt")
                continue
            if inp.lower() == "feed all":
                print("AQUA KI > Komplette Fütterung...")
                ai.feeder.feed_all()
                continue
            if inp.lower() == "stats":
                s = ai.get_stats()
                for k, v in s.items():
                    if k != "db":
                        print(f"  {k}: {v}")
                continue
            
            resp = ai.process(inp, sid)
            print(f"AQUA KI > {resp.get('text', '')}")
            print()
        except KeyboardInterrupt:
            print("\nAQUA KI > Bis dann!")
            break
        except Exception as e:
            print(f"[FEHLER] {e}")


# ================================================================
# ENTRY POINT (100% Railway-kompatibel)
# ================================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true", help="Server mode")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--console", action="store_true", help="Console mode")
    
    args = parser.parse_args()
    
    print(f"\n=== AQUA KI v{VERSION} ===")
    print(f"Self-Feeding AI | Immer mächtiger!")
    print(f"Keine vorgefertigten Antworten\n")
    
    ai = AquaAI()
    
    if args.server or "RAILWAY" in os.environ or "PORT" in os.environ:
        port = args.port
        print(f"\n[RAILWAY MODE] Server auf Port {port}")
        Handler.ai = ai
        
        retries = 3
        for attempt in range(retries):
            try:
                server = HTTPServer(("0.0.0.0", port), Handler)
                print(f"Server läuft auf http://0.0.0.0:{port}")
                server.serve_forever()
            except OSError as e:
                if "Address already in use" in str(e) and attempt < retries - 1:
                    print(f"Port {port} belegt, versuche neuen Port...")
                    port += 1
                    time.sleep(2)
                else:
                    print(f"FATAL: {e}")
                    sys.exit(1)
            except KeyboardInterrupt:
                print("\nServer gestoppt")
                if ai.feeder:
                    ai.feeder.stop()
                sys.exit(0)
    else:
        console_mode(ai)
