"""
ARGUS — Public Address Database Updater
by VERES · Intelligence without borders

Автоматически скачивает и агрегирует публичные базы крипто-адресов.

Источники:
  [1] OFAC SDN          — санкционные адреса (ETH, BTC, TRX, SOL, LTC, XMR...)
  [2] OpenSanctions      — агрегатор: OFAC + EU + UN + UK OFSI + ещё 20+
  [3] Ransomwhere.co     — адреса вымогателей (ransomware)
  [4] MetaMask Phishing  — фишинговые ETH адреса
  [5] Etherscan Labels   — биржи, протоколы, известные кошельки
  [6] CryptoScamDB       — скам адреса

Использование:
  python3 argus_db_update.py                  # обновить всё
  python3 argus_db_update.py --sources ofac ransomwhere
  python3 argus_db_update.py --out my_labels.json
  python3 argus_db_update.py --merge          # слить с существующим custom_labels.json
"""

import os
import re
import sys
import json
import time
import argparse
import zipfile
import io
from datetime import datetime

import requests
from dotenv import load_dotenv
load_dotenv()

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

# ─── URLS ──────────────────────────────────────────────────────────────────────

SOURCES = {
    "ofac": {
        "name":  "OFAC SDN List",
        "desc":  "US Treasury sanctions — ETH, BTC, TRX, SOL, LTC, XMR",
        "risk":  "high",
        "category": "sanctions",
        "urls": {
            "ETH": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_ETH.txt",
            "BTC": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_XBT.txt",
            "TRX": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_TRX.txt",
            "SOL": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_SOL.txt",
            "LTC": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_LTC.txt",
            "XMR": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_XMR.txt",
        },
    },
    "opensanctions": {
        "name":  "OpenSanctions",
        "desc":  "OFAC + EU + UN + UK OFSI + 20 more lists",
        "risk":  "high",
        "category": "sanctions",
        "urls": {
            "API": "https://api.opensanctions.org/entities?schema=CryptoWallet&limit=500",
        },
    },
    "ransomwhere": {
        "name":  "Ransomwhere.co",
        "desc":  "Ransomware payment addresses with amounts",
        "risk":  "high",
        "category": "ransomware",
        "urls": {
            "export": "https://api.ransomwhe.re/export",
        },
    },
    "phishing": {
        "name":  "MetaMask Phishing Detect",
        "desc":  "Known ETH phishing addresses",
        "risk":  "high",
        "category": "phishing",
        "urls": {
            "config": "https://raw.githubusercontent.com/MetaMask/eth-phishing-detect/master/src/config.json",
        },
    },
    "labels": {
        "name":  "Etherscan Labels",
        "desc":  "Exchanges, DeFi protocols, known wallets (10k+ addresses)",
        "risk":  "low",
        "category": "exchange",
        "urls": {
            "combined": "https://raw.githubusercontent.com/brianleect/etherscan-labels/main/data/etherscan/combined/combinedLabels.json",
            "dawsbot":  "https://raw.githubusercontent.com/dawsbot/eth-labels/main/src/labels.json",
        },
    },
    "scam": {
        "name":  "CryptoScamDB",
        "desc":  "Known scam addresses",
        "risk":  "high",
        "category": "scam",
        "urls": {
            "addresses": "https://api.cryptoscamdb.org/v1/addresses",
        },
    },
}

# ─── ПАРСЕРЫ ───────────────────────────────────────────────────────────────────

def fetch(url, timeout=30):
    """Скачивает URL с retry."""
    headers = {"User-Agent": "ARGUS-OSINT/1.0 (VERES Intelligence)"}
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r
            elif r.status_code == 429:
                print(f"  {Y}[!] Rate limited, waiting 10s...{RS}")
                time.sleep(10)
            else:
                print(f"  {Y}[!] HTTP {r.status_code} for {url[:60]}{RS}")
                return None
        except Exception as e:
            if attempt == 2:
                print(f"  {R}[✗] Failed: {str(e)[:60]}{RS}")
            else:
                time.sleep(2)
    return None


def parse_ofac(source_cfg):
    """Парсит OFAC адреса из 0xB10C GitHub (plain text, один адрес в строке)."""
    results = {}
    for coin, url in source_cfg["urls"].items():
        r = fetch(url)
        if not r:
            continue
        count = 0
        for line in r.text.strip().split("\n"):
            addr = line.strip()
            if not addr or addr.startswith("#"):
                continue
            results[addr] = {
                "name":     f"OFAC SDN — {coin}",
                "category": "sanctions",
                "risk":     "high",
                "chain":    coin,
                "source":   "OFAC SDN List",
                "source_url": url,
            }
            count += 1
        print(f"    {G}✓{RS} OFAC {coin}: {count} addresses")
    return results


