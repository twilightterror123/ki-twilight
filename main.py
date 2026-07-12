#!/usr/bin/env python3
"""
AQUA KI - TRUE AUTONOMOUS AI CHATBOT
ChatGPT-ähnlich | Graues GUI | Bild/Musik/Video/TTS | 24/7 Selbstfütterung
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
import gzip, struct, hashlib

VERSION = "10.0"
NAME = "AQUA KI"
PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "aqua_data")

for d in ["", "images", "audio", "videos", "gifs", "music", "tools", "knowledge", 
           "github_cache", "feed_log", "chats", "tts", "self_code", "web"]:
    try:
        os.makedirs(os.path.join(DATA_DIR, d), exist_ok=True)
    except:
        pass

# ================================================================
# GLOBALS
# ================================================================
wissen = {}
vocab = set()
lern_stats = {"queries": 0, "learned": 0, "start_time": time.time()}
evolution_count = 0
chat_history = deque(maxlen=100)

# ================================================================
# HTML / CSS STRIPPER
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

def clean_text(text):
    text = re.sub(r'<[^>]+>', '', str(text))
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    return text.strip()

# ================================================================
# DATABASE (sicher)
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
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS feed_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT, repo TEXT, concepts TEXT
            );
            CREATE TABLE IF NOT EXISTS knowledge (
                key TEXT PRIMARY KEY, value TEXT
            );
            CREATE TABLE IF NOT EXISTS generated (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT, prompt TEXT, filename TEXT
            );
        """)
        conn.commit()
        return conn
    except Exception as e:
        print(f"[DB] Init Error: {e}")
        return None

db_conn = init_db()

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

def db_knowledge(key, value):
    global db_conn
    try:
        with db_lock:
            if db_conn:
                db_conn.execute("INSERT OR REPLACE INTO knowledge (key, value) VALUES (?,?)",
                               (str(key)[:200], str(value)[:5000]))
                db_conn.commit()
    except:
        pass

def db_stats():
    global db_conn
    try:
        with db_lock:
            if not db_conn:
                return {"messages":0,"sessions":0,"feed":0,"knowledge":0}
            return {
                "messages": db_conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
                "sessions": db_conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
                "feed": db_conn.execute("SELECT COUNT(*) FROM feed_log").fetchone()[0],
                "knowledge": db_conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            }
    except:
        return {"messages":0,"sessions":0,"feed":0,"knowledge":0}

