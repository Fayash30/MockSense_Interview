import os
import json
import time
import random
import pickle
import logging
import numpy as np
import cv2
import spacy
import base64
from io import BytesIO
from PIL import Image
import tensorflow as tf
from pathlib import Path
from keras.models import model_from_json
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from pdfminer.high_level import extract_text
from tensorflow.keras.preprocessing.sequence import pad_sequences
import speech_recognition as sr
from sentence_transformers import SentenceTransformer, util

# Load spaCy model
nlp = spacy.load("en_core_web_lg")
similarity_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
# Load pre-trained RNN model and tokenizer
question_generator_path = settings.BASE_DIR / "mock_interview/ML_model/question_generator_rnn.h5"
model = tf.keras.models.load_model(question_generator_path)
with open(settings.BASE_DIR / "mock_interview/ML_model/tokenizer.pkl", "rb") as f:
    tokenizer = pickle.load(f)
with open(settings.BASE_DIR / "mock_interview/ML_model/label_encoder.pkl", "rb") as f:
    label_encoder = pickle.load(f)

# Load intents dataset
with open(settings.BASE_DIR / "mock_interview/ML_model/data/intents.json", 'r') as file:
    data = json.load(file)

max_length = 20  # This should match training config

def generate_question(user_response):
    input_sequence = tokenizer.texts_to_sequences([user_response])
    input_padded = pad_sequences(input_sequence, maxlen=max_length, padding='post')
    predicted_index = np.argmax(model.predict(input_padded))
    predicted_tag = label_encoder.inverse_transform([predicted_index])[0]

    question_response_map = {}
    for intent in data['intents']:
        if intent['tag'] == predicted_tag:
            for pattern in intent['patterns']:
                question_response_map[pattern] = intent['responses'][0]

    if not question_response_map:
        return "Sorry, I couldn't determine the topic from your response.", None

    question = random.choice(list(question_response_map.keys()))
    answer = question_response_map[question]
    return question, answer

