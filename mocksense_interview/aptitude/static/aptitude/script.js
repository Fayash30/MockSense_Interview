let questions = [];
let currentQuestionIndex = 0;
let userAnswers = [];
let skipped = {};

// Fetch questions from Django view
fetch("/apti/get-questions/")
  .then((res) => res.json())
  .then((data) => {
    questions = data;
    userAnswers = new Array(questions.length).fill(null);
    renderSidebar();
    showQuestion();
  });

function renderSidebar() {
  const sidebar = document.getElementById("sidebar");
  sidebar.innerHTML = "";

  for (let i = 0; i < questions.length; i++) {
    const btn = document.createElement("button");
    btn.innerText = i + 1;
    btn.onclick = () => {
      currentQuestionIndex = i;
      showQuestion();
    };
    sidebar.appendChild(btn);
  }
}

function updateSidebarColors() {
  const buttons = document.getElementById("sidebar").children;
  for (let i = 0; i < buttons.length; i++) {
    if (userAnswers[i]) {
      buttons[i].style.backgroundColor = "#007bff"; // Answered - Blue
    } else if (skipped[i]) {
      buttons[i].style.backgroundColor = "#ff9800"; // Skipped - Orange
    } else {
      buttons[i].style.backgroundColor = "#ccc";    // Unattempted - Gray
    }
  }
}

function showQuestion() {
  const question = questions[currentQuestionIndex];
  const questionNumber = document.getElementById("question-number");
  const questionText = document.getElementById("question-text");
  const optionsContainer = document.getElementById("options");

  questionNumber.textContent = `Question ${currentQuestionIndex + 1} of ${questions.length}`;
  questionText.textContent = question.question;
  optionsContainer.innerHTML = "";

  question.options.forEach((option) => {
    const label = document.createElement("label");
    label.textContent = option;
    if (userAnswers[currentQuestionIndex] === option) {
      label.classList.add("selected");
    }
    label.onclick = () => {
      userAnswers[currentQuestionIndex] = option;
      delete skipped[currentQuestionIndex];
      showQuestion(); // re-render for UI update
      updateSidebarColors();
    };
    optionsContainer.appendChild(label);
  });

  updateSidebarColors();
  updateNavButtons();
}

function nextQuestion() {
  if (currentQuestionIndex < questions.length - 1) {
    currentQuestionIndex++;
    showQuestion();
  }
}

function prevQuestion() {
  if (currentQuestionIndex > 0) {
    currentQuestionIndex--;
    showQuestion();
  }
}

function skipQuestion() {
  userAnswers[currentQuestionIndex] = null;
  skipped[currentQuestionIndex] = true;
  updateSidebarColors();
  nextQuestion();
}

function updateNavButtons() {
  const nav = document.querySelector(".nav-buttons");
  nav.innerHTML = "";

  const prevBtn = document.createElement("button");
  prevBtn.className = "nav";
  prevBtn.innerText = "Previous";
  prevBtn.onclick = prevQuestion;
  nav.appendChild(prevBtn);

  const skipBtn = document.createElement("button");
  skipBtn.className = "nav";
  skipBtn.innerText = "Skip";
  skipBtn.onclick = skipQuestion;
  nav.appendChild(skipBtn);

  if (currentQuestionIndex < questions.length - 1) {
    const nextBtn = document.createElement("button");
    nextBtn.className = "nav";
    nextBtn.innerText = "Next";
    nextBtn.onclick = nextQuestion;
    nav.appendChild(nextBtn);
  } else {
    const submitBtn = document.createElement("button");
    submitBtn.className = "nav";
    submitBtn.innerText = "Submit";
    submitBtn.onclick = submitQuiz;
    nav.appendChild(submitBtn);
  }
}

function submitQuiz() {
  const unansweredCount = userAnswers.filter(ans => ans === null).length;
  if (unansweredCount > 0) {
    alert(`You have ${unansweredCount} unanswered question(s).`);
    return;
  }

  fetch('/apti/submit-answers/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      answers: userAnswers,
      questions: questions
    })
  })
    .then(res => res.json())
    .then(data => {
      if (data.redirect_url) {
        window.location.href = data.redirect_url;
      }
    });
}
