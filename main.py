from flask import Flask, render_template, Response, request, redirect, url_for, session
import cv2 as cv
import time
import RPi.GPIO as GPIO
from multiprocessing import Process
from camera import CameraStream
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

GPIO.cleanup()
logged_in = True

app = Flask(__name__)

pi_camera = CameraStream().start()

# Servo Motor Setup

OFFSE_DUTY = 0.5
SERVO_MIN_DUTY = 2.5 + OFFSE_DUTY
SERVO_MAX_DUTY = 12.5 + OFFSE_DUTY
servoPin = 12


def map(value, fromLow, fromHigh, toLow, toHigh):
    return (toHigh - toLow) * (value - fromLow) / (fromHigh - fromLow) + toLow


def setup_servo():
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

    p.ChangeDutyCycle(map(angle, 0, 180, SERVO_MIN_DUTY, SERVO_MAX_DUTY))


def destroy_servo():
    p.stop()
    GPIO.cleanup()


@app.route("/live")
def live():
    if logged_in:
        return render_template("home.html")
    else:
        return redirect(url_for("login"))


def generate():
    while pi_camera:
        frame = pi_camera.read()
        convert = cv.imencode(".jpg", frame)[1].tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + convert + b'\r\n\r\n')


@app.route("/video_feed")
def video_feed():
    print("Video Feed")
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/unlock_door")
def unlock_door():
    if logged_in:
        for dc in range(0, 181, 1):  # make servo rotate from 0 to 180 deg
            servoWrite(dc)  # Write dc value to servo
            time.sleep(0.001)
        return "None"
    else:
        return redirect(url_for("login"))


@app.route("/lock_door")
def lock_door():
    if logged_in:
        for dc in range(180, 1, -1):  # make servo rotate from 180 to 0 deg
            servoWrite(dc)
            time.sleep(0.001)
        return "None"
    else:
        return redirect(url_for("login"))


@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            global logged_in
            logged_in = True
            return redirect(url_for('live'))
    return render_template('login.html', error=error)


def interpret_card(reader):
    id, text = reader.read()
    text = str(text)
    print(f"{id},{text}")
    if text == "Card":
        print("returning unlock")
        return "unlock"
    elif text == "Keychain":
        print("returning lock")
        return "lock"
    else:
        print("No read")
        return None


def RFID():
    reader = SimpleMFRC522()
    while True:
        output = interpret_card(reader)
        if output is not None:
            if output == "unlock":
                print("unlock")
                unlock_door()
            elif output == "lock":
                print("lock")
                lock_door()


if __name__ == "__main__":
    setup_servo()
    try:
        q = Process(target=RFID)
        q.start()
        app.directory = "./"
        app.run(host="0.0.0.0", port=5000, threaded=True)
    except KeyboardInterrupt:
        pi_camera.stop()
        destroy_servo()

