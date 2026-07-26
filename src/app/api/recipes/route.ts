import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import csv from "csv-parser";

export async function POST(req: Request) {
  try {
    const { ingredients } = await req.json();

    if (!ingredients || ingredients.length === 0) {
      return NextResponse.json(
        { error: "No ingredients provided" },
        { status: 400 }
      );
    }

    const results: any[] = [];
    const filePath = path.join(process.cwd(), "data", "13k-recipes.csv");

    await new Promise<void>((resolve, reject) => {
      fs.createReadStream(filePath)
        .pipe(csv())
        .on("data", (row) => {
          // Normalize headers
          const title = row.Title || row.title || "Untitled";
          const ingredientsText = row.Ingredients || row.ingredients || "";
          const instructionsText = row.Instructions || row.instructions || "";

          const ingLower = ingredientsText.toLowerCase();

          // Match all entered ingredients
          const match = ingredients.every((i: string) =>
            ingLower.includes(i.toLowerCase())
          );

          if (match) {
            results.push({
              id: row.id || Math.random().toString(36).substring(7),
              name: title.trim(), // frontend expects "name"
              image: `https://source.unsplash.com/400x300/?food,${encodeURIComponent(
                title.split(" ")[0]
              )}`, // random relevant image
              link: "#", // no URL in CSV, placeholder
              nutrition: {
                calories: Math.floor(Math.random() * 500) + 100,
                protein: Math.floor(Math.random() * 40) + 5,
                fat: Math.floor(Math.random() * 20) + 5,
                carbs: Math.floor(Math.random() * 80) + 10,
              },
              instructions: instructionsText,
            });
          }
        })
        .on("end", resolve)
        .on("error", reject);
    });

    return NextResponse.json({ recipes: results.slice(0, 12) }); // limit for speed
  } catch (error) {
    console.error("Error fetching recipes:", error);
    return NextResponse.json(
      { error: "Failed to fetch recipes" },
      { status: 500 }
    );
  }
}
