import json
import random
import os
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt

# Load questions from JSON file
def load_questions():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "data", "questions.json")
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def get_mixed_category_questions(data):
    selected_questions = []
    for category in ["Logical", "Quants", "Verbal", "Reasoning"]:
        all_levels = data[category]["Easy"] + data[category]["Medium"] + data[category]["Hard"]
        selected_questions += random.sample(all_levels, min(5, len(all_levels)))
    random.shuffle(selected_questions)
    return selected_questions

# Initial quiz view
def quiz_view(request):
    if request.method == "POST":
        return redirect("quiz_questions")
    return render(request, "quiz.html")

# Quiz page UI loader
def quiz_questions(request):
    return render(request, "quiz_questions.html", {"proctored" : True})

# ✅ Serve questions via AJAX
def get_questions(request):
    data = load_questions()
    if not data:
        return JsonResponse({"error": "Could not load questions."}, status=500)

    questions = get_mixed_category_questions(data)

    request.session["questions"] = questions  # ✅ Save full questions (with answer)

    # 🔒 Send copy to frontend without answers
    frontend_questions = []
    for q in questions:
        q_copy = q.copy()
        q_copy.pop("answer", None)
        frontend_questions.append(q_copy)

    request.session["answers"] = []  # reset previous answers
    return JsonResponse(frontend_questions, safe=False)

# ✅ Accept submitted answers and redirect
@csrf_exempt
def submit_answers(request):
    if request.method == "POST":
        try:
            payload = json.loads(request.body)
            user_answers = payload.get("answers", [])

            session_questions = request.session.get("questions", [])
            combined = []

            for i in range(len(user_answers)):
                combined.append({
                    "question": session_questions[i],     # ✅ use server-stored question with answer
                    "user_answer": user_answers[i]
                })

            request.session["answers"] = combined

            return JsonResponse({"redirect_url": "/apti/quiz-result/"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid method"}, status=405)

# Results page
def quiz_result(request):
    answers = request.session.get("answers", [])
    score = 0
    total = len(answers)

    for entry in answers:
        correct_answer = entry["question"].get("answer")
        if entry["user_answer"] == correct_answer:
            score += 1

    percentage = (score / total) * 100 if total else 0

    # Optionally clear
    request.session["answers"] = []
    request.session["questions"] = []

    return render(request, "result.html", {
        "score": score,
        "total": total,
        "percentage": percentage
    })
