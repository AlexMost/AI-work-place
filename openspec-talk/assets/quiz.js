// Quiz widget: миттєвий фідбек на multiple-choice питання.
// Розмітка:
//   <div class="quiz">
//     <p class="quiz-q">Питання?</p>
//     <button class="quiz-opt" data-explain="чому ні">A</button>
//     <button class="quiz-opt" data-correct data-explain="чому так">B</button>
//     <p class="quiz-feedback"></p>
//   </div>
// Неправильна відповідь лишає кнопки активними (retry — це retrieval practice);
// правильна — фіксує результат і вимикає питання.
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.quiz-opt');
  if (!btn || btn.disabled) return;
  const quiz = btn.closest('.quiz');
  const feedback = quiz.querySelector('.quiz-feedback');
  const isCorrect = btn.hasAttribute('data-correct');

  quiz.querySelectorAll('.quiz-opt').forEach((b) => b.classList.remove('wrong'));

  if (isCorrect) {
    btn.classList.add('correct');
    quiz.querySelectorAll('.quiz-opt').forEach((b) => (b.disabled = true));
    feedback.className = 'quiz-feedback show ok';
  } else {
    btn.classList.add('wrong');
    feedback.className = 'quiz-feedback show no';
  }
  feedback.textContent = ' ' + (btn.dataset.explain || '');
});
