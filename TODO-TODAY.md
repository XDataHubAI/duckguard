# Today's Tasks (Feb 3, 2026)

## For OC (when back):
- [ ] Enable GitHub Pages: go to github.com/xdatahubai-a11y/duckguard-ai → Settings → Pages → Source: Deploy from branch → Branch: `gh-pages` / `/ (root)` → Save
- [ ] Docs will be live at: https://xdatahubai-a11y.github.io/duckguard-ai/

## Completed:

### 1. Dev Environment (10 min)
- [ ] Create venv: `python3 -m venv .venv && source .venv/bin/activate`
- [ ] Install: `pip install -e ".[dev]"`
- [ ] Verify: `duckguard --version`

### 2. Test Suite (15 min)
- [ ] Run: `pytest tests/ -v --tb=short`
- [ ] Fix any failures
- [ ] Run: `ruff check src/`
- [ ] Fix any lint issues

### 3. Verify Examples (15 min)
- [ ] Run: `python examples/basic_usage.py`
- [ ] Run: `python examples/profiler_example.py`
- [ ] Run: `duckguard check examples/sample_data/orders.csv --config examples/sample_data/duckguard.yaml`
- [ ] Run: `duckguard profile examples/sample_data/orders.csv`
- [ ] Run: `duckguard discover examples/sample_data/orders.csv`

### 4. Build Docs (10 min)
- [ ] Install: `pip install mkdocs-material mkdocstrings[python] pymdown-extensions`
- [ ] Build: `mkdocs build`
- [ ] Preview: `mkdocs serve` (check in browser)
- [ ] Fix any broken links/content

### 5. Git Operations (10 min)
- [ ] Configure git: `git config user.name "Tar" && git config user.email "tar@openclaw.ai"`
- [ ] Check status: `git status`
- [ ] Stage new files: docs/*, launch/*, ROADMAP.md, SECURITY.md, CODE-REVIEW.md, etc.
- [ ] Stage fixes: src/duckguard/core/column.py, checks/conditional.py
- [ ] Commit: `git commit -m "docs: add MkDocs site, launch materials, security improvements"`
- [ ] Push: (need to confirm git credentials with OC)

### 6. Deploy Docs (5 min)
- [ ] Run: `mkdocs gh-deploy` (deploys to GitHub Pages)
- [ ] Verify: Check the live URL

## Already Done Today:
- [x] Full codebase review (27K LOC)
- [x] 34 documentation pages written
- [x] Launch materials (HN, Reddit, Twitter, LinkedIn posts)
- [x] Competitive analysis
- [x] ROADMAP.md
- [x] SQL escaping fixes (column.py, conditional.py)
- [x] SECURITY.md + dependabot.yml
- [x] py.typed marker
- [x] CODE-REVIEW.md
- [x] 30-min update cron
