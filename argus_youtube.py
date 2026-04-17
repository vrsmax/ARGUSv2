"""
ARGUS — YouTube Channel Address Parser
by VERES · Intelligence without borders

Парсит крипто-адреса из описаний видео YouTube канала.
На выходе — готовый custom_labels.json для ARGUS.

Использование:
  python3 argus_youtube.py @channelhandle
  python3 argus_youtube.py UCxxxxxxxxxxxxxxxxxxxxxx
  python3 argus_youtube.py @channelhandle --max 50
  python3 argus_youtube.py @channelhandle --comments
"""

import os
import re
import sys
import json
import time
import argparse
from datetime import datetime

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

from dotenv import load_dotenv
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# ─── REGEX ПАТТЕРНЫ ────────────────────────────────────────────────────────────

PATTERNS = {
    "evm":  re.compile(r'\b0x[a-fA-F0-9]{40}\b'),
    "btc_legacy": re.compile(r'\b1[a-km-zA-HJ-NP-Z1-9]{25,33}\b'),
    "btc_p2sh":   re.compile(r'\b3[a-km-zA-HJ-NP-Z1-9]{25,33}\b'),
    "btc_bech32": re.compile(r'\bbc1[a-z0-9]{6,87}\b'),
    "trx":  re.compile(r'\bT[a-zA-Z0-9]{33}\b'),
    "ton":  re.compile(r'\b(?:EQ|UQ)[a-zA-Z0-9_\-]{45,46}\b'),
    "sol":  re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'),
}

# Цепи для определения сети
CHAIN_MAP = {
    "evm":        "EVM (ETH/BSC/...)",
    "btc_legacy": "Bitcoin",
    "btc_p2sh":   "Bitcoin",
    "btc_bech32": "Bitcoin",
    "trx":        "Tron",
    "ton":        "TON",
    "sol":        "Solana",
}

# Слова-маркеры рядом с адресом — повышают уверенность что это донат
DONATE_KEYWORDS = [
    "donate", "donation", "support", "tip", "wallet",
    "btc", "eth", "crypto", "bitcoin", "ethereum", "usdt",
    "донат", "поддержать", "кошелёк", "пожертвование",
    "trc20", "erc20", "bep20",
]


# ─── YOUTUBE API ───────────────────────────────────────────────────────────────

def get_youtube_client():
    if not HAS_YOUTUBE:
        print(f"{R}[✗] Установи: pip install google-api-python-client{RS}")
        sys.exit(1)
    if not YOUTUBE_API_KEY:
        print(f"{R}[✗] Добавь YOUTUBE_API_KEY= в .env файл{RS}")
        print(f"{DIM}    Получить ключ: console.cloud.google.com → YouTube Data API v3{RS}")
        sys.exit(1)
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def resolve_channel_id(yt, handle_or_id):
    """Определяет channel ID по @handle или возвращает как есть."""
    if handle_or_id.startswith("UC") and len(handle_or_id) == 24:
        return handle_or_id

    # Убираем @ если есть
    handle = handle_or_id.lstrip("@")

    try:
        # Новый способ через forHandle
        resp = yt.channels().list(
            part="id,snippet",
            forHandle=handle
        ).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["id"]
    except Exception:
        pass

    # Fallback через search
    try:
        resp = yt.search().list(
            part="snippet",
            q=handle,
            type="channel",
            maxResults=1
        ).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["snippet"]["channelId"]
    except Exception:
        pass

    return None


def get_channel_info(yt, channel_id):
    """Получает базовую информацию о канале."""
    try:
        resp = yt.channels().list(
            part="snippet,statistics",
            id=channel_id
        ).execute()
        items = resp.get("items", [])
        if items:
            ch = items[0]
            return {
                "title":       ch["snippet"]["title"],
                "description": ch["snippet"].get("description", ""),
                "subscribers": ch["statistics"].get("subscriberCount", "?"),
                "videos":      ch["statistics"].get("videoCount", "?"),
            }
    except Exception:
        pass
    return {}


def get_video_ids(yt, channel_id, max_videos=100):
    """Получает список ID видео канала."""
    video_ids = []
    next_page = None

    while len(video_ids) < max_videos:
        batch = min(50, max_videos - len(video_ids))
        params = {
            "part":       "id",
            "channelId":  channel_id,
            "type":       "video",
            "maxResults": batch,
            "order":      "date",
        }
        if next_page:
            params["pageToken"] = next_page

        try:
            resp = yt.search().list(**params).execute()
            for item in resp.get("items", []):
                vid_id = item.get("id", {}).get("videoId")
                if vid_id:
                    video_ids.append(vid_id)
            next_page = resp.get("nextPageToken")
            if not next_page:
                break
            time.sleep(0.1)
        except Exception as e:
            print(f"{Y}[!] API error: {e}{RS}")
            break

    return video_ids


