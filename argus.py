"""
ARGUS — Crypto Address Intelligence Engine
by VERES · Intelligence without borders
v0.2 — Multichain
"""

import os
import re
import sys
import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import pyfiglet
    HAS_FIGLET = True
except ImportError:
    HAS_FIGLET = False

# ─── COLORS ────────────────────────────────────────────────────────────────────
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    G  = Fore.GREEN
    LG = Fore.LIGHTGREEN_EX
    Y  = Fore.YELLOW
    R  = Fore.RED
    LR = Fore.LIGHTRED_EX
    C  = Fore.CYAN
    W  = Fore.WHITE
    DIM = Style.DIM
    BR  = Style.BRIGHT
    RS  = Style.RESET_ALL
    HAS_COLOR = True
except ImportError:
    G = LG = Y = R = LR = C = W = DIM = BR = RS = ""
    HAS_COLOR = False

# ─── CONFIG ────────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()
ETHERSCAN_API = os.getenv("ETHERSCAN_API_KEY", "")

# Etherscan V2 — один ключ, все EVM сети через chainid
ETHERSCAN_URL = "https://api.etherscan.io/v2/api"

# EVM цепи: chainid -> отображаемое имя и тикер
EVM_CHAINS = {
    "1":       {"name": "Ethereum",    "ticker": "ETH"},
    "56":      {"name": "BNB Chain",   "ticker": "BNB"},
    "137":     {"name": "Polygon",     "ticker": "MATIC"},
    "42161":   {"name": "Arbitrum",    "ticker": "ETH"},
    "8453":    {"name": "Base",        "ticker": "ETH"},
}

# Публичные API без ключа
BTC_API     = "https://blockstream.info/api"
TRX_API     = "https://api.trongrid.io"
SOL_RPC     = "https://api.mainnet-beta.solana.com"
TON_API     = "https://toncenter.com/api/v2"

# Attribution / Label databases
LABEL_DB_URL = "https://raw.githubusercontent.com/brianleect/etherscan-labels/main/data/etherscan/combined/combinedLabels.json"

# OpenSanctions — агрегатор всех санкционных списков (OFAC + EU + UN + UK + ещё 20+)
# GitHub releases обновляются автоматически
OPENSANCTIONS_ETH_URL = "https://github.com/opensanctions/opensanctions/releases/latest/download/targets.simple.csv"
# Fallback — конкретный датасет криптоадресов
OPENSANCTIONS_CRYPTO_URL = "https://data.opensanctions.org/datasets/latest/sanctions/targets.simple.csv"

# OFAC
OFAC_ETH_LIST_URL = "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_ETH.txt"
OFAC_XML_URL      = "https://www.treasury.gov/ofac/downloads/sanctions/1.0/sdn_advanced.xml"


# ─── BANNER ────────────────────────────────────────────────────────────────────

def print_banner():
    # Коринфский шлем
    helmet = [
        r"                     (    )",
        r"                  (    ()   )",
        r"               .-( ()   ()   )-.",
        r"              /  ( ()   ()   )  \ ",
        r"             /.-. \          / .-. \ ",
        r"            /'/  \ \        / /  \' \ ",
        r"           | |    \ \______/ /    | |",
        r"           |=|     \========/     |=|",
        r"            \|      |      |      |/",
        r"             \      |______|      /",
        r"              \___/  |    |  \___/",
        r"                    | |  | |",
        r"                    | |  | |",
        r"                    |_|  |_|",
    ]

    if HAS_FIGLET:
        title = pyfiglet.figlet_format("ARGUS", font="roman")
    else:
        title = (
            "      .o.       ooooooooo.     .oooooo.    ooooo     ooo  .oooooo..o \n"
            "     .888.      `888   `Y88.  d8P'  `Y8b   `888'     `8' d8P'    `Y8\n"
            "    .8\"888.      888   .d88' 888            888       8  Y88bo.      \n"
            "   .8' `888.     888ooo88P'  888            888       8   `\"Y8888o.  \n"
            "  .88ooo8888.    888`88b.    888     ooooo  888       8       `\"Y88b \n"
            " .8'     `888.   888  `88b.  `88.    .88'   `88.    .8'  oo     .d8P \n"
            "o88o     o8888o o888o  o888o  `Y8bood8P'      `YbodP'    8\"\"88888P'  \n"
        )

    meander = "▓░" * 32

    print()
    # Шлем и заголовок рядом
    helmet_w = 38
    title_lines = title.rstrip().split("\n")
    # Центрируем шлем
    for line in helmet:
        print(f"{G}{BR}  {line}{RS}")
    print()
    for line in title_lines:
        print(f"{G}{BR}{line}{RS}")
    print()
    print(f"{G}{DIM}  {meander}{RS}")
    print(f"{G}  ▓▓▓  CRYPTO ADDRESS INTELLIGENCE ENGINE  ▓▓▓")
    print(f"  ▓▓▓  by VERES · Intelligence without borders  ▓▓▓{RS}")
    print(f"{G}{DIM}  {meander}{RS}")
    print()


def print_divider(label=""):
    width = 62
    if label:
        side = (width - len(label) - 2) // 2
        print(f"{G}{DIM}  {'─' * side} {W}{BR}{label}{RS}{G}{DIM} {'─' * side}{RS}")
    else:
        print(f"{G}{DIM}  {'─' * width}{RS}")


def print_status(msg, status="info"):
    icons = {
        "info":     f"{C}[*]{RS}",
        "ok":       f"{G}[✓]{RS}",
        "warn":     f"{Y}[!]{RS}",
        "error":    f"{R}[✗]{RS}",
        "scan":     f"{G}[>]{RS}",
        "critical": f"{LR}{BR}[!!!]{RS}",
    }
    icon = icons.get(status, icons["info"])
    print(f"  {icon} {msg}")


def loading_animation(msg, duration=0.8):
    frames = ["▓░░░░", "▓▓░░░", "▓▓▓░░", "▓▓▓▓░", "▓▓▓▓▓"]
    for frame in frames:
        print(f"\r  {G}[{frame}]{RS} {msg}...", end="", flush=True)
        time.sleep(duration / len(frames))
    print(f"\r  {G}[▓▓▓▓▓]{RS} {msg} {G}done{RS}     ")


def format_val(val, ticker=""):
    """Форматирует значение без научной нотации."""
    if val == 0:
        return f"0.0 {ticker}".strip()
    elif val < 0.0001:
        return f"{val:.8f} {ticker}".strip()
    elif val < 1:
        return f"{val:.6f} {ticker}".strip()
    else:
        return f"{val:.4f} {ticker}".strip()


# ─── АВТО-ДЕТЕКТОР СЕТИ ────────────────────────────────────────────────────────

def detect_chain(address):
    """
    Определяет тип сети по формату адреса.
    Возвращает: 'evm' | 'btc' | 'trx' | 'sol' | 'ton' | None
    """
    a = address.strip()

    # EVM: 0x + 40 hex символов (ETH, BSC, Polygon, Arbitrum, Base)
    if re.match(r'^0x[a-fA-F0-9]{40}$', a):
        return 'evm'

    # TON: user-friendly начинается с EQ/UQ, всего 48 символов (EQ + 46 или UQ + 46 → итого 48, но EQ=2, остаток 45)
    if re.match(r'^(EQ|UQ)[a-zA-Z0-9_\-]{45,46}$', a):
        return 'ton'
    # TON raw format: 0: + hex
    if re.match(r'^0:[a-fA-F0-9]{64}$', a):
        return 'ton'

    # TRX: начинается с T, 34 символа base58
    if re.match(r'^T[a-zA-Z0-9]{33}$', a):
        return 'trx'

    # BTC bech32: bc1...
    if re.match(r'^bc1[a-z0-9]{6,87}$', a):
        return 'btc'
    # BTC legacy P2PKH: начинается с 1
    if re.match(r'^1[a-km-zA-HJ-NP-Z1-9]{25,33}$', a):
        return 'btc'
    # BTC P2SH: начинается с 3
    if re.match(r'^3[a-km-zA-HJ-NP-Z1-9]{25,33}$', a):
        return 'btc'

    # SOL: base58, 32-44 символа (проверяем после BTC чтобы не было конфликта)
    if re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a):
        return 'sol'

    return None


# ─── EVM (ETH / BSC / POLYGON / ARBITRUM / BASE) ──────────────────────────────

def evm_get_balance(address, chainid):
    """Баланс через Etherscan V2 API."""
    if not ETHERSCAN_API:
        return None
    try:
        params = {
            "chainid": chainid, "module": "account", "action": "balance",
            "address": address, "tag": "latest", "apikey": ETHERSCAN_API
        }
        r = requests.get(ETHERSCAN_URL, params=params, timeout=10)
        data = r.json()
        if data.get("status") == "1":
            return int(data["result"]) / 1e18
    except Exception:
        pass

    # Fallback: public RPC для ETH (chainid=1)
    if chainid == "1":
        for rpc in ["https://eth.llamarpc.com", "https://rpc.ankr.com/eth"]:
            try:
                r = requests.post(rpc, json={
                    "jsonrpc": "2.0", "method": "eth_getBalance",
                    "params": [address, "latest"], "id": 1
                }, timeout=8)
                data = r.json()
                if "result" in data:
                    return int(data["result"], 16) / 1e18
            except Exception:
                continue
    return None


