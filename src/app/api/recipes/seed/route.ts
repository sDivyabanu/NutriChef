// src/app/api/recipes/seed/route.ts
// Previously downloaded recipes from TheMealDB (a remote service) into Prisma models that don't exist.
// The recipe corpus is now built locally and reproducibly from data/13k-recipes.csv:
//   cd backend && .venv/Scripts/python -m scripts.build_corpus
import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json(
    { error: "Remote seeding is disabled. Build the local corpus with: python -m scripts.build_corpus (in backend/)." },
    { status: 410 }
  );
}
