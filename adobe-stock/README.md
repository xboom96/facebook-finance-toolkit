# `adobe-stock/` — batch metadata generator for stock contributors

You have **two Adobe Stock contributor accounts** — that is real passive income potential. The bottleneck for almost every contributor is **metadata**: title + 30–50 keywords per asset. Get the metadata wrong and the asset never surfaces in search.

This folder gives you a Python tool to **batch-generate title + keywords for every asset in a folder** (images or videos) and write it to a CSV that Adobe Stock's Contributor Portal can import directly.

> Adobe Stock does not publish a contributor-upload API. The official workflows are: (a) drag-and-drop on the portal, or (b) SFTP upload + CSV metadata. This tool produces (b).

---

## What you get

```
adobe-stock/
├── prep.py            # the batch metadata generator
├── keywords.py        # niche-specific keyword libraries
└── stock-strategy.md  # what to actually shoot/render to earn $$
```

`prep.py` walks a folder of media files and writes `adobe_stock.csv` in the
**exact format** Adobe Stock accepts (Filename, Title, Keywords, Category,
Releases). It uses:

- Filename parsing (e.g. `coins-stacking-finance-001.jpg` → keywords `coins`,
  `stacking`, `finance`).
- Optional OpenAI vision call (if `OPENAI_API_KEY` is set) to generate
  better titles and additional keywords from the image contents.
- A curated keyword library in `keywords.py` covering Adobe Stock's
  highest-CPM niches: finance, business, AI/tech, lifestyle.

---

## Setup

```bash
# No mandatory deps — uses stdlib only
# Optional: install Pillow if you want auto image analysis without OpenAI
pip install Pillow
```

---

## Usage

### 1. Drop all your assets in a folder

```
assets/
  finance/
    coins-stack-001.jpg
    stock-chart-green-arrow.mp4
    laptop-spreadsheet-budget.jpg
    ...
```

### 2. Run the prep tool

```bash
python3 adobe-stock/prep.py assets/finance/ --niche finance --out adobe_stock.csv
```

You'll get a `adobe_stock.csv` like:

| Filename | Title | Keywords | Category |
|---|---|---|---|
| coins-stack-001.jpg | Stack of coins on dark background — saving money concept | coins, stack, saving, money, finance, dollar, cash, investment, ... | 1 |
| stock-chart-green-arrow.mp4 | Rising green stock market chart on dark display | stock, market, chart, rising, green, arrow, finance, trading, ... | 5 |
| ... | ... | ... | ... |

### 3. Upload assets via SFTP to Adobe Stock

Adobe Stock will match the CSV by filename and apply your title + keywords.

### 4. Niches the keyword library covers

```bash
python3 adobe-stock/prep.py assets/ --niche finance      # personal finance / investing
python3 adobe-stock/prep.py assets/ --niche business     # corporate / meetings
python3 adobe-stock/prep.py assets/ --niche ai-tech      # AI, robots, tech
python3 adobe-stock/prep.py assets/ --niche lifestyle    # frugal living, home
python3 adobe-stock/prep.py assets/ --niche custom --keywords "your,custom,list"
```

### 5. With OpenAI vision (better titles, ~$0.001/image)

```bash
export OPENAI_API_KEY="sk-..."
python3 adobe-stock/prep.py assets/finance/ --niche finance --use-vision
```

---

## Strategy notes

See [`stock-strategy.md`](./stock-strategy.md) for what's actually selling
on Adobe Stock right now (finance, AI, business, sustainable living) and
how to systematically produce 50+ sellable assets/month.

---

## Realistic numbers

Pure passive income compounds slowly:

| Month | Active portfolio | Expected monthly earnings |
|---|---|---|
| 1 | 50 assets | $0–$20 |
| 3 | 150 assets | $30–$100 |
| 6 | 300 assets | $80–$300 |
| 12 | 600 assets | $200–$800 |
| 24 | 1,200 assets | $500–$2,500 |

The math works if you stay consistent: 10 new assets/week × 52 weeks = 520
new assets/year. At the 12-month mark you're earning ~$500/month on
autopilot.
