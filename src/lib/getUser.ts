// lib/getUser.ts
import jwt from "jsonwebtoken";
import { cookies } from "next/headers";

const SECRET = process.env.JWT_SECRET!; // same secret as the login route (set in .env.local)

export async function getUser() {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get("token")?.value;

    if (!token) return null;

    const decoded = jwt.verify(token, SECRET) as { id: string; email: string };
    return decoded;
  } catch (err) {
    console.error("getUser error:", err);
    return null;
  }
}
