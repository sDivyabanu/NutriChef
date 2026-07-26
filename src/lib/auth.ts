// lib/auth.ts
import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";

const SECRET = process.env.JWT_SECRET!;

export async function hashPassword(password: string) {
  const saltRounds = 10;
  return await bcrypt.hash(password, saltRounds);
}

export async function comparePassword(password: string, hash: string) {
  return await bcrypt.compare(password, hash);
}

export function createToken(payload: object) {
  return jwt.sign(payload, SECRET, { expiresIn: "7d" });
}
// ✅ Add this function
export function verifyToken(token: string): any {
  try {
    return jwt.verify(token, SECRET); // returns the payload
  } catch (err) {
    return null; // invalid token
  }
}