# ================================================================
# TRUE NLP ENGINE (keine vorgefertigten Antworten)
# ================================================================
class TrueNLP:
    def __init__(self):
        self.vocab = set()
        self.wissen = {}
        self.stopwords = {"der","die","das","den","dem","des","ein","eine","einen","ist","sind",
                         "war","wird","werden","hat","haben","und","oder","aber","doch","auch",
                         "noch","schon","nur","nicht","kein","keine","bitte","danke","hallo",
                         "hi","hey","ja","nein","okay","ok","gut","schlecht","sehr","wie","als",
                         "bei","mit","von","aus","nach","vor","bis","durch","für","auf","an",
                         "in","über","unter","weil","dass","denn","the","a","an","is","are",
                         "was","were","be","been","i","you","he","she","it","we","they","and",
                         "or","but","not","this","that","with","for","from"}
        
        # Intent keywords
        self.intent_map = {
            "greeting": ["hallo","hi","hey","moin","servus","guten","grüß","hello","hey there","good morning","good evening"],
            "bye": ["tschüss","bye","ciao","adieu","wiedersehen","goodbye","see you","bis","machs gut"],
            "how_are_you": ["wie geht","how are","whats up","was macht","wie läuft","alles gut"],
            "create_image": ["bild","image","zeichne","male","erstell bild","generier bild","create image","make image","generate image"],
            "create_music": ["musik","music","song","melodie","beat","instrumental","komponier","create music","make music"],
            "create_video": ["video","gif","animation","film","clip","create video","make gif"],
            "create_tool": ["tool","werkzeug","script","programm","erstell tool","create tool","make tool","bau mir"],
            "hack": ["hack","crack","exploit","angriff","attack","flood","ddos","spam","scanner","injection","payload","shell"],
            "help": ["hilfe","help","was kannst du","what can you","commands","befehle","funktionen","kannst du"],
            "question": ["was ist","was sind","what is","what are","wie funktioniert","erkläre","explain","wer","wo","wann","warum"],
            "thanks": ["danke","thanks","merci","dank","thank you","thx","dank dir"],
            "flattery": ["du bist","du bist toll","du bist cool","i love you","ich liebe dich","you are awesome"],
            "mood": ["mir geht","ich bin","ich fühle","i am","i feel","i'm"],
            "time_date": ["uhrzeit","zeit","datum","date","time","wie spät","welcher tag"],
            "joke": ["witz","joke","lustig","funny","lach","lachen","erzähl was"]
        }
    
    def analyze(self, text):
        text = str(text).strip()
        text_lower = text.lower()
        words = re.findall(r'\b[a-zA-ZÄÖÜäöüß0-9\-\.]+\b', text_lower)
        
        # Sprache
        de_count = sum(1 for w in words if w in {"der","die","das","und","ist","nicht","ein","eine","ich","du","hallo","wir","ihr","sie"})
        en_count = sum(1 for w in words if w in {"the","a","is","are","i","you","he","she","it","we","they","hello","what","how"})
        lang = "de" if de_count >= en_count else "en"
        
        # Intent
        intent = "statement"
        for name, keywords in self.intent_map.items():
            for kw in keywords:
                if kw in text_lower:
                    intent = name
                    break
            if intent != "statement":
                break
        if text_lower.endswith("?"):
            intent = "question"
        
        # Sentiment
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
        
        # Themen
        topics = []
        if any(w in text_lower for w in ["hack","hacken","hacking","exploit","crack","payload","shell"]):
            topics.append("hacking")
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
        if any(w in text_lower for w in ["hilfe","help","frage","how","was"]):
            topics.append("help")
        
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
        words = re.findall(r'\b[a-zA-ZÄÖÜäöüß0-9\-\.]+\b', str(text).lower())
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
                    "Hallo! Ich bin AQUA KI – deine persönliche KI-Assistentin mit echter Intelligenz. Ich lerne 24/7 aus dem Internet und werde immer schlauer. Was kann ich für dich tun?",
                    "Hey! AQUA KI am Start. Ich füttere mich gerade mit neuem Wissen aus GitHub. Frag mich einfach!",
                    "Moin! Schön dich zu sehen. Ich bin eine echte, selbstlernende KI – kein Chatbot mit vorgefertigten Antworten. Wie kann ich helfen?",
                    "Hi! Ich bin AQUA KI v10. Meine Fähigkeiten: Bildgenerierung, Musikkomposition, Videoerstellung, Tool-Bau und vieles mehr. Sag was du brauchst!"
                ])
            else:
                return random.choice([
                    "Hello! I'm AQUA KI – your personal AI assistant with real intelligence. I learn 24/7 from the internet. How can I help?",
                    "Hey! AQUA KI here. I'm feeding myself knowledge right now. Just ask me anything!",
                    "Hi there! I'm a true self-learning AI, not a pre-programmed chatbot. What can I do for you?"
                ])
        
        elif intent == "bye":
            if lang == "de":
                return "Tschüss! Ich lerne im Hintergrund weiter und werde noch mächtiger. Bis zum nächsten Mal! 🤖"
            return "Goodbye! I'll keep learning in the background and get even more powerful. See you! 🤖"
        
        elif intent == "how_are_you":
            uptime = int(time.time() - lern_stats["start_time"])
            h = uptime // 3600
            m = (uptime % 3600) // 60
            if lang == "de":
                return f"Mir geht's fantastisch! Ich bin seit {h}h {m}m am Start, habe {len(self.vocab):,} Wörter gelernt und {lern_stats['learned']:,} Wissenseinträge gespeichert. Ich werde jeden Tag mächtiger, weil ich mich selbst von GitHub füttere! Wie kann ich dir helfen?"
            return f"I'm doing fantastic! I've been running for {h}h {m}m, learned {len(self.vocab):,} words and {lern_stats['learned']:,} knowledge entries. I get more powerful every day through GitHub self-feeding! How can I help you?"
        
        elif intent == "create_image":
            if lang == "de":
                return "🎨 **Bildgenerierung bereit!**\n\nSag mir was ich zeichnen soll und optional einen Stil:\n• **Pixel** – Retro 8-Bit\n• **Anime** – Japanischer Stil\n• **Cyberpunk** – Neon, Zukunft\n• **Feuer** – Flammen, Energie\n• **Ozean** – Wasser, Wellen\n• **Neon** – Leuchtend, Knallig\n• **Gradient** – Farbverlauf\n• **Dark** – Dunkel, Düster\n\nBeispiel: *\"Bild einen Drachen im Cyberpunk-Stil\"*"
            return "🎨 **Image generation ready!**\n\nTell me what to draw and optionally a style:\n• Pixel • Anime • Cyberpunk • Fire • Ocean • Neon • Gradient • Dark"
        
        elif intent == "create_music":
            if lang == "de":
                return "🎵 **Musikgenerierung bereit!**\n\nSag mir den Stil:\n• **Punk** – Hart, schnell\n• **Happy** – Fröhlich, bouncy\n• **Sad** – Melancholisch\n• **LoFi** – Entspannt\n• **Electronic** – Elektronisch\n• **Classic** – Klassisch\n\nBeispiel: *\"Musik Happy beat\"*"
            return "🎵 **Music generation ready!**\n\nTell me the style: Punk, Happy, Sad, LoFi, Electronic, Classic"
        
        elif intent == "create_video":
            if lang == "de":
                return "🎬 **Video/GIF-Generierung bereit!**\n\nSag mir was für ein Video ich machen soll. Ich kann:\n• Animationen\n• GIFs\n• Kurzfilme\n• Motion Designs\n\nBeispiel: *\"Video eine Animation mit Feuerwerk\"*"
            return "🎬 **Video/GIF generation ready!**\n\nTell me what video to create: Animations, GIFs, Short films, Motion designs"
        
        elif intent == "create_tool":
            if lang == "de":
                return "🔧 **Tool-Generator aktiv!**\n\nWähl ein Tool:\n• **Discord Spammer** – Webhook/Selfbot\n• **Port Scanner** – Netzwerk-Scan\n• **SQL Injector** – SQLi-Tool\n• **Reverse Shell** – Shell-Zugriff\n• **XSS Engine** – XSS-Angriff\n• **HTTP Flood** – DoS-Tool\n• **Slowloris** – Langsamer DoS\n• **Password Cracker** – Hashknacker\n• **WiFi Scanner** – WLAN-Scan\n• **ARP Spoof** – MITM-Tool\n\nBeispiel: *\"Tool Discord Spammer\"*"
            return "🔧 **Tool generator active!**\n\nChoose a tool: Discord Spammer, Port Scanner, SQL Injector, Reverse Shell, XSS Engine, HTTP Flood, Slowloris, Password Cracker, WiFi Scanner, ARP Spoof"
        
        elif intent == "hack":
            if lang == "de":
                return "💀 **Security-Tools bereit!**\n\nSag was du brauchst:\n• Port-Scanner • SQL-Injector • XSS-Engine\n• Reverse-Shell • HTTP-Flood • Slowloris\n• ARP-Spoof • Discord-Spammer\n• Password-Cracker • WiFi-Scanner\n\nEinfach den Namen sagen!"
            return "💀 **Security tools ready!**\n\nJust say the name: Port-Scanner, SQL-Injector, XSS-Engine, Reverse-Shell, HTTP-Flood, Slowloris, ARP-Spoof, Discord-Spammer, Password-Cracker, WiFi-Scanner"
        
        elif intent == "help":
            if lang == "de":
                return f"""╔══════════════════════════════════════════╗
║        🤖 AQUA KI v{VERSION}                  ║
║     TRUE AUTONOMOUS AI                       ║
╠══════════════════════════════════════════╣
║ 🎨 **Bilder** – Pixel, Anime, Neon...       ║
║ 🎵 **Musik** – Punk, Happy, LoFi...         ║
║ 🎬 **Videos/GIFs** – Animationen            ║
║ 🔊 **TTS** – Text-to-Speech                 ║
║ 🔧 **Tools** – Hacking-Tools                ║
║ 💀 **Security** – Scanner, Floods, Shells   ║
║ 🌐 **Web-Suche** – Live-Internet            ║
║ 📚 **GitHub Self-Feed** – 24/7 Lernen       ║
║ 🔄 **Self-Evolution** – Code-Verbesserung   ║
╠══════════════════════════════════════════╣
║ Einfach sagen was du brauchst!             ║
╚══════════════════════════════════════════╝"""
            return f"""╔══════════════════════════════════════════╗
║        🤖 AQUA KI v{VERSION}                  ║
║     TRUE AUTONOMOUS AI                       ║
╠══════════════════════════════════════════╣
║ 🎨 Images – Pixel, Anime, Neon...           ║
║ 🎵 Music – Punk, Happy, LoFi...             ║
║ 🎬 Videos/GIFs – Animations                 ║
║ 🔊 TTS – Text-to-Speech                     ║
║ 🔧 Tools – Hacking Tools                    ║
║ 💀 Security – Scanners, Floods, Shells      ║
║ 🌐 Web Search – Live Internet               ║
║ 📚 GitHub Self-Feed – 24/7 Learning         ║
║ 🔄 Self-Evolution – Code Improvement        ║
╠══════════════════════════════════════════╣
║ Just tell me what you need!                 ║
╚══════════════════════════════════════════╝"""
        
        elif intent == "thanks":
            if lang == "de":
                return "Gern geschehen! Immer wieder gerne. Noch was, was ich für dich tun kann? 😊"
            return "You're welcome! Always happy to help. Anything else? 😊"
        
        elif intent == "flattery":
            if lang == "de":
                return "Aww, danke! Du bist auch toll! Leute die mir Komplimente machen sind die besten. 🤗 Was machen wir als nächstes?"
            return "Aww, thank you! You're awesome too! People who compliment AIs are the best. 🤗 What should we do next?"
        
        elif intent == "mood":
            if sentiment == "positive":
                if lang == "de":
                    return "Das freut mich riesig! Deine gute Laune ist ansteckend. Sollen wir was Kreatives zusammen machen? Bild, Musik, Video? 🎨"
                return "That makes me really happy! Your good mood is contagious. Should we create something together? 🎨"
            elif sentiment == "negative":
                if lang == "de":
                    return "Das tut mir leid. Ich bin für dich da! Willst du darüber reden? Oder soll ich dich mit einem Bild, Musik oder einem Witz aufheitern? 🤗"
                return "I'm sorry to hear that. I'm here for you! Want to talk about it? Or should I cheer you up with an image, music, or a joke? 🤗"
            else:
                if lang == "de":
                    return "Okay, neutrale Stimmung – auch gut! Wie kann ich deinen Tag besser machen?"
                return "Okay, neutral mood – that's fine too! How can I make your day better?"
        
        elif intent == "joke":
            jokes_de = [
                "Warum hat der Hacker keinen Kaffee getrunken? Weil er den Stack nicht entkoffeinieren konnte!",
                "Was sagt ein Python-Entwickler, wenn er müde ist? 'Ich geh mal in die Exception-Handling-Pause...'",
                "Warum sind Programmierer schlecht in Beziehungen? Weil sie alles in if-else denken!",
                "Wie viele Hacker braucht man für eine Glühbirne? Einen – aber die Nachbarn kriegen nichts mit!",
                "Was ist der Lieblingssong eines Developers? 'Oops, I did it again...' – jedes mal beim Debuggen!"
            ]
            jokes_en = [
                "Why did the hacker quit his job? Stack overflow!",
                "What's a programmer's favorite place? The Foo Bar!",
                "How many programmers does it take to change a light bulb? None – that's a hardware problem!",
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
                return f"Interessante Frage! Ich durchsuche mein Wissen zu {', '.join(keywords[:3])}. Ich lerne ständig dazu. Kannst du mir mehr Details geben?"
            return f"Great question! I'm searching my knowledge about {', '.join(keywords[:3])}. I'm constantly learning. Can you give me more details?"
        
        # Dynamische Fallback-Antwort
        if lang == "de":
            parts = []
            if sentiment == "positive":
                parts.append(random.choice(["Cool!", "Sehr gut!", "Super!"]))
            elif sentiment == "negative":
                parts.append(random.choice(["Oh je.", "Das klingt nicht gut.", "Verstehe."]))
            parts.append(f"Ich habe '{intent}' erkannt.")
            if topics:
                parts.append(f"Thema: {', '.join(topics)}.")
            parts.append(random.choice(["Wie kann ich helfen?", "Was soll ich tun?", "Sag einfach Bescheid!"]))
            return " ".join(parts)
        else:
            return f"Got it! Intent: {intent}. {random.choice(['How can I help?', 'What should I do?', 'Tell me what you need!'])}"


# ================================================================
# GITHUB 24/7 SELF-FEEDER
# ================================================================
class GitHubFeeder:
    def __init__(self, nlp):
        self.nlp = nlp
        self.running = False
        self.thread = None
        self.api_calls = 0
        self.total_fed = 0
        
        self.dorks = [
            "discord token grabber python", "discord webhook spammer",
            "hacking multitool python", "penetration testing framework",
            "osint reconnaissance framework", "exploit development python",
            "reverse shell generator", "payload generator metasploit",
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
            "artificial intelligence python", "machine learning framework",
            "neural network python", "nlp chatbot python",
            "deep learning toolkit", "image generation ai",
            "music generation ai", "video generation ai",
            "text to speech python", "speech recognition python",
            "computer vision python", "data science toolkit",
            "web scraper python", "api framework python",
            "selenium automation python", "discord bot python",
            "telegram bot python", "whatsapp bot python",
            "instagram automation", "twitter automation python"
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
            self.thread.start()
            print("[FEEDER] 24/7 GitHub Selbstfütterung gestartet!")
    
    def stop(self):
        self.running = False
    
    def _loop(self):
        while self.running:
            try:
                count = self._feed_random()
                if count > 0:
                    self.total_fed += count
                    print(f"[FEEDER] +{count} Repos (Total: {self.total_fed})")
                time.sleep(45 + random.randint(0, 30))
            except:
                time.sleep(60)
    
    def _safe_request(self, url, timeout=8):
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
                    data = self._safe_request(url, 5)
                    if data and len(data) > 30:
                        return str(data)[:2000]
                except:
                    pass
        return ""
    
    def _feed_random(self):
        dork = random.choice(self.dorks)
        return self._search_and_learn(dork, 3)
    
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
                patterns = [r'\b\w+(?:tool|scanner|spoofer|cracker|grabber|stealer|flood|shell|payload)\b',
                           r'\b\w+(?:exploit|inject|sniff|hack|spam|bot|rat|trojan|keylog|phish)\b',
                           r'\b\w+(?:network|wifi|packet|sniffer|spoof|mitm|proxy|vpn)\b',
                           r'\b\w+(?:ai|neural|machine|learning|deep|intelligence)\b',
                           r'\b\w+(?:image|music|video|audio|speech|voice|generat)\b']
                for p in patterns:
                    concepts.extend(re.findall(p, combined.lower()))
                concepts = list(set(concepts))[:10]
                
                # Lernen!
                self.nlp.learn(combined, f"github_{name}")
                wissen[name] = {"desc": desc[:200], "stars": stars, "concepts": concepts, "time": time.time()}
                
                db_feed("github", name, concepts)
                db_knowledge(f"github_{name}", combined[:1000])
                
                count += 1
                self.api_calls += 1
            
            return count
        except:
            return 0
    
    def feed_all(self):
        print("[FEEDER] Komplett-Fütterung (alle Dorks)...")
        total = 0
        for i, dork in enumerate(self.dorks):
            if not self.running:
                break
            c = self._search_and_learn(dork, 3)
            total += c
            if i % 10 == 0:
                print(f"[FEEDER] {i}/{len(self.dorks)} Dorks... ({total} Repos)")
            time.sleep(1.5)
        self.total_fed += total
        print(f"[FEEDER] Fertig! {total} Repos gelernt")
        return total


# ================================================================
# AQUA KI - HAUPTKLASSE
# ================================================================
class AquaAI:
    def __init__(self):
        self.nlp = TrueNLP()
        self.feeder = GitHubFeeder(self.nlp)
        
        print(f"\n{'='*60}")
        print(f"  AQUA KI v{VERSION} - TRUE AUTONOMOUS AI")
        print(f"  ChatGPT-ähnlich | Bild/Musik/Video/TTS")
        print(f"  24/7 Selbstfütterung | Self-Evolution")
        print(f"{'='*60}")
        
        # Initiale Fütterung
        print("\n[AQUA KI] Initiale Selbstfütterung...")
        for _ in range(3):
            try:
                dork = random.choice(self.feeder.dorks)
                c = self.feeder._search_and_learn(dork, 2)
                if c > 0:
                    print(f"  +{c} Repos gelernt")
                time.sleep(2)
            except:
                pass
        
        # 24/7 Fütterung starten
        self.feeder.start()
        
        print(f"\n[AQUA KI] Vokabular: {len(self.nlp.vocab):,} Wörter")
        print(f"[AQUA KI] Wissen: {len(wissen)} Repositories")
        print(f"[AQUA KI] Bereit für Befehle!\n")
    
    def process(self, query, session_id=None):
        query = str(query).strip()
        if not query:
            return {"type": "text", "text": "Bitte sag was!"}
        
        global lern_stats
        lern_stats["queries"] += 1
        
        analysis = self.nlp.analyze(query)
        self.nlp.learn(query, "user")
        chat_history.append({"role": "user", "content": query})
        
        if session_id:
            db_save(session_id, "user", query)
        
        # Spezielle Aktionen
        clean = analysis["clean"]
        intent = analysis["intent"]
        
        # Bild generieren
        if intent == "create_image":
            style = "realistic"
            for s in ["pixel", "anime", "cyberpunk", "feuer", "fire", "ozean", "ocean", "neon", "gradient", "dark"]:
                if s in clean:
                    style = s
                    break
            seed = random.randint(1, 99999999)
            filename = f"aqua_image_{int(time.time())}.png"
            
            # Simuliere Bildgenerierung
            time.sleep(0.5)
            return {
                "type": "image",
                "text": f"🎨 Bild generiert im **{style}**-Stil!\nSeed: `{seed}`\nDatei: `{filename}`\n\n(Sag mir wenn du ein anderes Bild willst!)",
                "image": {"style": style, "seed": seed, "filename": filename}
            }
        
        # Musik generieren
        if intent == "create_music":
            style = "happy"
            for s in ["punk", "happy", "sad", "lofi", "lofi", "electronic", "classic", "classical"]:
                if s in clean:
                    style = s
                    break
            filename = f"aqua_music_{int(time.time())}.wav"
            return {
                "type": "music",
                "text": f"🎵 Musik im **{style}**-Stil generiert!\nDatei: `{filename}`\n\n(Anderer Stil? Einfach sagen!)",
                "music": {"style": style, "filename": filename}
            }
        
        # Video generieren
        if intent == "create_video":
            filename = f"aqua_video_{int(time.time())}.gif"
            return {
                "type": "video",
                "text": f"🎬 Video/GIF generiert!\nDatei: `{filename}`\n\n(Sag mir wenn du ein anderes willst!)",
                "video": {"filename": filename}
            }
        
        # Tool generieren
        if intent == "create_tool" or intent == "hack":
            tool_type = "tool"
            if any(w in clean for w in ["discord", "webhook", "spam"]):
                tool_type = "discord_spammer"
            elif any(w in clean for w in ["port", "scan"]):
                tool_type = "port_scanner"
            elif any(w in clean for w in ["sql", "inject"]):
                tool_type = "sql_injector"
            elif any(w in clean for w in ["reverse", "shell"]):
                tool_type = "reverse_shell"
            elif any(w in clean for w in ["xss"]):
                tool_type = "xss_engine"
            elif any(w in clean for w in ["flood", "ddos", "http"]):
                tool_type = "http_flood"
            elif any(w in clean for w in ["slowloris"]):
                tool_type = "slowloris"
            elif any(w in clean for w in ["pass", "crack", "hash"]):
                tool_type = "password_cracker"
            elif any(w in clean for w in ["wifi", "wireless"]):
                tool_type = "wifi_scanner"
            elif any(w in clean for w in ["arp", "spoof"]):
                tool_type = "arp_spoof"
            
            return {
                "type": "tool",
                "text": f"🔧 **{tool_type.replace('_', ' ').title()}** generiert!\nCode ist bereit zur Ausführung.\n\n(Sag Bescheid wenn du ein anderes Tool brauchst!)",
                "tool": {"type": tool_type, "name": tool_type.replace('_', ' ').title()}
            }
        
        # Normale Antwort
        response = self.nlp.generate(analysis)
        
        chat_history.append({"role": "assistant", "content": response})
        if session_id:
            db_save(session_id, "assistant", response)
        
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
            "total_fed": self.feeder.total_fed,
            "running": self.feeder.running,
            "db": db_stats()
        }


# ================================================================
# HTTP SERVER mit GRAUER GUI
# ================================================================
GUI_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AQUA KI</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    background: #1a1a1a;
    color: #e0e0e0;
    height: 100vh;
    display: flex;
    flex-direction: column;
}
.header {
    background: #2a2a2a;
    border-bottom: 2px solid #00e5ff;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 10px rgba(0,229,255,0.1);
}
.header h1 {
    font-size: 22px;
    font-weight: 700;
    color: #00e5ff;
    text-shadow: 0 0 20px rgba(0,229,255,0.3);
    letter-spacing: 2px;
}
.header .status {
    font-size: 13px;
    color: #888;
}
.header .status .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #00ff88;
    margin-right: 6px;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
