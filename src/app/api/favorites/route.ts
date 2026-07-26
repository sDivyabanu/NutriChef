export const runtime = "nodejs";

import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { createClient } from "@supabase/supabase-js";

// Initialize Supabase (server-side)
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY! // use service key only on server
);

// Add recipe to favorites
export async function POST(req: Request) {
  try {
    const cookieStore = await cookies();
    const cookieUserId = cookieStore.get("userId")?.value;
    const { userId: bodyUserId, recipe } = await req.json();

    const userId = bodyUserId || cookieUserId;

    if (!userId) {
      return NextResponse.json(
        { success: false, error: "User not logged in" },
        { status: 401 }
      );
    }

    if (!recipe || !recipe.recipe_name) {
      return NextResponse.json(
        { success: false, error: "Invalid recipe data" },
        { status: 400 }
      );
    }

    const { data, error } = await supabase
      .from("UserRecipe")
      .insert([
        {
          user_id: userId,
          recipe_name: recipe.recipe_name,
          calories: recipe.calories ?? null,
          protein: recipe.protein ?? null,
          fat: recipe.fat ?? null,
          carbs: recipe.carbs ?? null,
          instructions: recipe.instructions ?? null,
          tag: "favorite",
        },
      ])
      .select();

    if (error) {
      console.error("Supabase insert error:", error);
      return NextResponse.json(
        { success: false, error: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      recipe: data?.[0] || null,
    });
  } catch (err) {
    console.error("Add favorite error:", err);
    return NextResponse.json(
      { success: false, error: (err as Error).message },
      { status: 500 }
    );
  }
}

// ✅ Get all favorites for the logged-in user
export async function GET(req: Request) {
  try {
    const cookieStore = await cookies();
    const userId = cookieStore.get("userId")?.value;

    if (!userId) {
      return NextResponse.json(
        { error: "User not logged in" },
        { status: 401 }
      );
    }

    const { data, error } = await supabase
      .from("UserRecipe")
      .select("*")
      .eq("user_id", userId)
      .eq("tag", "favorite");

    if (error) throw error;

    return NextResponse.json({ recipes: data || [] });
  } catch (err) {
    console.error("Fetch favorites error:", err);
    return NextResponse.json(
      { error: (err as Error).message },
      { status: 500 }
    );
  }
}

// ✅ Delete a favorite by ID
export async function DELETE(req: Request) {
  try {
    const cookieStore = await cookies();
    const userId = cookieStore.get("userId")?.value;
    const { id } = await req.json();

    if (!userId) {
      return NextResponse.json(
        { error: "User not logged in" },
        { status: 401 }
      );
    }

    if (!id) {
      return NextResponse.json(
        { error: "Missing recipe ID" },
        { status: 400 }
      );
    }

    const { error } = await supabase
      .from("UserRecipe")
      .delete()
      .eq("id", id)
      .eq("user_id", userId);

    if (error) throw error;

    return NextResponse.json({ success: true });
  } catch (err) {
    console.error("Delete favorite error:", err);
    return NextResponse.json(
      { success: false, error: (err as Error).message },
      { status: 500 }
    );
  }
}
