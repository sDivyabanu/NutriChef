from ultralytics import YOLO
model = YOLO("yolov8n.pt") 
# load the YOLOv8 food detection model
  # small YOLOv8 food model

# path to your test image
img_path = "C:/Users/sdivy/OneDrive/Desktop/pics/ing1.png"




# predict ingredients
results = model(img_path)

# print detected ingredients
for r in results:
    for box, cls, conf in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
        print(f"Ingredient: {model.names[int(cls)]}, Confidence: {conf:.2f}")