def evm_get_transactions(address, chainid, limit=10):
    """Транзакции через Etherscan V2."""
    if not ETHERSCAN_API:
        return []
    try:
        params = {
            "chainid": chainid, "module": "account", "action": "txlist",
            "address": address, "page": 1, "offset": limit,
            "sort": "desc", "apikey": ETHERSCAN_API
        }
        r = requests.get(ETHERSCAN_URL, params=params, timeout=10)
        data = r.json()
        if data.get("status") == "1":
            txs = []
            for tx in data["result"]:
                val = int(tx["value"]) / 1e18
                txs.append({
                    "hash":      tx["hash"],
                    "from":      tx["from"],
                    "to":        tx.get("to", ""),
                    "value":     val,
                    "date":      datetime.fromtimestamp(int(tx["timeStamp"])).strftime("%Y-%m-%d %H:%M"),
                    "status":    "success" if tx["isError"] == "0" else "failed",
                    "is_contract": val == 0,
                })
            return txs
    except Exception:
        pass

    # Fallback ETH: Blockscout
    if chainid == "1":
        try:
            url = f"https://eth.blockscout.com/api/v2/addresses/{address}/transactions"
            r = requests.get(url, params={"filter": "to | from"}, timeout=10)
            data = r.json()
            txs = []
            for tx in data.get("items", [])[:limit]:
                val = int(tx.get("value", "0")) / 1e18
                ts = tx.get("timestamp", "")
                txs.append({
                    "hash":      tx.get("hash", ""),
                    "from":      tx.get("from", {}).get("hash", ""),
                    "to":        (tx.get("to") or {}).get("hash", ""),
                    "value":     val,
                    "date":      ts[:16].replace("T", " ") if ts else "N/A",
                    "status":    "success" if tx.get("status") == "ok" else "failed",
                    "is_contract": val == 0,
                })
            return txs
        except Exception:
            pass
    return []


def evm_get_tokens(address, chainid, limit=5):
    """Топ токенов через Etherscan V2."""
    if not ETHERSCAN_API:
        return []
    try:
        params = {
            "chainid": chainid, "module": "account", "action": "tokentx",
            "address": address, "page": 1, "offset": limit * 4,
            "sort": "desc", "apikey": ETHERSCAN_API
        }
        r = requests.get(ETHERSCAN_URL, params=params, timeout=10)
        data = r.json()
        if data.get("status") == "1":
            tokens, seen = [], set()
            for tx in data["result"]:
                sym = tx.get("tokenSymbol", "?")
                if sym not in seen:
                    seen.add(sym)
                    date = datetime.fromtimestamp(int(tx["timeStamp"])).strftime("%Y-%m-%d")
                    tokens.append({"token": sym, "name": tx.get("tokenName", ""), "last": date})
                if len(tokens) >= limit:
                    break
            return tokens
    except Exception:
        pass
    return []


def analyze_evm(address):
    """Анализирует EVM адрес во всех EVM сетях параллельно."""
    results = {}

    def fetch_chain(chainid, chain_info):
        bal = evm_get_balance(address, chainid)
        if bal is None or bal == 0:
            # Если баланс пустой — проверим есть ли хоть какие-то транзакции
            txs = evm_get_transactions(address, chainid, limit=3)
            if not txs and bal == 0:
                return chainid, None  # Пропускаем пустые сети
            return chainid, {"balance": bal or 0, "txs": txs, "tokens": [], **chain_info}

        txs    = evm_get_transactions(address, chainid, limit=10)
        tokens = evm_get_tokens(address, chainid, limit=5)
        return chainid, {"balance": bal, "txs": txs, "tokens": tokens, **chain_info}

    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(fetch_chain, cid, info): cid for cid, info in EVM_CHAINS.items()}
        for future in as_completed(futures):
            chainid, data = future.result()
            if data is not None:
                results[chainid] = data

    return results


# ─── BITCOIN ───────────────────────────────────────────────────────────────────

def analyze_btc(address):
    """Blockstream API — бесплатно, без ключа."""
    result = {"balance": None, "txs": [], "tokens": [], "name": "Bitcoin", "ticker": "BTC"}
    try:
        # Баланс
        r = requests.get(f"{BTC_API}/address/{address}", timeout=10)
        data = r.json()
        funded  = data.get("chain_stats", {}).get("funded_txo_sum", 0)
        spent   = data.get("chain_stats", {}).get("spent_txo_sum", 0)
        balance = (funded - spent) / 1e8
        tx_count = data.get("chain_stats", {}).get("tx_count", 0)
        result["balance"]  = balance
        result["tx_count"] = tx_count

        # Последние транзакции
        r2 = requests.get(f"{BTC_API}/address/{address}/txs", timeout=10)
        txs_raw = r2.json()
        txs = []
        for tx in txs_raw[:10]:
            # Определяем направление — входящий или исходящий
            out_sum = sum(o["value"] for o in tx.get("vout", [])
                         if any(a == address for a in o.get("scriptpubkey_address", []) if a))
            in_val  = out_sum / 1e8
            ts = tx.get("status", {}).get("block_time")
            date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "unconfirmed"
            txs.append({
                "hash":   tx["txid"],
                "value":  round(in_val, 8),
                "date":   date,
                "status": "confirmed" if tx.get("status", {}).get("confirmed") else "pending",
                "is_contract": False,
            })
        result["txs"] = txs
    except Exception as e:
        result["error"] = str(e)
    return result


# ─── TRON ──────────────────────────────────────────────────────────────────────

def analyze_trx(address):
    """Trongrid API — бесплатно, без ключа."""
    result = {"balance": None, "txs": [], "tokens": [], "name": "Tron", "ticker": "TRX"}
    try:
        # Баланс
        r = requests.get(f"{TRX_API}/v1/accounts/{address}", timeout=10)
        data = r.json()
        accounts = data.get("data", [])
        if accounts:
            acc = accounts[0]
            balance = acc.get("balance", 0) / 1e6
            result["balance"] = balance
            # Сохраняем raw data для attribution
            result["_raw_account"] = {
                "name": acc.get("name", ""),
                "accountName": acc.get("account_name", ""),
            }

            # Токены TRC-20
            trc20 = acc.get("trc20", [])
            tokens = []
            for t in trc20[:5]:
                for sym, val in t.items():
                    tokens.append({"token": sym[:10], "name": sym, "last": "N/A"})
            result["tokens"] = tokens

        # Транзакции
        r2 = requests.get(
            f"{TRX_API}/v1/accounts/{address}/transactions",
            params={"limit": 10, "order_by": "block_timestamp,desc"},
            timeout=10
        )
        data2 = r2.json()
        txs = []
        for tx in data2.get("data", [])[:10]:
            val_sun = 0
            raw = tx.get("raw_data", {})
            for c in raw.get("contract", []):
                val_sun = c.get("parameter", {}).get("value", {}).get("amount", 0)
            val = val_sun / 1e6
            ts = tx.get("block_timestamp", 0)
            date = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M") if ts else "N/A"
            txs.append({
                "hash":   tx.get("txID", ""),
                "value":  round(val, 4),
                "date":   date,
                "status": "success" if tx.get("ret", [{}])[0].get("contractRet") == "SUCCESS" else "failed",
                "is_contract": val == 0,
            })
        result["txs"] = txs
    except Exception as e:
        result["error"] = str(e)
    return result


# ─── SOLANA ────────────────────────────────────────────────────────────────────

def analyze_sol(address):
    """Solana public RPC."""
    result = {"balance": None, "txs": [], "tokens": [], "name": "Solana", "ticker": "SOL"}
    try:
        # Баланс
        r = requests.post(SOL_RPC, json={
            "jsonrpc": "2.0", "id": 1,
            "method": "getBalance",
            "params": [address]
        }, timeout=10)
        data = r.json()
        lamports = data.get("result", {}).get("value", 0)
        result["balance"] = lamports / 1e9

        # Последние подписи транзакций
        r2 = requests.post(SOL_RPC, json={
            "jsonrpc": "2.0", "id": 1,
            "method": "getSignaturesForAddress",
            "params": [address, {"limit": 10}]
        }, timeout=10)
        sigs = r2.json().get("result", [])
        txs = []
        for sig in sigs[:10]:
            ts = sig.get("blockTime")
            date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "N/A"
            txs.append({
                "hash":   sig.get("signature", "")[:20] + "...",
                "value":  0,
                "date":   date,
                "status": "success" if sig.get("err") is None else "failed",
                "is_contract": True,
            })
        result["txs"] = txs

        # SPL токены
        r3 = requests.post(SOL_RPC, json={
            "jsonrpc": "2.0", "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [address,
                       {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                       {"encoding": "jsonParsed"}]
        }, timeout=10)
        token_accounts = r3.json().get("result", {}).get("value", [])
        tokens = []
        seen = set()
        for acc in token_accounts[:5]:
            info = acc.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
            mint = info.get("mint", "")[:8]
            bal  = info.get("tokenAmount", {}).get("uiAmount", 0)
            if mint and mint not in seen and bal and bal > 0:
                seen.add(mint)
                tokens.append({"token": mint + "...", "name": "SPL Token", "last": "N/A"})
        result["tokens"] = tokens

    except Exception as e:
        result["error"] = str(e)
    return result


