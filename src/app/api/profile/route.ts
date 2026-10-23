import { NextResponse } from "next/server";
import prisma from "@/lib/prisma";
import { getUser } from "@/lib/getUser";

const toList = (v: unknown): string[] =>
  Array.isArray(v)
    ? v.map(String).map((s) => s.trim()).filter(Boolean)
    : typeof v === "string"
    ? v.split(",").map((s) => s.trim()).filter(Boolean)
    : [];

const toNum = (v: unknown, parse: (s: string) => number) => {
  const n = parse(String(v ?? ""));
  return Number.isFinite(n) ? n : null;
};

// Save profile (from onboarding). Identity comes from the verified auth token, not the request body.
export async function POST(req: Request) {
  try {
    const user = await getUser();
    if (!user) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    const { height, weight, age, dietType, allergies, conditions, otherInfo } = await req.json();

    const data = {
      height_cm: toNum(height, parseFloat),
      weight_kg: toNum(weight, parseFloat),
      age: toNum(age, (s) => parseInt(s, 10)),
      diet_type: dietType || null,
      allergies: toList(allergies),
      health_conditions: toList(conditions),
      other_info: otherInfo || null,
    };
    const profile = await prisma.profile.upsert({
      where: { id: user.id },
      update: data,
      create: { id: user.id, ...data },
    });
    return NextResponse.json(profile);
  } catch (err) {
    console.error("Profile POST error:", err);
    return NextResponse.json({ error: "Failed to save profile" }, { status: 500 });
  }
}

// Only these columns may be updated from the profile page.
const EDITABLE = {
  full_name: "string",
  avatar_url: "string",
  height_cm: "float",
  weight_kg: "float",
  age: "int",
  diet_type: "string",
  allergies: "list",
  health_conditions: "list",
  other_info: "string",
} as const;

export async function PUT(req: Request) {
  try {
    const user = await getUser();
    if (!user) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    const body = await req.json();

    const data: Record<string, unknown> = {};
    for (const [key, kind] of Object.entries(EDITABLE)) {
      if (!(key in body)) continue;
      const v = body[key];
      if (kind === "float") data[key] = v === "" || v == null ? null : toNum(v, parseFloat);
      else if (kind === "int") data[key] = v === "" || v == null ? null : toNum(v, (s) => parseInt(s, 10));
      else if (kind === "list") data[key] = toList(v);
      else data[key] = v == null ? null : String(v);
    }
    await prisma.profile.update({ where: { id: user.id }, data });
    return NextResponse.json({ success: true });
  } catch (err) {
    console.error("Profile update error:", err);
    return NextResponse.json({ error: "Failed to update profile" }, { status: 500 });
  }
}

export async function GET() {
  try {
    const user = await getUser();
    if (!user) return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    const profile = await prisma.profile.findUnique({ where: { id: user.id } });
    if (!profile) return NextResponse.json({ message: "Profile not found" }, { status: 404 });
    return NextResponse.json(profile);
  } catch (err) {
    console.error("Profile GET error:", err);
    return NextResponse.json({ error: "Failed to fetch profile" }, { status: 500 });
  }
}
