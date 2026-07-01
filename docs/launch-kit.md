# okfgen launch kit

Ready-to-post copy for launching okfgen, tuned to the **"make your systems
agent-readable in one command"** angle. Edit the voice to sound like you before
posting.

**Canonical links to reuse:**
- Repo: https://github.com/bushans/okfgen
- Live demo: https://bushans.github.io/okfgen/
- PyPI: https://pypi.org/project/okfgen/

---

## Suggested sequence

Don't fire everything in one hour — space it over a few days so momentum
compounds:

1. **Record the demo GIF first** (see [RECORD_DEMO.md](RECORD_DEMO.md)) — the graph in
   motion is your most shareable asset.
2. **Publish the blog** on your canonical home (dev.to recommended — see below).
3. **Show HN** and **Reddit**, linking the blog or repo (best shot at a spike).
4. **LinkedIn** and **X** (sustained trickle; point at the blog).
5. Reply to every comment in the first hour on each channel.

---

## Where to post the blog

Publish the canonical copy on **one** home, then cross-post with a canonical URL
(see the worked example at the bottom of this file).

| Platform | Why | Notes |
|---|---|---|
| **dev.to** ⭐ | Best developer reach + community + SEO, free | Tags: `#opensource #python #ai #showdev`. Has a `canonical_url` field. |
| **Hashnode** | Dev-native, custom domain, good SEO | Good canonical home if you want your own brand. |
| **GitHub Pages** (`/blog`) | You own the URL long-term | Lower initial traffic; great as canonical. |
| **Medium** | Broad audience | Weaker for devs; use "Import a story" to auto-set canonical. |

**Practical:** publish on dev.to → submit *that URL* to HN/Reddit → LinkedIn/X
point at it too.

---

## 1. Show HN

**Title (pick one — concrete beats hype):**
- `Show HN: okfgen – turn any repo, database, or open-data portal into a knowledge graph`
- `Show HN: okfgen – generate Open Knowledge Format bundles, deterministically (no LLM)`
- `Show HN: Make your systems agent-readable in one command`

**Post (as the first comment; put the repo in the URL field):**

> okfgen turns a source — a git repo, a database schema, a docs site, or a live open-data portal — into an Open Knowledge Format (OKF) bundle: a directory of plain markdown files with YAML frontmatter that agents and humans can both read.
>
> I built it after reading Google's OKF spec. I wanted a reference implementation of *both* sides — producing bundles and consuming them — but with one opinionated constraint: it's deterministic. No LLM and no API key are required. It extracts real facts (table schemas, foreign-key join paths, file/module structure, dependency manifests, doc headings), so the output is reproducible and diffable, not hallucinated. There's an optional `--llm` flag if you want Claude to polish descriptions, but it's off by default.
>
> The core runs on the Python standard library alone (zero third-party deps for git/local/web/schema sources). Cloud SDKs are lazy optional extras.
>
> One command gives you: a self-contained interactive graph (single HTML file, data never leaves the page); full-text search + a citation-backed reasoning agent (`okfgen ask` shows the concepts it traversed); and an MCP server, so Claude/Cursor can produce and query bundles directly.
>
> Live demos on real public data — Toronto & NYC open data, via CKAN and Socrata adapters that work against thousands of gov portals.
>
>     uvx okfgen generate .
>
> It's young and the spec is a v0.1 draft, so I'd love feedback — especially on the producer adapters and where deterministic extraction falls short.
>
> Repo: https://github.com/bushans/okfgen
> Live graphs: https://bushans.github.io/okfgen/

*Tips: submit Tue–Thu ~8–10am ET; repo link in the URL field, text above as the first comment; reply fast and candidly.*

---

## 2. Reddit

**Golden rule:** Reddit punishes overt self-promo. Lead with value, disclose
you're the author, ask for feedback (not stars), follow each sub's flair/rules,
and don't make this your only activity (~9:1 ratio). Post to one or two subs at
a time.

**Subreddits + the angle to lead with:**
- **r/Python** — *"Show and Tell"* flair; angle: stdlib-only core, zero deps.
- **r/dataengineering** — angle: auto-catalog schemas + join paths, no catalog to deploy.
- **r/opensource** — angle: reference implementation of an open standard.
- **r/LocalLLaMA** / **r/AI_Agents** — angle: deterministic local context; MCP; no API key.
- **r/coolgithubprojects** / **r/programming** — link the repo; neutral title.

**Title:**
- `I built okfgen: turn any repo, database, or open-data portal into an agent-readable knowledge graph — deterministic, no LLM [OC]`
- (r/Python) `okfgen – generate Open Knowledge Format bundles from repos/DBs/open-data; stdlib-only core`

**Body:**

