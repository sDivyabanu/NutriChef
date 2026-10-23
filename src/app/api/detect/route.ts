import { NextResponse } from "next/server";
import { forward } from "@/lib/backend";

// Previously sent photos to OpenAI. Now forwards to the local YOLOv8n detector in the FastAPI service.
export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const file = formData.get("file");
    if (!(file instanceof File)) {
      return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
    }
    const body = new FormData();
    body.append("file", file);
    const res = await forward("/api/vision/detect", { method: "POST", body });
    const data = await res.json();
    if (!res.ok) return NextResponse.json({ error: data.detail || "Detection failed" }, { status: res.status });
    return NextResponse.json({ ingredients: data.ingredients.map((i: { name: string }) => i.name), details: data });
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Failed to detect ingredients." }, { status: 500 });
  }
}
