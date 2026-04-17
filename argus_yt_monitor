"""
ARGUS — YouTube Global Address Monitor
by VERES · Intelligence without borders

Глобальный мониторинг YouTube — ищет крипто-адреса по всей платформе.
Использует YouTube Search API + Google Custom Search API.

Использование:
  python3 argus_yt_monitor.py                    # стандартный запуск
  python3 argus_yt_monitor.py --lang ru          # только русскоязычные видео
  python3 argus_yt_monitor.py --lang en          # только английские
  python3 argus_yt_monitor.py --queries custom   # только свои запросы
  python3 argus_yt_monitor.py --out results.json # другой выходной файл
  python3 argus_yt_monitor.py --days 7           # только видео за последние 7 дней

Нужны ключи в .env:
  YOUTUBE_API_KEY=...
  GOOGLE_CSE_KEY=...      (опционально)
  GOOGLE_CSE_CX=...       (опционально, Search Engine ID)
"""

import os
import re
import sys
import json
import time
import argparse
from datetime import datetime, timedelta, timezone

try:
    from googleapiclient.discovery import build
    HAS_YOUTUBE = True
except ImportError:
    HAS_YOUTUBE = False

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    G   = Fore.GREEN
    Y   = Fore.YELLOW
    R   = Fore.RED
    C   = Fore.CYAN
    W   = Fore.WHITE
    DIM = Style.DIM
    BR  = Style.BRIGHT
    RS  = Style.RESET_ALL
except ImportError:
    G = Y = R = C = W = DIM = BR = RS = ""

import requests
from dotenv import load_dotenv
load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
GOOGLE_CSE_KEY  = os.getenv("GOOGLE_CSE_KEY", "")
GOOGLE_CSE_CX   = os.getenv("GOOGLE_CSE_CX", "")

# ─── ПОИСКОВЫЕ ЗАПРОСЫ ─────────────────────────────────────────────────────────

SEARCH_QUERIES = {
    "en": [
        "bitcoin donate address",
        "ethereum wallet donate support",
        "crypto donation btc eth",
        "usdt trc20 donate address",
        "support channel crypto wallet",
        "0x donate ethereum",
        "bitcoin wallet support creator",
        "cryptocurrency donation address",
        "solana sol donate",
        "ton crypto donate",
    ],
    "ru": [
        "биткоин кошелёк донат",
        "поддержать крипта адрес",
        "донаты биткоин эфириум",
        "крипто кошелёк поддержка",
        "btc eth донат адрес",
        "поддержать канал биткоин",
        "usdt trc20 донат",
        "крипта донаты помочь",
        "кошелёк для доната",
        "поддержать эфириум адрес",
    ],
    "custom": [],  # заполняется из --queries-file
}

# ─── REGEX ПАТТЕРНЫ ────────────────────────────────────────────────────────────