> **TL;DR:** `uvx okfgen generate .` turns a repo, database schema, docs site, or live open-data portal into a portable knowledge graph (markdown + YAML) that AI agents can reason over. Open source, on PyPI. I'm the author and would love feedback.
>
> ---
>
> I've been building **okfgen**, a reference implementation of Google's new Open Knowledge Format (OKF). The idea: represent the knowledge around your systems as plain markdown files with YAML frontmatter — no proprietary catalog, no lock-in.
>
> My one design constraint: it's deterministic. No LLM, no API key. It reads real schemas, code structure, and dependency manifests, so the output is reproducible facts rather than hallucinated docs. (There's an optional `--llm` flag, but nothing requires it, and the core runs on the Python standard library alone.)
>
> From one command you get:
> - a self-contained interactive graph (a single HTML file — no backend, data never leaves your browser)
> - full-text search + a reasoning agent that answers with citations and shows which concepts it traversed
> - foreign-key join-path inference between tables (`customer_id → customers`)
> - an MCP server, so Claude/Cursor can produce and query bundles directly
>
> It works on real data today via CKAN and Socrata adapters (data.gov, NYC, Toronto, thousands of gov portals). Live demo gallery: https://bushans.github.io/okfgen/
>
> It's early and the spec is a v0.1 draft, so I'm genuinely after feedback — what source would you point it at, and where does the extraction fall short?
>
> Repo (Apache-2.0): https://github.com/bushans/okfgen

