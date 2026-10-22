import { NextResponse } from "next/server";

export async function GET() {
  const response = NextResponse.json({ message: "Logged out" });
  response.cookies.set("token", "", { httpOnly: true, sameSite: "lax", path: "/", maxAge: 0 });
  response.cookies.set("userId", "", { sameSite: "lax", path: "/", maxAge: 0 });
  return response;
}
