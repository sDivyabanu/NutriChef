import { NextResponse } from "next/server";
import pool from "@/lib/db";
import { verifyToken } from "@/lib/auth";
import { cookies } from "next/headers";

export async function GET() {
  try {
    // ✅ cookies() is synchronous in route handlers
    const cookieStore = await cookies();  
    const token = cookieStore.get("token")?.value;

    if (!token) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const payload = verifyToken(token); // throws if invalid

    const result = await pool.query(
      'SELECT "id", "full_name" FROM "Profile" WHERE "id" = $1',
      [payload.id]
    );

    if (!result.rows[0]) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    return NextResponse.json({ user: result.rows[0] });
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }
}