*Tips: repo link goes inline/in the link field (Reddit doesn't suppress links); add the required flair; reply quickly and take criticism gracefully; space posts across subs over several days.*

---

## 3. X / Twitter thread

**1/** Your AI agents are only as good as the context you give them. But that context — schemas, docs, tribal knowledge — is scattered across a dozen systems.

I built okfgen: turn any repo, database, or open-data portal into an agent-readable knowledge graph. One command. 🧵

**2/**
```
uvx okfgen generate .
```
Point it at a git repo, a DB schema, a docs site, or a live open-data portal → out comes a portable bundle of markdown + YAML. No proprietary format. No lock-in. Just files you can grep and diff.

**3/** The opinionated part: it's deterministic.

No LLM. No API key. It reads real schemas and structure, so the output is facts — not hallucinations — and it's reproducible every run. (Optional --llm flag if you want it.)

**4/** One command → three ways to explore:
🔹 a self-contained interactive graph (single HTML file, data stays in your browser)
🔹 full-text search
🔹 a reasoning agent that answers with citations + shows its work

[attach the graph GIF/screenshot]

**5/** It even infers join paths between your tables from foreign-key naming, and wires backlinks — so the graph is navigable both ways.

`customer_id → customers` ✅

**6/** And it ships as an MCP server. Claude, Cursor, and any MCP client can catalog a database and reason over it without leaving the chat.
```
pip install "okfgen[mcp]"
```

**7/** Live demos on real public data — Toronto beach water quality & NYC 311 — via CKAN + Socrata adapters that work against thousands of gov portals.
🎨 https://bushans.github.io/okfgen/

**8/** It's open source (Apache-2.0), on PyPI, and early.

I'd love your feedback — what would *you* point it at?
⭐ https://github.com/bushans/okfgen

---

## 4. LinkedIn

**Post (put the links in the FIRST COMMENT, not the body — see tips):**

> **What if any repo, database, or open-data portal could become an AI-ready knowledge graph in one command?**
>
> I've been building **okfgen** — an open-source tool that turns your existing systems into portable knowledge bundles that AI agents can actually reason over. It's a producer *and* consumer implementation of Google's new Open Knowledge Format (OKF).
>
> The part I'm most happy with: it's deterministic. No LLM, no API key, no cloud lock-in. It reads real schemas, code structure, and docs — so the output is facts, not hallucinations. And it works across git repos, databases, documentation sites, and live open-data portals (I wired up Toronto & NYC open data as demos).
>
> One command and you get:
> 🔹 a self-contained interactive knowledge graph (a single HTML file)
> 🔹 full-text search + a citation-backed reasoning agent
> 🔹 an MCP server, so Claude, Cursor & co. can use it directly
>
> It's early and I'd genuinely love your feedback — especially: what source would *you* point it at? What's missing?
>
> (Repo + live demo in the comments 👇)
>
> #OpenSource #AI #KnowledgeGraph #DataEngineering #AIAgents #Python #MCP

**First comment:**
> ⭐ Repo: https://github.com/bushans/okfgen
> 🎨 Live demo: https://bushans.github.io/okfgen/

**Why the link goes in the comment:** LinkedIn's feed shows posts with external
links in the *body* to fewer people (it wants users to stay on-platform). Links
in *comments* aren't penalized. So: post text with no link → immediately add a
comment with the links → optionally edit the link into the post once it has
traction. Also attach a screenshot/GIF (visual ≈ 2–3× reach) and reply to every
comment in the first hour.

---

## 5. Blog post (publish on dev.to — this is your canonical URL)

Paste-ready below. The whole block is fenced with tildes (`~~~`) so the inner
```` ``` ```` code blocks copy through intact. The front-matter is dev.to format:
leave `published: false` until you've reviewed it, add a `cover_image`, and set
`canonical_url` only if you publish the original somewhere else first.

~~~markdown
---
title: Make your systems agent-readable in one command
published: false
description: A deterministic tool that turns your repos, databases, and docs into portable knowledge graphs AI agents can reason over.
tags: opensource, python, ai, showdev
cover_image:
canonical_url:
---

## The context problem

Everyone is wiring AI agents into their stack. But an agent is only as smart as
the context it's given, and that context — table schemas, join logic, API docs,
the "why" behind a system — is fragmented across databases, wikis, and
codebases. Most attempts to fix this either lock your knowledge in a proprietary
catalog or ask an LLM to hallucinate documentation you can't trust.

## A simpler idea: knowledge as files

Google recently proposed the [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
(OKF): represent knowledge as *just markdown files with YAML frontmatter*. No
schema registry, no SDK, no central authority. A bundle is a directory of
"concepts"; each file is readable by humans, parseable by agents, and diffable
in git.

I liked it enough to build **okfgen** — a reference implementation of both sides
of that ecosystem.

## Deterministic by default

okfgen's one opinion: it extracts *facts*, not guesses. Point it at a database
and it reads the actual column schemas. Point it at a repo and it maps the real
module structure and dependencies. No LLM, no API key — so the output is
reproducible, auditable, and runs in an air-gapped environment. (An optional
`--llm` flag adds Claude-written polish where you want it, but nothing needs it.)

## Producers → bundle → consumers

The *producers* turn a source into a bundle:

```bash
uvx okfgen generate ./my-repo
uvx okfgen generate schema:./warehouse.json
uvx okfgen generate ckan:https://data.gov/dataset/...
```

Then an *enrichment* pass infers join paths between tables from foreign-key
naming (`customer_id → customers`) and wires backlinks, so the knowledge becomes
a navigable graph.

The *consumers* read any bundle back — regardless of who produced it:

- **visualize** → a self-contained interactive graph (one HTML file, no backend, data never leaves the page)
- **search** → a full-text index
- **ask** → a reasoning agent that answers with citations *and shows which concepts it traversed*
- **validate** → an OKF conformance check

## In your agent, via MCP

okfgen ships an MCP server, so Claude, Cursor, and any MCP client can generate
and reason over bundles directly. An agent can now say "catalog this database
and tell me how orders relate to customers" and get a grounded, cited answer.

## It works on real data today

The same adapters that read a local schema also read live open-data portals —
CKAN (data.gov, Toronto, thousands of city/gov portals) and Socrata (NYC,
Seattle, Chicago). The live demo gallery is built from exactly these:
[browse the interactive graphs →](https://bushans.github.io/okfgen/)

## Try it

```bash
uvx okfgen generate .
```

It's open source (Apache-2.0), on PyPI, and early — the spec itself is a v0.1
draft. If you try it, I'd genuinely love to hear what source you pointed it at
and where it fell short.

⭐ [github.com/bushans/okfgen](https://github.com/bushans/okfgen)
~~~

---

## Cross-posting without hurting SEO — worked example

Posting the same article in several places normally triggers Google's
"duplicate content" handling. A **canonical URL** tells Google which copy is the
original, so all ranking credit lands on that one URL.

Say your original goes on dev.to:

1. **Publish first on dev.to.** That URL is your canonical:
   `https://dev.to/bushans/make-your-systems-agent-readable-in-one-command-1a2b`
2. **Repost on Hashnode.** In *Article settings → SEO → Canonical URL*, paste the
   dev.to link. Hashnode emits into that page's `<head>`:
   ```html
   <link rel="canonical" href="https://dev.to/bushans/make-your-systems-agent-readable-in-one-command-1a2b" />
   ```
3. **Repost on Medium.** Use *Import a story* (paste the dev.to URL); Medium sets
   the canonical back to dev.to automatically.

Result: three copies for reach, one canonical for SEO — no duplicate-content
penalty, and ranking signals compound on a single URL.

Prefer your own brand as canonical? Publish first on your GitHub Pages blog, then
set dev.to's `canonical_url` front-matter to that Pages URL. Whichever you pick:
**one** canonical, everyone else points to it.
