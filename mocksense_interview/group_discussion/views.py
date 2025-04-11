import os
import json
import time
import random
import base64
import logging
import numpy as np
import cv2
from dotenv import load_dotenv
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from keras.models import model_from_json
import google.generativeai as genai

# Base Directory and Logging
BASE_DIR = settings.BASE_DIR
logger = logging.getLogger(__name__)
load_dotenv()

# Load Emotion Detection Model
emotion_model_path = BASE_DIR / "mock_interview/ML_model/emotiondetector_updated.json"
emotion_weights_path = BASE_DIR / "mock_interview/ML_model/emotiondetector_updated.h5"

with open(emotion_model_path, "r") as json_file:
    emotion_model = model_from_json(json_file.read())

emotion_model.load_weights(emotion_weights_path)

# Load Motivational Quotes
with open(BASE_DIR / "mock_interview/ML_model/motivational_quotes.json", "r") as file:
    quotes = json.load(file)["quotes"]

# Labels and Haar Cascade
labels = {0: "fear", 1: "confused", 2: "shy", 3: "neutral", 4: "happy"}
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Quote display configuration
CONFUSED_THRESHOLD = 3
QUOTE_DISPLAY_DURATION = 7
NEXT_QUOTE_DELAY = 4

# Quote tracking state
confused_start_time = None
quote_display_time = None
current_quote = None

# Google Gemini API setup
apikey = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=apikey)
model = genai.GenerativeModel("models/gemini-1.5-pro")

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


def discussion_view(request):
    return render(request, "group_discussion/index.html")


def start_grp_discussion_view(request):
    """Generate topic and AI sample discussion."""
    topic = request.GET.get("topic", "").strip()

    if topic:
        prompt = (
            f"Create a group discussion around the topic: '{topic}'.\n"
            "Simulate a discussion between two participants: Male and Female.\n"
            "Each person should share 3 points in a conversational, easy-to-understand tone.\n"
            "Keep it natural, realistic, and friendly. Avoid formal speech.\n\n"
            f"Group Discussion Topic: {topic}\n\n"
            "Male:\n1. ...\n2. ...\n3. ...\n\n"
            "Female:\n1. ...\n2. ...\n3. ..."
        )
    else:
        prompt = (
            "Generate a random group discussion topic. It Should be most random topics. Like Technology, current affairs, society and etc... It should be random every time.\n\n"
            "Then simulate a discussion between Male and Female.\n"
            "Each person shares 3 points casually.\n\n"
            "Group Discussion Topic: <Topic>\n\n"
            "Male:\n1. ...\n2. ...\n3. ...\n\n"
            "Female:\n1. ...\n2. ...\n3. ..."
        )

    response = model.generate_content(prompt)
    lines = response.text.strip().splitlines()

    topic, male_points, female_points, current_speaker = "", [], [], None
    for line in lines:
        line = line.strip()
        if line.lower().startswith("group discussion topic"):
            topic = line.split(":", 1)[1].strip()
        elif line.lower().startswith("male"):
            current_speaker = "male"
        elif line.lower().startswith("female"):
            current_speaker = "female"
        elif line and line[0].isdigit() and "." in line:
            point = line.split(".", 1)[1].strip()
            if current_speaker == "male":
                male_points.append(point)
            elif current_speaker == "female":
                female_points.append(point)

    with open(BASE_DIR / "group_discussion/response.txt", "w", encoding="utf-8") as file:
        file.write(f"Group Discussion Topic: {topic}\n\nMale:\n")
        file.writelines(f"{i+1}. {p}\n" for i, p in enumerate(male_points))
        file.write("\nFemale:\n")
        file.writelines(f"{i+1}. {p}\n" for i, p in enumerate(female_points))

    return render(request, "group_discussion/brainstorming.html", {"topic": topic})


def group_discussion_view(request):
    """Render group discussion with topic and sample responses."""
    topic = ""
    male_points, female_points = [], []

    with open(BASE_DIR / "group_discussion/response.txt", "r", encoding="utf-8") as file:
        lines = file.readlines()

        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith("Group Discussion Topic:"):
                topic = line.split(":", 1)[1].strip()
            elif line.startswith("Male:"):
                current_section = "male"
            elif line.startswith("Female:"):
                current_section = "female"
            elif line and line[0].isdigit():
                point = line.split(".", 1)[1].strip()
                if current_section == "male":
                    male_points.append(point)
                elif current_section == "female":
                    female_points.append(point)

    return render(request, "group_discussion/discussion.html", {
        "topic": topic,
        "male_points": male_points,
        "female_points": female_points,
        "proctored":True
    })


@csrf_exempt
def save_user_gd_response(request):
    """Save and improve user responses using Gemini."""
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request."}, status=400)

    try:
        data = json.loads(request.body)
        topic = data.get("topic", "")
        responses = data.get("user_responses", [])

        response_path = BASE_DIR / "group_discussion/user_gd_response.txt"
        with open(response_path, "w", encoding="utf-8") as file:
            file.write(f"Topic: {topic}\n\n")
            for item in responses:
                file.write(f"Round {item['round']}: {item['response']}\n")

        # Use Gemini to improve the responses
        with open(response_path, "r", encoding="utf-8") as file:
            user_text = file.read()

        prompt = (
            "Improve the clarity, grammar, and structure of these responses for a group discussion. "
            "Return the improved sentences as a bullet list. Don't change the context.\n\n"
            f"{user_text}"
        )

        response = model.generate_content(prompt)
        improved_path = BASE_DIR / "group_discussion/improved_response.txt"

        with open(improved_path, "w", encoding="utf-8") as file:
            file.write(response.text.strip())

        return JsonResponse({"status": "success", "message": "Responses saved and improved."})

    except Exception as e:
        logger.exception("Failed to process user responses.")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def improve_sentences_view(request):
    """Render the improved vs original responses, then clear files for next session."""
    user_path = BASE_DIR / "group_discussion/user_gd_response.txt"
    improved_path = BASE_DIR / "group_discussion/improved_response.txt"

    with open(user_path, "r", encoding="utf-8") as file:
        user_text = file.read()
    with open(improved_path, "r", encoding="utf-8") as file:
        improved_text = file.read()

    return render(request, "group_discussion/result.html", {
        "original": user_text,
        "improved": improved_text
    })

@csrf_exempt
def group_discussion(request):
    """Handle ongoing user input during live discussion."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
        topic = data.get("topic", "General")
        user_response = data.get("user_response", "")

        logger.debug(f"User Response: {user_response}")

        # Placeholder response – integrate AI if needed
        ai_response = "Hello"

        return JsonResponse({
            "ai_male": ai_response,
            "ai_female": ai_response
        })

    except json.JSONDecodeError:
        logger.error("Invalid JSON received")
        return JsonResponse({"error": "Invalid JSON"}, status=400)