PATTERNS = {
    "evm":        (re.compile(r'\b0x[a-fA-F0-9]{40}\b'),        "EVM"),
    "btc_legacy": (re.compile(r'\b1[a-km-zA-HJ-NP-Z1-9]{25,33}\b'), "Bitcoin"),
    "btc_p2sh":   (re.compile(r'\b3[a-km-zA-HJ-NP-Z1-9]{25,33}\b'), "Bitcoin"),
    "btc_bech32": (re.compile(r'\bbc1[a-z0-9]{6,87}\b'),         "Bitcoin"),
    "trx":        (re.compile(r'\bT[a-zA-Z0-9]{33}\b'),          "Tron"),
    "ton":        (re.compile(r'\b(?:EQ|UQ)[a-zA-Z0-9_\-]{45,46}\b'), "TON"),
    "sol":        (re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{43,44}\b'), "Solana"),
}

# ─── YOUTUBE API ───────────────────────────────────────────────────────────────

def get_youtube_client():
    if not HAS_YOUTUBE:
        print(f"{R}[✗] pip install google-api-python-client{RS}")
        sys.exit(1)
    if not YOUTUBE_API_KEY:
        print(f"{R}[✗] Добавь YOUTUBE_API_KEY= в .env{RS}")
        sys.exit(1)
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def search_videos(yt, query, max_results=50, published_after=None, lang=None):
    """Ищет видео по запросу через YouTube Search API."""
    videos = []
    next_page = None
    fetched = 0

    while fetched < max_results:
        batch = min(50, max_results - fetched)
        params = {
            "part":       "snippet",
            "q":          query,
            "type":       "video",
            "maxResults": batch,
            "order":      "date",
        }
        if published_after:
            params["publishedAfter"] = published_after
        if lang:
            params["relevanceLanguage"] = lang
        if next_page:
            params["pageToken"] = next_page

        try:
            resp = yt.search().list(**params).execute()
            for item in resp.get("items", []):
                s = item["snippet"]
                vid_id = item["id"].get("videoId", "")
                if not vid_id:
                    continue
                videos.append({
                    "id":          vid_id,
                    "title":       s.get("title", ""),
                    "description": s.get("description", ""),  # короткое из search
                    "channel":     s.get("channelTitle", ""),
                    "channel_id":  s.get("channelId", ""),
                    "published":   s.get("publishedAt", "")[:10],
                    "url":         f"https://youtube.com/watch?v={vid_id}",
                })
                fetched += 1

            next_page = resp.get("nextPageToken")
            if not next_page or fetched >= max_results:
                break
            time.sleep(0.2)

        except Exception as e:
            if "quotaExceeded" in str(e):
                print(f"\n  {R}[✗] YouTube API quota exceeded{RS}")
                return videos, True  # quota_exceeded=True
            print(f"  {Y}[!] Search error: {e}{RS}")
            break

    return videos, False


def get_full_descriptions(yt, video_ids):
    """Получает полные описания видео (search API даёт только preview)."""
    full = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        try:
            resp = yt.videos().list(
                part="snippet",
                id=",".join(batch)
            ).execute()
            for item in resp.get("items", []):
                full[item["id"]] = item["snippet"].get("description", "")
            time.sleep(0.1)
        except Exception as e:
            if "quotaExceeded" in str(e):
                print(f"\n  {R}[✗] YouTube API quota exceeded{RS}")
                break
    return full


# ─── GOOGLE CUSTOM SEARCH ──────────────────────────────────────────────────────

def google_cse_search(query, num=10):
    """
    Ищет через Google Custom Search API.
    site:youtube.com с паттернами адресов.
    """
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_CX:
        return []

    try:
        r = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": GOOGLE_CSE_KEY,
                "cx":  GOOGLE_CSE_CX,
                "q":   query,
                "num": min(num, 10),
            },
            timeout=10
        )
        if r.status_code == 200:
            items = r.json().get("items", [])
            results = []
            for item in items:
                url = item.get("link", "")
                # Извлекаем video ID из URL
                vid_match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
                if vid_match:
                    results.append({
                        "id":          vid_match.group(1),
                        "title":       item.get("title", ""),
                        "description": item.get("snippet", ""),
                        "url":         url,
                        "channel":     "",
                        "published":   "",
                    })
            return results
        elif r.status_code == 429:
            print(f"  {Y}[!] Google CSE rate limit{RS}")
    except Exception as e:
        print(f"  {Y}[!] Google CSE error: {e}{RS}")
    return []


# ─── ПАРСЕР АДРЕСОВ ────────────────────────────────────────────────────────────

def extract_addresses(text, source_url="", channel="", title="", published=""):
    """Извлекает крипто-адреса из текста."""
    found = {}
    if not text:
        return found

    for chain_type, (pattern, chain_name) in PATTERNS.items():
        for addr in pattern.findall(text):
            # SOL — только длинные адреса (43-44 символа)
            if chain_type == "sol" and len(addr) < 43:
                continue

            if addr not in found:
                # Контекст вокруг адреса
                idx = text.find(addr)
                ctx = text[max(0, idx-50):idx+len(addr)+50].replace("\n", " ").strip()

                found[addr] = {
                    "chain":     chain_name,
                    "chain_key": chain_type,
                    "context":   ctx[:120],
                    "url":       source_url,
                    "channel":   channel,
                    "title":     title[:70],
                    "published": published,
                }

    return found


# ─── ДЕДУПЛИКАЦИЯ И СТАТИСТИКА ─────────────────────────────────────────────────

