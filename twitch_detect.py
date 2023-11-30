import cv2
import mediapipe as mp

import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_face_mesh = mp.solutions.face_mesh


# For webcam input:
drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)
cap = cv2.VideoCapture(0)


class ANN(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(in_features=956, out_features=500)
        self.fc2 = nn.Linear(in_features=500, out_features=200)
        self.fc3 = nn.Linear(in_features=200, out_features=50)
        self.output = nn.Linear(in_features=50, out_features=2)
 
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = self.output(x)
        return x


def detect(conn):
    
    model = torch.load('model.pth')
    # print("Model Parameters:\n",model.eval(), sep='')

    if conn is not None:
        conn.send("Ready")

    with mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5) as face_mesh:

        while cap.isOpened():
            success, image = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                # If loading a video, use 'break' instead of 'continue'.
                continue

            # To improve performance, optionally mark the image as not writeable to
            # pass by reference.
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(image)

            # Draw the face mesh annotations on the image.
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            if results.multi_face_landmarks:

                face = []

                face_landmarks = results.multi_face_landmarks[0]
                landmarks = face_landmarks.landmark

                for landmark in landmarks:
                    face.extend([landmark.x, landmark.y])

                for face_landmarks in results.multi_face_landmarks:

                    mp_drawing.draw_landmarks(
                            image=image,
                            landmark_list=face_landmarks,
                            connections=mp_face_mesh.FACEMESH_TESSELATION,
                            landmark_drawing_spec=None,
                            connection_drawing_spec=mp_drawing_styles
                            .get_default_face_mesh_tesselation_style())
                    mp_drawing.draw_landmarks(
                            image=image,
                            landmark_list=face_landmarks,
                            connections=mp_face_mesh.FACEMESH_CONTOURS,
                            landmark_drawing_spec=None,
                            connection_drawing_spec=mp_drawing_styles
                            .get_default_face_mesh_contours_style())


                if conn is not None and conn.poll(0.005):
                    if conn.recv() == "Request":
                        conn.send(model.forward(torch.FloatTensor(face)).argmax().item())

                if __name__ == "__main__":
                    print(model.forward(torch.FloatTensor(face)).argmax().item())


            # Flip the image horizontally for a selfie-view display.
            cv2.imshow('MediaPipe Face Mesh', cv2.flip(image, 1))
            if cv2.waitKey(10) & 0xFF == 27:
                break

    conn.close()
    cap.release()

if __name__ == "__main__":
    detect(None)

