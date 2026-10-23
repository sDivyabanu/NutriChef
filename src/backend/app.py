from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import shutil

app = FastAPI()

# allow your Next.js frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # your frontend dev URL
    allow_methods=["*"],
    allow_headers=["*"],
)

model = YOLO("yolov8n.pt") 

@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    # save uploaded file
    file_location = f"temp_{file.filename}"
    with open(file_location, "wb") as f:
        shutil.copyfileobj(file.file, f)

    results = model(file_location)

    ingredients = []
    for r in results:
        for cls in r.boxes.cls:
            ingredients.append(model.names[int(cls)])

    return {"ingredients": list(set(ingredients))}  # remove duplicates
