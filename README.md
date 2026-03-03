# WeChat Article to PDF Generator

A production-oriented web app that converts WeChat Official Account articles into readable PDFs with better formatting, preview, and flexible save routing.

## Highlights

- **Article fetching with fallback chain**
  - Direct fetch (requests)
  - Remote fallback (no sudo required)
  - Optional browser fallback (Playwright)
- **PDF generation modes**
  - Styled generator (WeChat-like typography)
  - Optional **browser print to PDF** mode
- **Formatting support**
  - Bold / italic / bold-italic
  - Better paragraph spacing and Chinese text handling
- **Web preview workflow**
  - Preview article content before generation
  - Preview generated PDF in-browser (no forced download)
- **Save destination control**
  - Default folder
  - Per-author folder routing
  - Custom fixed folder
  - Remember preferences (no repeated prompts)
- **Author path mapping UI**
  - Bind specific author -> specific local path
  - Manage (add/remove) mappings from the UI

## Quick Start

### Requirements

- Python 3.10+
- Linux/macOS/Windows
- For browser fallback/print mode: Playwright + Chromium

### Install

```bash
git clone https://github.com/kindom-builder/wechat-pdf-generator.git
cd wechat-pdf-generator
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Optional (browser fallback / browser print):

```bash
venv/bin/pip install playwright
venv/bin/playwright install chromium
```

### Run

```bash
python3 start_server.py
```

Then open:

- `http://127.0.0.1:8080/`

## Main UI Features

1. Paste WeChat URL
2. (Optional) Set custom title
3. Choose save strategy:
   - default
   - by author
   - fixed custom path
4. Toggle fallbacks:
   - remote fallback (recommended)
   - browser fallback
5. Optional: use browser print mode
6. Generate and preview PDF inline

## API Overview

- `GET /api/status`
- `POST /api/preview`
- `POST /api/generate`
- `GET /api/list`
- `GET /api/view/<filename>`
- `GET /api/download/<filename>`
- `GET /api/save-prefs`
- `POST /api/save-prefs`
- `GET /api/author-paths`
- `POST /api/author-paths`
- `DELETE /api/author-paths`

## Notes

- Browser sandbox / missing system libs may break Playwright on minimal systems.
- If that happens, keep **remote fallback** enabled (works without sudo).
- Some WeChat pages are access-restricted; success rate depends on upstream controls.

## License

MIT
