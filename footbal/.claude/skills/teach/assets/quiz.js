// Reusable quiz widget shared by all lessons.
// Markup:
//   <div class="quiz" data-correct="1">
//     <p class="q">Question?</p>
//     <button class="opt">wrong answer</button>
//     <button class="opt">right answer</button>
//     <p class="fb" data-ok="Yes — why." data-no="Not quite — why."></p>
//   </div>
// data-correct is the 0-based index of the right option.
document.querySelectorAll('.quiz').forEach(quiz => {
  const correct = Number(quiz.dataset.correct);
  const opts = [...quiz.querySelectorAll('.opt')];
  const fb = quiz.querySelector('.fb');
  let done = false;
  opts.forEach((opt, i) => {
    opt.addEventListener('click', () => {
      if (done) return;
      done = true;
      opts[correct].classList.add('correct');
      if (i !== correct) opt.classList.add('wrong');
      fb.textContent = i === correct ? (fb.dataset.ok || 'Правильно.') : (fb.dataset.no || 'Спробуй ще раз подумати.');
      fb.classList.add('show');
    });
  });
});
