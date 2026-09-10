// Seaglass template — site.js
// Two jobs: mobile nav toggle, and the Seaglass signature motion.
(function () {
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- Mobile nav toggle ----
  var toggle = document.querySelector('.nav-toggle');
  var links = document.getElementById('nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var isOpen = links.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(isOpen));
    });
    links.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        links.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // ---- Signature motion: hero glow follows the pointer, subtly ----
  var hero = document.querySelector('.hero-panel');
  if (hero && !reduceMotion) {
    document.addEventListener('mousemove', function (e) {
      var x = (e.clientX / window.innerWidth - 0.5) * 2;
      var y = (e.clientY / window.innerHeight - 0.5) * 2;
      hero.style.setProperty('--mx', x.toFixed(2));
      hero.style.setProperty('--my', y.toFixed(2));
    });
  }

  // ---- Signature motion: anything marked .glass-focus sharpens on scroll ----
  // Add this class to showcase cards/panels only — see CLAUDE.md, restraint
  // is the point. Not meant to be applied to every element on a page.
  var focusables = document.querySelectorAll('.glass-focus');
  if ('IntersectionObserver' in window && focusables.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        entry.target.classList.toggle('is-focused', entry.isIntersecting);
      });
    }, { threshold: 0.35 });
    focusables.forEach(function (el) { io.observe(el); });
  } else {
    focusables.forEach(function (el) { el.classList.add('is-focused'); });
  }

  // ---- Footer year ----
  var yearEl = document.getElementById('year');
  if (yearEl) { yearEl.textContent = new Date().getFullYear(); }
})();
