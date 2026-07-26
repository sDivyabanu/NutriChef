import { NextResponse } from "next/server";
import pool from "@/lib/db";
import { comparePassword, createToken } from "@/lib/auth";

export async function POST(req: Request) {
  try {
    const { email, password } = await req.json();

    if (!email || !password) {
      return NextResponse.json({ error: "Missing credentials" }, { status: 400 });
    }

    const result = await pool.query(
      `SELECT id, password_hash FROM auth_users WHERE email = $1`,
      [email]
    );

    if (result.rows.length === 0) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    const user = result.rows[0];
    const isMatch = await comparePassword(password, user.password_hash);

    if (!isMatch) {
      return NextResponse.json({ error: "Invalid password" }, { status: 401 });
    }

    // Generate auth token
    const token = createToken({ id: user.id, email });

    // Create response and set cookies
    const response = NextResponse.json({
      message: "Login successful",
      userId: user.id,
    });

    // ✅ Secure cookies
    response.cookies.set("token", token, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
    });

    response.cookies.set("userId", user.id, {
      sameSite: "lax",
      path: "/",
    });

    return response;
  } catch (err: any) {
    console.error("Login error:", err);
    return NextResponse.json({ error: "Login failed" }, { status: 500 });
  }
}
