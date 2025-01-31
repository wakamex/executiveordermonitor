# Executive Order Monitor

Monitors the Federal Register API for new Executive Orders. Features:
- Real-time monitoring with adaptive polling (1s → 5s → 10s → 30s → 60s)
- Caches seen EOs to avoid duplicates
- Smart backoff on API errors
- Rate limit awareness

## Usage

Run using any of these methods:

1. With uvx:
```bash
uvx executiveordermonitor
```

## Installation

Requirements:
- Python 3.8+
- requests>=2.32.3

From PyPI:
```bash
pip install executiveordermonitor
```

From source:
```bash
# Clone the repository
git clone https://github.com/wakamex/executiveordermonitor.git
cd executiveordermonitor

# Create virtual environment
.venv/bin/python -m venv .venv
source .venv/bin/activate
```

2. Run as a Python module:
```bash
python -m executiveordermonitor
```

3. Run as an installed script:
```bash
executiveordermonitor
```

The monitor will:
- Start checking every 1 second
- If errors occur, gradually back off to longer intervals (5s → 10s → 30s → 60s)
- Return to faster intervals when API is responsive
- Cache seen EOs in `seen_eos.json` to avoid duplicate notifications

Each time a new Executive Order is found, it will display:
- Title
- EO Number
- Signing Date
- URL to the full document

## License
MIT License. See [LICENSE](LICENSE) file for details.