class AddressDatabase:
    def __init__(self, db_path="yt_monitor_db.json"):
        self.db_path = db_path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"addresses": {}, "videos_seen": [], "last_run": ""}

    def save(self):
        self.data["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def is_new_address(self, addr):
        return addr.lower() not in self.data["addresses"]

    def is_seen_video(self, vid_id):
        return vid_id in self.data["videos_seen"]

    def add_address(self, addr, info):
        key = addr.lower() if info["chain_key"] == "evm" else addr
        if key not in self.data["addresses"]:
            self.data["addresses"][key] = info
            return True
        return False

    def mark_video_seen(self, vid_id):
        if vid_id not in self.data["videos_seen"]:
            self.data["videos_seen"].append(vid_id)

    def get_stats(self):
        chains = {}
        for addr, info in self.data["addresses"].items():
            ch = info.get("chain", "?")
            chains[ch] = chains.get(ch, 0) + 1
        return {
            "total": len(self.data["addresses"]),
            "videos_seen": len(self.data["videos_seen"]),
            "by_chain": chains,
        }

    def export_custom_labels(self, out_path="custom_labels.json"):
        """Экспортирует в формат ARGUS custom_labels.json."""
        existing = {}
        if os.path.exists(out_path):
            try:
                with open(out_path, "r", encoding="utf-8") as f:
                    existing = {k: v for k, v in json.load(f).items()
                               if not k.startswith("_")}
            except Exception:
                pass

        new_count = 0
        for addr, info in self.data["addresses"].items():
            if addr not in existing:
                channel = info.get("channel", "Unknown Channel")
                existing[addr] = {
                    "name":     f"{channel} — {info.get('chain','?')}",
                    "category": "donation",
                    "risk":     "low",
                    "chain":    info.get("chain", ""),
                    "source":   info.get("url", ""),
                    "context":  info.get("context", "")[:80],
                    "added":    datetime.now().strftime("%Y-%m-%d"),
                }
                new_count += 1

        output = {
            "_comment": "YouTube monitor results. Edit name/category/risk as needed.",
            "_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        output.update(existing)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        return new_count


# ─── ПЕЧАТЬ ────────────────────────────────────────────────────────────────────

def print_banner():
    print(f"\n{G}{BR}")
    print("  ▓▓▓  ARGUS YOUTUBE GLOBAL MONITOR  ▓▓▓")
    print(f"  ▓▓▓  by VERES · Intelligence without borders  ▓▓▓{RS}\n")


def print_found(addr, info, is_new=True):
    tag = f"{G}[NEW]{RS}" if is_new else f"{DIM}[DUP]{RS}"
    chain_colors = {
        "EVM": C, "Bitcoin": Y, "Tron": R, "TON": G, "Solana": W
    }
    cc = chain_colors.get(info["chain"], W)
    print(f"  {tag} {cc}{addr[:20]}...{RS}  {DIM}{info['chain']}{RS}")
    print(f"       {DIM}Channel: {info['channel'][:40]}{RS}")
    print(f"       {DIM}Video  : {info['title'][:50]}{RS}")
    print(f"       {DIM}Context: {info['context'][:60]}{RS}")


def print_summary(db, new_found, queries_done, videos_processed):
    stats = db.get_stats()
    print(f"\n{G}╔{'═' * 62}╗")
    print(f"║{'MONITOR SESSION COMPLETE':^62}║")
    print(f"╚{'═' * 62}╝{RS}\n")
    print(f"  {DIM}Queries run     :{RS} {queries_done}")
    print(f"  {DIM}Videos scanned  :{RS} {videos_processed}")
    print(f"  {DIM}New addresses   :{RS} {G}{BR}{new_found}{RS}")
    print(f"  {DIM}Total in DB     :{RS} {stats['total']}")
    print()
    if stats["by_chain"]:
        print(f"  {DIM}By chain:{RS}")
        for chain, count in sorted(stats["by_chain"].items()):
            print(f"    {chain:<18} {count}")
    print()


# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ARGUS YouTube Global Monitor — ищет крипто-адреса по всему YouTube"
    )
    parser.add_argument("--lang", choices=["en", "ru", "all"], default="all",
                        help="Язык поиска (default: all)")
    parser.add_argument("--days", type=int, default=0,
                        help="Только видео за последние N дней (0 = все)")
    parser.add_argument("--max", type=int, default=50,
                        help="Видео на запрос (default: 50, max: 50)")
    parser.add_argument("--out", default="custom_labels.json",
                        help="Выходной файл custom_labels (default: custom_labels.json)")
    parser.add_argument("--db", default="yt_monitor_db.json",
                        help="База данных найденных адресов (default: yt_monitor_db.json)")
    parser.add_argument("--no-sol", action="store_true",
                        help="Не искать Solana (много ложных срабатываний)")
    parser.add_argument("--new-only", action="store_true",
                        help="Пропускать уже виденные видео")
    parser.add_argument("--queries-file",
                        help="JSON файл с дополнительными поисковыми запросами")
    args = parser.parse_args()

    print_banner()

    # Инициализация
    yt  = get_youtube_client()
    db  = AddressDatabase(args.db)

    # Дополнительные запросы из файла
    extra_queries = []
    if args.queries_file and os.path.exists(args.queries_file):
        try:
            with open(args.queries_file, "r", encoding="utf-8") as f:
                extra_queries = json.load(f)
            print(f"  {G}[✓]{RS} Loaded {len(extra_queries)} custom queries")
        except Exception:
            pass

    # Составляем список запросов
    queries = []
    if args.lang in ("en", "all"):
        queries += SEARCH_QUERIES["en"]
    if args.lang in ("ru", "all"):
        queries += SEARCH_QUERIES["ru"]
    queries += extra_queries

    # published_after для фильтра по дате
    published_after = None
    if args.days > 0:
        dt = datetime.now(timezone.utc) - timedelta(days=args.days)
        published_after = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"  {C}[*]{RS} Filtering: videos from last {args.days} days\n")

    stats_obj = db.get_stats()
    print(f"  {C}[*]{RS} DB loaded: {stats_obj['total']} addresses, "
          f"{stats_obj['videos_seen']} videos seen")
    print(f"  {C}[*]{RS} Running {len(queries)} search queries\n")

    # Счётчики
    total_new     = 0
    videos_total  = 0
    quota_hit     = False
    queries_done  = 0

    for i, query in enumerate(queries):
        if quota_hit:
            break

        print(f"  {G}[{i+1}/{len(queries)}]{RS} {DIM}\"{query}\"{RS}")

        # YouTube Search
        videos, quota_hit = search_videos(
            yt, query,
            max_results=args.max,
            published_after=published_after,
            lang=args.lang if args.lang != "all" else None
        )
        queries_done += 1

        if not videos:
            continue

        # Фильтруем уже виденные
        new_videos = [v for v in videos
                     if not (args.new_only and db.is_seen_video(v["id"]))]

        if not new_videos:
            print(f"         {DIM}All {len(videos)} videos already seen{RS}")
            continue

        # Получаем полные описания
        vid_ids = [v["id"] for v in new_videos]
        full_descs = get_full_descriptions(yt, vid_ids)

        found_in_query = 0
        for video in new_videos:
            db.mark_video_seen(video["id"])
            videos_total += 1

            # Берём полное описание если есть
            description = full_descs.get(video["id"], video["description"])

            # Парсим адреса
            addresses = extract_addresses(
                description,
                source_url=video["url"],
                channel=video["channel"],
                title=video["title"],
                published=video["published"],
            )

            # Фильтр SOL
            if args.no_sol:
                addresses = {k: v for k, v in addresses.items()
                            if v["chain_key"] != "sol"}

            for addr, info in addresses.items():
                is_new = db.add_address(addr, info)
                if is_new:
                    total_new += 1
                    found_in_query += 1
                    print_found(addr, info, is_new=True)

        if found_in_query:
            print(f"         {G}+{found_in_query} new addresses{RS}")
        else:
            print(f"         {DIM}0 new addresses in {len(new_videos)} videos{RS}")

        # Сохраняем после каждого запроса
        db.save()
        time.sleep(0.3)

        # Google CSE поиск дополнительно
        if GOOGLE_CSE_KEY and GOOGLE_CSE_CX and i < 10:
            cse_queries = [
                f'site:youtube.com "0x" "donate" "{query.split()[0]}"',
                f'site:youtube.com "bitcoin" "wallet" "{query.split()[0]}"',
            ]
            for cse_q in cse_queries[:1]:
                cse_results = google_cse_search(cse_q)
                for item in cse_results:
                    if db.is_seen_video(item["id"]):
                        continue
                    addresses = extract_addresses(
                        item["description"],
                        source_url=item["url"],
                        channel=item.get("channel", ""),
                        title=item["title"],
                    )
                    if args.no_sol:
                        addresses = {k: v for k, v in addresses.items()
                                    if v["chain_key"] != "sol"}
                    for addr, info in addresses.items():
                        if db.add_address(addr, info):
                            total_new += 1
                            print_found(addr, info, is_new=True)
                time.sleep(0.2)

    # Финальный экспорт
    db.save()
    new_exported = db.export_custom_labels(args.out)

    print_summary(db, total_new, queries_done, videos_total)

    if quota_hit:
        print(f"  {Y}[!] YouTube API quota exceeded — run again tomorrow{RS}\n")

    print(f"  {G}[✓]{RS} Database saved: {W}{BR}{args.db}{RS}")
    print(f"  {G}[✓]{RS} Custom labels:  {W}{BR}{args.out}{RS}")
    print(f"       {DIM}{new_exported} new addresses exported{RS}\n")


if __name__ == "__main__":
    main()