# ─── TON ───────────────────────────────────────────────────────────────────────

def analyze_ton(address):
    """TONCenter API — бесплатно, без ключа (rate limited)."""
    result = {"balance": None, "txs": [], "tokens": [], "name": "TON", "ticker": "TON"}
    try:
        # Баланс
        r = requests.get(f"{TON_API}/getAddressBalance",
                         params={"address": address}, timeout=10)
        data = r.json()
        if data.get("ok"):
            result["balance"] = int(data["result"]) / 1e9

        # Транзакции
        r2 = requests.get(f"{TON_API}/getTransactions",
                          params={"address": address, "limit": 10}, timeout=10)
        data2 = r2.json()
        txs = []
        for tx in data2.get("result", [])[:10]:
            val_nano = tx.get("in_msg", {}).get("value", 0) or 0
            val = int(val_nano) / 1e9
            ts = tx.get("utime", 0)
            date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "N/A"
            txs.append({
                "hash":   tx.get("transaction_id", {}).get("hash", "")[:16] + "...",
                "value":  round(val, 6),
                "date":   date,
                "status": "success",
                "is_contract": val == 0,
            })
        result["txs"] = txs

    except Exception as e:
        result["error"] = str(e)
    return result


# ─── OFAC ──────────────────────────────────────────────────────────────────────

KNOWN_ENTITIES = {
    "0xd551234ae421e3bcba99a0da6d736074f22192ff": ("Binance",          "exchange", "low"),
    "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be": ("Binance Hot Wallet","exchange", "low"),
    "0x742d35cc6634c0532925a3b844bc454e4438f44e": ("Bitfinex",          "exchange", "low"),
    "0x722122df12d4e14e13ac3b6895a86e84145b6967": ("Tornado Cash",      "mixer",    "high"),
    "0xdd4c48c0b24039969fc16d1cdf626eab821d3384": ("Tornado Cash",      "mixer",    "high"),
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": ("Tornado Cash",      "mixer",    "high"),
}


# ─── KNOWN ENTITIES — ALL CHAINS ──────────────────────────────────────────────

KNOWN_BTC = {
    "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa": ("Satoshi Genesis Block",   "historic",  "low"),
    "1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF": ("Patoshi / Early Miner",   "historic",  "low"),
    "3Cbq7aT1tY8kMxWLbitaG7yT6bPbKChq64": ("Bitfinex Cold Wallet",    "exchange",  "low"),
    "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97": ("Binance Cold", "exchange", "low"),
    "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s": ("Binance Hot Wallet",      "exchange",  "low"),
    "12cgpFdJViXbwHbhrA3TuW1EGnL25Zqc3P": ("Huobi",                   "exchange",  "low"),
    "1HckjUpRGcrrRAtFaaCAUaGjsPx9oYmLaZ": ("Kraken",                  "exchange",  "low"),
    "3E5RJF1X5V9QFBZrMxPzaX1GWtP1jVQEMh": ("Tornado Cash BTC",       "mixer",     "high"),
}

KNOWN_TRX = {
    "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE": ("Binance Hot",             "exchange",  "low"),
    "TVj7RNVHy6thbM7BWdSe9G6gXwKhjhdNZS": ("Binance Cold",            "exchange",  "low"),
    "TKzxdSv2FZKQrEqkKVgp5DcwEXBEKMg2Ax": ("Huobi TRX",              "exchange",  "low"),
    "TNaRAoLUyYEV2uF3RQjRENcpZNDhMZQVcm": ("OKX TRX",                "exchange",  "low"),
    "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9": ("Bybit TRX",              "exchange",  "low"),
    "TXJgMdjVX5dKiQaUi9QobwNxtSQaFqccvd": ("USDT Tron Treasury",     "stablecoin","low"),
    "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7": ("Tornado Cash TRX",       "mixer",     "high"),
}

KNOWN_SOL = {
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": ("Binance SOL Hot",   "exchange", "low"),
    "5tzFkiKscXHK5ZXCGbXZxdw7gHa5vgMKGY2PiKnGYpbH": ("Coinbase SOL",      "exchange", "low"),
    "GugU1tP7doLeTw9hQP51xmJFZjbQdHVF2KFMgEXFWBKY": ("OKX SOL",           "exchange", "low"),
    "HVh6wHNBAsG3pq1Bj5oCzRjoWKVogEDHwUHkRz3ekFgt": ("FTX SOL (defunct)", "exchange", "low"),
    "4vJ9JU1bJJE96FbKdjnVIkDUXThTjbMEpKpSQS7ezfAP": ("Serum DEX",         "dex",      "low"),
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4":  ("Jupiter Aggregator","dex",      "low"),
}

KNOWN_TON = {
    "EQD2NmD_lH5f5u1Kj3KfGyTvhZSX0Eg6qp2a5IQUKXxOG3a": ("TON Foundation",   "foundation","low"),
    "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs": ("OKX TON",          "exchange",  "low"),
    "EQBfAN7LfaUYgXZNw5Wc7GBgkEX2yhuJ5ka95J1oNOxf4Rkx": ("Binance TON",      "exchange",  "low"),
    "EQAUTPkNpjJkwREZSBmCGLNGfJqe0V5r6JHVMhyNUHTFksBz": ("Fragment",         "marketplace","low"),
    "EQBlqsm144Dq6SjbPI4jjZvA1hqTIP3CvHovbIfW_t-SCALE": ("Getgems NFT",      "marketplace","low"),
}

# ─── ATTRIBUTION / LABELS ─────────────────────────────────────────────────────

# Кэш label базы — загружаем один раз
_label_cache = None

def load_label_db():
    """Загружает публичную базу Etherscan labels с GitHub."""
    global _label_cache
    if _label_cache is not None:
        return _label_cache
    try:
        r = requests.get(LABEL_DB_URL, timeout=15)
        if r.status_code == 200:
            raw = r.json()
            # Формат: {"0xADDR": {"nameTag": "...", "labels": [...]}} или похожий
            db = {}
            for addr, info in raw.items():
                name = info.get("nameTag") or info.get("name") or info.get("label") or ""
                labels = info.get("labels", [])
                if name or labels:
                    db[addr.lower()] = {
                        "name": name,
                        "labels": labels if isinstance(labels, list) else [labels],
                    }
            _label_cache = db
            return db
    except Exception:
        pass
    _label_cache = {}
    return {}


def get_etherscan_contract_name(address, chainid="1"):
    """Получает имя верифицированного контракта через Etherscan API."""
    if not ETHERSCAN_API:
        return None
    try:
        params = {
            "chainid": chainid, "module": "contract", "action": "getsourcecode",
            "address": address, "apikey": ETHERSCAN_API
        }
        r = requests.get(ETHERSCAN_URL, params=params, timeout=8)
        data = r.json()
        if data.get("status") == "1" and data.get("result"):
            result = data["result"][0]
            name = result.get("ContractName", "")
            if name and name != "":
                return name
    except Exception:
        pass
    return None


def resolve_address_label(address, label_db=None):
    """
    Определяет владельца/метку адреса.
    Порядок: local known_entities → label_db → etherscan contract name
    Возвращает dict {name, category, source} или None
    """
    addr_low = address.lower()

    # 1. Локальная база
    if addr_low in KNOWN_ENTITIES:
        name, cat, risk = KNOWN_ENTITIES[addr_low]
        return {"name": name, "category": cat, "risk": risk, "source": "local"}

    # 2. Публичная label DB
    if label_db:
        if addr_low in label_db:
            info = label_db[addr_low]
            labels = info.get("labels", [])
            cat = labels[0] if labels else "entity"
            return {"name": info["name"], "category": cat, "risk": "low", "source": "etherscan-labels"}

    # 3. Etherscan contract name (только для EVM)
    contract_name = get_etherscan_contract_name(address)
    if contract_name:
        return {"name": contract_name, "category": "contract", "risk": "low", "source": "etherscan"}

    return None


