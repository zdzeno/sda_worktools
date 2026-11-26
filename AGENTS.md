# Agent instructions

This repo is a Python monorepo of **local desktop** tools for SDA/Copyright workflows. Prefer small, focused changes; match existing Poetry layout under `apps/`.

## Agent skills

### Issue tracker

GitHub Issues on **zdzeno/sda_worktools** (`gh` CLI). See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `GLOSSARY.md` + `docs/adr/` at the repo root when they exist; overview in `README.md`. See `docs/agents/domain.md`.

## Engineering skills (Matt Pocock)

Install additional skills from [mattpocock/skills](https://github.com/mattpocock/skills) as needed, e.g.:

```bash
npx skills@latest add mattpocock/skills --skill=<name> -a cursor
```

Repo config for those skills lives under `docs/agents/`. Copied skill files live under `.agents/skills/`.