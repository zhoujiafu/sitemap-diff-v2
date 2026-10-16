# AGENTS.md

Cross-platform game monitor. A scheduled crawler fetches sitemaps, diffs
URLs, extracts game titles, and writes them to Supabase; a Next.js Dashboard
reads from the same database.

## Active code vs legacy

The repo contains two trees. Only `lib/` + `web/` are the live V2 (see
`.claude.md` § "架构 (V2.0)" and `.github/workflows/check-sitemaps.yml`).

- **Live — crawler**: `lib/` (Node ESM, run via `npm run check` at repo root).
  Uses `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`.
- **Live — dashboard**: `web/` (Next.js 14 + TypeScript). Uses
  `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- **Legacy — DO NOT EDIT**: `src/` (Cloudflare Workers, Telegram/Discord bots).
  `package.json` scripts (`check`, `dev`, `deploy`) and `wrangler.toml` still
  point at `src/index.js`, but the project does not deploy via Cloudflare
  anymore. Treat `src/` as read-only unless explicitly told otherwise.

## Commands

Run from repo root unless noted.

- `npm run check` — run the crawler once locally (needs `.dev.vars` with
  `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`; `lib/load-env.js` reads it).
- `cd web && npm run dev` — dashboard on http://localhost:3000 (needs
  `web/.env.local` from `web/.env.example`).
- `cd web && npm run build` / `npm start` — production build for the
  dashboard.
- `cd web && npm run lint` — only lint script in the repo (Next.js built-in).

There is no test runner, formatter, or typecheck script. `tsconfig.json`
enables `strict` but Next.js builds it; running plain `tsc` is not wired up.

## Deploy flow

Two independent targets — push code does NOT deploy either automatically.

1. **Crawler** — `.github/workflows/check-sitemaps.yml` runs `npm run check`
   every 4h UTC on schedule (`0 */4 * * *`) and on manual dispatch. Requires
   repo secrets `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`.
2. **Dashboard** — Vercel project `sitemap-diff-v2` (see `.vercel/project.json`).
   `vercel.json` at root declares `framework: nextjs` and `outputDirectory: .next`,
   but the actual Next.js app is in `web/`. Deploy via `vercel --prod` from
   `web/` (per `QUICKSTART.md`) or import the repo in Vercel and override the
   root directory to `web`. Required env: `NEXT_PUBLIC_SUPABASE_URL`,
   `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

## Environment variables

| Where | Variable | Used by |
| --- | --- | --- |
| GitHub Actions secret | `SUPABASE_URL` | crawler |
| GitHub Actions secret | `SUPABASE_SERVICE_KEY` | crawler |
| `web/.env.local` + Vercel | `NEXT_PUBLIC_SUPABASE_URL` | dashboard |
| `web/.env.local` + Vercel | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | dashboard |
| Root `.dev.vars` (gitignored) | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | local crawler |

Note `web/next.config.js` maps `SUPABASE_URL` / `SUPABASE_ANON_KEY` (no
`NEXT_PUBLIC_` prefix) onto the `NEXT_PUBLIC_*` keys for build-time
inlining. If you add new public env vars, mirror them in both
`.env.example` and `next.config.js`.

## Database

`supabase/schema.sql` is the canonical V2 schema (tables: `feeds`, `sitemaps`,
`games`, `game_sources`, `update_logs`; RLS enabled with public-read +
service-write policies). Run it in the Supabase SQL Editor before first
crawl.

Helpers:
- `supabase/migration.sql` — V1 → V2 migration.
- `supabase/diagnose-pollution.sql`, `supabase/clean-polluted-data.sql` —
  data cleanup (run in SQL Editor).
- `supabase/fix-sitemaps-table.sql` — recreate `sitemaps` table.

If the API returns `column does not exist` after a schema change, run
`NOTIFY pgrst, 'reload schema';` in the SQL Editor (see `.claude.md` §
"Schema 刷新").

## Crawler logic worth knowing

`lib/check-sitemaps.js` is the entry point. For each feed it:
1. Downloads the sitemap (handles `.gz` via `zlib.gunzipSync`).
2. Rejects if URL count is 0, drops > 50%, or (first run) < 10 URLs —
   this is the "三层异常检测" guard against empty-sitemap pollution. Don't
   loosen without thinking about the consequences.
3. Diffs new vs stored sitemap content (keyed by `domain`), processes only
   new URLs.
4. `lib/rss-manager.js#extractGameName` extracts game slugs per platform
   (poki, coolmathgames, itch.io, kongregate, armorgames, newgrounds,
   miniclip, y8, friv, generic). New platforms → add a branch before the
   generic fallback block. The `-games` suffix rejection whitelist
   (hunger-games, squid-game, mario-games, pokemon-games, sonic-games) is
   narrow on purpose.

Cross-platform matching uses `normalizeGameName` (lowercase, strip
non-alphanumeric, collapse dashes) to produce `clean_name`.

## Misc

- Root `package.json` declares `"type": "module"` — all Node files are ESM.
- Root scripts use `node lib/...`, not `wrangler` — ignore `wrangler.toml`
  for day-to-day work.
- `scripts/extract_inparams_to_csv.py` is an unrelated one-off Python tool;
  do not call it as part of the pipeline.
- `.dev.vars`, `.vercel/`, `.wrangler/`, `node_modules/` are gitignored.