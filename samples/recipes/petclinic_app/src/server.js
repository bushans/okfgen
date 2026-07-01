const express = require("express");
const { ownersRouter } = require("./owners");
const { petsRouter } = require("./pets");

function createServer() {
  const app = express();
  app.use(express.json());
  app.use("/owners", ownersRouter);
  app.use("/pets", petsRouter);
  return app;
}

function start(port) {
  const app = createServer();
  return app.listen(port, () => console.log(`petclinic listening on ${port}`));
}

module.exports = { createServer, start };