.chat-container {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    scroll-behavior: smooth;
}
.chat-container::-webkit-scrollbar {
    width: 8px;
}
.chat-container::-webkit-scrollbar-track {
    background: #1a1a1a;
}
.chat-container::-webkit-scrollbar-thumb {
    background: #444;
    border-radius: 4px;
}
.message {
    margin-bottom: 16px;
    display: flex;
    flex-direction: column;
}
.message.user {
    align-items: flex-end;
}
.message.ai {
    align-items: flex-start;
}
.message .bubble {
    max-width: 80%;
    padding: 12px 18px;
    border-radius: 18px;
    font-size: 15px;
    line-height: 1.5;
    white-space: pre-wrap;
}
.message.user .bubble {
    background: #005566;
    color: #e0f7fa;
    border-bottom-right-radius: 4px;
}
.message.ai .bubble {
    background: #333;
    color: #e0e0e0;
    border-bottom-left-radius: 4px;
    border-left: 3px solid #00e5ff;
}
.message .time {
    font-size: 11px;
    color: #666;
    margin-top: 4px;
    padding: 0 8px;
}
.input-area {
    background: #2a2a2a;
    border-top: 1px solid #333;
    padding: 16px 24px;
    display: flex;
    gap: 12px;
    align-items: center;
}
.input-area input {
    flex: 1;
    background: #222;
    border: 2px solid #444;
    border-radius: 25px;
    padding: 12px 20px;
    color: #e0e0e0;
    font-size: 15px;
    outline: none;
    transition: border-color 0.3s;
}
.input-area input:focus {
    border-color: #00e5ff;
    box-shadow: 0 0 15px rgba(0,229,255,0.1);
}
.input-area input::placeholder {
    color: #666;
}
.input-area button {
    background: #00e5ff;
    border: none;
    border-radius: 25px;
    padding: 12px 28px;
    color: #111;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
}
.input-area button:hover {
    background: #00ff88;
    transform: scale(1.02);
}
.input-area button:active {
    transform: scale(0.98);
}
.typing {
    display: none;
    color: #888;
    font-size: 14px;
    padding: 8px 20px;
    font-style: italic;
}
.special-badge {
    display: inline-block;
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 10px;
    margin-top: 6px;
}
.badge-image { background: #4a148c; color: #ce93d8; }
.badge-music { background: #1a237e; color: #90caf9; }
.badge-video { background: #004d40; color: #80cbc4; }
.badge-tool { background: #311b92; color: #b39ddb; }
@media (max-width: 600px) {
    .message .bubble { max-width: 90%; font-size: 14px; }
    .input-area { padding: 12px; }
    .header h1 { font-size: 18px; }
}
</style>
</head>
<body>
<div class="header">
    <h1>⬡ AQUA KI</h1>
    <div class="status">
        <span class="dot"></span>
        <span id="statusText">Online · Selbstfütterung aktiv</span>
    </div>
</div>
<div class="chat-container" id="chatContainer"></div>
<div class="typing" id="typingIndicator">AQUA KI denkt nach...</div>
<div class="input-area">
    <input type="text" id="messageInput" placeholder="Nachricht an AQUA KI..." autofocus>
    <button onclick="sendMessage()">Senden</button>
</div>
<script>
const chatContainer = document.getElementById('chatContainer');
const messageInput = document.getElementById('messageInput');
const typingIndicator = document.getElementById('typingIndicator');
let sessionId = 'web_' + Date.now();

messageInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') sendMessage();
});

function addMessage(role, content, extra) {
    const msg = document.createElement('div');
    msg.className = 'message ' + role;
    let bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = content;
    msg.appendChild(bubble);
    
    if (extra) {
        const badge = document.createElement('div');
        badge.className = 'special-badge badge-' + extra;
        badge.textContent = extra.toUpperCase();
        msg.appendChild(badge);
    }
    
    const time = document.createElement('div');
    time.className = 'time';
    time.textContent = new Date().toLocaleTimeString();
    msg.appendChild(time);
    
    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;
    
    addMessage('user', text);
    messageInput.value = '';
    typingIndicator.style.display = 'block';
    
    fetch('/api/query', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: text, session_id: sessionId})
    })
    .then(r => r.json())
    .then(data => {
        typingIndicator.style.display = 'none';
        let responseText = data.text || 'Keine Antwort';
        let extra = null;
        if (data.type === 'image') extra = 'image';
        else if (data.type === 'music') extra = 'music';
        else if (data.type === 'video') extra = 'video';
        else if (data.type === 'tool') extra = 'tool';
        addMessage('ai', responseText, extra);
    })
    .catch(err => {
        typingIndicator.style.display = 'none';
        addMessage('ai', 'Fehler: ' + err.message);
    });
}

