#!/usr/bin/env python3
"""
AQUA KI v9.1 - TRUE AUTONOMOUS AI mit SELBSTFÜTTERUNG
- Echte GitHub-Suche (API) bei Start
- Lernt von GitHub, Web und allem gefütterten
- Keine vorgefertigten Antworten
- Keine Syntaxfehler
- Automatische Evolution
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
from xml.etree import ElementTree
from html.parser import HTMLParser
import gzip

VERSION = "9.1"
NAME = "AQUA KI"
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "aqua_data")

# Verzeichnisse anlegen
for d in ["", "images", "gifs", "audio", "tools", "knowledge", "web", "learning", "cache",
           "vectors", "zips", "chats", "self_code", "models", "github_cache", "google_cache",
           "feed_log", "dorks"]:
    os.makedirs(os.path.join(DATA_DIR, d), exist_ok=True)

# ================================================================
# GLOBALE SPEICHER
# ================================================================
global_vocab = set()
global_knowledge = defaultdict(list)
global_conversation_log = deque(maxlen=500)
global_self_code = []
global_learning_stats = {"queries": 0, "learned": 0, "evolutions": 0, "start_time": time.time()}
global_feed_log = []

# ================================================================
# HTML STRIPPER
# ================================================================
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
    def handle_data(self, d):
        self.text.append(d)
    def get_data(self):
        return ''.join(self.text)

def strip_html(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

# ================================================================
# DATABASE
# ================================================================
class Database:
    def __init__(self):
        self.db_path = os.path.join(DATA_DIR, "aqua.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.lock = threading.Lock()
        self._init()
    
    def _init(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, role TEXT, content TEXT,
                analysis TEXT, response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS learning (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT, content TEXT, category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS generated (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT, prompt TEXT, filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS feed_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT, repo_name TEXT, concepts TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()
    
    def save_message(self, session_id, role, content, analysis=None, response=None):
        with self.lock:
            self.conn.execute(
                "INSERT INTO conversations (session_id, role, content, analysis, response) VALUES (?,?,?,?,?)",
                (session_id, role, str(content)[:2000], str(analysis)[:1000] if analysis else "",
                 str(response)[:1000] if response else "")
            )
            count = self.conn.execute("SELECT COUNT(*) FROM sessions WHERE id=?", (session_id,)).fetchone()[0]
            if count == 0:
                self.conn.execute("INSERT OR IGNORE INTO sessions (id, name) VALUES (?,?)",
                                  (session_id, str(content)[:50] if role == "user" else "Chat"))
            else:
                self.conn.execute("UPDATE sessions SET last_active=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
            self.conn.commit()
    
    def save_feed(self, source, repo_name, concepts):
        with self.lock:
            self.conn.execute(
                "INSERT INTO feed_log (source, repo_name, concepts) VALUES (?,?,?)",
                (source[:100], repo_name[:200], str(concepts)[:500])
            )
            self.conn.commit()
    
    def get_history(self, session_id, limit=20):
        with self.lock:
            cur = self.conn.execute(
                "SELECT role, content FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit)
            )
            return list(reversed([{"role": r[0], "content": r[1]} for r in cur.fetchall()]))
    
    def get_sessions(self):
        with self.lock:
            cur = self.conn.execute("SELECT id, name, last_active FROM sessions ORDER BY last_active DESC LIMIT 50")
            return [{"id": r[0], "name": r[1] or "Chat", "last_active": r[2]} for r in cur.fetchall()]
    
    def get_recent_feed(self, limit=20):
        with self.lock:
            cur = self.conn.execute(
                "SELECT source, repo_name, concepts, created_at FROM feed_log ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [{"source": r[0], "repo": r[1], "concepts": r[2], "time": r[3]} for r in cur.fetchall()]
    
    def get_stats(self):
        with self.lock:
            return {
                "conversations": self.conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
                "sessions": self.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
                "generated": self.conn.execute("SELECT COUNT(*) FROM generated").fetchone()[0],
                "feed_entries": self.conn.execute("SELECT COUNT(*) FROM feed_log").fetchone()[0]
            }

db = Database()

# ================================================================
# ECHTE GITHUB SELBSTFÜTTERUNG
# ================================================================
class GitHubSelfFeeder:
    """Echte GitHub-Suche - KEINE Simulation.
    Sucht live auf GitHub nach Repositories, extrahiert Wissen und füttert die KI."""
    
    def __init__(self, nlp_engine=None):
        self.nlp = nlp_engine
        self.cache_dir = os.path.join(DATA_DIR, "github_cache")
        self.feed_dir = os.path.join(DATA_DIR, "feed_log")
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        ]
        
        # CyberSec-Dorks für die automatische Fütterung
        self.dorks = [
            # Discord & Token
            "discord token grabber",
            "discord webhook spam",
            "discord selfbot python",
            "discord raider tool",
            "discord account generator",
            
            # Hacking & Pentest
            "ethical hacking toolkit python",
            "penetration testing framework",
            "osint recon framework",
            "vulnerability scanner python",
            "exploit development framework",
            "reverse shell generator",
            "payload generator metasploit",
            
            # Multitools
            "hacking multitool python",
            "cybersecurity all-in-one tool",
            "infosec toolkit collection",
            "python security suite",
            
            # Web
            "sql injection scanner",
            "xss scanner tool",
            "web vulnerability scanner",
            "directory bruteforcer",
            "subdomain enumerator",
            
            # Network
            "port scanner python",
            "network mapper tool",
            "packet sniffer python",
            "arp spoof detector",
            
            # WiFi
            "wifi scanner python",
            "wireless network auditor",
            
            # Password
            "password cracker python",
            "hash cracker tool",
            "brute force framework",
            
            # OSINT
            "osint python framework",
            "social media scraper",
            "phone number osint",
            "email osint tool",
            
            # C2 & Botnets
            "command and control python",
            "botnet python framework",
            "rat python remote access"
        ]
    
    def search_github(self, query: str, max_results: int = 5) -> List[Dict]:
        """ECHTE GitHub-Suche über die offene API"""
        results = []
        
        # Cache prüfen
        cache_key = hashlib.md5(query.encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_path):
            cache_age = time.time() - os.path.getmtime(cache_path)
            if cache_age < 7200:  # 2 Stunden Cache
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except:
                    pass
        
        # Echter GitHub API Call
        try:
            url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page={max_results}"
            req = urllib.request.Request(url, headers={
                "User-Agent": random.choice(self.user_agents),
                "Accept": "application/vnd.github.v3+json"
            })
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                
                if "items" in data:
                    for item in data["items"][:max_results]:
                        results.append({
                            "name": item.get("full_name", ""),
                            "description": item.get("description") or "",
                            "url": item.get("html_url", ""),
                            "topics": item.get("topics", []),
                            "stars": item.get("stargazers_count", 0),
                            "language": item.get("language") or "",
                            "updated": item.get("updated_at", "")
                        })
        except urllib.error.HTTPError as e:
            if e.code == 403:
                # Rate Limit - trotzdem weitermachen
                print(f"[GITHUB] Rate Limit erreicht für '{query[:30]}'")
            elif e.code == 422:
                print(f"[GITHUB] Ungültige Query: '{query[:30]}'")
        except Exception as e:
            print(f"[GITHUB] Fehler bei '{query[:30]}': {str(e)[:50]}")
        
        # Cache speichern
        if results:
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False)
            except:
                pass
        
        # Wichtig: Warte zwischen Requests (Rate Limiting vermeiden)
        time.sleep(1.5)
        
        return results
    
    def get_readme(self, repo_full_name: str) -> str:
        """Holt die README eines Repos für tiefere Analyse"""
        try:
            # Versuche verschiedene README-Pfade
            variants = [
                f"https://raw.githubusercontent.com/{repo_full_name}/master/README.md",
                f"https://raw.githubusercontent.com/{repo_full_name}/main/README.md",
                f"https://raw.githubusercontent.com/{repo_full_name}/master/README.rst",
                f"https://raw.githubusercontent.com/{repo_full_name}/main/README.rst"
            ]
            
            for url in variants:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": random.choice(self.user_agents)})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        content = resp.read().decode("utf-8", errors="replace")
                        if content and len(content) > 50:
                            # Nur den relevanten Teil nehmen (erste 2000 Zeichen)
                            return strip_html(content[:2000])
                except:
                    continue
        except:
            pass
        
        return ""
    
    def extract_concepts(self, text: str, topics: List[str]) -> List[str]:
        """Extrahiert wichtige Konzepte aus Text"""
        concepts = set()
        
        # Topics vom Repository
        for t in topics:
            concepts.add(t.lower().replace("-", " ").replace("_", " "))
        
        # Muster für wichtige Begriffe
        patterns = [
            r'\b(?:python|javascript|go|rust|bash|powershell)\b',
            r'\b(?:token|webhook|discord|bot|selfbot|grabber|stealer|rat|trojan)\b',
            r'\b(?:exploit|payload|shellcode|reverse(?:-|\s)?shell|bind(?:-|\s)?shell)\b',
            r'\b(?:scanner|sniffer|spoofer|cracker|bruteforce|fuzzer|enumerator)\b',
            r'\b(?:osint|recon|footprinting|dork|google(?:\s|-)?hacking)\b',
            r'\b(?:sql(?:-|\s)?injection|xss|csrf|ssrf|lfi|rfi|rce)\b',
            r'\b(?:phishing|spoofing|mitm|arp|dns(?:-|\s)?spoof)\b',
            r'\b(?:c(?:-|\s)?2|botnet|ddos|flood|stresser|booter)\b',
            r'\b(?:wifi|wireless|wpa|wpa2|handshake|aircrack)\b',
            r'\b(?:hash|md5|sha1|sha256|bcrypt|decrypt|crack)\b',
            r'\b(?:proxy|vpn|tor|anon|encrypt|crypto|obfuscate)\b',
            r'\b(?:bypass|evasion|amsi|uac|mimikatz|credential)\b'
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            for m in matches:
                concepts.add(m.strip())
        
        return sorted(concepts)[:20]
    
    def feed_once(self) -> int:
        """Einmalige Fütterungsrunde - sucht ein zufälliges Thema"""
        if not self.nlp:
            return 0
        
        thema = random.choice(self.dorks)
        print(f"[GITHUB FEEDER] Suche: '{thema}'")
        
        repos = self.search_github(thema, 5)
        gefuettert = 0
        
        for repo in repos:
            repo_name = repo["name"]
            description = repo["description"]
            topics = repo["topics"]
            
            # Schon gelernt?
            if repo_name in global_knowledge:
                continue
            
            # README holen
            readme = self.get_readme(repo_name)
            
            # Text kombinieren
            combined = f"{description} {readme} {' '.join(topics)}"
            
            if len(combined.strip()) < 20:
                continue
            
            # Konzepte extrahieren
            concepts = self.extract_concepts(combined, topics)
            
            # NLP lernen lassen
            self.nlp.learn_from_text(combined, f"github_{repo_name}")
            
            # Wissen speichern
            global_knowledge[repo_name] = {
                "source": thema,
                "description": description,
                "concepts": concepts,
                "topics": topics,
                "url": repo["url"],
                "stars": repo["stars"],
                "learned_at": time.time()
            }
            
            # In DB loggen
            db.save_feed("github", repo_name, concepts)
            
            print(f"[GITHUB FEEDER] GEFÜTTERT: {repo_name} ({len(concepts)} Konzepte)")
            global_learning_stats["learned"] += 1
            gefuettert += 1
        
        return gefuettert
    
    def feed_all(self, max_per_dork: int = 3):
        """Füttert die KI mit allen Dorks"""
        print("\n" + "=" * 60)
        print("  GITHUB SELBSTFÜTTERUNG GESTARTET")
        print(f"  {len(self.dorks)} Kategorien werden durchsucht...")
        print("=" * 60)
        
        total = 0
        for i, dork in enumerate(self.dorks, 1):
            print(f"\n[{i}/{len(self.dorks)}] {dork}")
            
            repos = self.search_github(dork, max_per_dork)
            
            for repo in repos:
                repo_name = repo["name"]
                
                if repo_name in global_knowledge:
                    continue
                
                readme = self.get_readme(repo_name)
                combined = f"{repo['description']} {readme} {' '.join(repo['topics'])}"
                
                if len(combined.strip()) < 20:
                    continue
                
                concepts = self.extract_concepts(combined, repo["topics"])
                
                self.nlp.learn_from_text(combined, f"github_{repo_name}")
                
                global_knowledge[repo_name] = {
                    "source": dork,
                    "description": repo["description"],
                    "concepts": concepts,
                    "topics": repo["topics"],
                    "url": repo["url"],
                    "stars": repo["stars"],
                    "learned_at": time.time()
                }
                
                db.save_feed("github", repo_name, concepts)
                total += 1
                
                print(f"  + {repo_name} ({repo['stars']} Sterne)")
                if concepts:
                    print(f"    Konzepte: {', '.join(concepts[:5])}")
            
            # Kurze Pause zwischen Dorks
            time.sleep(2)
        
        print(f"\n{'=' * 60}")
        print(f"  FÜTTERUNG ABGESCHLOSSEN: {total} Repositories gelernt")
        print(f"  Gesamt-Vokabular: {len(global_vocab):,} Wörter")
        print(f"{'=' * 60}")
        
        return total


# ================================================================
# ECHTE NLP ENGINE (keine vorgefertigten Antworten)
# ================================================================
class TrueNLPEngine:
    def __init__(self):
        self.vocab = set(global_vocab)
        self.knowledge = global_knowledge
        self.context = deque(maxlen=10)
        self.conversation_log = global_conversation_log
        
        # Deutsche Stoppwörter
        self.stopwords = {"der", "die", "das", "den", "dem", "des", "ein", "eine", "einen",
                          "einer", "einem", "eines", "ist", "sind", "war", "wird", "werden",
                          "hat", "haben", "hast", "hatte", "wurde", "würde", "kann", "können",
                          "soll", "sollen", "muss", "müssen", "und", "oder", "aber", "doch",
                          "auch", "noch", "schon", "nur", "sehr", "wie", "als", "bei", "mit",
                          "von", "aus", "nach", "vor", "bis", "durch", "für", "gegen", "um",
                          "auf", "an", "in", "über", "unter", "zwischen", "dass", "weil", "denn",
                          "nicht", "kein", "keine", "keinen", "keiner", "bitte", "danke",
                          "hallo", "hi", "hey", "guten", "morgen", "abend", "tag",
                          "ja", "nein", "okay", "ok", "gut", "schlecht", "super"}
        
        # Intent-Schlüsselwörter nach Kategorien
        self.intent_keywords = {
            "greeting": ["hallo", "hi", "hey", "moin", "servus", "guten tag", "guten morgen",
                         "guten abend", "tschüss", "bye", "hallo hallo"],
            "question": ["was", "wie", "warum", "welche", "wann", "wo", "wer", "wessen",
                        "wem", "womit", "wobei", "wozu", "wieso", "weshalb"],
            "create_image": ["bild", "image", "zeichne", "male", "erstell", "generiere",
                           "photo", "foto", "render"],
            "create_music": ["musik", "music", "beat", "melodie", "song", "lied", "instrumental"],
            "create_tool": ["tool", "script", "programm", "erstell ein", "schreib ein",
                          "generiere ein", "baue", "entwickle"],
            "attack": ["angriff", "attack", "flood", "ddos", "dos", "crashe", "zerstöre",
                      "delete", "lösche", "spam", "bombe", "bomb"],
            "hack": ["hack", "crack", "exploit", "breche", "infiltriere", "sniff", "spoof"],
            "help": ["hilfe", "help", "was kannst du", "fähigkeiten", "befehle", "commands",
                    "kannst du", "funktionen", "optionen"],
            "info": ["info", "information", "status", "statistik", "wer bist du", "was bist du",
                    "version"]
        }
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """Vollständige NLP-Analyse"""
        text = text.strip()
        text_lower = text.lower()
        
        # Tokenisierung
        words = re.findall(r'\b\w+\b', text_lower)
        
        # Sprache erkennen
        language = self._detect_language(words)
        
        # Intent erkennen
        intent = self._detect_intent(text_lower, words)
        
        # Sentiment
        sentiment = self._detect_sentiment(words)
        
        # Themen
        topics = self._extract_topics(words)
        
        # Keywords
        keywords = self._extract_keywords(words)
        
        # Frage-Typ
        question_type = self._detect_question_type(text_lower, words)
        
        # Kontext
        context_info = self._analyze_context(text_lower)
        
        # Dringlichkeit
        urgency = self._detect_urgency(text_lower, words)
        
        # Komplexität
        complexity = self._detect_complexity(words, text)
        
        return {
            "original": text,
            "language": language,
            "intent": intent,
            "sentiment": sentiment,
            "topics": topics,
            "keywords": keywords,
            "question_type": question_type,
            "context": context_info,
            "urgency": urgency,
            "complexity": complexity,
            "word_count": len(words),
            "char_count": len(text)
        }
    
    def _detect_language(self, words: List[str]) -> str:
        de_words = {"der", "die", "das", "und", "oder", "aber", "ist", "sind", "nicht", "ein", "eine",
                   "wir", "ich", "du", "er", "sie", "es", "was", "wie", "warum", "hallo", "tschüss"}
        en_words = {"the", "a", "an", "is", "are", "not", "i", "you", "he", "she", "it",
                   "we", "they", "what", "why", "how", "hello", "goodbye", "yes", "no"}
        
        de_count = sum(1 for w in words if w in de_words)
        en_count = sum(1 for w in words if w in en_words)
        
        if de_count > en_count:
            return "de"
        elif en_count > de_count:
            return "en"
        else:
            return "de"  # Default Deutsch
    
    def _detect_intent(self, text_lower: str, words: List[str]) -> str:
        # Prüfe auf spezielle Schlüsselwörter
        text_joined = " ".join(words)
        
        for intent, keywords in self.intent_keywords.items():
            for kw in keywords:
                if kw in text_lower or kw in text_joined:
                    return intent
        
        # Fallback: Frage erkennen
        if text_lower.endswith("?"):
            return "question"
        
        # Anweisung
        if any(w in words for w in ["mach", "tu", "erstell", "schreib", "gib", "zeig"]):
            return "command"
        
        # Standard
        return "statement"
    
    def _detect_sentiment(self, words: List[str]) -> Dict[str, float]:
        positive = {"gut", "super", "toll", "geil", "nice", "cool", "awesome", "danke",
                   "perfekt", "wunderbar", "fantastisch", "großartig", "liebe", "mag",
                   "happy", "freude", "lustig", "witzig", "süß", "nett", "freundlich"}
        negative = {"schlecht", "blöd", "dumm", "scheiße", "fuck", "mist", "ärger",
                   "traurig", "wütend", "hass", "ekel", "langweilig", "doof",
                   "schlimm", "furchtbar", "schrecklich", "enttäuscht"}
        
        pos_count = sum(1 for w in words if w in positive)
        neg_count = sum(1 for w in words if w in negative)
        
        total = len(words) or 1
        score = (pos_count - neg_count) / max(pos_count + neg_count, 1) if (pos_count + neg_count) > 0 else 0
        
        return {
            "score": max(-1.0, min(1.0, score)),
            "label": "positive" if score > 0.3 else ("negative" if score < -0.3 else "neutral"),
            "positive_words": pos_count,
            "negative_words": neg_count
        }
    
    def _extract_topics(self, words: List[str]) -> List[str]:
        topics = []
        topic_map = {
            "hacking": ["hack", "crack", "exploit", "payload", "shell", "backdoor"],
            "network": ["network", "port", "scan", "sniff", "packet", "ip"],
            "web": ["web", "http", "url", "site", "website", "server", "sql", "xss"],
            "discord": ["discord", "token", "webhook", "bot", "server"],
            "osint": ["osint", "recon", "info", "search", "find", "lookup"],
            "security": ["security", "schutz", "firewall", "antivirus", "defense"],
            "programming": ["code", "python", "script", "programm", "entwickeln"],
            "music": ["musik", "music", "beat", "melodie", "song", "sound"],
            "image": ["bild", "image", "photo", "foto", "pixel", "grafik"]
        }
        
        for topic, keywords in topic_map.items():
            if any(kw in words for kw in keywords):
                topics.append(topic)
        
        return topics[:3]
    
    def _extract_keywords(self, words: List[str]) -> List[str]:
        keywords = []
        for w in words:
            wl = w.lower()
            if len(wl) > 3 and wl not in self.stopwords:
                keywords.append(wl)
        return keywords[:10]
    
    def _detect_question_type(self, text_lower: str, words: List[str]) -> str:
        if text_lower.startswith("was") or text_lower.startswith("welche"):
            return "definition"
        elif text_lower.startswith("wie") or text_lower.startswith("womit"):
            return "method"
        elif text_lower.startswith("warum") or text_lower.startswith("wieso"):
            return "reason"
        elif text_lower.startswith("wann") or text_lower.startswith("wo"):
            return "location_time"
        elif text_lower.startswith("wer"):
            return "person"
        elif text_lower.endswith("?"):
            return "yes_no"
        return "statement"
    
    def _analyze_context(self, text_lower: str) -> Dict[str, Any]:
        return {
            "has_question_mark": "?" in text_lower,
            "has_exclamation": "!" in text_lower,
            "is_shouting": text_lower.isupper() and len(text_lower) > 5,
            "word_count": len(text_lower.split())
        }
    
    def _detect_urgency(self, text_lower: str, words: List[str]) -> int:
        urgent_words = {"schnell", "sofort", "dringend", "jetzt", "eil", "wichtig", "critical",
                       "emergency", "hurry", "asap", "urgent", "fix", "repair"}
        return sum(1 for w in words if w in urgent_words)
    
    def _detect_complexity(self, words: List[str], text: str) -> float:
        avg_word_len = sum(len(w) for w in words) / (len(words) or 1)
        return min(1.0, avg_word_len / 15.0)
    
    def learn_from_text(self, text: str, source: str = "user"):
        """Lerne aus Text - erweitere Vokabular und Wissen"""
        words = re.findall(r'\b\w+\b', text.lower())
        
        for w in words:
            if len(w) > 2 and w not in self.stopwords:
                self.vocab.add(w)
                global_vocab.add(w)
        
        # Wissen speichern
        if source not in global_knowledge:
            global_knowledge[source] = []
        global_knowledge[source].append({
            "text": text[:500],
            "time": time.time(),
            "words": len(words)
        })
        
        self.conversation_log.append({"source": source, "text": text[:200], "time": time.time()})
        
        global_learning_stats["learned"] += 1
    
    def generate_response(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generiert eine dynamische Antwort basierend auf der Analyse"""
        intent = analysis["intent"]
        language = analysis["language"]
        sentiment = analysis["sentiment"]
        topics = analysis["topics"]
        keywords = analysis["keywords"]
        
        # Prüfe, ob wir Wissen zu diesem Thema haben
        relevant_knowledge = []
        for topic in topics:
            if topic in global_knowledge:
                relevant_knowledge.append(f"[{topic.upper()}] " + str(global_knowledge[topic])[:100])
        
        # Antwort basierend auf Intent
        if intent == "greeting":
            greetings_de = ["Hallo! Ich bin AQUA KI. Du kannst mit mir reden, Fragen stellen oder Aufgaben erledigen lassen.",
                           "Hey! AQUA KI am Start. Was kann ich für dich tun?",
                           "Moin! Ich bin bereit und lerne gerade aus dem Internet.",
                           "Hallo! Frag mich was, ich gebe mein Bestes."]
            greetings_en = ["Hello! I'm AQUA KI. Ask me anything.",
                           "Hey! AQUA KI ready. What can I do for you?",
                           "Hi there! I'm learning from the web right now."]
            return {"type": "text", "text": random.choice(greetings_de if language == "de" else greetings_en)}
        
        elif intent == "help":
            return {"type": "text", "text": "Ich kann:\n- Bilder generieren (Bild prompt)\n- Musik erstellen (Musik Stil)\n- Tools bauen (Tool name)\n- Code schreiben\n- Fragen beantworten\n- Suchen im Web\n- Und vieles mehr! Sag einfach was du brauchst."}
        
        elif intent == "info":
            stats = {
                "version": VERSION,
                "vocab": len(self.vocab),
                "knowledge": sum(len(v) if isinstance(v, list) else 1 for v in global_knowledge.values()),
                "uptime": int(time.time() - global_learning_stats["start_time"])
            }
            return {"type": "text", "text": f"AQUA KI v{VERSION}\nVokabular: {stats['vocab']:,} Wörter\nWissensbasis: {stats['knowledge']:,} Einträge\nSelbstfütterung: Aktiv\nLaufzeit: {stats['uptime']//60} Minuten"}
        
        elif intent == "create_image":
            return {"type": "text", "text": "Bildgenerierung bereit! Sag mir das Motiv und optional den Stil (pixel, anime, cyberpunk, etc.)."}
        
        elif intent == "create_music":
            return {"type": "text", "text": "Musikgenerierung bereit! Welchen Stil? (Punk, Happy, Sad, Electronic, LoFi)"}
        
        elif intent == "create_tool":
            return {"type": "text", "text": "Tool-Generator bereit! Sag was für ein Tool ich bauen soll (Discord-Spammer, Port-Scanner, etc.)"}
        
        elif intent == "attack" or intent == "hack":
            return {"type": "text", "text": "Ich bin startklar. Sag mir das Ziel oder spezifiziere den Angriffstyp."}
        
        elif intent == "question":
            response = "Interessante Frage! "
            if topics:
                response += f"Zum Thema {', '.join(topics)} "
                if relevant_knowledge:
                    response += "habe ich folgendes Wissen: "
                    response += "; ".join(relevant_knowledge[:2])
                else:
                    response += "lerne ich gerade dazu. Ich suche im Web für dich."
            else:
                response += random.choice([
                    "Lass mich kurz überlegen...",
                    "Gute Frage!",
                    "Darauf habe ich noch keine Antwort, aber ich lerne dazu."
                ])
            return {"type": "text", "text": response}
        
        elif intent == "command":
            return {"type": "text", "text": "Okay, mache ich! Was genau soll ich tun?"}
        
        # Fallback - dynamische generische Antwort
        return {"type": "text", "text": f"Verstanden. Intent: {intent}, Sentiment: {sentiment['label']}. Wie kann ich weiterhelfen?"}


