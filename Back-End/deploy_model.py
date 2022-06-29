from tensorflow.keras.models import load_model
from flask import Flask, request, render_template, jsonify
import cv2
import numpy as np
from flask_cors import CORS, cross_origin
import base64
from dlib import get_frontal_face_detector




# load model dan label
modelpath = 'model/upgrade_model.h5'
labels = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
model = load_model(modelpath)
faceDetector = get_frontal_face_detector()

def image2Base64(img):
    retval, buffer = cv2.imencode('.jpg', img)
    base64_img = base64.b64encode(buffer)
    base64_img = str(base64_img,'utf-8')
    return base64_img

def crop_image_dlib(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = faceDetector(gray, 1)
    if len(faces) == 0:
        return None
    top = faces[0].top()
    bottom = faces[0].bottom()
    left = faces[0].left()
    right = faces[0].right()
    img = img[top:bottom, left:right]
    return img

def crop_image(img):
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    face_bb = face_cascade.detectMultiScale(gray_img, 1.1, 4)
    if len(face_bb) == 0:
        return None
    x, y, w, h = face_bb[0]
    crop_img = img[y:y + h, x:x + w]

    return crop_img


def preprocessing_image(crop_image):
        # img = image.load_img(imagepath,target_size = (48,48),color_mode = "grayscale")
    img = cv2.cvtColor(crop_image, cv2.COLOR_BGR2GRAY)
    img = cv2.resize(img, (48,48))
    base64_img = image2Base64(img)
    # print(img.shape)
    # print(type(img))
    img = cv2.normalize(img, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
    img = np.expand_dims(img,axis = 0)
    return img, base64_img


def predict_emotion(prep_img):
    result = model.predict(prep_img)
    return result


def single_predict(img):
    img = crop_image_dlib(img)
    if img is None:
        return None, None
    # print(img, file=sys.stdout)
    img, base64_img = preprocessing_image(img)
    # print(img)
    result = predict_emotion(img)
    # img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # result = img.shape
    return result, base64_img


def summary_predict(predicts: list) -> dict:
    summary = dict(zip(labels, np.zeros(7)))
    numberPredict = 0
    for predict in predicts:
        if predict['predict'] is None:
            continue
        numberPredict += 1
        for label in labels:
            summary[label] += predict['predict'][label]
    if numberPredict == 0:
        return summary
    summary = {key: summary[key] / numberPredict for key in summary}
    return summary


app = Flask("__name__")
CORS(app)

@app.route('/api/predict', methods=['POST'])
@cross_origin()
def predictEmotion():
    predicts = []
    file_images = request.files.getlist('image')
    total_images = len(file_images)

    
    for file_image in file_images:
        name = file_image.filename
        npimg = np.fromfile(file_image, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        temp_predict, base64_img = single_predict(img)

        if temp_predict is not None:
            temp_predict = dict(zip(labels, temp_predict[0].tolist()))
        
        predict = {
            'name' : name,
            'image' : base64_img,
            'predict' : temp_predict
        }
        predicts.append(predict)


    summary = summary_predict(predicts)
    result = {
        'predictions': predicts,
        'summary': summary
    }
    return jsonify(result)


if __name__ == '__main__':
    app.run(port=5000, debug=True)
