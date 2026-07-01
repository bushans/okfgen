const express = require("express");
const ownersRouter = express.Router();

const owners = new Map();

function listOwners() {
  return [...owners.values()];
}

function createOwner(name) {
  const id = String(owners.size + 1);
  const owner = { id, name, pets: [] };
  owners.set(id, owner);
  return owner;
}

ownersRouter.get("/", (_req, res) => res.json(listOwners()));
ownersRouter.post("/", (req, res) => res.status(201).json(createOwner(req.body.name)));

module.exports = { ownersRouter, listOwners, createOwner, owners };
