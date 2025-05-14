from ultralytics import YOLO
import cv2
from math import dist
import asyncio
import websockets
import json
import base64
from threading import Thread, Lock
import time

# Global variables to share alert status and image between OpenCV and WebSocket
alert_status = None
alert_image = None
stop_server_flag = False
lock = Lock()  # Lock for thread-safe access to shared variables
last_alert_time = 0

# Function to send alert to the WebSocket server
async def send_alert():
    uri = "ws://localhost:3000"  # Adjust WebSocket server URI as needed
    global last_alert_time

    try:
        global alert_status, alert_image, stop_server_flag
        async with websockets.connect(uri) as websocket:
            while not stop_server_flag:  # Stop when the flag is set
                with lock:
                    if alert_status and alert_image:
                        # Check if 5 minutes have passed since the last alert
                        current_time = time.time()
                        if current_time - last_alert_time >= 20:  # 300 seconds = 5 minutes
                            # Prepare the data with message and encoded image
                            alert_data = json.dumps({
                                "message": alert_status,
                                "image": alert_image  # Send image as Base64 string
                            })

                            # Send data to WebSocket server
                            await websocket.send(alert_data)
                            print(f"Sent alert: {alert_status}")

                            last_alert_time = current_time

                            # Reset alert status and image after sending
                            alert_status = None
                            alert_image = None

                await asyncio.sleep(0.1)  # Avoid busy waiting

    except websockets.exceptions.InvalidURI:
        print(f"Error: Invalid WebSocket URI {uri}")
    except Exception as e:
        print(f"Error: {e}")


# Function to encode image to Base64
def encode_image_to_base64(image, max_width=800):
    height, width = image.shape[:2]
    if width > max_width:
        scaling_factor = max_width / width
        new_size = (int(width * scaling_factor), int(height * scaling_factor))
        image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

    _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 50])
    return base64.b64encode(buffer).decode('utf-8')

def run_argus():
    global alert_image
    global alert_status
    global stop_server_flag

    # Load models
    pose_model = YOLO('yolov8n-pose.pt')  # pose model
    weapon_model = YOLO('yolov8s_pistol.pt')  # weapon detection model

    # Classifications in models
    pose_names = pose_model.names
    weapon_names = weapon_model.names

    # IDs of interest for the models
    human_ids = [0, 15, 16, 17, 18, 19, 20, 21, 22, 23, 34, 42, 43, 76]
    weapon_ids = [0, 1]  # Example: Pistol and other weapon IDs

    # Helper function to find bottom center of a detected object
    def botm_center(x1, y1, x2, y2):
        x = int((x1 + x2) / 2)
        y = int(max(y1, y2))
        return [x, y]

    cap = cv2.VideoCapture("sm.mp4")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            break

        # Object detection for weapons
        weapon_results = weapon_model(frame, stream=True, verbose=False)
        weapon_centroids = []

        for result in weapon_results:
            boxes = result.boxes
            if boxes.shape[0] > 0:
                xyxy_array = boxes.xyxy.cpu().numpy()
                cls_array = boxes.cls.cpu().numpy()
                for xyxy, cls in zip(xyxy_array, cls_array):
                    if int(cls) in weapon_ids:
                        x1, y1, x2, y2 = map(int, xyxy)
                        weapon_centroids.append(botm_center(x1, y1, x2, y2))
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

                        # Weapon detected, send alert to server
                        with lock:
                            alert_status = "ALERT: Threat detected from location 2"
                            alert_image = encode_image_to_base64(frame)

        # Object detection for humans
        pose_results = pose_model.track(frame, stream=True, verbose=False)

        for result in pose_results:
            boxes = result.boxes
            if boxes.shape[0] > 0:
                if boxes.id is not None:
                    ids_array = boxes.id.cpu().numpy()
                else:
                    ids_array = None
                xyxy_array = boxes.xyxy.cpu().numpy()
                cls_array = boxes.cls.cpu().numpy()

                for xyxy, cls in zip(xyxy_array, cls_array):
                    if int(cls) in human_ids:
                        x1, y1, x2, y2 = map(int, xyxy)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Check who is holding the weapon
                if weapon_centroids:
                    keypoints = result.keypoints.xy.cpu().numpy()
                    suspect_ids = []

                    for center in weapon_centroids:
                        min_dist = 500
                        suspect_id = None
                        if ids_array is not None:
                            for id, keypoint in zip(ids_array, keypoints):
                                left_wrist = keypoint[9]
                                right_wrist = keypoint[10]
                                lor_dist = min(dist(left_wrist, center), dist(right_wrist, center))

                                if lor_dist < min_dist:
                                    min_dist = lor_dist
                                    suspect_id = int(id)
                        else:
                            ids_index = -1
                            for keypoint in keypoints:
                                ids_index += 1
                                left_wrist = keypoint[9]
                                right_wrist = keypoint[10]
                                lor_dist = min(dist(left_wrist, center), dist(right_wrist, center))

                                if lor_dist < min_dist:
                                    min_dist = lor_dist
                                    suspect_id = ids_index

                        if suspect_id not in suspect_ids and suspect_id is not None:
                            suspect_ids.append(suspect_id)

                    if suspect_ids:
                        for id in suspect_ids:
                            x1, y1, x2, y2 = map(int, xyxy_array[id-1])
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                            cv2.putText(frame, f"Suspect: {suspect_ids.index(id)+1}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        cv2.imshow('camera live feed', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_server_flag = True
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Run OpenCV in a separate thread
    argus_thread = Thread(target=run_argus)
    argus_thread.start()

    # Run WebSocket server in asyncio event loop
    asyncio.run(send_alert())
