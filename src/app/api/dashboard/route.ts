// app/api/dashboard/route.ts
import { NextRequest, NextResponse } from "next/server"; // use NextRequest
import { prisma } from "@/lib/prisma";
import { verifyToken } from "@/lib/auth";

export async function GET(req: NextRequest) {
  //NextRequest
  try {
    const token = req.cookies.get("token")?.value;

    if (!token) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const payload = verifyToken(token);

    const profile = await prisma.profile.findUnique({
      where: { id: payload.id },
      include: {
        IngredientLists: true,
        WeightLogs: true,
        WaterLogs: true,
      },
    });

    if (!profile) {
      return NextResponse.json({ error: "Profile not found" }, { status: 404 });
    }

    const weightLogs = profile.WeightLogs.map((w) => ({
      day: w.logged_on ? w.logged_on.toISOString().slice(0, 10) : "Unknown",
      weight: w.weight_kg ? Number(w.weight_kg) : 0,
    }));

    const waterLogs = profile.WaterLogs.map((w) => ({
      day: w.logged_at ? w.logged_at.toISOString().slice(0, 10) : "Unknown",
      liters: w.amount_ml ? w.amount_ml / 1000 : 0,
    }));

    return NextResponse.json({
      profile,
      weightLogs,
      waterLogs,
    });
  } catch (err: any) {
    console.error(err);
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
}
