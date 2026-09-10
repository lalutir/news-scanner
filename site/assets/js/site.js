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

  function renderEntries(entries) {
    entriesEl.innerHTML = '';
    if (!entries.length) {
      var empty = document.createElement('p');
      empty.className = 'empty-state';
      empty.textContent = 'No new stories in this run.';
      entriesEl.appendChild(empty);
      return;
    }

    var groups = {};
    var order = [];
    entries.forEach(function (entry) {
      if (!groups[entry.source]) {
        groups[entry.source] = [];
        order.push(entry.source);
      }
      groups[entry.source].push(entry);
    });

    order.forEach(function (source) {
      var section = document.createElement('section');
      section.className = 'entry-group';

      var heading = document.createElement('h2');
      heading.textContent = source;
      section.appendChild(heading);

      var list = document.createElement('ul');
      list.className = 'entry-list';

      groups[source].forEach(function (entry) {
        var item = document.createElement('li');
        item.className = 'glass-panel';

        var link = document.createElement('a');
        link.href = entry.url;
        link.textContent = entry.title;
        link.target = '_blank';
        link.rel = 'noopener';
        item.appendChild(link);

        if (entry.summary) {
          var summary = document.createElement('p');
          summary.className = 'entry-summary';
          summary.textContent = entry.summary;
          item.appendChild(summary);
        }

        list.appendChild(item);
      });

      section.appendChild(list);
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
    renderEntries(payload.entries || []);
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
