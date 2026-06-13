import os
import sys
import json
import re
import urllib.request
import pdfplumber
from datetime import datetime, timezone

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config


# Primary keywords — pages must have these to be considered financial statements
PRIMARY_KEYWORDS = [
    'Earnings per share',
    'earnings per share',
    'Profit after tax',
    'profit after tax',
    'Profit before tax',
    'profit before tax',
    'Interest income',
    'interest income',
]

# Secondary keywords — used to boost page score but not required
SECONDARY_KEYWORDS = [
    'Return on equity',
    'Total equity',
    'total equity',
    'Total assets',
    'total assets',
    'Revenue',
    'Gross earnings',
]

# Known company name patterns for auto-matching
COMPANY_NAME_PATTERNS = {
    'GTCO': ['guaranty trust', 'gtco', 'gtbank'],
    'ZENITHBANK': ['zenith bank', 'zenith bank plc'],
    'DANGSUGAR': ['dangote sugar', 'dangote sugar refinery'],
    'FIRSTHOLDCO': ['first holdco', 'firstbank', 'first bank of nigeria', 'fbn holdings'],
    'NB': ['nigerian breweries', 'nigerian breweries plc'],
    'STANBIC': ['stanbic ibtc', 'stanbic'],
    'MTNN': ['mtn nigeria', 'mtn communications'],
    'OANDO': ['oando plc', 'oando'],
    'DANGCEM': ['dangote cement', 'dangote cement plc'],
    'BUACEMENT': ['bua cement', 'bua cement plc'],
    'WAPCO': ['lafarge africa', 'lafarge africa plc', 'wapco'],
}

MAX_FINANCIAL_PAGES = 20
CHAR_LIMIT = 14000


