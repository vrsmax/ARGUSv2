           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⣴⡆⢾⣇⣾⣿⢂⣴⣤⡄⠀⠀⠀⠀⠀⠀⠀      .o.       ooooooooo.     .oooooo.    ooooo     ooo  .oooooo..o
         ⠀⠀⠀⠀⠀⠀⠀⠀⣠⣦⡹⣿⣿⣿⢸⣿⣿⣷⣿⣿⣷⣾⣿⣶⡄⠀⠀⠀     .888.      `888   `Y88.  d8P'  `Y8b   `888'     `8' d8P'    `Y8
         ⠀⠀⠀⠀⠀⠀⠀⢾⣿⣿⣷⡹⣟⣫⣬⣭⣭⣝⣻⠿⠟⠋⠁⠀⠀⠀⠀⠀    .8"888.      888   .d88' 888            888       8  Y88bo.
         ⠀⠀⠀⠀⠀⢀⣿⣶⣽⡛⣱⡾⢛⣩⣭⣭⣭⣝⡋⠀⠀⠀⠀⠀⠀⠀⠀⠀   .8' `888.     888ooo88P'  888            888       8   `"Y8888o.
         ⠀⠀⠀⠀⠀⣘⣛⣻⡟⣾⢏⣾⣿⣿⣿⣿⣿⣿⣿⡷⢄⣠⠀⠀⠀⠀⠀⠀  .88ooo8888.    888`88b.    888     ooooo  888       8       `"Y88b
         ⠀⠀⠀⠀⠀⣿⡿⣟⢹⣇⣿⣿⣿⣿⣿⣿⣿⢟⣫⣴⣿⣿⡇⠀⠀⠀⠀⠀ .8'     `888.   888  `88b.  `88.    .88'   `88.    .8'  oo     .d8P
         ⠀⠀⠀⠀⠀⠋⣾⣿⠈⢹⣿⣿⣿⣿⣿⣯⣶⣿⡿⠿⠿⢿⣧⠀⠀⠀⠀⠀o88o     o8888o o888o  o888o  `Y8bood8P'      `YbodP'    8""88888P'
         ⠀⠀⠀⠀⠀⠀⣿⣿⠀⠀⢿⣿⣿⣿⡿⠿⣿⣿⣷⣄⣀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
         ⠀⠀⠀⠀⠀⠀⢹⣿⠆⠀⢸⣿⣿⣿⠁⠀⢸⣿⣿⣿⣿⡇⠻⡆⠀⠀⠀⠀⠀
         ⠀⠀⠀⠀⠀⠀⢸⡿⠀⢀⣾⡿⠟⠋⠀⠀⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀                           ⚔️ ARGUSv2 ⚔️
         ⠀⠀⠀⠀⠀⢀⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⢿⣿⣿⣿⡀⠀⠀⠀⠀⠀⠀
         ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⠻⠇⠀⠀⠀⠀⠀⠀⠀

# 

> **CRYPTO ADDRESS INTELLIGENCE ENGINE**  
> *by [VERES](https://github.com/vrsmax) · Intelligence without borders*

---

## ◈ CAPABILITIES

```
┌─────────────────────────────────────────────────────────────┐
│  MULTICHAIN SUPPORT                                         │
│  [01] Ethereum + BSC + Polygon + Arbitrum + Base (EVM)      │
│  [02] Bitcoin (BTC)                                         │
│  [03] Tron (TRX)                                            │
│  [04] Solana (SOL)                                          │
│  [05] TON                                                   │
│                                                             │
│  INTELLIGENCE                                               │
│  [06] Address Attribution  · Who owns this address          │
│  [07] Sanctions Check      · OFAC + EU + UN + UK OFSI       │
│  [08] Cluster Analysis     · Behavioural patterns           │
│  [09] Counterparty Map     · Top interacting addresses      │
│  [10] Wallet Profiling     · BOT/TRADER/HOLDER/DORMANT...   │
│  [11] Volume & Age         · IN/OUT, first/last seen        │
│  [12] Funding Source       · Where first funds came from    │
│  [13] Public Mentions      · GitHub repos/commits/issues    │
│  [14] Risk Scoring         · LOW / HIGH / CRITICAL          │
│  [15] Report Export        · Auto-saved .txt report         │
└─────────────────────────────────────────────────────────────┘
```

---

## ◈ INSTALL

```bash
git clone https://github.com/vrsmax/argus
cd argus
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
```
ETHERSCAN_API_KEY=your_key_here
```

> Free key at [etherscan.io](https://etherscan.io/register)

---

## ◈ USAGE

```bash
python argus.py <ADDRESS>
```

**Auto-detects chain by address format:**

```bash
# Ethereum / BSC / Polygon / Arbitrum / Base
python argus.py 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Bitcoin
python argus.py 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa

# Tron
python argus.py TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE

# Solana
python argus.py 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM

# TON
python argus.py EQD2NmD_lH5f5u1Kj3KfGyTvhZSX0Eg6qp2a5IQUKXxOG3a
```

---

## ◈ REPORT SECTIONS

```
  ▓ BALANCES BY CHAIN          · Balance on each active network
  ▓ SANCTIONS CHECK            · OFAC + EU + UN + UK OFSI
  ▓ ADDRESS ATTRIBUTION        · Owner / entity identification
  ▓ CLUSTER ANALYSIS           · Behavioural & structural patterns
  ▓ TOP COUNTERPARTIES         · Most frequent transaction partners
  ▓ KNOWN ENTITY INTERACTIONS  · Exchanges, mixers, contracts
  ▓ WALLET INTELLIGENCE        · Profile, age, volume, funding source
  ▓ PUBLIC MENTIONS            · GitHub appearances
  ▓ SUMMARY                    · Risk + key metrics
```

---

## ◈ RISK LEVELS

```
  ██ CRITICAL  — Address found in sanctions list (OFAC/EU/UN)
  ██ HIGH      — Interaction with mixers / high-risk entities
  ██ LOW       — No matches found
  ██ UNKNOWN   — No transaction history
```

---

## ◈ WALLET PROFILES

```
  BOT              — High frequency, mostly contract calls
  TRADER           — 40%+ DeFi/contract interactions
  BRIDGE/EXCHANGE  — Balanced in/out volume
  HOLDER           — Low activity, long history
  DORMANT          — Inactive 365+ days
  FRESH WALLET     — Created recently
  ACTIVE WALLET    — Regular mixed activity
```

---

## ◈ STACK

```
  Python 3.12+
  Etherscan API v2   (EVM chains — free tier)
  Blockstream API    (Bitcoin — no key)
  Trongrid API       (Tron — no key)
  Solana RPC         (Solana — no key)
  TONCenter API      (TON — no key)
  OFAC / OpenSanctions  (Sanctions lists)
  GitHub Search      (Public mentions)
  pyfiglet · colorama · requests · python-dotenv
```

---

## ◈ PART OF VERES ECOSYSTEM

```
  VERES ────────────────────────────────────────────────────
    ├── VELES     · 1300+ OSINT tool directory
    ├── ARGUS     · Crypto address intelligence  ◄ YOU ARE HERE
    └── MURAMASA  · [in development]
```

---

## ◈ DISCLAIMER

```
┌─────────────────────────────────────────────────────────┐
│  This tool is for OSINT and compliance research only.   │
│  Use responsibly and in accordance with applicable law. │
│  Author bears no responsibility for misuse.             │
└─────────────────────────────────────────────────────────┘
```

---

*ARGUS · VERES · Yerevan · 2025*