def get_video_details(yt, video_ids):
    """Получает description и title для списка видео (батчами по 50)."""
    videos = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        try:
            resp = yt.videos().list(
                part="snippet",
                id=",".join(batch)
            ).execute()
            for item in resp.get("items", []):
                s = item["snippet"]
                videos.append({
                    "id":          item["id"],
                    "title":       s.get("title", ""),
                    "description": s.get("description", ""),
                    "published":   s.get("publishedAt", "")[:10],
                    "url":         f"https://youtube.com/watch?v={item['id']}",
                })
            time.sleep(0.1)
        except Exception as e:
            print(f"{Y}[!] Batch error: {e}{RS}")
    return videos


def get_pinned_comments(yt, video_ids, max_per_video=1):
    """Получает закреплённые комментарии (где часто размещают адреса)."""
    comments = []
    for vid_id in video_ids[:50]:  # Лимит запросов
        try:
            resp = yt.commentThreads().list(
                part="snippet",
                videoId=vid_id,
                maxResults=max_per_video,
                order="relevance"
            ).execute()
            for item in resp.get("items", []):
                top = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "video_id": vid_id,
                    "text":     top.get("textDisplay", ""),
                    "author":   top.get("authorDisplayName", ""),
                })
            time.sleep(0.05)
        except Exception:
            pass
    return comments


# ─── ПАРСЕР АДРЕСОВ ────────────────────────────────────────────────────────────

def extract_addresses(text, source_url="", source_title=""):
    """Извлекает крипто-адреса из текста с контекстом."""
    found = {}  # addr -> info

    text_lower = text.lower()
    has_donate_context = any(kw in text_lower for kw in DONATE_KEYWORDS)

    for chain_type, pattern in PATTERNS.items():
        matches = pattern.findall(text)
        for addr in matches:
            # Для SOL — фильтруем слишком короткие и похожие на BTC
            if chain_type == "sol":
                if len(addr) < 32:
                    continue
                # Пропускаем если уже нашли как BTC
                if addr in found:
                    continue
                # Фильтр мусора — слова из текста попадают под SOL regex
                if addr.lower() in ["description", "subscribe", "donation", "bitcoins"]:
                    continue

            if addr not in found:
                # Берём контекст вокруг адреса (50 символов до и после)
                idx = text.find(addr)
                ctx_start = max(0, idx - 60)
                ctx_end = min(len(text), idx + len(addr) + 60)
                context = text[ctx_start:ctx_end].replace("\n", " ").strip()

                found[addr] = {
                    "chain":       CHAIN_MAP.get(chain_type, chain_type),
                    "chain_type":  chain_type,
                    "context":     context[:120],
                    "source_url":  source_url,
                    "source_title": source_title[:60],
                    "donate_context": has_donate_context,
                }

    return found


def is_likely_real_address(addr, chain_type):
    """Простая фильтрация мусора."""
    # SOL адреса часто ложные срабатывания на обычные слова
    if chain_type == "sol":
        # Реальные SOL адреса обычно 43-44 символа
        if len(addr) < 40:
            return False
        # Если содержит только строчные буквы и цифры — подозрительно
        if addr == addr.lower() and len(addr) < 43:
            return False
    return True


# ─── ВЫВОД И ЭКСПОРТ ───────────────────────────────────────────────────────────

def print_results(all_addresses, channel_info, stats):
    print(f"\n{G}╔{'═' * 62}╗")
    print(f"║{'ARGUS YOUTUBE PARSER — RESULTS':^62}║")
    print(f"╚{'═' * 62}╝{RS}\n")

    print(f"  {DIM}Channel  :{RS} {W}{BR}{channel_info.get('title', '?')}{RS}")
    print(f"  {DIM}Videos   :{RS} {stats['videos_scanned']} scanned / {channel_info.get('videos','?')} total")
    print(f"  {DIM}Found    :{RS} {G}{BR}{len(all_addresses)} unique addresses{RS}\n")

    if not all_addresses:
        print(f"  {Y}No crypto addresses found{RS}\n")
        return

    # Группируем по сети
    by_chain = {}
    for addr, info in all_addresses.items():
        chain = info["chain"]
        if chain not in by_chain:
            by_chain[chain] = []
        by_chain[chain].append((addr, info))

    for chain, items in sorted(by_chain.items()):
        print(f"  {G}{BR}── {chain} ({len(items)}) ──{RS}")
        for addr, info in items:
            donate_mark = f" {G}[donate context]{RS}" if info["donate_context"] else ""
            print(f"  {C}{addr}{RS}{donate_mark}")
            print(f"    {DIM}{info['context'][:80]}{RS}")
            print(f"    {DIM}↳ {info['source_url']}{RS}")
        print()