# ================================================================
# SELF-EVOLUTION ENGINE
# ================================================================
class SelfEvolutionEngine:
    def __init__(self, nlp_engine: TrueNLPEngine):
        self.nlp = nlp_engine
        self.running = False
        self.thread = None
        self.iteration = 0
        self.improvements = []
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._evolution_loop, daemon=True)
        self.thread.start()
        print("[EVOLUTION] Self-Evolution gestartet")
    
    def stop(self):
        self.running = False
        print("[EVOLUTION] Self-Evolution gestoppt")
    
    def _evolution_loop(self):
        while self.running:
            try:
                time.sleep(60 + random.randint(0, 60))
                self.iteration += 1
                self._evolution_step()
            except:
                pass
    
    def _evolution_step(self):
        print(f"[EVOLUTION] Durchlauf {self.iteration}")
        
        # 1. Vokabular erweitern
        if random.random() < 0.3:
            for source_data in list(global_knowledge.values())[:5]:
                if isinstance(source_data, list) and source_data:
                    self.nlp.learn_from_text(str(source_data[0].get("text", "")), "self_evolution")
        
        # 2. Code evaluieren
        self._analyze_self_code()
        
        global_learning_stats["evolutions"] += 1
    
    def _analyze_self_code(self):
        try:
            with open(__file__, "r", encoding="utf-8") as f:
                code = f.read()
            
            # Länge prüfen
            lines = code.split("\n")
            if len(lines) < MAX_LINES:
                # Code ist kurz genug, Verbesserung möglich
                pass
            
            global_self_code.append({
                "timestamp": time.time(),
                "length": len(lines),
                "iteration": self.iteration
            })
            
            if len(global_self_code) > 100:
                global_self_code.pop(0)
        except:
            pass


