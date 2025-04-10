let questions = [];
let currentIndex = 0;
let answers = {};
let skipped = {};

fetch("/techmcq/get-questions/")
  .then(res => res.json())
  .then(data => {
    questions = data;
    generateSidebar();
    renderQuestion();
  });

function generateSidebar() {
  const sidebar = document.getElementById("sidebar");
  sidebar.innerHTML = "";
  for (let i = 0; i < questions.length; i++) {
    const btn = document.createElement("button");
    btn.innerText = i + 1;
    btn.onclick = () => {
      currentIndex = i;
      renderQuestion();
    };
    sidebar.appendChild(btn);
  }
}

function renderQuestion() {
  const q = questions[currentIndex];
  document.getElementById("question-number").innerText = `Question ${currentIndex + 1} of ${questions.length}`;
  document.getElementById("question-text").innerText = q.question;

  const optionsDiv = document.getElementById("options");
  optionsDiv.innerHTML = "";

  for (let [key, value] of Object.entries(q.options)) {
    const checked = answers[currentIndex] === key ? "checked" : "";
    optionsDiv.innerHTML += `<label><input type='radio' name='option' value='${key}' ${checked} onchange='selectOption("${key}")'> ${value}</label>`;
  }

  updateSidebarColors();
  updateNavButtons();
}

function selectOption(opt) {
  answers[currentIndex] = opt;
  delete skipped[currentIndex];
  updateSidebarColors();
}

function updateSidebarColors() {
  const buttons = document.getElementById("sidebar").children;
  for (let i = 0; i < buttons.length; i++) {
    if (answers[i]) {
      buttons[i].style.backgroundColor = "#007bff"; // Answered - Blue
    } else if (skipped[i]) {
      buttons[i].style.backgroundColor = "#ff9800"; // Skipped - Orange
    } else {
      buttons[i].style.backgroundColor = "#ccc";    // Unattempted - Light Gray
    }
    
  }
}

function nextQuestion() {
  if (currentIndex < questions.length - 1) {
    currentIndex++;
    renderQuestion();
  }
}

function prevQuestion() {
  if (currentIndex > 0) {
    currentIndex--;
    renderQuestion();
  }
}

function skipQuestion() {
  delete answers[currentIndex];
  skipped[currentIndex] = true;
  updateSidebarColors();
  nextQuestion();
}

function updateNavButtons() {
  const nav = document.getElementById("nav-buttons");
  nav.innerHTML = "";

  const prevBtn = document.createElement("button");
  prevBtn.className = "nav";
  prevBtn.innerText = "Previous";
  prevBtn.onclick = prevQuestion;

  const skipBtn = document.createElement("button");
  skipBtn.className = "nav";
  skipBtn.innerText = "Skip";
  skipBtn.onclick = skipQuestion;

  nav.appendChild(prevBtn);
  nav.appendChild(skipBtn);

  if (currentIndex < questions.length - 1) {
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
  const unanswered = questions.filter((_, idx) => !(idx in answers));
  if (unanswered.length > 0) {
    alert(`You have ${unanswered.length} unanswered question(s).`);
    return;
  }

  fetch('/techmcq/submit-answers/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers: answers, questions: questions })
  })
  .then(response => response.json())
  .then(data => {
    if (data.redirect_url) {
      window.location.href = data.redirect_url;
    }
  });
}