def analyze_counterparties(address, txs, label_db=None, max_check=10):
    """
    Анализирует контрагентов из транзакций.
    Возвращает список {address, count, label} топ контрагентов.
    """
    from collections import Counter
    addr_low = address.lower()

    # Собираем все контрагенты
    counter = Counter()
    for tx in txs:
        other = tx.get("to", "") if tx.get("from", "").lower() == addr_low else tx.get("from", "")
        if other and other.lower() != addr_low:
            counter[other.lower()] += 1

    # Топ контрагентов — проверяем labels
    results = []
    for addr, count in counter.most_common(max_check):
        label = resolve_address_label(addr, label_db)
        results.append({
            "address": addr,
            "count": count,
            "label": label,
        })
    return results[:7]


def resolve_btc_label(address):
    """BTC attribution: локальная база → WalletExplorer API."""
    if address in KNOWN_BTC:
        name, cat, risk = KNOWN_BTC[address]
        return {"name": name, "category": cat, "risk": risk, "source": "local"}
    try:
        r = requests.get(
            "https://www.walletexplorer.com/api/1/address",
            params={"address": address, "caller": "argus-osint"},
            timeout=8
        )
        data = r.json()
        wallet_id = data.get("wallet", {}).get("id", "")
        if wallet_id:
            return {"name": wallet_id, "category": "entity", "risk": "low", "source": "walletexplorer"}
    except Exception:
        pass
    return None


def resolve_trx_label(address, tronscan_data=None):
    """TRX attribution: локальная база → тэг из Tronscan ответа → Tronscan API."""
    if address in KNOWN_TRX:
        name, cat, risk = KNOWN_TRX[address]
        return {"name": name, "category": cat, "risk": risk, "source": "local"}
    # Данные уже могут быть в tronscan_data (из analyze_trx)
    if tronscan_data:
        name = tronscan_data.get("name") or tronscan_data.get("accountName") or ""
        risk_flag = tronscan_data.get("risk", False)
        if name:
            return {"name": name, "category": "entity", "risk": "high" if risk_flag else "low", "source": "tronscan"}
    # Отдельный запрос если данных нет
    try:
        r = requests.get(
            "https://apilist.tronscanapi.com/api/accountv2",
            params={"address": address},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8
        )
        data = r.json()
        name = data.get("name") or data.get("accountName") or ""
        if name:
            return {"name": name, "category": "entity", "risk": "low", "source": "tronscan"}
    except Exception:
        pass
    return None


def resolve_sol_label(address):
    """SOL attribution: локальная база → Solana FM → Solscan."""
    if address in KNOWN_SOL:
        name, cat, risk = KNOWN_SOL[address]
        return {"name": name, "category": cat, "risk": risk, "source": "local"}
    # Solana FM
    try:
        r = requests.get(
            f"https://hyper.solana.fm/v3/accounts/{address}",
            headers={"Accept": "application/json"},
            timeout=8
        )
        data = r.json()
        name = (data.get("result", {}).get("data", {}) or {}).get("accountName", "")
        acc_type = (data.get("result", {}).get("data", {}) or {}).get("accountType", "")
        if name:
            return {"name": name, "category": acc_type or "entity", "risk": "low", "source": "solana-fm"}
    except Exception:
        pass
    # Solscan
    try:
        r = requests.get(
            "https://public-api.solscan.io/account/info",
            params={"address": address},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8
        )
        data = r.json()
        name = (data.get("data") or {}).get("label", "")
        if name:
            return {"name": name, "category": "entity", "risk": "low", "source": "solscan"}
    except Exception:
        pass
    return None


def resolve_ton_label(address):
    """TON attribution: локальная база → TON API (name + is_scam)."""
    if address in KNOWN_TON:
        name, cat, risk = KNOWN_TON[address]
        return {"name": name, "category": cat, "risk": risk, "source": "local"}
    try:
        r = requests.get(
            f"https://tonapi.io/v2/accounts/{address}",
            headers={"Accept": "application/json"},
            timeout=8
        )
        data = r.json()
        name = data.get("name") or ""
        is_scam = data.get("is_scam", False)
        interfaces = data.get("interfaces", [])
        cat = interfaces[0] if interfaces else "wallet"
        if name:
            return {
                "name": name,
                "category": cat,
                "risk": "high" if is_scam else "low",
                "source": "tonapi"
            }
    except Exception:
        pass
    return None


def resolve_label_for_chain(address, chain, extra_data=None):
    """Единый интерфейс для attribution по любой сети."""
    if chain == "evm":
        return resolve_address_label(address, _label_cache or {})
    elif chain == "btc":
        return resolve_btc_label(address)
    elif chain == "trx":
        return resolve_trx_label(address, extra_data)
    elif chain == "sol":
        return resolve_sol_label(address)
    elif chain == "ton":
        return resolve_ton_label(address)
    return None


# ─── PUBLIC MENTIONS ──────────────────────────────────────────────────────────

def search_github_mentions(address, max_results=5):
    """
    Ищет упоминания адреса на GitHub через web search JSON API.
    Возвращает список {source, repo, author, date, context, url}
    """
    results = []
    headers = {"User-Agent": "Mozilla/5.0 (OSINT)", "Accept": "application/json"}
    addr_lower = address.lower()

    # 1. Repositories
    try:
        r = requests.get(
            f"https://github.com/search?q=%22{address}%22&type=repositories",
            headers=headers, timeout=10
        )
        data = r.json().get("payload", {})
        for item in (data.get("results") or [])[:max_results]:
            repo = item.get("repo", {}).get("repository", {})
            owner = repo.get("owner_login", "?")
            name  = repo.get("name", "?")
            desc  = item.get("repo", {}).get("description", "") or ""
            results.append({
                "source":  "github_repo",
                "repo":    f"{owner}/{name}",
                "author":  owner,
                "date":    repo.get("updated_at", "")[:10],
                "context": desc[:80] or f"Repository named after address",
                "url":     f"https://github.com/{owner}/{name}",
            })
    except Exception:
        pass

    # 2. Commits
    try:
        r = requests.get(
            f"https://github.com/search?q={address}&type=commits",
            headers=headers, timeout=10
        )
        data = r.json().get("payload", {})
        total = data.get("result_count", 0)
        for item in (data.get("results") or [])[:max_results]:
            repo = item.get("repository", {}).get("repository", {})
            owner  = repo.get("owner_login", "?")
            rname  = repo.get("name", "?")
            sha    = item.get("sha", "")[:7]
            msg    = item.get("message", "")[:80].replace(chr(10), ' ')
            author = (item.get("authors") or [{}])[0].get("login") or                      (item.get("authors") or [{}])[0].get("display_name", "?")
            date   = item.get("author_date", "")[:10]
            results.append({
                "source":  "github_commit",
                "repo":    f"{owner}/{rname}",
                "author":  author,
                "date":    date,
                "context": msg,
                "url":     f"https://github.com/{owner}/{rname}/commit/{item.get('sha','')}",
                "_total":  total,
            })
    except Exception:
        pass

    # 3. Code search (quoted)
    try:
        r = requests.get(
            f"https://github.com/search?q=%22{addr_lower}%22&type=code",
            headers=headers, timeout=10
        )
        data = r.json().get("payload", {})
        total_code = data.get("result_count", 0)
        for item in (data.get("results") or [])[:max_results]:
            repo  = item.get("repo", {}).get("repository", {})
            owner = repo.get("owner_login", "?")
            rname = repo.get("name", "?")
            path  = item.get("path", "")
            results.append({
                "source":  "github_code",
                "repo":    f"{owner}/{rname}",
                "author":  owner,
                "date":    repo.get("updated_at", "")[:10],
                "context": f"Found in file: {path}",
                "url":     f"https://github.com/{owner}/{rname}/blob/HEAD/{path}",
                "_total":  total_code,
            })
    except Exception:
        pass

    return results


def search_github_issues(address, max_results=5):
    """Ищет упоминания адреса в GitHub issues и discussions."""
    results = []
    headers = {"User-Agent": "Mozilla/5.0 (OSINT)", "Accept": "application/json"}
    try:
        r = requests.get(
            f"https://github.com/search?q={address}&type=issues",
            headers=headers, timeout=10
        )
        data = r.json().get("payload", {})
        total = data.get("result_count", 0)
        for item in (data.get("results") or [])[:max_results]:
            repo = item.get("repo", {}).get("repository", {})
            owner = repo.get("owner_login", "?")
            rname = repo.get("name", "?")
            title = re.sub(r'<[^>]+>', '', item.get("hl_title", ""))[:70]
            author = item.get("author_name", "?")
            state = item.get("state", "?")
            num = item.get("number", "?")
            results.append({
                "source":  "github_issue",
                "repo":    f"{owner}/{rname}",
                "author":  author,
                "date":    repo.get("updated_at", "")[:10],
                "context": f"[{state}] #{num}: {title}",
                "url":     f"https://github.com/{owner}/{rname}/issues/{num}",
                "_total":  total,
            })
    except Exception:
        pass
    return results