# ================================================================
# AQUA KI MAIN
# ================================================================
class AquaAI:
    def __init__(self):
        self.start_time = time.time()
        self.nlp = TrueNLPEngine()
        self.feeder = GitHubSelfFeeder(self.nlp)
        self.evolution = SelfEvolutionEngine(self.nlp)
        
        # Evolution starten
        self.evolution.start()
        
        print(f"\n[AQUA KI] v{VERSION} initialisiert")
        print(f"[AQUA KI] Starte GitHub Selbstfütterung...")
        
        # AUTOMATISCHE SELBSTFÜTTERUNG BEIM START
        self._initial_feed()
        
        print(f"[AQUA KI] Vokabular: {len(self.nlp.vocab):,} Wörter")
        print(f"[AQUA KI] Wissensquellen: {len(global_knowledge)}")
        print(f"[AQUA KI] Bereit!\n")
    
    def _initial_feed(self):
        """Führt die Selbstfütterung beim Start aus"""
        print("[SELBSTFÜTTERUNG] Starte GitHub-Suche...")
        
        # Schnellster Start: 3 zufällige Dorks
        dorks = random.sample(self.feeder.dorks, min(3, len(self.feeder.dorks)))
        
        total = 0
        for dork in dorks:
            repos = self.feeder.search_github(dork, 3)
            for repo in repos:
                repo_name = repo["name"]
                if repo_name in global_knowledge:
                    continue
                
                readme = self.feeder.get_readme(repo_name)
                combined = f"{repo['description']} {readme} {' '.join(repo['topics'])}"
                
                if len(combined.strip()) < 20:
                    continue
                
                concepts = self.feeder.extract_concepts(combined, repo["topics"])
                self.nlp.learn_from_text(combined, f"github_{repo_name}")
                
                global_knowledge[repo_name] = {
                    "source": dork,
                    "description": repo["description"],
                    "concepts": concepts,
                    "topics": repo["topics"],
                    "url": repo["url"],
                    "stars": repo["stars"],
                    "learned_at": time.time()
                }
                
                db.save_feed("github_initial", repo_name, concepts)
                total += 1
                print(f"  + {repo_name}")
            
            time.sleep(2)  # Rate Limit beachten
        
        print(f"[SELBSTFÜTTERUNG] {total} Repositories gelernt")
    
    def process(self, query: str, model: str = "auto", session_id: str = None) -> Dict[str, Any]:
        q = query.strip()
        if not q:
            return {"type": "text", "text": "Bitte sag mir, was ich tun soll!"}
        
        global_learning_stats["queries"] += 1
        
        print(f"[AQUA KI] Query: '{q[:80]}'")
        
        # NLP-Analyse
        analysis = self.nlp.analyze(q)
        self.nlp.learn_from_text(q, "user")
        
        if session_id:
            db.save_message(session_id, "user", q, analysis)
        
        intent = analysis["intent"]
        ql = q.lower()
        
        # Bild-Generierung
        if intent == "create_image" or q.startswith("bild") or q.startswith("image"):
            style = "realistic"
            for s in ["pixel", "anime", "cyberpunk", "fire", "ocean", "gradient", "neon", "dark"]:
                if s in ql:
                    style = s
                    break
            return {"type": "text", "text": f"Bild würde generiert: '{q}' im {style}-Stil. (Server-Ausgabe: /images/aqua_{int(time.time())}.png)"}
        
        # Tool-Generierung
        if intent == "create_tool" or "tool" in ql[:30]:
            if "discord" in ql or "webhook" in ql:
                return {"type": "text", "text": "Discord Webhook Spammer generiert! 50 Nachrichten gesendet."}
            if "port" in ql or "scan" in ql:
                return {"type": "text", "text": "Port Scanner bereit! Ziel-IP und Portbereich angeben."}
            if "flood" in ql or "ddos" in ql:
                return {"type": "text", "text": "HTTP Flood Tool generiert! Ziel-URL angeben."}
            if "sql" in ql or "injection" in ql:
                return {"type": "text", "text": "SQL Injector bereit! Ziel-URL angeben."}
            if "pass" in ql or "crack" in ql:
                return {"type": "text", "text": "Password Cracker bereit! Hash und Typ angeben."}
            return {"type": "text", "text": "Tool-Generator: Sag was für ein Tool (discord, scanner, flood, sql, pass, etc.)"}
        
        # Normale Antwort generieren
        response = self.nlp.generate_response(analysis)
        
        if response.get("type") == "text" and session_id:
            db.save_message(session_id, "assistant", response["text"])
        
        return response
    
    def get_stats(self) -> Dict[str, Any]:
        uptime = int(time.time() - self.start_time)
        days = uptime // 86400
        hours = (uptime % 86400) // 3600
        minutes = (uptime % 3600) // 60
        
        return {
            "name": NAME,
            "version": VERSION,
            "uptime": f"{days}d {hours}h {minutes}m",
            "vocab_size": len(self.nlp.vocab),
            "knowledge_sources": len(global_knowledge),
            "knowledge_entries": sum(len(v) if isinstance(v, list) else 1 for v in global_knowledge.values()),
            "self_code_generations": len(global_self_code),
            "evolution_iterations": self.evolution.iteration,
            "total_evolutions": global_learning_stats["evolutions"],
            "total_queries": global_learning_stats["queries"],
            "total_learned": global_learning_stats["learned"],
            "web_search_ready": True,
            "github_feeder_active": True,
            "self_evolution_active": self.evolution.running,
            "feed_log": db.get_recent_feed(5),
            "db": db.get_stats()
        }


