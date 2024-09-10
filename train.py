import tkinter as tk
from tkinter import Message, Text
import cv2, os
import csv
import numpy as np
from PIL import Image
import pandas as pd
import datetime
import time

# Function to ensure the directory exists
def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# Function to ensure the CSV has the correct headers
def ensure_csv_headers(file_path, headers):
    if not os.path.isfile(file_path):
        # If file doesn't exist, create it with headers
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
    else:
        # If file exists, check headers
        with open(file_path, 'r') as file:
            reader = csv.reader(file)
            existing_headers = next(reader, None)
        
        if existing_headers != headers:
            print(f"The required columns {headers} are missing from the CSV file!")
            # Optionally rewrite the file with correct headers
            with open(file_path, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(headers)

# Function to capture and save images
def TakeImages():
    Id = txt.get()
    name = txt2.get()
    if not Id.isnumeric() or not name.isalpha():
        res = "Invalid Input"
        message.configure(text=res)
        return
    
    cam = cv2.VideoCapture(0)
    harcascadePath = "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(harcascadePath)
    sampleNum = 0
    
    ensure_directory_exists('TrainingImage')
    
    while True:
        ret, img = cam.read()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in faces:
            sampleNum += 1
            cv2.imwrite(os.path.join('TrainingImage', f"{name}.{Id}.{sampleNum}.jpg"), gray[y:y + h, x:x + w])
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.imshow('Frame', img)
        if cv2.waitKey(100) & 0xFF == ord('q'):
            break
        elif sampleNum > 60:
            break
    cam.release()
    cv2.destroyAllWindows()
    
    res = f"Images Saved for ID : {Id}, Name : {name}"
    
    # Save student details with correct headers
    ensure_directory_exists('StudentDetails')
    file_path = os.path.join('StudentDetails', 'StudentDetails.csv')
    
    # Ensure correct headers exist in the CSV
    ensure_csv_headers(file_path, ['Id', 'Name'])
    
    with open(file_path, 'a+', newline='') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow([Id, name])
    
    message.configure(text=res)

# Function to train images and save recognizer model
def TrainImages():
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    harcascadePath = "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(harcascadePath)
    
    ensure_directory_exists('TrainingImageLabel')

    faces, Ids = getImagesAndLabels('TrainingImage')
    
    recognizer.train(faces, np.array(Ids))
    recognizer.save(os.path.join('TrainingImageLabel', 'Trainner.yml'))
    
    res = "Image Trained"
    message.configure(text=res)

# Function to get images and labels for training
def getImagesAndLabels(path):
    imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
    faces = []
    Ids = []
    for imagePath in imagePaths:
        pilImage = Image.open(imagePath).convert('L')
        imageNp = np.array(pilImage, 'uint8')
        Id = int(os.path.split(imagePath)[-1].split('.')[1])
        faces.append(imageNp)
        Ids.append(Id)
    return faces, Ids

# Function to track images and mark attendance
def TrackImages():
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    try:
        recognizer.read(os.path.join('TrainingImageLabel', 'Trainner.yml'))
    except cv2.error as e:
        print(f"Error reading training file: {e}")
        return
    
    harcascadePath = "haarcascade_frontalface_default.xml"
    faceCascade = cv2.CascadeClassifier(harcascadePath)
    
    try:
        df = pd.read_csv(os.path.join('StudentDetails', 'StudentDetails.csv'))
    except FileNotFoundError:
        print("CSV file with student details not found!")
        return
    
    # Ensure CSV has required columns
    if 'Id' not in df.columns or 'Name' not in df.columns:
        print("The required columns ('Id', 'Name') are missing from the CSV file!")
        return
    
    cam = cv2.VideoCapture(0)
    font = cv2.FONT_HERSHEY_SIMPLEX
    ensure_directory_exists('Attendance')
    
    while True:
        ret, img = cam.read()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = faceCascade.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in faces:
            Id, conf = recognizer.predict(gray[y:y + h, x:x + w])
            if conf < 50:
                name = df.loc[df['Id'] == Id]['Name'].values
                tt = f"{Id}-{name[0]}"
                ts = time.time()
                date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                timeStamp = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                attendance = [Id, name[0], date, timeStamp]
                
                with open(os.path.join('Attendance', 'Attendance.csv'), 'a+', newline='') as csvFile:
                    writer = csv.writer(csvFile)
                    writer.writerow(attendance)
            else:
                tt = 'Unknown'
            cv2.putText(img, str(tt), (x, y + h), font, 1, (255, 255, 255), 2)
            cv2.imshow('Frame', img)
        if cv2.waitKey(1) == ord('q'):
            break
    cam.release()
    cv2.destroyAllWindows()

# GUI setup
def setup_gui():
    global txt, txt2, message
    
    window = tk.Tk()
    window.title("Face Recognition Attendance System")

    tk.Label(window, text="Enter ID").grid(row=0, column=0)
    txt = tk.Entry(window)
    txt.grid(row=0, column=1)

    tk.Label(window, text="Enter Name").grid(row=1, column=0)
    txt2 = tk.Entry(window)
    txt2.grid(row=1, column=1)

    tk.Button(window, text="Take Images", command=TakeImages).grid(row=2, column=0)
    tk.Button(window, text="Train Images", command=TrainImages).grid(row=2, column=1)
    tk.Button(window, text="Track Images", command=TrackImages).grid(row=2, column=2)

    message = tk.Label(window, text="", fg="red")
    message.grid(row=3, columnspan=3)

    window.mainloop()

if __name__ == "__main__":
    setup_gui()
