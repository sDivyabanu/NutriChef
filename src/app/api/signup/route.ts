// app/api/signup/route.ts
import { NextResponse } from "next/server";
import pool from "@/lib/db";
import { hashPassword } from "@/lib/auth";
import { randomUUID } from "crypto";

export async function POST(req: Request) {
  try {
    const { name, email, password } = await req.json();

    if (!name || !email || !password) {
      return NextResponse.json({ error: "Missing fields" }, { status: 400 });
    }

    const hashed = await hashPassword(password);
    const id = randomUUID();

    // Insert into profiles + store credentials
    await pool.query(
      `INSERT INTO "Profile" (id, full_name, created_at, updated_at)
       VALUES ($1, $2, NOW(), NOW())`,
      [id, name]
    );

    // Create a simple auth table if not exists
    await pool.query(`
      CREATE TABLE IF NOT EXISTS auth_users (
        id uuid PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT now()
      );
    `);

    await pool.query(
      `INSERT INTO auth_users (id, email, password_hash) VALUES ($1, $2, $3)`,
      [id, email, hashed]
    );

    return NextResponse.json({ message: "Signup successful!" }, { status: 201 });
  } catch (err: any) {
    console.error(err);
    return NextResponse.json({ error: "Signup failed" }, { status: 500 });
  }
}
