---
type: Document
title: Installation
description: Documentation file `installation.md`.
resource: installation.md
tags:
  - documentation
timestamp: "2026-07-01T00:00:00+00:00"
---

# Installation

The Nimbus agent runs as a sidecar or a host daemon.

```bash
curl -sSL https://get.nimbus.example/install.sh | sh
nimbus-agent --api-key $NIMBUS_KEY
```

Once installed, verify connectivity, then continue to the
[Ingest API](./ingest-api.md) to start sending data. See
[Getting Started](./getting-started.md) for the full flow.