def generate_questions_from_resume(resume_json):
    with open(resume_json, 'r') as file:
        resume_data = json.load(file)

    skills = resume_data.get("Skills", [])
    projects = resume_data.get("Projects", [])
    topics = skills + projects

    if len(topics) < 5:
        topics = topics * (5 // len(topics) + 1)

    topics = topics[:5]

    questions_answers = []
    for topic in topics:
        question, answer = generate_question(topic)
        questions_answers.append({"question": question, "answer": answer})

    return questions_answers

# Load Emotion Detection Model
emotion_model_path = settings.BASE_DIR / "mock_interview/ML_model/emotiondetector_updated.json"
emotion_weights_path = settings.BASE_DIR / "mock_interview/ML_model/emotiondetector_updated.h5"
with open(emotion_model_path, "r") as json_file:
    emotion_model = model_from_json(json_file.read())
emotion_model.load_weights(emotion_weights_path)

# Load Motivational Quotes
with open(settings.BASE_DIR / "mock_interview/ML_model/motivational_quotes.json", "r") as file:
    quotes = json.load(file)["quotes"]

# Emotion labels
labels = {0: "fear", 1: "confused", 2: "shy", 3: "neutral", 4: "happy"}

# Haar Cascade for Face Detection
haar_file = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(haar_file)

# Config values
CONFUSED_THRESHOLD = 5
QUOTE_DISPLAY_DURATION = 7
NEXT_QUOTE_DELAY = 5
ANSWER_TIME_LIMIT = 10

confused_start_time = None
quote_display_time = None
current_quote = None

# Load keywords
with open(settings.BASE_DIR / "mock_interview/ML_model/data/keywords.json", "r") as file:
    keywords = json.load(file)

def load_questions():
    questions_path = os.path.join(settings.BASE_DIR, "mock_interview", "ML_model", "questions.json")
    with open(questions_path, "r", encoding="utf-8") as file:
        return json.load(file)["questions"]

def start_interview(request):
    file_path = os.path.join(settings.BASE_DIR, "mock_interview", "user_answers.json")
    if os.path.exists(file_path):
        os.remove(file_path)
    questions = load_questions()
    return JsonResponse({"status": "started", "questions": questions})

@csrf_exempt
def save_answer(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            with open("mock_interview/user_answers.json", "a") as file:
                json.dump({"question_index": data["question_index"], "answer": data["answer"]}, file)
                file.write("\n")
            return JsonResponse({"status": "saved"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)

def listen_answer(request):
    if request.method == "POST":
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            try:
                audio = recognizer.listen(source, timeout=5)
                user_answer = recognizer.recognize_google(audio)
                return JsonResponse({"status": "completed", "answer": user_answer})
            except sr.UnknownValueError:
                return JsonResponse({"status": "completed", "answer": "Could not understand"})
            except sr.RequestError:
                return JsonResponse({"status": "error", "message": "Speech recognition API unavailable"})
    return JsonResponse({"error": "Invalid request"}, status=400)

def quiz_view(request):
    return render(request, "mock_interview/quiz.html", {'proctored': True})

def generate_frames():
    global confused_start_time, quote_display_time, current_quote 
    cap = cv2.VideoCapture(0)
    while True:
        success, frame = cap.read()
        if not success:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        current_time = time.time()

        for (x, y, w, h) in faces:
            face = gray[y:y + h, x:x + w]
            face = cv2.resize(face, (48, 48))
            face = np.expand_dims(face, axis=0)
            face = np.expand_dims(face, axis=-1) / 255.0

            emotion_prediction = emotion_model.predict(face)
            emotion_text = labels[np.argmax(emotion_prediction)]

            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(frame, emotion_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

            if quote_display_time:
                if current_time - quote_display_time < QUOTE_DISPLAY_DURATION:
                    cv2.putText(frame, current_quote, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    quote_display_time = None
                    confused_start_time = None
            elif emotion_text == "confused":
                if confused_start_time is None:
                    confused_start_time = current_time
                elif current_time - confused_start_time >= CONFUSED_THRESHOLD:
                    current_quote = random.choice(quotes)
                    quote_display_time = current_time
                    confused_start_time = None

        _, buffer = cv2.imencode(".jpg", frame)
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")

def video_feed(request):
    return StreamingHttpResponse(generate_frames(), content_type="multipart/x-mixed-replace; boundary=frame")

def index(request):
    return render(request, "mock_interview/index.html")

def resume_uploading(request):
    return render(request, "mock_interview/resume_upload.html")

@csrf_exempt
def upload_resume(request):
    if request.method == "POST" and request.FILES.get("resume"):
        uploaded_file = request.FILES["resume"]
        file_path = default_storage.save("resumes/" + uploaded_file.name, uploaded_file)
        resume_text = extract_text(Path(settings.MEDIA_ROOT) / file_path)
        parsed_data = extract_resume_entities(resume_text)
        json_path = Path(settings.MEDIA_ROOT) / "resume_data.json"
        with open(json_path, "w", encoding="utf-8") as json_file:
            json.dump(parsed_data, json_file, indent=4)
        questions_with_answers = generate_questions_from_resume("resume_data.json")
        save_questions_and_answers(questions_with_answers)
        return JsonResponse(parsed_data, safe=False)
    return JsonResponse({"error": "No file uploaded"}, status=400)

def extract_resume_entities(text):
    doc = nlp(text)
    extracted_data = {"Name": "", "Skills": [], "Projects": []}
    skillset, projectset = set(), set()

    for ent in doc.ents:
        if ent.label_ == "PERSON" and not extracted_data["Name"]:
            extracted_data["Name"] = ent.text

    for line in text.split("\n"):
        for skill in keywords["skills"]:
            if skill.lower() in line.lower():
                skillset.add(skill)
        for project in keywords["projects"]:
            if project in line.lower():
                projectset.add(line.strip())

    extracted_data["Skills"] = list(skillset)
    extracted_data["Projects"] = [proj.replace("\u2022", "").strip() for proj in projectset]
    return extracted_data

def save_questions_and_answers(questions_with_answers):
    question_path = settings.BASE_DIR / "mock_interview/ML_model/questions.json"
    answer_path = settings.BASE_DIR / "mock_interview/ML_model/answers.json"

    questions = [qa["question"] for qa in questions_with_answers]
    answers = [qa["answer"] for qa in questions_with_answers]

    with open(question_path, "w", encoding="utf-8") as q_file:
        json.dump({"questions": questions}, q_file, indent=4)

    with open(answer_path, "w", encoding="utf-8") as a_file:
        json.dump({"answers": answers}, a_file, indent=4)

logger = logging.getLogger(__name__)

def load_correct_answers(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data["answers"] if isinstance(data, dict) and "answers" in data else []
    except Exception as e:
        logger.error(f"❌ Error loading correct answers: {e}")
        return []

def load_user_answers(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return [entry["answer"] for entry in data if "answer" in entry] if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"❌ Error loading user answers: {e}")
        return []

def calculate_similarity(answer, user_answer):
    if not is_valid_answer(user_answer):
        return 0.0  # Or a very low score
    embeddings = similarity_model.encode([answer, user_answer], convert_to_tensor=True)
    score = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
    return score

def limit_exceeded(request):
    reason = request.GET.get('reason', 'tab')
    return render(request, "limit_exceeded.html", {"proctored": True, "reason": reason})

def mock_interview_result(request):
    user_answer_file = settings.BASE_DIR / "mock_interview/user_answers.json"
    with open(user_answer_file, 'r') as file:
        lines = file.readlines()

    formatted_json = f"[{', '.join([line.strip() for line in lines])}]"
    with open(user_answer_file, 'w') as output_file:
        output_file.write(formatted_json)

    correct_answers = load_correct_answers(settings.BASE_DIR / "mock_interview/ML_model/answers.json")
    user_answers = load_user_answers(user_answer_file)

    if not correct_answers or not user_answers:
        return render(request, "result.html", {"error": "Missing answer files or invalid data format!"})

    similarity_scores = [calculate_similarity(ca, ua) for ca, ua in zip(correct_answers, user_answers)]
    overall_score = np.mean(similarity_scores) * 100

    result_data = {
        "similarity_scores": [round(score * 100, 2) for score in similarity_scores],
        "overall_score": round(overall_score, 2)
    }

    return render(request, "mock_interview/result.html", {"result_data": result_data})

def is_valid_answer(text):
    return text and text.strip().lower() not in ["", "could not understand", "i dont know", "iam not aware"]

@csrf_exempt
def detect_emotion(request):
    """Detect emotion and return motivational quote if user seems confused."""
    global confused_start_time, quote_display_time, current_quote

    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        image_base64 = data.get("image", "")
        if not image_base64:
            return JsonResponse({"error": "Missing 'image' data"}, status=400)

        image_data = base64.b64decode(image_base64.split(",")[1])
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return JsonResponse({"error": "Invalid image data"}, status=400)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        detected_emotion = "neutral"
        current_time = time.time()

        for (x, y, w, h) in faces:
            face = gray[y:y + h, x:x + w]
            face = cv2.resize(face, (48, 48))
            face = np.expand_dims(face, axis=(0, -1)) / 255.0

            emotion_prediction = emotion_model.predict(face)
            emotion_index = np.argmax(emotion_prediction)
            detected_emotion = labels[emotion_index]

            # Handle quote logic
            if quote_display_time and current_time - quote_display_time < QUOTE_DISPLAY_DURATION:
                return JsonResponse({"emotion": detected_emotion, "quote": current_quote})
            elif detected_emotion == "confused":
                if not confused_start_time:
                    confused_start_time = current_time
                elif current_time - confused_start_time >= CONFUSED_THRESHOLD:
                    current_quote = random.choice(quotes)
                    quote_display_time = current_time
                    confused_start_time = None
                    return JsonResponse({"emotion": detected_emotion, "quote": current_quote})
            else:
                confused_start_time = None

        return JsonResponse({"emotion": detected_emotion})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        logger.exception("Emotion detection failed")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def process_frame(request):
    import json
    data = json.loads(request.body)
    image_data = data.get('image')

    if image_data:
        # Remove the data:image/jpeg;base64, part
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Convert to OpenCV image
        pil_image = Image.open(BytesIO(image_bytes)).convert('RGB')
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # TODO: Run your emotion detection or proctoring logic here
        print("Received frame for analysis")

        # Dummy response
        return JsonResponse({ "status": "ok", "emotion": "happy" })

    return JsonResponse({ "status": "error", "message": "No image received" })
