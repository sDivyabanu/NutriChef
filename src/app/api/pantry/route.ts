import { NextResponse } from "next/server";
import pool from "@/lib/db";
import { getUser } from "@/lib/getUser";

export async function GET() {
  try {
    const user = await getUser();
    if (!user) return NextResponse.json({ error: "User not logged in" }, { status: 401 });
    const { rows } = await pool.query(
      `SELECT * FROM "PantryItem" WHERE user_id = $1 ORDER BY created_at DESC`,
      [user.id]
    );
    return NextResponse.json({ pantry: rows });
  } catch (err) {
    console.error("GET /api/pantry error:", err);
    return NextResponse.json({ error: "Failed to load pantry" }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const user = await getUser();
    if (!user) return NextResponse.json({ error: "User not logged in" }, { status: 401 });
    const { name, quantity, category } = await req.json();
    if (!name || !String(name).trim()) {
      return NextResponse.json({ error: "Invalid item name" }, { status: 400 });
    }
    const { rows } = await pool.query(
      `INSERT INTO "PantryItem" (user_id, name, quantity, category) VALUES ($1, $2, $3, $4) RETURNING *`,
      [user.id, String(name).trim().slice(0, 120), quantity ?? null, category ?? null]
    );
    return NextResponse.json({ item: rows[0] ?? null });
  } catch (err) {
    console.error("POST /api/pantry error:", err);
    return NextResponse.json({ error: "Failed to add item" }, { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const user = await getUser();
    if (!user) return NextResponse.json({ error: "User not logged in" }, { status: 401 });
    const { id } = await req.json();
    if (!id) return NextResponse.json({ error: "Missing id" }, { status: 400 });
    await pool.query(`DELETE FROM "PantryItem" WHERE id = $1 AND user_id = $2`, [id, user.id]);
    return NextResponse.json({ success: true });
  } catch (err) {
    console.error("DELETE /api/pantry error:", err);
    return NextResponse.json({ error: "Failed to delete item" }, { status: 500 });
  }
}