def search_github_donate_context(address, max_results=3):
    """Ищет адрес в контексте донатов/кошельков в README и конфигах."""
    results = []
    headers = {"User-Agent": "Mozilla/5.0 (OSINT)", "Accept": "application/json"}
    addr_lower = address.lower()

    donate_queries = [
        (f"%22{address}%22+donate", "donate"),
        (f"%22{address}%22+tip", "tip"),
        (f"%22{addr_lower}%22+wallet", "wallet"),
    ]
    for query, context_type in donate_queries:
        try:
            r = requests.get(
                f"https://github.com/search?q={query}&type=code",
                headers=headers, timeout=8
            )
            data = r.json().get("payload", {})
            total = data.get("result_count", 0)
            if total == 0:
                continue
            for item in (data.get("results") or [])[:max_results]:
                repo = item.get("repo", {}).get("repository", {})
                owner = repo.get("owner_login", "?")
                rname = repo.get("name", "?")
                path  = item.get("path", "")
                results.append({
                    "source":  "github_social",
                    "repo":    f"{owner}/{rname}",
                    "author":  owner,
                    "date":    repo.get("updated_at", "")[:10],
                    "context": f"[{context_type}] in {path}",
                    "url":     f"https://github.com/{owner}/{rname}/blob/HEAD/{path}",
                    "_total":  total,
                    "_type":   context_type,
                })
        except Exception:
            continue
    return results


def search_mentions(address):
    """
    Агрегирует упоминания адреса из всех доступных источников.
    Возвращает dict {source_name: [results], _summary: {...}}
    """
    all_mentions = {}
    summary = {}

    # GitHub: repos + commits + code
    github = search_github_mentions(address)
    # GitHub: issues/discussions
    issues = search_github_issues(address)
    # GitHub: donate/tip/wallet контекст
    social = search_github_donate_context(address)

    all_items = github + issues + social
    if all_items:
        all_mentions["GitHub"] = all_items

    for item in all_items:
        src = item["source"]
        total = item.get("_total", 1)
        if src not in summary or summary[src] < total:
            summary[src] = total

    all_mentions["_summary"] = summary
    return all_mentions


# ─── WALLET INTELLIGENCE ───────────────────────────────────────────────────────

def compute_wallet_stats(address, txs, ticker="ETH"):
    """
    Вычисляет статистику кошелька по списку транзакций.
    Возвращает dict с профилем, возрастом, объёмом, funding source.
    """
    if not txs:
        return {"profile": "UNKNOWN", "reason": "No transactions"}

    addr_low = address.lower()

    # --- Возраст кошелька ---
    dates = []
    for tx in txs:
        d = tx.get("date", "")
        if d and d != "N/A":
            try:
                dates.append(datetime.strptime(d[:16], "%Y-%m-%d %H:%M"))
            except Exception:
                pass

    first_seen = min(dates) if dates else None
    last_seen  = max(dates) if dates else None
    age_days   = (last_seen - first_seen).days if first_seen and last_seen else 0

    # --- Объём in/out ---
    vol_in  = sum(tx["value"] for tx in txs
                  if tx.get("to", "").lower() == addr_low and not tx.get("is_contract"))
    vol_out = sum(tx["value"] for tx in txs
                  if tx.get("from", "").lower() == addr_low and not tx.get("is_contract"))

    total_in  = len([tx for tx in txs if tx.get("to", "").lower() == addr_low])
    total_out = len([tx for tx in txs if tx.get("from", "").lower() == addr_low])
    contract_calls = len([tx for tx in txs if tx.get("is_contract")])

    # --- Funding source — первая входящая транзакция ---
    incoming = [tx for tx in txs if tx.get("to", "").lower() == addr_low]
    # Сортируем по дате (самая ранняя)
    incoming_sorted = sorted(incoming, key=lambda x: x.get("date", ""))
    funding_tx = incoming_sorted[0] if incoming_sorted else None

    # --- Wallet profiling ---
    profile, reason = _classify_wallet(
        txs, total_in, total_out, contract_calls, age_days, vol_in, vol_out
    )

    return {
        "profile":      profile,
        "reason":       reason,
        "first_seen":   first_seen.strftime("%Y-%m-%d") if first_seen else "N/A",
        "last_seen":    last_seen.strftime("%Y-%m-%d") if last_seen else "N/A",
        "age_days":     age_days,
        "vol_in":       round(vol_in, 6),
        "vol_out":      round(vol_out, 6),
        "tx_in":        total_in,
        "tx_out":       total_out,
        "contract_pct": round(contract_calls / len(txs) * 100) if txs else 0,
        "funding_tx":   funding_tx,
        "ticker":       ticker,
    }


def _classify_wallet(txs, tx_in, tx_out, contract_calls, age_days, vol_in, vol_out):
    """Классифицирует тип кошелька по поведенческим паттернам."""
    total = len(txs)
    if total == 0:
        return "UNKNOWN", "No transaction history"

    contract_pct = contract_calls / total * 100

    # Интервалы между транзакциями
    dates = []
    for tx in txs:
        d = tx.get("date", "")
        if d and d != "N/A":
            try:
                dates.append(datetime.strptime(d[:16], "%Y-%m-%d %H:%M"))
            except Exception:
                pass

    avg_interval_hours = 999
    if len(dates) >= 2:
        dates_sorted = sorted(dates)
        intervals = [(dates_sorted[i+1] - dates_sorted[i]).total_seconds() / 3600
                     for i in range(len(dates_sorted)-1)]
        avg_interval_hours = sum(intervals) / len(intervals) if intervals else 999

    days_since_last = 0
    if dates:
        days_since_last = (datetime.now() - max(dates)).days

    # 1. BOT: высокая частота + много контрактных вызовов
    if avg_interval_hours < 1 and contract_pct > 60:
        return "BOT", f"High frequency ({avg_interval_hours:.1f}h avg), {contract_pct:.0f}% contract calls"

    # 2. DORMANT: давно не было активности (приоритет над HOLDER)
    if days_since_last > 365:
        return "DORMANT", f"Inactive for {days_since_last} days"

    # 3. BRIDGE/EXCHANGE: много входящих И исходящих, примерно равный объём
    if tx_in > 2 and tx_out > 2:
        ratio = vol_in / vol_out if vol_out > 0 else 99
        if 0.4 < ratio < 2.5:
            return "BRIDGE / EXCHANGE", f"Balanced in/out volume (ratio {ratio:.2f})"

    # 4. TRADER: много контрактных вызовов (DEX swaps)
    if contract_pct > 40 and total > 3:
        return "TRADER", f"{contract_pct:.0f}% DeFi/contract interactions"

    # 5. HOLDER: мало транзакций, долго держит
    if total <= 5 and age_days > 30:
        return "HOLDER", f"Low activity ({total} txs over {age_days} days)"

    # 6. BRIDGE (второй шанс с меньшим порогом — для коротких историй)
    if tx_in > 1 and tx_out > 1:
        ratio = vol_in / vol_out if vol_out > 0 else 99
        if 0.3 < ratio < 3.0 and (vol_in + vol_out) > 0:
            return "BRIDGE / EXCHANGE", f"Balanced in/out (ratio {ratio:.2f})"

    # 7. FRESH
    if age_days < 7 and total < 10:
        return "FRESH WALLET", f"Created {age_days} days ago"

    return "ACTIVE WALLET", f"{total} transactions, {age_days} days history"


# ─── CLUSTER HINT ─────────────────────────────────────────────────────────────

