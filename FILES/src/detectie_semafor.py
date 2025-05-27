from ultralytics import YOLO
import cv2
import numpy as np
import os

model = YOLO("yolov8n.pt")

def detect_traffic_light_color(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    red_mask = cv2.inRange(hsv, (0, 70, 50), (10, 255, 255)) | \
               cv2.inRange(hsv, (160, 70, 50), (180, 255, 255))
    green_mask = cv2.inRange(hsv, (40, 70, 50), (90, 255, 255))
    yellow_mask = cv2.inRange(hsv, (15, 70, 50), (35, 255, 255))
    red = cv2.countNonZero(red_mask)
    green = cv2.countNonZero(green_mask)
    yellow = cv2.countNonZero(yellow_mask)
    if red > green and red > yellow: return "RED"
    elif green > red and green > yellow: return "GREEN"
    elif yellow > red and yellow > green: return "YELLOW"
    return "UNKNOWN"

def analizeaza_semafor_din_imagine(image_path, folder_rezultate):
    frame = cv2.imread(image_path)
    if frame is None:
        print("❌ Imagine invalidă:", image_path)
        return "fara semafor"

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    os.makedirs(folder_rezultate, exist_ok=True)

    h, w, _ = frame.shape
    center_image = (w // 2, h // 2)
    results = model(frame)
    names = model.names

    # Salvează imagine cu toate obiectele detectate
    img_all = results[0].plot()
    cv2.imwrite(os.path.join(folder_rezultate, f"{base_name}_ALL.jpg"), img_all)

    semafoare_utilizabile = []

    for idx, box in enumerate(results[0].boxes):
        cls_id = int(box.cls)
        label = names[cls_id]
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        roi = frame[y1:y2, x1:x2]

        # Salvează fiecare ROI
        roi_name = f"{base_name}_ROI_{idx}_{label}.jpg"
        cv2.imwrite(os.path.join(folder_rezultate, roi_name), roi)

        if label == "traffic light":
            culoare = detect_traffic_light_color(roi)
            if culoare in ["YELLOW", "UNKNOWN"]:
                continue  # ignorăm

            center_box = ((x1 + x2) // 2, (y1 + y2) // 2)
            dist_to_center = np.linalg.norm(np.array(center_box) - np.array(center_image))

            semafoare_utilizabile.append({
                "box": (x1, y1, x2, y2),
                "culoare": culoare,
                "distanta": dist_to_center
            })

    # Dacă nu avem niciunul valid:
    if not semafoare_utilizabile:
        return "fara semafor"

    # ✅ Dacă e exact unul valid → îl luăm fără comparații
    if len(semafoare_utilizabile) == 1:
        cel_ales = semafoare_utilizabile[0]
    else:
        # Dacă sunt mai mulți → alegem cel mai apropiat de centru
        cel_ales = min(semafoare_utilizabile, key=lambda x: x["distanta"])

    # Salvează doar imaginea finală cu semaforul ALES
    x1, y1, x2, y2 = cel_ales["box"]
    culoare = cel_ales["culoare"]

    frame_copy = frame.copy()
    cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(frame_copy, culoare, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # cv2.imwrite(os.path.join(folder_rezultate, f"{base_name}_traffic_light_{culoare}.jpg"), frame_copy)
    cv2.imwrite(os.path.join(folder_rezultate, f"{base_name}_SEMAFOR_ALES.jpg"), frame_copy)

    return culoare