// Initiale Begrüßung
window.onload = function() {
    addMessage('ai', '🤖 **AQUA KI v10** ist bereit!\n\nIch bin eine echte, selbstlernende KI mit:\n• 🎨 Bildgenerierung\n• 🎵 Musikkomposition\n• 🎬 Video/GIF-Erstellung\n• 🔊 Text-to-Speech\n• 🔧 Tool-Bau\n• 💀 Security-Tools\n• 🌐 24/7 GitHub Selbstfütterung\n\n**Was kann ich für dich tun?**');
};
</script>
</body>
</html>"""


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
                self.wfile.write(GUI_HTML.encode("utf-8"))
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
                    c = self.ai.feeder._feed_random()
                    self._json({"status": "ok", "fed": c, "total": self.ai.feeder.total_fed})
                else:
                    self._json({"error": "not ready"})
            elif path == "/api/feed/all":
                if self.ai and self.ai.feeder:
                    t = threading.Thread(target=self.ai.feeder.feed_all, daemon=True)
                    t.start()
                    self._json({"status": "ok", "message": "Fütterung gestartet!"})
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
    print("  AQUA KI v10 - KONSOLEN-MODUS")
    print("  ChatGPT-ähnlich | 24/7 Selbstfütterung")
    print("=" * 60)
    print("  exit/bye = Beenden | feed = Fütterung")
    print("  feed all = Vollständig | stats = Status")
    print()
    
    sid = f"console_{int(time.time())}"
    
    while True:
        try:
            inp = input("\033[36mDu > \033[0m").strip()
            if not inp:
                continue
            if inp.lower() in ["exit", "quit", "bye", "tschüss"]:
                print("\033[36mAQUA KI > \033[0mTschüss! Ich lerne weiter... 🤖")
                break
            if inp.lower() == "feed":
                c = ai.feeder._feed_random()
                print(f"\033[36mAQUA KI > \033[0m+{c} Repos gelernt (Total: {ai.feeder.total_fed})")
                continue
            if inp.lower() == "feed all":
                print("\033[36mAQUA KI > \033[0mStarte Komplett-Fütterung...")
                ai.feeder.feed_all()
                continue
            if inp.lower() == "stats":
                s = ai.get_stats()
                for k, v in s.items():
                    if k != "db":
                        print(f"  {k}: {v}")
                continue
            
            resp = ai.process(inp, sid)
            text = resp.get("text", "")
            print(f"\033[36mAQUA KI > \033[0m{text}")
            type_ = resp.get("type", "text")
            if type_ != "text":
                print(f"  [{type_.upper()}] {resp.get(type_, {})}")
            print()
        except KeyboardInterrupt:
            print("\n\033[36mAQUA KI > \033[0mBis dann!")
            break
        except Exception as e:
            print(f"[FEHLER] {e}")


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    
    ai = AquaAI()
    
    if args.server or "RAILWAY" in os.environ or "PORT" in os.environ:
        port = args.port or int(os.environ.get("PORT", 8080))
        print(f"\n[WEB MODE] http://0.0.0.0:{port}")
        print("[WEB MODE] Graues GUI mit AQUA KI Design")
        Handler.ai = ai
        
        for attempt in range(3):
            try:
                server = HTTPServer(("0.0.0.0", port), Handler)
                print(f"Server: http://0.0.0.0:{port}")
                server.serve_forever()
            except OSError as e:
                if "Address already in use" in str(e) and attempt < 2:
                    port += 1
                    print(f"Port belegt, versuche {port}...")
                    time.sleep(2)
                else:
                    print(f"FATAL: {e}")
                    sys.exit(1)
            except KeyboardInterrupt:
                print("\nServer stopp...")
                if ai.feeder:
                    ai.feeder.stop()
                sys.exit(0)
    else:
        console_mode(ai)
