# VZ Voice Agent — Build Checklist (Gate 0)

Project: Vodafone Ziggo Voice AI Demonstration Agent
Repo: https://github.com/horseback-jp/zig-voice-build
App: jph-zig-voice-agent (projects/ces-demo-emea/locations/us/apps/a76b5888-1d16-413c-9a3b-2f8d10c0b180)
Working dir: ~/Documents/claude-working-area/vz-voice-agent

## Build Gates

- [x] 1. Requirements gathered — PRD saved to sources/prd.md (gate 1)
- [x] 2. TDD drafted + user approval (gate 2)
- [x] 3. Scaffold app — cxas_app/jph_zig_voice_agent/ (gate 3)
- [x] 4. Lint clean — cxas lint (gate 4) — 0 errors, 0 warnings
- [ ] 5. Generate evals (gate 5)
- [ ] 6. Push to GitHub + deploy.yml triggers CI deployment (gate 6)

## Repo Structure to Create

- `.github/workflows/deploy.yml` — CI deploy (adapted from banking-demo)
- `cxas_app/jph_zig_voice_agent/` — agent code (agents, tools, app.json, global_instruction.txt)
- `evals/goldens/` — golden eval YAMLs
- `evals/simulations/simulations.yaml`
- `scratch/prune_gecx_assets.py` — from agent-repo-sync (generic version)
- `gecx-config.json` — project/location/app config
- `tdd.md` — TDD (gate 2)

## Notes

- Deploy: GitHub push → GitHub Actions (never local cxas push)
- WIF: projects/1097682577517/locations/global/workloadIdentityPools/github-pool/providers/github-provider
- Service account: github-deployer@ces-demo-emea.iam.gserviceaccount.com
- Default language: en-GB (Dutch nl-NL secondary, explicit-switch-only pattern)
- Voice: to be confirmed — use en-GB-Chirp3-HD voice (TBD exact voice name)
- Prune script: use agent-repo-sync generic version (supports Tools, Toolsets, Sub-Agents, Variables)