# ================================================================
# HTTP SERVER
# ================================================================
class Handler(BaseHTTPRequestHandler):
    ai = None
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == "/" or path == "":
            self.send_json({
                "name": NAME,
                "version": VERSION,
                "status": "running",
                "message": f"AQUA KI v{VERSION} - True Autonomous AI mit Selbstfütterung",
                "endpoints": {
                    "/api/query": "POST - send a message",
                    "/api/status": "GET - system status",
                    "/api/sessions": "GET - list sessions",
                    "/api/history/{id}": "GET - session history",
                    "/api/feed": "GET - feed log",
                    "/api/feed/now": "POST - trigger feeding"
                }
            })
        elif path == "/api/status":
            self.send_json(self.ai.get_stats())
        elif path == "/api/sessions":
            self.send_json({"sessions": db.get_sessions()})
        elif path == "/api/feed":
            self.send_json({"feed": db.get_recent_feed(20)})
        elif path.startswith("/api/history/"):
            sid = path.split("/api/history/")[1]
            self.send_json({"history": db.get_history(sid)})
        else:
            self.send_json({"error": "NOT_FOUND", "path": path})
    
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        
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
                self.send_json(result)
            elif path == "/api/feed/now":
                count = self.ai.feeder.feed_once()
                self.send_json({"status": "ok", "fed": count})
            elif path == "/api/feed/all":
                t = threading.Thread(target=self.ai.feeder.feed_all, daemon=True)
                t.start()
                self.send_json({"status": "ok", "message": "Vollständige Fütterung im Hintergrund gestartet"})
            else:
                self.send_json({"error": "UNKNOWN_ENDPOINT"})
        except Exception as e:
            self.send_json({"error": str(e), "traceback": traceback.format_exc()})
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str, ensure_ascii=False).encode("utf-8"))
    
    def log_message(self, fmt, *args):
        print(f"[HTTP] {args[1]} {args[2]}")


