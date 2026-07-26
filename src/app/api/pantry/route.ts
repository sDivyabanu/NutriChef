import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
const supabase = createClient(supabaseUrl, supabaseServiceKey);

// ✅ Get pantry items
export async function GET() {
  try {
    const cookieStore = await cookies();
    const userId = cookieStore.get("userId")?.value;

    if (!userId) {
      return NextResponse.json({ error: "User not logged in" }, { status: 401 });
    }

    const { data, error } = await supabase
      .from("PantryItem")
      .select("*")
      .eq("user_id", userId)
      .order("created_at", { ascending: false });

    if (error) throw error;
    return NextResponse.json({ pantry: data || [] });
  } catch (err) {
    console.error("GET /api/pantry error:", err);
    return NextResponse.json({ error: (err as Error).message }, { status: 500 });
  }
}

// ✅ Add pantry item
export async function POST(req: Request) {
  try {
    const cookieStore = await cookies();
    const userId = cookieStore.get("userId")?.value;

    if (!userId) {
      return NextResponse.json({ error: "User not logged in" }, { status: 401 });
    }

    const { name } = await req.json();

    if (!name || !name.trim()) {
      return NextResponse.json({ error: "Invalid item name" }, { status: 400 });
    }

    const { data, error } = await supabase
      .from("PantryItem")
      .insert([{ user_id: userId, name: name.trim() }])
      .select();

    if (error) throw error;
    return NextResponse.json({ item: data?.[0] || null });
  } catch (err) {
    console.error("POST /api/pantry error:", err);
    return NextResponse.json({ error: (err as Error).message }, { status: 500 });
  }
}

// ✅ Delete pantry item
export async function DELETE(req: Request) {
  try {
    const cookieStore = await cookies();
    const userId = cookieStore.get("userId")?.value;

    if (!userId) {
      return NextResponse.json({ error: "User not logged in" }, { status: 401 });
    }

    const { id } = await req.json();
    if (!id) return NextResponse.json({ error: "Missing id" }, { status: 400 });

    const { error } = await supabase
      .from("PantryItem")
      .delete()
      .eq("id", id)
      .eq("user_id", userId);

    if (error) throw error;
    return NextResponse.json({ success: true });
  } catch (err) {
    console.error("DELETE /api/pantry error:", err);
    return NextResponse.json({ error: (err as Error).message }, { status: 500 });
  }
}
