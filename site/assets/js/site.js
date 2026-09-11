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

// ---- Digest: newsletter dropdown + fetch/render ----
// Reads site/data/newsletters.json (the registry), then fetches and renders
// whichever newsletter's latest.json is selected. See CLAUDE.md — "The
// newsletter registry (how the dropdown works)".
(function () {
  var select = document.getElementById('newsletter-select');
  var meta = document.getElementById('digest-meta');
  var briefingEl = document.getElementById('briefing');
  var entriesEl = document.getElementById('entries');
  if (!select || !entriesEl) return;

  function formatGeneratedAt(iso, run) {
    var date = new Date(iso);
    if (isNaN(date.getTime())) return '';
    var formatted = new Intl.DateTimeFormat(undefined, {
      dateStyle: 'long',
      timeStyle: 'short',
    }).format(date);
    var label = run === 'am' ? 'Morning digest' : run === 'pm' ? 'Evening digest' : 'Digest';
    return label + ' — ' + formatted;
  }

  function renderTopics(topics) {
    entriesEl.innerHTML = '';
    if (!topics.length) {
      var empty = document.createElement('p');
      empty.className = 'empty-state';
      empty.textContent = 'No new stories in this run.';
      entriesEl.appendChild(empty);
      return;
    }

    // One card per story cluster: a combined summary across every source
    // covering it, plus a numbered (IEEE-style) reference list linking out
    // to each original article. See news_scanner/cluster.py.
    topics.forEach(function (topic) {
      var section = document.createElement('section');
      section.className = 'entry-group';

      var heading = document.createElement('h2');
      heading.textContent = topic.topic;
      section.appendChild(heading);

      var card = document.createElement('div');
      card.className = 'glass-panel topic-card';

      if (topic.summary) {
        var summary = document.createElement('p');
        summary.className = 'topic-summary';
        summary.textContent = topic.summary;
        card.appendChild(summary);
      }

      var refs = document.createElement('ol');
      refs.className = 'reference-list';
      (topic.sources || []).forEach(function (src, i) {
        var li = document.createElement('li');
        var link = document.createElement('a');
        link.href = src.url;
        link.target = '_blank';
        link.rel = 'noopener';
        link.textContent = '[' + (i + 1) + '] ' + src.source + ', “' + src.title + '”';
        li.appendChild(link);
        refs.appendChild(li);
      });
      card.appendChild(refs);

      section.appendChild(card);
      entriesEl.appendChild(section);
    });
  }

  function renderDigest(payload) {
    if (meta) meta.textContent = formatGeneratedAt(payload.generated_at, payload.run);
    if (briefingEl) {
      briefingEl.innerHTML = '';
      if (payload.briefing) {
        var p = document.createElement('p');
        p.textContent = payload.briefing;
        briefingEl.appendChild(p);
      }
    }
    renderTopics(payload.topics || []);
  }

  function loadDigest(dataPath) {
    entriesEl.innerHTML = '<p class="empty-state">Loading…</p>';
    fetch(dataPath)
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to load ' + dataPath);
        return res.json();
      })
      .then(renderDigest)
      .catch(function () {
        entriesEl.innerHTML = '<p class="empty-state">Couldn’t load this digest. Try again shortly.</p>';
      });
  }

  fetch('/data/newsletters.json')
    .then(function (res) { return res.json(); })
    .then(function (newsletters) {
      select.innerHTML = '';
      newsletters.forEach(function (nl) {
        var option = document.createElement('option');
        option.value = nl.data;
        option.textContent = nl.label;
        select.appendChild(option);
      });
      select.addEventListener('change', function () {
        loadDigest(select.value);
      });
      if (newsletters.length) {
        select.value = newsletters[0].data;
        loadDigest(newsletters[0].data);
      }
    })
    .catch(function () {
      entriesEl.innerHTML = '<p class="empty-state">Couldn’t load the newsletter list.</p>';
    });
})();