def export_custom_labels(all_addresses, channel_info, output_path):
    """Экспортирует адреса в формат custom_labels.json для ARGUS."""
    channel_name = channel_info.get("title", "Unknown Channel")

    # Загружаем существующий файл если есть
    existing = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                # Убираем служебные ключи
                existing = {k: v for k, v in existing.items()
                           if not k.startswith("_")}
        except Exception:
            pass

    new_count = 0
    for addr, info in all_addresses.items():
        addr_lower = addr.lower() if info["chain_type"] == "evm" else addr
        if addr_lower not in existing:
            existing[addr_lower] = {
                "name":     f"{channel_name} — {info['chain']}",
                "category": "donation",
                "risk":     "low",
                "chain":    info["chain"],
                "source":   info["source_url"],
                "context":  info["context"][:80],
                "added":    datetime.now().strftime("%Y-%m-%d"),
            }
            new_count += 1
        else:
            # Обновляем только source если адрес уже есть
            existing[addr_lower]["source"] = info["source_url"]

    # Добавляем служебный комментарий
    output = {
        "_comment": "Пользовательская база адресов для ARGUS. Редактируй name/category/risk.",
        "_format":  "{\"address\": {\"name\": \"...\", \"category\": \"...\", \"risk\": \"low|high\"}}",
        "_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    output.update(existing)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return new_count


# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ARGUS YouTube Parser — собирает крипто-адреса с YouTube канала"
    )
    parser.add_argument("channel", help="YouTube канал: @handle или UCxxxxxx")
    parser.add_argument("--max", type=int, default=100,
                        help="Максимум видео для парсинга (default: 100)")
    parser.add_argument("--comments", action="store_true",
                        help="Парсить закреплённые комментарии")
    parser.add_argument("--out", default="custom_labels.json",
                        help="Выходной файл (default: custom_labels.json)")
    parser.add_argument("--no-sol", action="store_true",
                        help="Не искать Solana адреса (много ложных срабатываний)")
    args = parser.parse_args()

    print(f"\n{G}{BR}")
    print("  ▓▓▓  ARGUS YOUTUBE PARSER  ▓▓▓")
    print(f"  ▓▓▓  by VERES · Intelligence without borders  ▓▓▓{RS}\n")

    yt = get_youtube_client()

    # Резолвим канал
    print(f"  {C}[*]{RS} Resolving channel: {args.channel}")
    channel_id = resolve_channel_id(yt, args.channel)
    if not channel_id:
        print(f"  {R}[✗] Channel not found: {args.channel}{RS}")
        sys.exit(1)

    channel_info = get_channel_info(yt, channel_id)
    print(f"  {G}[✓]{RS} Channel: {W}{BR}{channel_info.get('title', channel_id)}{RS}")
    print(f"  {DIM}    Subscribers: {channel_info.get('subscribers','?')} · Videos: {channel_info.get('videos','?')}{RS}\n")

    # Проверяем адреса в описании самого канала
    all_addresses = {}
    channel_desc = channel_info.get("description", "")
    if channel_desc:
        found = extract_addresses(channel_desc, f"https://youtube.com/@{args.channel}", "Channel Description")
        if found:
            print(f"  {G}[✓]{RS} Found {len(found)} address(es) in channel description")
            all_addresses.update(found)

    # Получаем видео
    print(f"  {C}[*]{RS} Fetching video list (max {args.max})...")
    video_ids = get_video_ids(yt, channel_id, max_videos=args.max)
    print(f"  {G}[✓]{RS} Got {len(video_ids)} videos\n")

    # Парсим описания
    print(f"  {C}[*]{RS} Scanning video descriptions...")
    videos = get_video_details(yt, video_ids)

    for i, video in enumerate(videos):
        found = extract_addresses(
            video["description"],
            video["url"],
            video["title"]
        )
        if found:
            # Фильтрация SOL если запрошено
            if args.no_sol:
                found = {k: v for k, v in found.items() if v["chain_type"] != "sol"}
            all_addresses.update(found)
            print(f"  {G}▓{RS} [{i+1}/{len(videos)}] {video['title'][:50]} — {G}{len(found)} addr{RS}")
        elif (i+1) % 10 == 0:
            print(f"  {DIM}  [{i+1}/{len(videos)}] scanned...{RS}")

    # Парсим комментарии если нужно
    if args.comments:
        print(f"\n  {C}[*]{RS} Scanning pinned comments...")
        comments = get_pinned_comments(yt, video_ids)
        for comment in comments:
            found = extract_addresses(
                comment["text"],
                f"https://youtube.com/watch?v={comment['video_id']}",
                f"Comment by {comment['author']}"
            )
            if found:
                if args.no_sol:
                    found = {k: v for k, v in found.items() if v["chain_type"] != "sol"}
                all_addresses.update(found)

    stats = {"videos_scanned": len(videos)}

    # Выводим результаты
    print_results(all_addresses, channel_info, stats)

    if not all_addresses:
        print(f"  {Y}[!] No addresses found — nothing to export{RS}\n")
        return

    # Экспортируем
    new_count = export_custom_labels(all_addresses, channel_info, args.out)
    print(f"  {G}[✓]{RS} Exported to: {W}{BR}{args.out}{RS}")
    print(f"  {DIM}    {new_count} new addresses added{RS}")
    print(f"  {DIM}    Total in file: {len(all_addresses)} addresses{RS}\n")
    print(f"  {C}[*]{RS} Now run ARGUS with the updated custom_labels.json\n")


if __name__ == "__main__":
    main()
