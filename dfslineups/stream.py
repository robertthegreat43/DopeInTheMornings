import cv2
import time

class CameraController:
    def __init__(self):
        self.cap = None              # Camera NOT started yet
        self.recording = False
        self.writer = None

    def init_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)

    def get_frame(self):
        # Ensure camera is initialized
        if self.cap is None:
            self.init_camera()

        success, frame = self.cap.read()
        if not success:
            return None

        _, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes(), frame

    def stream(self):
        while True:
            jpeg, frame = self.get_frame()
            if jpeg is None:
                continue

            if self.recording and self.writer:
                self.writer.write(frame)

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')

    def start_recording(self):
        self.init_camera()  # Camera starts HERE

        if not self.recording:
            self.recording = True
            filename = f"recording_{int(time.time())}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.writer = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
            return filename
        return None

    def stop_recording(self):
        self.recording = False
        if self.writer:
            self.writer.release()
            self.writer = None
        return None
