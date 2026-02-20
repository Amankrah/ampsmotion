# AmpsMotion

**Desktop scoring system for AmpeSports** — digitising the officiating workflow for AmpeSports, a Ghanaian indigenous sport built on rhythmic foot-tapping exchanges.

- **Stack:** Python 3.11+ · PySide6 · SQLite · OpenCV  
- **Platforms:** Windows 10+, macOS 12+, Ubuntu 22.04+

---

## What it does

AmpsMotion serves three audiences:

| Audience | Role |
|----------|------|
| **Ampfres (Officials)** | Set up matches, record Opa/Oshi calls and scores, manage timers, track fouls, handle substitutions and eliminations. |
| **Audience / Broadcast** | Second-screen live scoreboard with current match state, scores, rounds, and standings. |
| **Video Assistant Ampfre (VAR)** | Camera feed with instant-replay and highlight clipping. |

Game modes (per Official AmpeSports Rules): **1 vs 1**, **Team vs Team (Shooter Mode)**, and **Tournament**.

---

## Quick start

### Requirements

- Python 3.11+
- See [pyproject.toml](pyproject.toml) for dependencies.

### Install and run

```bash
# Clone the repo (after pushing to GitHub)
git clone https://github.com/YOUR_USERNAME/ampsmotion.git
cd ampsmotion

# Create virtual environment and install
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -e ".[dev]"

# Run the app
python main.py
```

### Tests

```bash
pytest
```

---

## Project layout

```
ampsmotion/
├── main.py              # Entry point
├── app.py               # QApplication, window management
├── config.py            # Settings, paths
├── models/              # SQLAlchemy ORM (match, bout, player, foul, tournament)
├── engine/              # Game logic: scoring, timer, rules (no GUI)
├── gui/                 # PySide6 UI (Ampfre console, audience display, VAR)
├── camera/              # OpenCV capture, ring buffer, replay
├── services/            # Event bus, export, backup
├── migrations/           # Alembic
├── tests/
├── pyproject.toml
└── AmpsMotion_Engineering_Guide.md   # Full spec and architecture
```

---

## Documentation

- **[AmpsMotion_Engineering_Guide.md](AmpsMotion_Engineering_Guide.md)** — Full engineering guide: domain model, architecture, database schema, scoring engine, GUI design, camera/VAR, event bus, testing, and roadmap.

---

## Pushing to GitHub

From the project root:

```bash
git init
git add .
git commit -m "Initial commit: AmpsMotion desktop scoring for AmpeSports"

# Create a new repository on GitHub (github.com/new), then:
git remote add origin https://github.com/YOUR_USERNAME/ampsmotion.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username (or org). If you use SSH:

```bash
git remote add origin git@github.com:YOUR_USERNAME/ampsmotion.git
```

---

## License

MIT
