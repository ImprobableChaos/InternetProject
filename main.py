from flask import Flask, render_template, Response, request, redirect, url_for
import os
import cv2 as cv
from imutils.video.pivideostream import PiVideoStream
import imutils
import time
from datetime import datetime
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()

class VideoCamera(object):
    def __init__(self, file_type=".jpg", photo_string="stream_photo"):
        self.vs = PiVideoStream().start()
        self.file_type = file_type
        self.photo_string = photo_string
        time.sleep(2.0)

    def __del__(self):
        self.vs.stop()

    def frame(self, frame):
        return frame

    def get_frame(self):
        frame = self.frame(self.vs.read())
        ret, jpeg = cv.imencode(self.file_type, frame)
        self.previous_frame = jpeg
        return jpeg.tobytes()

    # Take a photo, called by camera button
    def take_picture(self):
        frame = self.frame(self.vs.read())
        ret, image = cv.imencode(self.file_type, frame)
        today_date = datetime.now().strftime("%m%d%Y-%H%M%S")  # get current time
        cv.imwrite(str(self.photo_string + "_" + today_date + self.file_type), frame)


app = Flask(__name__)
pi_camera = VideoCamera()

#Servo Motor Setup

OFFSE_DUTY = 0.5
SERVO_MIN_DUTY = 2.5+OFFSE_DUTY
SERVO_MAX_DUTY = 12.5+OFFSE_DUTY
servoPin = 12


def setup():
    global p
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(servoPin, GPIO.OUT)
    GPIO.output(servoPin, GPIO.LOW)

    p = GPIO.PWM(servoPin, 50)
    p.start(0)


def servoWrite(angle):
    if angle < 0:
        angle = 0
    elif angle > 180:
        angle = 180

    p.ChangeDutyCycle(map(angle,0,180,SERVO_MIN_DUTY,SERVO_MAX_DUTY))


def setOpen():
    servoWrite(90)


def setClose():
    servoWrite(0)


def destroy():
    p.stop()
    GPIO.cleanup()


@app.route("/live")
def live():
    return render_template("home.html")


def generate(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


@app.route("/video_feed")
def video_feed():
    return Response(generate(pi_camera),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/picture")
def take_picture():
    pi_camera.take_picture()
    return "None"


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            return redirect(url_for('live'))
    return render_template('login.html', error=error)

@app.route("/")
def run():
    setup()


    try:
        while True:
            id, text = reader.read()
            if id != 0:
                setOpen()
            else:
                setClose()
    finally:
        GPIO.cleanup()



if __name__ == "__main__":
    app.directory = "./"
    app.run(host="0.0.0.0", port=5000)
