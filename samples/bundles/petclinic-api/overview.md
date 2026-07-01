---
type: Project
title: PetClinic API
description: PetClinic API
resource: samples/recipes/petclinic_app
tags:
  - JavaScript
timestamp: "2026-07-01T00:00:00+00:00"
---

# PetClinic API

A small Node.js REST API for managing veterinary clinic **owners**, their
**pets**, and scheduled **visits**. This fixture exists to demonstrate the
okfgen *source-system* producer: pointing okfgen at a code repository and
getting an OKF bundle of the project's structure.

## Endpoints
- `GET /owners` — list owners
- `POST /pets` — register a pet to an owner
- `GET /visits` — upcoming visits

## Stack
Express + an in-memory store. See `src/` for the route handlers.

# Schema

- **Files scanned:** 5
- **Languages:** JavaScript (3)
- **Top-level directories:** src
