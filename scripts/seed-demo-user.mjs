// Creates a local demo account (local Postgres only) for trying the app.
// Usage: node scripts/seed-demo-user.mjs      (dev server must be running on :3000)
// Set NUTRICHEF_DEMO_PASSWORD before running; credentials are never stored in source.
const BASE = process.argv[2] || "http://localhost:3000";
const password = process.env.NUTRICHEF_DEMO_PASSWORD;
if (!password) throw new Error("Set NUTRICHEF_DEMO_PASSWORD before creating the local demo account.");
const DEMO = { name: "Demo Cook", email: process.env.NUTRICHEF_DEMO_EMAIL || "demo@nutrichef.test", password };

const res = await fetch(`${BASE}/api/signup`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(DEMO),
});
if (res.status === 201) console.log(`created ${DEMO.email}`);
else {
  const login = await fetch(`${BASE}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: DEMO.email, password: DEMO.password }),
  });
  console.log(login.ok ? `${DEMO.email} already exists (login ok)` : `could not create or log in: ${res.status}/${login.status}`);
}
