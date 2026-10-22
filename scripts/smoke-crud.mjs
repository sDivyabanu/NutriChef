// End-to-end API smoke test against the running dev servers.
// Usage: node scripts/smoke-crud.mjs [baseUrl]   (default http://localhost:3000)
import { randomBytes } from "node:crypto";
const BASE = process.argv[2] || "http://localhost:3000";
let cookie = "";
let failures = 0;

async function call(method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json", ...(cookie ? { cookie } : {}) },
    body: body ? JSON.stringify(body) : undefined,
    redirect: "manual",
  });
  const setCookies = res.headers.getSetCookie?.() || [];
  if (setCookies.length) {
    const jar = Object.fromEntries(cookie.split("; ").filter(Boolean).map((c) => c.split(/=(.*)/s).slice(0, 2)));
    for (const sc of setCookies) {
      const [kv] = sc.split(";");
      const [k, v] = kv.split(/=(.*)/s);
      if (v) jar[k] = v;
      else delete jar[k];
    }
    cookie = Object.entries(jar).map(([k, v]) => `${k}=${v}`).join("; ");
  }
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch { json = text; }
  return { status: res.status, json };
}

function check(name, cond, detail) {
  if (cond) console.log(`  ok   ${name}`);
  else { failures++; console.log(`  FAIL ${name}`, detail ?? ""); }
}

const email = `smoke+${Date.now()}@nutrichef.test`;
const password = randomBytes(24).toString("base64url");

let r = await call("POST", "/api/signup", { name: "Smoke Tester", email, password });
check("signup", r.status === 201, r);
r = await call("POST", "/api/login", { email, password });
check("login", r.status === 200 && cookie.includes("token="), r);
r = await call("GET", "/api/me");
check("me", r.status === 200 && r.json.user?.full_name === "Smoke Tester", r);
r = await call("POST", "/api/profile", { height: "165", weight: "60", age: "24", dietType: "Vegetarian", allergies: "peanut, sesame", conditions: [], otherInfo: "" });
check("onboarding profile save", r.status === 200 && r.json.allergies?.length === 2, r);
r = await call("PUT", "/api/profile", { full_name: "Smoke Tester 2", '"id" = NULL --': "x" });
check("profile update (unknown keys ignored)", r.status === 200, r);
r = await call("GET", "/api/profile");
check("profile read", r.status === 200 && r.json.full_name === "Smoke Tester 2", r);
r = await call("POST", "/api/pantry", { name: "paneer" });
check("pantry add", r.status === 200 && r.json.item?.name === "paneer", r);
const pantryId = r.json.item?.id;
r = await call("GET", "/api/pantry");
check("pantry list", r.status === 200 && r.json.pantry?.length === 1, r);
r = await call("DELETE", "/api/pantry", { id: pantryId });
check("pantry delete", r.status === 200, r);
r = await call("POST", "/api/favorites", { recipe: { recipe_name: "Smoke Curry", recipe_ref: "1" } });
check("favorite add", r.status === 200 && r.json.success, r);
const favId = r.json.recipe?.id;
r = await call("GET", "/api/favorites");
check("favorite list", r.status === 200 && r.json.recipes?.length === 1, r);
r = await call("DELETE", "/api/favorites", { id: favId });
check("favorite delete", r.status === 200, r);
r = await call("GET", "/api/dashboard");
check("dashboard", r.status === 200 && r.json.profile, r);
r = await call("GET", "/backend/nlp/health");
check("NLP backend via proxy", r.status === 200 && r.json.recipes > 0, r);

// Recipe CRUD through the NLP service (owned by the logged-in user).
r = await call("POST", "/backend/recipes", { title: "Smoke Tomato Rice", ingredients: ["1 cup rice", "2 tomatoes", "1 onion"], instructions: "Cook rice. Add tomato and onion." });
check("recipe create", r.status === 201 && r.json.id, r);
const rid = r.json.id;
r = await call("PUT", `/backend/recipes/${rid}`, { title: "Smoke Tomato Rice v2" });
check("recipe update persists", r.status === 200 && r.json.title === "Smoke Tomato Rice v2" && r.json.version === 2, r);
r = await call("GET", `/backend/recipes/${rid}`);
check("recipe read", r.status === 200 && r.json.title === "Smoke Tomato Rice v2", r);
r = await call("PUT", `/backend/recipes/1`, { title: "hijack" });
check("dataset recipe is read-only", r.status === 403, r);
r = await call("DELETE", `/backend/recipes/${rid}`);
check("recipe delete", r.status === 204, r);
r = await call("GET", `/backend/recipes/${rid}`);
check("deleted recipe hidden", r.status === 404, r);

r = await call("GET", "/api/logout");
check("logout", r.status === 200 && !cookie.includes("token="), r);
r = await call("POST", "/backend/recipes", { title: "x", ingredients: ["y"] });
check("recipe create requires login", r.status === 401, r);

console.log(failures ? `\n${failures} check(s) failed` : "\nall checks passed");
process.exit(failures ? 1 : 0);
