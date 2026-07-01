# Testing okfgen locally (VS Code, Windows/PowerShell)

A step-by-step guide to run and exercise okfgen on your own machine. Commands
are PowerShell (the default VS Code terminal on Windows); on macOS/Linux swap
`.\.venv\Scripts\Activate.ps1` for `source .venv/bin/activate` and `\` for `/`.

## A. Open the project
1. **File → Open Folder…** → the repo root.
2. Install the **Python** extension (`ms-python.python`) if prompted — this repo
   also recommends it via [`.vscode/extensions.json`](.vscode/extensions.json).
3. Open the integrated terminal: **Ctrl+`** .

## B. Create an environment and install
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # prompt shows (.venv)
python -m pip install --upgrade pip
pip install -e ".[dev,all]"           # editable install + tests + cloud extras
```
- If activation is blocked (*"running scripts is disabled"*):
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then re-activate.
- Don't need the BigQuery/Firebase producers? Use `pip install -e ".[dev]"`;
  every other producer/consumer still works.

Then **Ctrl+Shift+P → "Python: Select Interpreter"** → choose `.venv`. VS Code
will use it for the Testing panel and the tasks below.

## C. Run the tests
```powershell
pytest -q                              # expect: 56 passed
```
Or open the **Testing** panel (beaker icon) and click **Run Tests**. The pytest
integration is pre-configured in [`.vscode/settings.json`](.vscode/settings.json).

## D. Drive the tool
The editable install adds an `okfgen` command. Equivalent without installing:
`python -m okfgen.cli …`.

```powershell
# 1) PRODUCE from a local folder (the bundled sample app)
okfgen generate .\samples\recipes\petclinic_app -o .\out\petclinic --overwrite

# 2) PRODUCE from a database schema file (no cloud) and ENRICH it
okfgen generate .\samples\recipes\acme_sales.schema.json -o .\out\acme --overwrite
okfgen enrich .\out\acme               # infer FK join paths + backlinks

# 3) CONSUME — search, ask, validate
okfgen search   .\out\acme "orders customer"
okfgen ask      .\out\acme "how do I join orders to customers?"
okfgen validate .\out\acme

# 4) VISUALIZE — a self-contained HTML graph
okfgen visualize .\out\acme -o .\out\acme\graph.html
Invoke-Item .\out\acme\graph.html      # open in your browser
```

### Network-backed producers (live demos, no API keys)
```powershell
# CKAN — Toronto Open Data (E. coli beach readings)
okfgen generate "ckan:https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/toronto-beaches-water-quality" -o .\out\beaches --overwrite

# Socrata — NYC Open Data (311 service requests)
okfgen generate "socrata:https://data.cityofnewyork.us/d/erm2-nwe9" -o .\out\nyc311 --overwrite

# Git repo
okfgen generate https://github.com/octocat/Hello-World.git -o .\out\hello --overwrite
```

## E. View a graph inside VS Code
- Quick: `Invoke-Item .\out\acme\graph.html` (opens your default browser).
- In-editor: run the **"okfgen: serve docs site"** task (or
  `python -m http.server 8100 --directory .\out\acme`), then
  **Ctrl+Shift+P → "Simple Browser: Show"** → `http://localhost:8100/graph.html`.

## F. Rebuild samples / Pages
```powershell
python samples\build_samples.py        # 3 offline bundles (reproducible)
python samples\build_live_samples.py   # live Toronto beaches bundle (needs net)
python samples\build_pages.py          # regenerates docs\ for GitHub Pages
```

## VS Code tasks & debug configs
Pre-defined in [`.vscode/tasks.json`](.vscode/tasks.json) — run via
**Ctrl+Shift+P → "Tasks: Run Task"**:
- **okfgen: install (editable, dev+all)**
- **okfgen: run tests**
- **okfgen: generate acme sample**
- **okfgen: visualize acme sample**
- **okfgen: serve docs site**

Debug the CLI itself via **Run and Debug** (F5) using
[`.vscode/launch.json`](.vscode/launch.json).

## Command reference
| Command | Role |
|---|---|
| `okfgen generate <src>` | producer: git · local · schema · `bq:` · `firebase:` · `ckan:` · `socrata:` · http docs |
| `okfgen enrich <bundle>` | enrichment agent (join paths + backlinks) |
| `okfgen search <bundle> <q>` | search-index consumer |
| `okfgen ask <bundle> <q>` | reasoning-agent consumer |
| `okfgen visualize <bundle>` | HTML graph consumer |
| `okfgen validate <bundle>` | OKF conformance check |

Add `-h` to any command for its full options.
