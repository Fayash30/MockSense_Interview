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
    # Return copies of each question without the answer
    questions_to_send = []
    for q in selected_questions:
        q_copy = q.copy()
        q_copy.pop("answer", None)
        questions_to_send.append(q_copy)
    return JsonResponse(questions_to_send, safe=False)


@csrf_exempt
@require_POST
def submit_answers(request):
    data = json.loads(request.body)
    user_answers = data.get("answers", {})
    selected_qs = data.get("questions", [])
    
    score = 0
    results = []

    for idx, user_q in enumerate(selected_qs):
        question_text = user_q['question']
        actual_q = next((q for q in all_questions if q['question'] == question_text), None)
        if actual_q:
            correct = actual_q.get('answer')
            user_ans = user_answers.get(str(idx))
            is_correct = (user_ans == correct)
            if is_correct:
                score += 1

            results.append({
                "question": actual_q['question'],
                "user_answer": actual_q['options'].get(user_ans, 'Not Answered'),
                "correct_answer": actual_q['options'][correct],
                "is_correct": is_correct
            })

    request.session['quiz_score'] = score
    request.session['quiz_total'] = len(selected_qs)
    return JsonResponse({"redirect_url": reverse('mcq_result')})

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