def parse_opensanctions(source_cfg):
    """Парсит OpenSanctions API — CryptoWallet entities."""
    results = {}
    url = source_cfg["urls"]["API"]

    # Пагинация
    offset = 0
    total_fetched = 0
    while True:
        r = fetch(f"{url}&offset={offset}")
        if not r:
            break
        try:
            data = r.json()
        except Exception:
            break

        items = data.get("results", [])
        if not items:
            break

        for entity in items:
            props  = entity.get("properties", {})
            addrs  = props.get("address", [])
            name   = (props.get("name") or [""])[0]
            datasets = entity.get("datasets", [])
            sources  = [d for d in datasets if d not in ("default", "sanctions")]
            src_str  = " + ".join(sources[:3]) if sources else "OpenSanctions"

            for addr in addrs:
                addr = addr.strip()
                if not addr:
                    continue
                results[addr] = {
                    "name":     f"SANCTIONED — {name or 'Entity'}",
                    "category": "sanctions",
                    "risk":     "high",
                    "source":   src_str,
                    "source_url": "https://opensanctions.org",
                }
                total_fetched += 1

        # Следующая страница
        if len(items) < 500:
            break
        offset += 500
        time.sleep(0.3)

    print(f"    {G}✓{RS} OpenSanctions: {total_fetched} addresses")
    return results


def parse_ransomwhere(source_cfg):
    """Парсит Ransomwhere.co — BTC/ETH адреса вымогателей."""
    results = {}
    r = fetch(source_cfg["urls"]["export"])
    if not r:
        return results
    try:
        data = r.json()
        # Формат: {"result": [{"address": "...", "blockchain": "bitcoin", "family": "WannaCry", ...}]}
        items = data.get("result", [])
        for item in items:
            addr    = item.get("address", "").strip()
            family  = item.get("family", "Unknown")
            blockchain = item.get("blockchain", "")
            total   = item.get("totalAmountReceived", 0)
            if not addr:
                continue
            results[addr] = {
                "name":     f"Ransomware — {family}",
                "category": "ransomware",
                "risk":     "high",
                "chain":    blockchain.capitalize(),
                "source":   "Ransomwhere.co",
                "source_url": "https://ransomwhe.re",
                "context":  f"Total received: {total:.4f}",
            }
        print(f"    {G}✓{RS} Ransomwhere: {len(results)} addresses")
    except Exception as e:
        print(f"    {Y}[!] Parse error: {e}{RS}")
    return results


def parse_phishing(source_cfg):
    """Парсит MetaMask phishing detect — ETH адреса фишинга."""
    results = {}
    r = fetch(source_cfg["urls"]["config"])
    if not r:
        return results
    try:
        data = r.json()
        # Формат: {"blacklist": ["domain.com", "0xADDR", ...], ...}
        blacklist = data.get("blacklist", [])
        eth_pattern = re.compile(r'^0x[a-fA-F0-9]{40}$')
        count = 0
        for entry in blacklist:
            if eth_pattern.match(entry):
                results[entry.lower()] = {
                    "name":     "Phishing Address",
                    "category": "phishing",
                    "risk":     "high",
                    "chain":    "EVM",
                    "source":   "MetaMask Phishing Detect",
                    "source_url": "https://github.com/MetaMask/eth-phishing-detect",
                }
                count += 1
        print(f"    {G}✓{RS} MetaMask phishing: {count} ETH addresses")
    except Exception as e:
        print(f"    {Y}[!] Parse error: {e}{RS}")
    return results