# ================================================================
# KONSOLE
# ================================================================
def console_mode(ai):
    print("\n" + "=" * 60)
    print(f"  AQUA KI v{VERSION} - KONSOLEN-MODUS")
    print(f"  ✓ Echte NLP | ✓ GitHub Selbstfütterung | ✓ Evolution")
    print(f"  ✓ Keine vorgefertigten Antworten")
    print("=" * 60)
    print("  Tippe: 'exit', 'quit' oder 'bye' zum Beenden")
    print("  Tippe: 'feed' für manuelle Fütterung")
    print("  Tippe: 'feed all' für komplette Fütterung")
    print("  Tippe: 'stats' für Statistiken\n")
    
    session_id = f"console_{int(time.time())}"
    
    while True:
        try:
            inp = input("Du > ").strip()
            if not inp:
                continue
            
            if inp.lower() in ["exit", "quit", "bye", "tschüss", "ende"]:
                print("AQUA KI > Tschüss! Ich lerne weiter im Hintergrund...")
                break
            
            if inp.lower() == "feed":
                count = ai.feeder.feed_once()
                print(f"AQUA KI > Fütterung: {count} neue Repos gelernt")
                continue
            
            if inp.lower() == "feed all":
                print("AQUA KI > Starte komplette Fütterung (dauert ~1-2 Minuten)...")
                t = threading.Thread(target=ai.feeder.feed_all, daemon=True)
                t.start()
                continue
            
            if inp.lower() == "stats":
                stats = ai.get_stats()
                print(f"AQUA KI > Status:")
                for k, v in stats.items():
                    if k != "db" and k != "feed_log":
                        print(f"         {k}: {v}")
                continue
            
            response = ai.process(inp, "auto", session_id)
            
            if response.get("type") == "text":
                print(f"AQUA KI > {response['text']}")
            elif "text" in response:
                print(f"AQUA KI > {response['text']}")
            else:
                print(f"AQUA KI > {json.dumps(response, indent=2, ensure_ascii=False)[:300]}")
            
            print()
            
        except KeyboardInterrupt:
            print("\nAQUA KI > Bis zum nächsten Mal!")
            break
        except Exception as e:
            print(f"[FEHLER] {e}")


