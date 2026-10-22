// Runs a fully local PostgreSQL server (no Docker, no cloud) for NutriChef.
// Data lives in ./.localdb (git-ignored). Usage: `npm run db`
import EmbeddedPostgres from "embedded-postgres";
import fs from "node:fs";
import path from "node:path";

const port = Number(process.env.LOCAL_PG_PORT || 5433);
const dataDir = path.resolve(".localdb", "pgdata");
const firstRun = !fs.existsSync(path.join(dataDir, "PG_VERSION"));

const pg = new EmbeddedPostgres({
  databaseDir: dataDir,
  user: "nutrichef",
  password: process.env.LOCAL_PG_PASSWORD || "nutrichef_local",
  port,
  persistent: true,
  // Only accept connections from this machine.
  postgresFlags: ["-c", "listen_addresses=localhost"],
});

if (firstRun) {
  console.log("[local-db] initialising new cluster in", dataDir);
  await pg.initialise();
}
await pg.start();
if (firstRun) await pg.createDatabase("nutrichef");
console.log(`[local-db] PostgreSQL ready on localhost:${port} (db: nutrichef)`);

const stop = async () => {
  console.log("[local-db] stopping...");
  await pg.stop();
  process.exit(0);
};
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
setInterval(() => {}, 1 << 30);
