import { NextResponse } from "next/server";
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY, // put your key in .env.local
});

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const file = formData.get("file") as File;

    if (!file) {
      return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
    }

    const arrayBuffer = await file.arrayBuffer();
    const base64 = Buffer.from(arrayBuffer).toString("base64");

    const response = await client.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: "List all the ingredients visible in this image." },
            { type: "image_url", image_url: { url: `data:image/jpeg;base64,${base64}` } },
          ],
        },
      ],
    });

    const ingredientsText = response.choices[0].message?.content || "";
    const ingredients = ingredientsText
      .split("\n")
      .map((i) => i.replace(/[-\d.]/g, "").trim())
      .filter((i) => i.length > 0);

    return NextResponse.json({ ingredients });
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Failed to detect ingredients." }, { status: 500 });
  }
}