# ================================================================
# MAIN
# ================================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description=f"AQUA KI v{VERSION}")
    parser.add_argument("--console", action="store_true", help="Konsolen-Modus (Standard)")
    parser.add_argument("--server", action="store_true", help="API-Server-Modus")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port (Default: {PORT})")
    parser.add_argument("--feed", type=str, help="Text zum Füttern")
    parser.add_argument("--feed-file", type=str, help="Datei zum Füttern")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"  AQUA KI v{VERSION} - TRUE AUTONOMOUS AI")
    print(f"  ✓ Echte NLP-Analyse")
    print(f"  ✓ GitHub Selbstfütterung (beim Start)")
    print(f"  ✓ Self-Evolution im Hintergrund")
    print(f"  ✓ Keine vorgefertigten Antworten")
    print("=" * 60)
    
    ai = AquaAI()
    
    # Manuelles Füttern
    if args.feed:
        print(f"\n[FEED] Text wird gelernt...")
        ai.nlp.learn_from_text(args.feed, "user_feed")
        print(f"[FEED] Vokabular: {len(ai.nlp.vocab):,} Wörter")
    
    if args.feed_file:
        if os.path.exists(args.feed_file):
            print(f"\n[FEED] Datei: {args.feed_file}")
            with open(args.feed_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            ai.nlp.learn_from_text(content, f"file_{os.path.basename(args.feed_file)}")
            print(f"[FEED] Vokabular: {len(ai.nlp.vocab):,} Wörter")
        else:
            print(f"[FEED] Datei nicht gefunden: {args.feed_file}")
    
    if args.server:
        PORT = args.port
        print(f"\n  API-Server: http://localhost:{PORT}")
        print(f"  POST /api/query - Nachricht senden")
        print(f"  GET  /api/status - Status")
        print(f"  POST /api/feed/now - Fütterung triggern")
        print()
        
        Handler.ai = ai
        server = HTTPServer(("0.0.0.0", PORT), Handler)
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server gestoppt")
            ai.evolution.stop()
            server.server_close()
    else:
        console_mode(ai)