def parse_labels(source_cfg):
    """Парсит Etherscan labels — биржи, протоколы, known wallets."""
    results = {}

    # Source 1: brianleect/etherscan-labels
    r = fetch(source_cfg["urls"]["combined"])
    if r:
        try:
            data = r.json()
            count = 0
            for addr, info in data.items():
                name   = info.get("nameTag") or info.get("name") or ""
                labels = info.get("labels", [])
                cat    = labels[0] if labels else "entity"
                if not name:
                    continue
                # Определяем риск по категории
                risk = "high" if any(x in cat.lower() for x in ["mixer", "hack", "scam", "exploit"]) else "low"
                results[addr.lower()] = {
                    "name":     name,
                    "category": cat,
                    "risk":     risk,
                    "chain":    "EVM",
                    "source":   "Etherscan Labels",
                    "source_url": "https://etherscan.io",
                }
                count += 1
            print(f"    {G}✓{RS} Etherscan labels (brianleect): {count} addresses")
        except Exception as e:
            print(f"    {Y}[!] Parse error: {e}{RS}")

    # Source 2: dawsbot/eth-labels
    r2 = fetch(source_cfg["urls"]["dawsbot"])
    if r2:
        try:
            data2 = r2.json()
            count2 = 0
            # Формат может отличаться — проверяем структуру
            if isinstance(data2, dict):
                for addr, info in data2.items():
                    if isinstance(info, dict):
                        name = info.get("label") or info.get("name") or ""
                    else:
                        name = str(info)
                    if name and addr.startswith("0x"):
                        key = addr.lower()
                        if key not in results:
                            results[key] = {
                                "name":     name,
                                "category": "entity",
                                "risk":     "low",
                                "chain":    "EVM",
                                "source":   "eth-labels (dawsbot)",
                                "source_url": "https://github.com/dawsbot/eth-labels",
                            }
                            count2 += 1
            print(f"    {G}✓{RS} eth-labels (dawsbot): {count2} new addresses")
        except Exception as e:
            print(f"    {Y}[!] Parse error: {e}{RS}")

    return results


def parse_scam(source_cfg):
    """Парсит CryptoScamDB."""
    results = {}
    r = fetch(source_cfg["urls"]["addresses"])
    if not r:
        return results
    try:
        data = r.json()
        # Формат: {"success": true, "result": {"0xADDR": {"type": "scam", ...}, ...}}
        entries = data.get("result", {})
        count = 0
        for addr, info in entries.items():
            if not addr.startswith("0x"):
                continue
            scam_type = info.get("type", "scam") if isinstance(info, dict) else "scam"
            results[addr.lower()] = {
                "name":     f"Scam — {scam_type}",
                "category": "scam",
                "risk":     "high",
                "chain":    "EVM",
                "source":   "CryptoScamDB",
                "source_url": "https://cryptoscamdb.org",
            }
            count += 1
        print(f"    {G}✓{RS} CryptoScamDB: {count} addresses")
    except Exception as e:
        print(f"    {Y}[!] Parse error: {e}{RS}")
    return results


PARSERS = {
    "ofac":          parse_ofac,
    "opensanctions": parse_opensanctions,
    "ransomwhere":   parse_ransomwhere,
    "phishing":      parse_phishing,
    "labels":        parse_labels,
    "scam":          parse_scam,
}

# ─── ЭКСПОРТ ───────────────────────────────────────────────────────────────────

def save_db(all_data, db_path):
    """Сохраняет полную базу данных."""
    output = {
        "_meta": {
            "updated":  datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total":    len(all_data),
            "sources":  list(set(v.get("source","?") for v in all_data.values())),
        }
    }
    output.update(all_data)
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    return len(all_data)


def export_custom_labels(all_data, out_path, merge_path=None):
    """
    Экспортирует в формат ARGUS custom_labels.json.
    Если merge_path указан — мержит с существующим файлом.
    """
    existing = {}
    if merge_path and os.path.exists(merge_path):
        try:
            with open(merge_path, "r", encoding="utf-8") as f:
                existing = {k: v for k, v in json.load(f).items()
                           if not k.startswith("_")}
            print(f"  {C}[*]{RS} Merging with existing: {len(existing)} entries")
        except Exception:
            pass

    new_count = 0
    updated_count = 0
    for addr, info in all_data.items():
        if addr not in existing:
            existing[addr] = {
                "name":     info.get("name", "Unknown"),
                "category": info.get("category", "unknown"),
                "risk":     info.get("risk", "low"),
                "chain":    info.get("chain", ""),
                "source":   info.get("source", ""),
                "added":    datetime.now().strftime("%Y-%m-%d"),
            }
            new_count += 1
        else:
            # Обновляем риск если новый источник говорит HIGH
            if info.get("risk") == "high" and existing[addr].get("risk") != "high":
                existing[addr]["risk"] = "high"
                existing[addr]["source"] = info.get("source", existing[addr]["source"])
                updated_count += 1

    output = {
        "_comment": "ARGUS address database. Edit name/category/risk as needed.",
        "_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "_total":   len(existing),
        "_sources": list(set(v.get("source","?") for v in all_data.values())),
    }
    output.update(existing)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return new_count, updated_count