class QwenExtractor:
    """
    Extracts financial metrics from company annual/quarterly report PDFs.
    Supports auto-matching PDFs to stock symbols based on company name detection.
    """

    def __init__(self):
        self.api_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {config.QWEN_API_KEY}",
            "Content-Type": "application/json"
        }

    # ------------------------------------------------------------------
    # AUTO-MATCHING
    # ------------------------------------------------------------------

    def detect_symbol_from_pdf(self, pdf_path: str) -> str:
        """
        Reads first 5 pages of a PDF and tries to match company name
        to a known NGX symbol using COMPANY_NAME_PATTERNS.
        Returns symbol string or None if no match found.
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ''
                for page in pdf.pages[:5]:
                    text += (page.extract_text() or '').lower()

            for symbol, patterns in COMPANY_NAME_PATTERNS.items():
                for pattern in patterns:
                    if pattern.lower() in text:
                        return symbol

        except Exception as e:
            print(f"  Auto-detect error: {e}")

        return None

    def auto_build_pdf_map(self, pdf_dir: str = None) -> dict:
        """
        Scans pdf_dir for all PDF files, attempts to auto-match each
        to a symbol, returns {symbol: pdf_path} dict.
        Falls back to filename-based matching if text detection fails.
        """
        if pdf_dir is None:
            pdf_dir = config.PDF_DIR

        pdf_map = {}
        pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]

        print(f"Found {len(pdf_files)} PDFs in {pdf_dir}")

        for filename in pdf_files:
            pdf_path = os.path.join(pdf_dir, filename)
            symbol = None

            # Method 1 — try text-based detection
            print(f"  Detecting: {filename}")
            symbol = self.detect_symbol_from_pdf(pdf_path)

            if symbol:
                print(f"    → Matched to {symbol} (text detection)")
            else:
                # Method 2 — fallback: extract symbol from filename
                # Expects format: SYMBOL_*.pdf e.g. GTCO_FY2025.pdf
                name_part = filename.split('_')[0].upper()
                if name_part in COMPANY_NAME_PATTERNS:
                    symbol = name_part
                    print(f"    → Matched to {symbol} (filename)")
                else:
                    print(f"    → No match found, skipping")
                    continue

            # If symbol already matched to a PDF, keep the one with more pages
            if symbol in pdf_map:
                existing_pages = self._get_page_count(pdf_map[symbol])
                new_pages = self._get_page_count(pdf_path)
                if new_pages > existing_pages:
                    pdf_map[symbol] = pdf_path
                    print(f"    → Replaced previous {symbol} PDF (more pages)")
            else:
                pdf_map[symbol] = pdf_path

        return pdf_map

    def _get_page_count(self, pdf_path: str) -> int:
        """Returns page count of a PDF."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # PAGE DETECTION
    # ------------------------------------------------------------------

    def score_page(self, text: str) -> int:
        """
        Scores a page based on financial keyword density.
        Higher score = more likely to be a financial statement page.
        Primary keywords worth 3 pts, secondary worth 1 pt.
        Also checks for dense number patterns (tables).
        """
        score = 0
        text_lower = text.lower()

        for kw in PRIMARY_KEYWORDS:
            if kw.lower() in text_lower:
                score += 3

        for kw in SECONDARY_KEYWORDS:
            if kw.lower() in text_lower:
                score += 1

        # Bonus for dense number patterns (financial tables)
        numbers = re.findall(r'\b\d{3,}\b', text)
        if len(numbers) > 20:
            score += 2
        if len(numbers) > 50:
            score += 3

        return score

    def find_financial_pages(self, pdf_path: str) -> list[int]:
        """
        Scores all pages and returns indices of highest-scoring ones.
        Prioritizes pages with actual financial table data.
        """
        page_scores = []

        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            print(f"  Scanning {total} pages...")

            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ''
                score = self.score_page(text)
                if score > 0:
                    page_scores.append((i, score))

        # Sort by score descending, take top MAX_FINANCIAL_PAGES
        page_scores.sort(key=lambda x: x[1], reverse=True)
        top_pages = [idx for idx, score in page_scores[:MAX_FINANCIAL_PAGES]]

        # Re-sort by page number (sequential order for context)
        top_pages.sort()

        print(f"  Top financial pages (by score): {[p+1 for p in top_pages[:10]]}")
        return top_pages

    # ------------------------------------------------------------------
    # TEXT EXTRACTION
    # ------------------------------------------------------------------

    def extract_text_from_pages(self, pdf_path: str, page_indices: list[int]) -> str:
        """Extracts text from specified pages, concatenated with page markers."""
        text = ''
        with pdfplumber.open(pdf_path) as pdf:
            for i in page_indices:
                page_text = pdf.pages[i].extract_text() or ''
                text += f'\n--- PAGE {i+1} ---\n{page_text}'
        return text

    # ------------------------------------------------------------------
    # QWEN CALL
    # ------------------------------------------------------------------

    def call_qwen(self, text: str, symbol: str) -> dict:
        """
        Sends financial text to Qwen with structured extraction prompt.
        Returns parsed JSON dict or None on failure.
        """
        prompt = f"""You are a precise financial data extractor for Nigerian company reports.
Extract ONLY the following metrics from the financial statements below for {symbol}.

Return ONLY a valid JSON object with exactly these keys.
If a value cannot be found with certainty, use null. Never guess or estimate.
All monetary values should be in Nigerian Naira (NGN).
Percentages should be numbers only (e.g. 28.5 not "28.5%").

Required JSON:
{{
  "symbol": "{symbol}",
  "period": null,
  "EPS": null,
  "EPS_prior_year": null,
  "ROE_percent": null,
  "revenue": null,
  "revenue_prior_year": null,
  "revenue_growth_percent": null,
  "profit_after_tax": null,
  "profit_after_tax_prior_year": null,
  "profit_growth_percent": null,
  "total_assets": null,
  "total_equity": null,
  "total_liabilities": null,
  "debt_to_equity": null,
  "currency": "NGN",
  "figures_in": null
}}

Rules:
- figures_in: state the unit used in the report ("thousands", "millions", "billions")
- debt_to_equity: calculate as total_liabilities / total_equity if both values present
- revenue_growth_percent: calculate as ((current - prior) / prior) * 100 if both present
- profit_growth_percent: calculate as ((current - prior) / prior) * 100 if both present
- ROE_percent: calculate as (profit_after_tax / total_equity) * 100 if both present
- For banks: use "Interest income" or "Gross earnings" as revenue
- For non-banks: use "Revenue" or "Turnover" as revenue

FINANCIAL STATEMENTS:
{text[:CHAR_LIMIT]}

Return ONLY the JSON object. No explanation. No markdown. No code blocks."""

        payload = json.dumps({
            "model": config.QWEN_MODEL,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()

        req = urllib.request.Request(
            self.api_url,
            data=payload,
            headers=self.headers
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                raw = result['choices'][0]['message']['content'].strip()

                # Strip markdown if present
                if '```' in raw:
                    parts = raw.split('```')
                    for part in parts:
                        part = part.strip()
                        if part.startswith('json'):
                            part = part[4:].strip()
                        if part.startswith('{'):
                            raw = part
                            break

                return json.loads(raw.strip())

        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            print(f"  Raw response: {raw[:200]}")
            return None
        except Exception as e:
            print(f"  Qwen API error: {e}")
            return None

    # ------------------------------------------------------------------
    # MAIN EXTRACT METHODS
    # ------------------------------------------------------------------

    def extract(self, pdf_path: str, symbol: str) -> dict:
        """Full extraction pipeline for one PDF."""
        print(f"\n[{symbol}] Extracting from {os.path.basename(pdf_path)}")

        if not os.path.exists(pdf_path):
            print(f"  ERROR: PDF not found")
            return None

        financial_pages = self.find_financial_pages(pdf_path)

        if not financial_pages:
            print(f"  ERROR: No financial pages found")
            return None

        text = self.extract_text_from_pages(pdf_path, financial_pages)
        print(f"  Text length: {len(text)} chars")

        result = self.call_qwen(text, symbol)

        if not result:
            print(f"  ERROR: Extraction failed")
            return None

        result['extracted_at'] = datetime.now(timezone.utc).isoformat()
        result['source_pdf'] = os.path.basename(pdf_path)

        os.makedirs(config.EXTRACTED_DIR, exist_ok=True)
        period = result.get('period') or 'unknown'
        output_path = os.path.join(config.EXTRACTED_DIR, f"{symbol}_{period}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        print(f"  Saved to {output_path}")

        return result

    def extract_all(self, pdf_map: dict = None) -> dict:
        """
        Runs extraction for multiple stocks.
        If pdf_map not provided, auto-detects from PDF_DIR.
        """
        if pdf_map is None:
            print("Auto-detecting PDFs...")
            pdf_map = self.auto_build_pdf_map()

        if not pdf_map:
            print("No PDFs found or matched.")
            return {}

        print(f"\nProcessing {len(pdf_map)} PDFs: {list(pdf_map.keys())}")
        results = {}

        for symbol, pdf_path in pdf_map.items():
            result = self.extract(pdf_path, symbol)
            if result:
                results[symbol] = result

        print(f"\n{'='*50}")
        print(f"EXTRACTION SUMMARY — {len(results)}/{len(pdf_map)} successful")
        print(f"{'='*50}")
        for sym, data in results.items():
            eps = data.get('EPS') or 'null'
            roe = data.get('ROE_percent') or 'null'
            rev_growth = data.get('revenue_growth_percent') or 'null'
            pat_growth = data.get('profit_growth_percent') or 'null'
            print(f"  {sym:<15} EPS={eps}  ROE={roe}%  RevGrowth={rev_growth}%  PATGrowth={pat_growth}%")

        return results


if __name__ == "__main__":
    extractor = QwenExtractor()
    # Auto-detect all PDFs in data/pdfs/ — no manual input needed
    results = extractor.extract_all()