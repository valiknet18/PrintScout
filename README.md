<div align="center">

<img src="webapp/public/icon.png" alt="PrintScout" width="160" />

# PrintScout

**Find 3D-printable models that actually fit on your printer.**
A Telegram mini app that searches Printables (and more), parses the actual STL,
and tells you whether it fits your bed before you download.

[![Try the bot](https://img.shields.io/badge/Try%20it-%40print__scout__bot-2AABEE?logo=telegram&logoColor=white)](https://t.me/print_scout_bot)
[![Backend](https://img.shields.io/website?url=https%3A%2F%2Fprintscout-white-thunder-7639.fly.dev%2Fhealth&label=backend&up_color=brightgreen&down_color=red&up_message=up&down_message=down)](https://printscout-white-thunder-7639.fly.dev/health)
[![Mini app](https://img.shields.io/website?url=https%3A%2F%2Fprintscout-lac.vercel.app&label=mini%20app&up_color=brightgreen&down_color=red&up_message=up&down_message=down)](https://printscout-lac.vercel.app)
[![Sponsor](https://img.shields.io/github/sponsors/valiknet18?label=Sponsor&logo=GitHub-Sponsors&color=ea4aaa)](https://github.com/sponsors/valiknet18)

</div>

---

## What it does

- 🔎 **Smart search** across model marketplaces (Printables today; Thingiverse and more wired but dormant).
- 📐 **Real fit checks** — downloads the STL, parses the bounding box with `trimesh`, compares to your printer's build volume (with rotation support and a configurable margin).
- 🌍 **Multilingual** — type in Ukrainian, Russian, Chinese, Japanese, etc.; the query is auto-translated to English (MyMemory) before hitting source catalogs.
- ❤️ **Likes + leaderboard** — community-curated front page sorted by global like count, with per-source fallback when nothing's been liked yet.
- 📚 **Collections** — Pinterest-style boards for saving models. A model can live in many.
- ⚙️ **Multiple printers per user** — switch context per search, fit checks adapt to the active printer.

## Architecture

| Piece | Tech | Hosted on |
|---|---|---|
| Mini app | React 19 · Vite · TypeScript · Tailwind v4 · TanStack Query · `@telegram-apps/sdk-react` | Vercel |
| Backend | Python 3.12 · FastAPI · aiogram 3 · SQLAlchemy 2 (async) · Alembic · `trimesh` | Fly.io |
| Database | PostgreSQL | Neon |
| Translation | MyMemory (free public API) | n/a |
| Cache | In-memory (per-machine) | n/a |

The webapp uses Vercel rewrites to proxy `/api/*` to Fly — same-origin from the browser, no CORS, no env-var juggling for `VITE_API_BASE_URL`.

The bot runs in **webhook** mode in production and falls back to **polling** in local dev (when `PUBLIC_BASE_URL` isn't HTTPS).

## Repo layout

```
printscout/
├── backend/                  Python — FastAPI + aiogram
│   ├── app/
│   │   ├── api/              REST routes (search, fit, model, popular, collections, likes)
│   │   ├── bot/              aiogram dispatcher + /start handler
│   │   ├── core/             settings, db, in-memory cache
│   │   ├── matcher/          STL bbox parse + fit-vs-buildvolume math
│   │   ├── sources/          Adapter per marketplace (Printables, Thingiverse)
│   │   ├── models.py         SQLAlchemy ORM
│   │   ├── translation.py    Auto-translate non-English queries
│   │   └── main.py           App factory, lifespan, webhook/polling switch
│   ├── alembic/              Migrations
│   ├── Dockerfile
│   └── fly.toml
├── webapp/                   React mini app
│   ├── src/
│   │   ├── pages/            Home, Search, ModelDetail, Collections, Likes, Printers, …
│   │   ├── components/       ModelCard, PrinterCard, AddToCollectionSheet, …
│   │   └── lib/              api client, telegram-sdk wrapper, recents, likes hooks
│   └── vercel.json           /api rewrite to Fly
├── docker-compose.yml        Local Postgres
└── .env.example
```

## Local development

Requirements: Python 3.12+, [uv](https://github.com/astral-sh/uv), Node 20+, Docker, a Telegram bot token from `@BotFather`.

```bash
# 1. Postgres
docker compose up -d

# 2. Backend
cd backend
cp ../.env.example .env       # edit BOT_TOKEN; everything else has dev defaults
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# 3. Mini app (separate terminal)
cd webapp
npm install
npm run dev
```

Local-dev shortcut: set `DEV_FAKE_USER_ID=42` in `.env` to bypass Telegram `initData` validation and click around the mini app at `http://localhost:5173` in a regular browser tab. **Must be `0` or unset in production.**

To launch the mini app inside Telegram from your laptop, expose Vite via a tunnel and set `WEBAPP_URL` accordingly:

```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:5173
# copy the https URL into backend/.env as WEBAPP_URL, restart backend
```

## Deploy

The repo is wired to deploy automatically on push to `main`:

- **Vercel** (mini app) — auto-deploy via GitHub integration.
- **Fly.io** (backend) — `flyctl deploy` from `backend/`. `release_command = "alembic upgrade head"` keeps the schema in sync.
- **Neon** Postgres — free tier, EU region, pooled connection string.

## Roadmap

- [ ] Add more sources (MyMiniFactory, Thangs, STLFinder)
- [ ] Cross-source dedup (same model uploaded in multiple places)
- [ ] Direct in-Telegram file delivery for small STLs
- [ ] Push notifications when liked authors publish new models
- [ ] Per-source toggle in the search filter sheet

## License

Code is MIT-licensed unless stated otherwise. Model files served from third-party catalogs remain under their original licenses — PrintScout doesn't host or re-distribute model content.

## Support

If PrintScout saves you time finding fitting models, consider sponsoring further development:

[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-on%20GitHub-ea4aaa?logo=github-sponsors&logoColor=white)](https://github.com/sponsors/valiknet18)

Sources I lean on for ongoing data:
- [Printables](https://www.printables.com) — primary catalog
- [MyMemory](https://mymemory.translated.net) — translation
- [trimesh](https://github.com/mikedh/trimesh) — STL parsing

---

<div align="center">
<sub>Built with Claude Code. Telegram bot:
<a href="https://t.me/print_scout_bot">@print_scout_bot</a></sub>
</div>