def compute_cluster_hint(address, txs, counterparties, label_db=None):
    """
    Анализирует кластерные признаки кошелька.
    Возвращает список выводов {type, confidence, description}
    """
    hints = []
    addr_low = address.lower()
    if not txs:
        return hints

    total = len(txs)

    # 1. ENTITY CONCENTRATION
    # Если большинство транзакций идут через одну известную сущность
    entity_counts = {}
    for cp in counterparties:
        label = cp.get("label")
        if label:
            name = label["name"]
            entity_counts[name] = entity_counts.get(name, 0) + cp["count"]

    if entity_counts:
        top_entity, top_count = max(entity_counts.items(), key=lambda x: x[1])
        pct = round(top_count / total * 100)
        if pct >= 50:
            hints.append({
                "type":        "ENTITY CONCENTRATION",
                "confidence":  "HIGH" if pct >= 70 else "MEDIUM",
                "description": f"{pct}% of transactions involve {top_entity} — likely deposit address",
                "risk":        "low",
            })

    # 2. HIGH-RISK NEIGHBOURS
    # Если есть контакты с миксерами/санкционными адресами
    high_risk_contacts = []
    for cp in counterparties:
        label = cp.get("label")
        if label and label.get("risk") == "high":
            high_risk_contacts.append(label["name"])

    if high_risk_contacts:
        names = ", ".join(set(high_risk_contacts))
        hints.append({
            "type":        "HIGH-RISK NEIGHBOURS",
            "confidence":  "HIGH",
            "description": f"Direct interaction with: {names}",
            "risk":        "high",
        })

    # 3. SHARED FUNDING SOURCE
    # Если funding source — известная сущность
    incoming = sorted(
        [tx for tx in txs if tx.get("to", "").lower() == addr_low],
        key=lambda x: x.get("date", "")
    )
    if incoming:
        first_sender = incoming[0].get("from", "").lower()
        if first_sender:
            funder_label = resolve_address_label(first_sender, label_db or {})
            if funder_label:
                hints.append({
                    "type":        "FUNDED BY",
                    "confidence":  "HIGH",
                    "description": f"First funds received from {funder_label['name']} ({funder_label['category']})",
                    "risk":        funder_label.get("risk", "low"),
                })
            else:
                # Неизвестный источник — тоже интересно
                short = first_sender[:10] + "..." + first_sender[-6:]
                hints.append({
                    "type":        "FUNDED BY",
                    "confidence":  "MEDIUM",
                    "description": f"First funds from unknown address {short}",
                    "risk":        "low",
                })

    # 4. ONE-WAY FLOW
    # Только получает или только отправляет — характерно для депозитов/холодных кошельков
    tx_in  = len([tx for tx in txs if tx.get("to","").lower() == addr_low])
    tx_out = len([tx for tx in txs if tx.get("from","").lower() == addr_low])

    if tx_in > 0 and tx_out == 0:
        hints.append({
            "type":        "ONE-WAY FLOW",
            "confidence":  "MEDIUM",
            "description": "Only receives funds — possible cold storage or accumulation address",
            "risk":        "low",
        })
    elif tx_out > 0 and tx_in == 0:
        hints.append({
            "type":        "ONE-WAY FLOW",
            "confidence":  "MEDIUM",
            "description": "Only sends funds — possible hot wallet or payout address",
            "risk":        "low",
        })

    # 5. ROUND AMOUNTS
    # Круглые суммы часто означают ручные переводы (не DEX)
    non_contract = [tx for tx in txs if not tx.get("is_contract") and tx.get("value", 0) > 0]
    if non_contract:
        round_count = sum(1 for tx in non_contract
                         if tx["value"] > 0 and abs(tx["value"] - round(tx["value"], 0)) < 0.001)
        round_pct = round(round_count / len(non_contract) * 100)
        if round_pct >= 60 and len(non_contract) >= 3:
            hints.append({
                "type":        "ROUND AMOUNTS",
                "confidence":  "LOW",
                "description": f"{round_pct}% of transfers are round numbers — likely manual OTC/P2P activity",
                "risk":        "low",
            })

    return hints


def load_sanctions_db():
    """
    Загружает санкционную базу из нескольких источников.
    Возвращает dict {address_lower: [source_names]}
    Источники: OFAC, EU, UN, UK OFSI (через OpenSanctions + прямые)
    """
    sanctions = {}  # addr -> set of sources

    def add(addr, source):
        addr = addr.lower().strip()
        if addr not in sanctions:
            sanctions[addr] = set()
        sanctions[addr].add(source)

    # 1. OFAC ETH list (0xB10C GitHub — только ETH адреса, быстро)
    try:
        r = requests.get(OFAC_ETH_LIST_URL, timeout=15)
        if r.status_code == 200 and len(r.text) > 10:
            for line in r.text.strip().split("\n"):
                line = line.strip()
                if re.match(r'0x[a-fA-F0-9]{40}', line):
                    add(line, "OFAC")
    except Exception:
        pass

    # 2. OpenSanctions crypto addresses (OFAC + EU + UN + UK + 20+ sources)
    # Пробуем получить через API — бесплатный tier позволяет поиск
    try:
        r = requests.get(
            "https://api.opensanctions.org/search/default",
            params={"q": "cryptocurrency", "schema": "CryptoWallet", "limit": 1},
            headers={"Accept": "application/json"},
            timeout=10
        )
        if r.status_code == 200:
            # API работает — делаем поиск по типу CryptoWallet
            r2 = requests.get(
                "https://api.opensanctions.org/entities",
                params={"schema": "CryptoWallet", "limit": 500},
                headers={"Accept": "application/json"},
                timeout=20
            )
            if r2.status_code == 200:
                data = r2.json()
                for entity in data.get("results", []):
                    props = entity.get("properties", {})
                    addrs = props.get("address", [])
                    datasets = entity.get("datasets", [])
                    source_names = [d for d in datasets if d not in ("default", "sanctions")]
                    source_str = " + ".join(source_names[:3]) if source_names else "OpenSanctions"
                    for addr in addrs:
                        if re.match(r'0x[a-fA-F0-9]{40}', addr):
                            add(addr, source_str)
    except Exception:
        pass

    # 3. OFAC XML fallback (если GitHub недоступен)
    if not sanctions:
        try:
            r = requests.get(OFAC_XML_URL, timeout=60)
            if r.status_code == 200:
                for match in re.finditer(r'0x[a-fA-F0-9]{40}', r.text):
                    add(match.group(), "OFAC")
        except Exception:
            pass

    # Конвертируем sets в списки
    return {addr: list(sources) for addr, sources in sanctions.items()}


def check_sanctions(address, sanctions_db):
    """Проверяет адрес против всей санкционной базы."""
    addr_low = address.lower()
    if addr_low in sanctions_db:
        return {"sanctioned": True, "sources": sanctions_db[addr_low]}
    return {"sanctioned": False, "sources": []}


# Обратная совместимость
def load_ofac_addresses():
    db = load_sanctions_db()
    return set(db.keys())


def check_ofac(address, ofac_set):
    return {"sanctioned": address.lower() in ofac_set}


def check_ofac(address, ofac_set):
    return {"sanctioned": address.lower() in ofac_set}


def check_known_entities(address, txs):
    findings = []
    all_addrs = {address.lower()}
    for tx in txs:
        if tx.get("from"): all_addrs.add(tx["from"].lower())
        if tx.get("to"):   all_addrs.add(tx["to"].lower())
    for addr in all_addrs:
        if addr in KNOWN_ENTITIES:
            name, cat, risk = KNOWN_ENTITIES[addr]
            findings.append({"entity": name, "category": cat, "risk": risk, "address": addr})
    return findings


def calculate_risk(ofac, entities, tx_count, balance=None):
    if ofac["sanctioned"]: return "CRITICAL"
    if any(e["risk"] == "high" for e in entities): return "HIGH"
    has_balance = balance is not None and balance > 0
    if tx_count == 0 and not has_balance: return "UNKNOWN"
    return "LOW"


# ─── PRINT — EVM ОТЧЁТ ─────────────────────────────────────────────────────────

