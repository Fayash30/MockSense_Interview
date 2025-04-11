import json
import random
from django.urls import reverse
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

# Load questions from the static JSON once and keep it in memory
with open("techmcq/static/techmcq/sde_mcq_275_unique.json") as f:
    all_questions = json.load(f)

def quiz_view(request):
    return render(request, 'techmcq/index.html', { "proctored": True })

def quiz_home(request):
    return render(request, 'techmcq/instructions.html')

@require_GET
def get_questions(request):
    selected_questions = random.sample(all_questions, 10)
    randomized_questions = []

    for q in selected_questions:
        # Convert dict to list of (label, text) pairs and shuffle
        options_list = list(q["options"].items())
        random.shuffle(options_list)

        # Reassign labels A-D
        new_labels = ['A', 'B', 'C', 'D']
        new_options = {}
        new_answer = None

        for i, (old_label, text) in enumerate(options_list):
            new_label = new_labels[i]
            new_options[new_label] = text
            if old_label == q["answer"]:
                new_answer = new_label

        # Build updated question dict
        randomized_question = {
            "question": q["question"],
            "options": new_options,
            "answer": new_answer,  # Keep correct answer for backend
            "difficulty": q.get("difficulty", ""),
            "topic": q.get("topic", "")
        }

        randomized_questions.append(randomized_question)

    # Save the full version (with answers) in session
    request.session["mcq_questions"] = randomized_questions

    # Send to frontend without answers
    frontend_questions = [
        {k: v for k, v in q.items() if k != "answer"} for q in randomized_questions
    ]

    return JsonResponse(frontend_questions, safe=False)

@csrf_exempt
@require_POST
def submit_answers(request):
    data = json.loads(request.body)
    user_answers = data.get("answers", {})

    # Use stored randomized questions
    session_questions = request.session.get("mcq_questions", [])
    score = 0
    results = []

    for idx, actual_q in enumerate(session_questions):
        user_ans = user_answers.get(str(idx))
        correct = actual_q.get("answer")
        is_correct = (user_ans == correct)

        if is_correct:
            score += 1

        results.append({
            "question": actual_q["question"],
            "user_answer": actual_q["options"].get(user_ans, 'Not Answered'),
            "correct_answer": actual_q["options"][correct],
            "is_correct": is_correct
        })

    request.session["quiz_score"] = score
    request.session["quiz_total"] = len(session_questions)
    return JsonResponse({"redirect_url": reverse("mcq_result")})


@require_GET
def quiz_result_view(request):
    score = request.session.get('quiz_score')
    total = request.session.get('quiz_total')

    if score is None or total is None:
        return redirect('mcq-home')  # fallback if session missing

    percentage = (score / total) * 100
    return render(request, 'techmcq/result.html', {
        "score": score,
        "total": total,
        "percentage": percentage
    })