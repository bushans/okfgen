const express = require("express");
const { owners } = require("./owners");
const petsRouter = express.Router();

function registerPet(ownerId, name, species) {
  const owner = owners.get(ownerId);
  if (!owner) return null;
  const pet = { id: `${ownerId}-${owner.pets.length + 1}`, name, species };
  owner.pets.push(pet);
  return pet;
}

petsRouter.post("/", (req, res) => {
  const pet = registerPet(req.body.ownerId, req.body.name, req.body.species);
  if (!pet) return res.status(404).json({ error: "owner not found" });
  res.status(201).json(pet);
});

module.exports = { petsRouter, registerPet };