def print_evm_report(address, evm_results, ofac, entities, attribution=None, counterparties=None, wallet_stats=None, mentions=None, cluster_hints=None, sanctions=None):
    total_balance_usd_note = ""
    risk_colors = {
        "CRITICAL": f"{LR}{BR}", "HIGH": f"{Y}{BR}",
        "LOW": f"{G}{BR}", "UNKNOWN": f"{C}{BR}",
    }

    # Считаем общий риск по всем транзакциям всех сетей
    all_txs = []
    for cid, data in evm_results.items():
        all_txs.extend(data.get("txs", []))

    risk = calculate_risk(ofac, entities,
                          len(all_txs),
                          sum(d.get("balance", 0) for d in evm_results.values()))
    risk_display = f"{risk_colors.get(risk, '')}{risk}{RS}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"\n{G}╔{'═' * 62}╗")
    print(f"║{'ARGUS — INTELLIGENCE REPORT':^62}║")
    print(f"╚{'═' * 62}╝{RS}\n")

    print(f"  {DIM}Date     :{RS} {W}{now}{RS}")
    print(f"  {DIM}Address  :{RS} {G}{BR}{address}{RS}")
    print(f"  {DIM}Type     :{RS} EVM (ETH / BSC / Polygon / Arbitrum / Base)")
    print(f"  {DIM}Risk     :{RS} {risk_display}\n")

    # Балансы по сетям
    print_divider("BALANCES BY CHAIN")
    active_chains = 0
    for cid, data in sorted(evm_results.items(), key=lambda x: x[0]):
        bal = data.get("balance", 0) or 0
        name = data["name"]
        ticker = data["ticker"]
        bal_str = format_val(bal, ticker)
        if bal > 0:
            print(f"  {G}▓{RS} {W}{BR}{name:<12}{RS}  {G}{bal_str}{RS}")
            active_chains += 1
        else:
            print(f"  {DIM}▓ {name:<12}  {bal_str}{RS}")
    print()

    # Sanctions
    print_divider("SANCTIONS CHECK")
    if ofac["sanctioned"]:
        print_status("OFAC SDN LIST — MATCH FOUND", "critical")
    else:
        print_status("OFAC SDN List — No match", "ok")
    print()

    # Sanctions — обновлённый вывод с источниками
    print_divider("SANCTIONS CHECK")
    if sanctions and sanctions.get("sanctioned"):
        sources_str = " + ".join(sanctions.get("sources", ["?"]))
        print_status(f"SANCTIONED — found in: {sources_str}", "critical")
    elif sanctions:
        print_status("No match in sanctions lists (OFAC / EU / UN / UK)", "ok")
    else:
        print_status("Sanctions check unavailable", "warn")
    print()

    # Attribution — кому принадлежит адрес
    print_divider("ADDRESS ATTRIBUTION")
    if attribution:
        src_color = {"local": G, "etherscan-labels": C, "etherscan": Y}.get(attribution.get("source"), W)
        risk_tag = f" {R}[HIGH RISK]{RS}" if attribution.get("risk") == "high" else ""
        print(f"  {G}[✓]{RS} {W}{BR}{attribution['name']}{RS}{risk_tag}")
        print(f"        {DIM}Category : {attribution.get('category', 'unknown')}{RS}")
        print(f"        {DIM}Source   : {src_color}{attribution.get('source', '?')}{RS}")
    else:
        print(f"  {DIM}[?] No label found — unknown entity{RS}")
    print()

    # Counterparties
    if counterparties:
        print_divider("TOP COUNTERPARTIES")
        for cp in counterparties[:5]:
            label = cp.get("label")
            addr_short = cp["address"][:10] + "..." + cp["address"][-6:]
            count_str = f"{DIM}({cp['count']} tx){RS}"
            if label:
                risk_c = R if label.get("risk") == "high" else G
                print(f"  {risk_c}▓{RS} {W}{label['name']}{RS} {count_str}")
                print(f"        {DIM}{addr_short}  [{label['category']}  via {label['source']}]{RS}")
            else:
                print(f"  {DIM}▓ {addr_short}{RS}  {count_str}")
        print()

    # Cluster hints
    if cluster_hints:
        print_divider("CLUSTER ANALYSIS")
        for hint in cluster_hints:
            conf_color = {
                "HIGH":   f"{R}{BR}" if hint["risk"] == "high" else f"{G}{BR}",
                "MEDIUM": f"{Y}",
                "LOW":    f"{DIM}",
            }.get(hint["confidence"], W)
            risk_tag = f" {R}[RISK]{RS}" if hint["risk"] == "high" else ""
            print(f"  {conf_color}[{hint['confidence']}]{RS} {W}{hint['type']}{RS}{risk_tag}")
            print(f"        {DIM}{hint['description']}{RS}")
        print()

    # Known entities
    if entities:
        print_divider("KNOWN ENTITY INTERACTIONS")
        for e in entities:
            color = R if e["risk"] == "high" else Y
            print(f"  {color}[{e['risk'].upper()}]{RS} {e['entity']} ({e['category']})")
            print(f"        {DIM}{e['address']}{RS}")
        print()

    # Транзакции и токены по каждой активной сети
    for cid, data in sorted(evm_results.items()):
        txs    = data.get("txs", [])
        tokens = data.get("tokens", [])
        name   = data["name"]
        ticker = data["ticker"]

        if not txs and not tokens:
            continue

        print_divider(f"{name.upper()}")

        if tokens:
            print(f"  {DIM}Tokens:{RS}")
            for t in tokens:
                print(f"    {G}▓{RS} {W}{t['token']}{RS} {DIM}({t['name']}) — {t['last']}{RS}")

        if txs:
            print(f"  {DIM}Last {min(len(txs), 5)} transactions:{RS}")
            for tx in txs[:5]:
                direction = f"{G}IN {RS}" if (tx.get("to", "").lower() == address.lower()) else f"{Y}OUT{RS}"
                val = tx["value"]
                if tx.get("is_contract") or val == 0:
                    val_str = f"{DIM}contract call{RS}"
                else:
                    val_str = f"{W}{format_val(val, ticker)}{RS}"
                status_c = G if tx["status"] == "success" else R
                print(f"    {DIM}{tx['date']}{RS}  {direction}  {val_str}  {status_c}[{tx['status']}]{RS}")
        print()

    # Summary
    # Wallet Intelligence
    if wallet_stats and wallet_stats.get("profile") != "UNKNOWN":
        print_divider("WALLET INTELLIGENCE")
        profile = wallet_stats["profile"]
        profile_colors = {
            "BOT":               R,
            "BRIDGE / EXCHANGE": Y,
            "TRADER":            C,
            "DORMANT":           DIM,
            "HOLDER":            G,
            "FRESH WALLET":      Y,
            "ACTIVE WALLET":     W,
        }
        pc = profile_colors.get(profile, W)
        print(f"  {DIM}Profile      :{RS} {pc}{BR}{profile}{RS}  {DIM}({wallet_stats['reason']}){RS}")
        print(f"  {DIM}First seen   :{RS} {wallet_stats['first_seen']}")
        print(f"  {DIM}Last seen    :{RS} {wallet_stats['last_seen']}")
        if wallet_stats['age_days']:
            print(f"  {DIM}Active for   :{RS} {wallet_stats['age_days']} days")
        ticker = wallet_stats.get("ticker", "ETH")
        print(f"  {DIM}Volume IN    :{RS} {G}{format_val(wallet_stats['vol_in'], ticker)}{RS}  {DIM}({wallet_stats['tx_in']} tx){RS}")
        print(f"  {DIM}Volume OUT   :{RS} {Y}{format_val(wallet_stats['vol_out'], ticker)}{RS}  {DIM}({wallet_stats['tx_out']} tx){RS}")
        print(f"  {DIM}Contract     :{RS} {wallet_stats['contract_pct']}% of transactions")
        # Funding source
        ftx = wallet_stats.get("funding_tx")
        if ftx:
            faddr = ftx.get("from", "")
            faddr_short = faddr[:10] + "..." + faddr[-6:] if faddr else "N/A"
            print(f"  {DIM}Funded from  :{RS} {faddr_short}  {DIM}({ftx.get('date','')}){RS}")
        print()

    # Public mentions
    if mentions:
        github_items = mentions.get("GitHub", [])
        summary = mentions.get("_summary", {})
        if github_items or summary:
            print_divider("PUBLIC MENTIONS")
            commit_total = summary.get("github_commit", 0)
            code_total   = summary.get("github_code", 0)
            repo_total   = summary.get("github_repo", 0)
            if commit_total or code_total or repo_total:
                print(f"  {G}[GitHub]{RS}  {W}repos: {repo_total}  commits: {commit_total}  code files: {code_total}{RS}")
            for item in github_items[:4]:
                src_label = {"github_repo": "REPO", "github_commit": "COMMIT", "github_code": "CODE"}.get(item["source"], item["source"])
                print(f"  {DIM}[{src_label}]{RS} {W}{item['repo']}{RS}  {DIM}{item['date']}{RS}")
                print(f"         {DIM}{item['context'][:70]}{RS}")
                print(f"         {C}{item['url']}{RS}")
            print()

    print_divider("SUMMARY")
    high_risk = len([e for e in entities if e["risk"] == "high"])
    total_txs = sum(len(d.get("txs", [])) for d in evm_results.values())
    print(f"  {DIM}Risk assessment     :{RS} {risk_display}")
    print(f"  {DIM}Active chains       :{RS} {active_chains} / {len(EVM_CHAINS)}")
    print(f"  {DIM}Total transactions  :{RS} {total_txs}")
    print(f"  {DIM}Sanctions matches   :{RS} {'⚠ YES — OFAC SDN' if ofac['sanctioned'] else '✓ None'}")
    print(f"  {DIM}High-risk contacts  :{RS} {R if high_risk else G}{high_risk}{RS}")

    print(f"\n{G}╔{'═' * 62}╗")
    print(f"║{'ARGUS by VERES · Intelligence without borders':^62}║")
    print(f"╚{'═' * 62}╝{RS}\n")

    return risk, now


# ─── PRINT — SINGLE CHAIN ОТЧЁТ ────────────────────────────────────────────────

