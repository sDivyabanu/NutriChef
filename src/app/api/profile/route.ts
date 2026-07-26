import { NextResponse } from "next/server";
import prisma from "@/lib/prisma";
import { cookies } from "next/headers";
import pool from "@/lib/db";
import { verifyToken } from "@/lib/auth";
// Save profile (from onboarding)
export async function POST(req: Request) {
  try {
    const body = await req.json();
    const {
      userId,
      height,
      weight,
      age,
      dietType,
      allergies,
      conditions,
      otherInfo,
    } = body;

    if (!userId) {
      return NextResponse.json({ error: "Missing userId" }, { status: 400 });
    }

    const profile = await prisma.profile.upsert({
      where: { id: userId }, // ✅ use 'id', not 'userId'
      update: {
        height_cm: parseFloat(height),
        weight_kg: parseFloat(weight),
        age: parseInt(age),
        diet_type: dietType,
        allergies: [],
        health_conditions: Array.isArray(conditions)
          ? conditions
          : [conditions],
        other_info: otherInfo,
      },
      create: {
        id: userId, // ✅ use 'id' here as well
        height_cm: parseFloat(height),
        weight_kg: parseFloat(weight),
        age: parseInt(age),
        diet_type: dietType,
        allergies: [],
        health_conditions: Array.isArray(conditions)
          ? conditions
          : [conditions],
        other_info: otherInfo,
      },
    });

    return NextResponse.json(profile);
  } catch (err) {
    console.error("Profile POST error:", err);
    return NextResponse.json(
      { error: "Failed to save profile" },
      { status: 500 }
    );
  }
}
export async function PUT(req: Request) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get("token")?.value;
    if (!token)
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });

    const { id } = verifyToken(token);
    const body = await req.json();

    // Update only provided fields
    const fields = Object.keys(body);
    const values = Object.values(body);

    const setClause = fields.map((f, i) => `"${f}" = $${i + 1}`).join(", ");

   await pool.query(
      `UPDATE "Profile" SET ${setClause} WHERE "id" = $${fields.length + 1}`,
      [...values, id] // id as last parameter
    );

    return NextResponse.json({ success: true });
  } catch (err) {
    console.error("Profile update error:", err);
    return NextResponse.json(
      { error: "Failed to update profile" },
      { status: 500 }
    );
  }
}
// Fetch profile (for /profile page)

export async function GET(req: Request) {
  try {
    const cookieStore = await cookies();
    const userId = cookieStore.get("userId")?.value;

    if (!userId) {
      return NextResponse.json({ error: "Missing userId" }, { status: 400 });
    }

    const profile = await prisma.profile.findUnique({
      where: { id: userId },
    });

    if (!profile) {
      return NextResponse.json(
        { message: "Profile not found" },
        { status: 404 }
      );
    }

    return NextResponse.json(profile);
  } catch (err) {
    console.error("Profile GET error:", err);
    return NextResponse.json(
      { error: "Failed to fetch profile" },
      { status: 500 }
    );
  }
}