def print_stats(all_data):
    """Печатает статистику по источникам и категориям."""
    by_source = {}
    by_category = {}
    by_risk = {"high": 0, "low": 0}

    for addr, info in all_data.items():
        src = info.get("source", "?")
        cat = info.get("category", "?")
        risk = info.get("risk", "low")
        by_source[src]   = by_source.get(src, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1
        by_risk[risk]    = by_risk.get(risk, 0) + 1

    print(f"\n{G}╔{'═' * 62}╗")
    print(f"║{'DATABASE UPDATE COMPLETE':^62}║")
    print(f"╚{'═' * 62}╝{RS}\n")

    print(f"  {DIM}Total addresses :{RS} {G}{BR}{len(all_data)}{RS}\n")

    print(f"  {DIM}By risk:{RS}")
    print(f"    {R}HIGH{RS}  : {by_risk.get('high', 0)}")
    print(f"    {G}LOW{RS}   : {by_risk.get('low', 0)}")

    print(f"\n  {DIM}By category:{RS}")
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        bar = "▓" * min(20, count // max(1, len(all_data) // 20))
        print(f"    {cat:<20} {count:>6}  {G}{bar}{RS}")

    print(f"\n  {DIM}By source:{RS}")
    for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"    {src:<35} {count:>6}")
    print()


# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ARGUS DB Updater — скачивает публичные базы крипто-адресов"
    )
    parser.add_argument("--sources", nargs="+",
                        choices=list(SOURCES.keys()) + ["all"],
                        default=["all"],
                        help="Источники для обновления (default: all)")
    parser.add_argument("--out", default="custom_labels.json",
                        help="Выходной файл custom_labels (default: custom_labels.json)")
    parser.add_argument("--db", default="argus_address_db.json",
                        help="Полная база данных (default: argus_address_db.json)")
    parser.add_argument("--merge", action="store_true",
                        help="Слить с существующим custom_labels.json")
    parser.add_argument("--list", action="store_true",
                        help="Показать список источников")
    args = parser.parse_args()

    print(f"\n{G}{BR}")
    print("  ▓▓▓  ARGUS DATABASE UPDATER  ▓▓▓")
    print(f"  ▓▓▓  by VERES · Intelligence without borders  ▓▓▓{RS}\n")

    # Показать источники
    if args.list:
        print(f"  {W}{BR}Available sources:{RS}\n")
        for key, src in SOURCES.items():
            print(f"  {G}{key:<20}{RS} {src['name']}")
            print(f"  {DIM}{'':20} {src['desc']}{RS}")
            print(f"  {DIM}{'':20} Risk: {src['risk']} · Category: {src['category']}{RS}\n")
        return

    # Определяем какие источники запускать
    selected = list(SOURCES.keys()) if "all" in args.sources else args.sources

    print(f"  {C}[*]{RS} Sources: {', '.join(selected)}\n")

    all_data = {}

    for source_key in selected:
        src_cfg = SOURCES[source_key]
        print(f"  {G}[▓▓▓▓▓]{RS} {W}{BR}{src_cfg['name']}{RS}")
        print(f"  {DIM}  {src_cfg['desc']}{RS}")

        parser_fn = PARSERS.get(source_key)
        if not parser_fn:
            print(f"  {Y}[!] No parser for {source_key}{RS}")
            continue

        try:
            results = parser_fn(src_cfg)
            all_data.update(results)
            print(f"  {DIM}  Subtotal: {len(results)} addresses{RS}\n")
        except Exception as e:
            print(f"  {R}[✗] Error in {source_key}: {e}{RS}\n")

        time.sleep(0.5)

    if not all_data:
        print(f"  {Y}[!] No data collected — check your internet connection{RS}\n")
        return

    # Статистика
    print_stats(all_data)

    # Сохраняем полную БД
    total = save_db(all_data, args.db)
    print(f"  {G}[✓]{RS} Full database saved: {W}{BR}{args.db}{RS}  ({total} entries)")

    # Экспортируем custom_labels
    merge_path = args.out if args.merge else None
    new_count, updated_count = export_custom_labels(all_data, args.out, merge_path)
    print(f"  {G}[✓]{RS} Custom labels saved: {W}{BR}{args.out}{RS}")
    print(f"  {DIM}    {new_count} new · {updated_count} updated{RS}\n")

    print(f"  {C}[*]{RS} Use {W}custom_labels.json{RS} with ARGUS for enriched attribution\n")


if __name__ == "__main__":
    main()