def print_single_chain_report(address, data, ofac=None):
    """Отчёт для BTC / TRX / SOL / TON."""
    risk_colors = {
        "CRITICAL": f"{LR}{BR}", "HIGH": f"{Y}{BR}",
        "LOW": f"{G}{BR}", "UNKNOWN": f"{C}{BR}",
    }
    name   = data["name"]
    ticker = data["ticker"]
    bal    = data.get("balance")
    txs    = data.get("txs", [])
    tokens = data.get("tokens", [])
    error  = data.get("error")

    # Для не-EVM сетей OFAC check не делаем (другой формат адресов)
    mock_ofac = {"sanctioned": False}
    risk = calculate_risk(mock_ofac, [], len(txs), bal)
    risk_display = f"{risk_colors.get(risk, '')}{risk}{RS}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"\n{G}╔{'═' * 62}╗")
    print(f"║{'ARGUS — INTELLIGENCE REPORT':^62}║")
    print(f"╚{'═' * 62}╝{RS}\n")

    print(f"  {DIM}Date     :{RS} {W}{now}{RS}")
    print(f"  {DIM}Address  :{RS} {G}{BR}{address}{RS}")
    print(f"  {DIM}Network  :{RS} {name} ({ticker})")
    print(f"  {DIM}Risk     :{RS} {risk_display}\n")

    if error:
        print_status(f"Fetch error: {error}", "warn")

    # Attribution
    attribution = data.get("_attribution")
    print_divider("ADDRESS ATTRIBUTION")
    if attribution:
        src_color = {"local": G, "tronscan": C, "walletexplorer": C,
                     "solana-fm": C, "solscan": C, "tonapi": C}.get(attribution.get("source"), W)
        risk_tag = f" {R}[HIGH RISK]{RS}" if attribution.get("risk") == "high" else ""
        print(f"  {G}[✓]{RS} {W}{BR}{attribution['name']}{RS}{risk_tag}")
        print(f"        {DIM}Category : {attribution.get('category', 'unknown')}{RS}")
        print(f"        {DIM}Source   : {src_color}{attribution.get('source', '?')}{RS}")
    else:
        print(f"  {DIM}[?] No label found — unknown entity{RS}")
    print()

    print_divider("BALANCE")
    bal_str = format_val(bal, ticker) if bal is not None else "N/A"
    print(f"  {DIM}{ticker} Balance :{RS} {G}{BR}{bal_str}{RS}\n")

    if tokens:
        print_divider("TOKEN ACTIVITY")
        for t in tokens:
            print(f"  {G}▓{RS} {W}{t['token']}{RS} {DIM}({t['name']}){RS}")
        print()

    if txs:
        print_divider(f"LAST {min(len(txs), 7)} TRANSACTIONS")
        for tx in txs[:7]:
            val = tx["value"]
            if tx.get("is_contract") or val == 0:
                val_str = f"{DIM}contract call{RS}"
            else:
                val_str = f"{W}{format_val(val, ticker)}{RS}"
            status_c = G if tx["status"] in ("success", "confirmed") else R
            print(f"  {DIM}{tx['date']}{RS}  {val_str}  {status_c}[{tx['status']}]{RS}")
        print()

    print_divider("SUMMARY")
    print(f"  {DIM}Risk assessment  :{RS} {risk_display}")
    print(f"  {DIM}Transactions     :{RS} {len(txs)}")
    if bal is not None:
        print(f"  {DIM}Balance          :{RS} {format_val(bal, ticker)}")

    print(f"\n{G}╔{'═' * 62}╗")
    print(f"║{'ARGUS by VERES · Intelligence without borders':^62}║")
    print(f"╚{'═' * 62}╝{RS}\n")

    return risk, now


# ─── SAVE REPORT ───────────────────────────────────────────────────────────────

def save_report(address, chain_type, data_summary, risk, now):
    safe_addr = address[:8].replace(":", "_")
    filename = f"argus_{safe_addr}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    lines = [
        "ARGUS — INTELLIGENCE REPORT",
        "=" * 64,
        f"Date     : {now}",
        f"Address  : {address}",
        f"Type     : {chain_type}",
        f"Risk     : {risk}",
        "",
    ]
    for key, val in data_summary.items():
        lines.append(f"  {key}: {val}")
    lines += ["", "=" * 64, "ARGUS by VERES · Intelligence without borders"]
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return filename


# ─── MAIN ──────────────────────────────────────────────────────────────────────

def analyze(address):
    print_banner()

    chain = detect_chain(address)

    if chain is None:
        print_status(f"Unknown address format: {address}", "error")
        print_status("Supported: ETH/BSC/Polygon/Arbitrum/Base (0x...), BTC (1.../3.../bc1...), TRX (T...), SOL, TON (EQ.../UQ...)", "info")
        sys.exit(1)

    chain_label = {
        "evm": "EVM (ETH/BSC/Polygon/Arbitrum/Base)",
        "btc": "Bitcoin",
        "trx": "Tron",
        "sol": "Solana",
        "ton": "TON",
    }
    print_status(f"Target  : {address}", "scan")
    print_status(f"Network : {chain_label[chain]}", "info")
    print()

    if chain == "evm" and not ETHERSCAN_API:
        print_status("ETHERSCAN_API_KEY not set in .env — EVM data will be limited", "warn")

    risk, now = "UNKNOWN", datetime.now().strftime("%Y-%m-%d %H:%M")
    data_summary = {"address": address, "chain": chain_label[chain]}

    if chain == "evm":
        loading_animation("Scanning EVM chains", 1.0)
        evm_results = analyze_evm(address)

        if not evm_results:
            print_status("No activity found on any EVM chain", "warn")

        loading_animation("Loading sanctions lists (OFAC/EU/UN)", 1.5)
        sanctions_db = load_sanctions_db()
        if not sanctions_db:
            print_status("Sanctions lists unavailable", "warn")
        sanctions = check_sanctions(address, sanctions_db)
        # Обратная совместимость для check_known_entities
        ofac = {"sanctioned": sanctions["sanctioned"]}

        loading_animation("Loading address label database", 0.8)
        label_db = load_label_db()

        # Attribution — кому принадлежит сам адрес
        attribution = resolve_address_label(address, label_db)

        # Собираем все транзакции
        all_txs = []
        for d in evm_results.values():
            all_txs.extend(d.get("txs", []))

        entities = check_known_entities(address, all_txs)

        loading_animation("Analyzing counterparties", 0.6)
        counterparties = analyze_counterparties(address, all_txs, label_db)

        loading_animation("Computing cluster hints", 0.5)
        cluster_hints = compute_cluster_hint(address, all_txs, counterparties, label_db)

        loading_animation("Computing wallet profile", 0.5)
        # Берём транзакции из основной сети (ETH)
        eth_txs = evm_results.get("1", {}).get("txs", []) or all_txs
        ticker  = evm_results.get("1", {}).get("ticker", "ETH")
        wallet_stats = compute_wallet_stats(address, eth_txs, ticker)

        loading_animation("Searching public mentions", 1.0)
        mentions = search_mentions(address)

        print()
        risk, now = print_evm_report(address, evm_results, ofac, entities,
                                     attribution, counterparties,
                                     wallet_stats, mentions,
                                     cluster_hints, sanctions)

        active = [d["name"] for d in evm_results.values()]
        data_summary["active_chains"] = ", ".join(active) if active else "none"
        data_summary["ofac"] = "MATCH" if ofac["sanctioned"] else "No match"

    elif chain == "btc":
        loading_animation("Fetching Bitcoin data", 1.0)
        data = analyze_btc(address)
        loading_animation("Resolving address label", 0.5)
        data["_attribution"] = resolve_btc_label(address)
        print()
        risk, now = print_single_chain_report(address, data)
        data_summary["balance"] = format_val(data.get("balance") or 0, "BTC")

    elif chain == "trx":
        loading_animation("Fetching Tron data", 1.0)
        data = analyze_trx(address)
        loading_animation("Resolving address label", 0.5)
        data["_attribution"] = resolve_trx_label(address, data.get("_raw_account"))
        print()
        risk, now = print_single_chain_report(address, data)
        data_summary["balance"] = format_val(data.get("balance") or 0, "TRX")

    elif chain == "sol":
        loading_animation("Fetching Solana data", 1.0)
        data = analyze_sol(address)
        loading_animation("Resolving address label", 0.5)
        data["_attribution"] = resolve_sol_label(address)
        print()
        risk, now = print_single_chain_report(address, data)
        data_summary["balance"] = format_val(data.get("balance") or 0, "SOL")

    elif chain == "ton":
        loading_animation("Fetching TON data", 1.0)
        data = analyze_ton(address)
        loading_animation("Resolving address label", 0.5)
        data["_attribution"] = resolve_ton_label(address)
        print()
        risk, now = print_single_chain_report(address, data)
        data_summary["balance"] = format_val(data.get("balance") or 0, "TON")

    filename = save_report(address, chain_label[chain], data_summary, risk, now)
    print_status(f"Report saved: {filename}", "ok")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_banner()
        print(f"  {Y}Usage:{RS}   python argus.py <ADDRESS>\n")
        print(f"  {DIM}Examples:")
        print(f"    ETH/EVM  : python argus.py 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        print(f"    Bitcoin  : python argus.py 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        print(f"    Tron     : python argus.py TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE")
        print(f"    Solana   : python argus.py 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM")
        print(f"    TON      : python argus.py EQD2NmD_lH5f5u1Kj3KfGyTvhZSX0Eg6qp2a5IQUKXxOG3a{RS}\n")
    else:
        analyze(sys.argv[1])
