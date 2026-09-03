function getCookie(name) {
  var match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return match ? decodeURIComponent(match.pop()) : '';
}

document.addEventListener('DOMContentLoaded', function () {
  // Forceful Smooth Scroll for Browse Services
  document.addEventListener('click', function (e) {
    var link = e.target.closest('.scroll-link');
    if (!link) return;

    var href = link.getAttribute('href');
    if (href && href.includes('#services')) {
      var target = document.getElementById('services');
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    }
  });

  // Handle hash scroll on page load
  window.addEventListener('load', function () {
    if (window.location.hash === '#services') {
      var target = document.getElementById('services');
      if (target) {
        setTimeout(function () {
          target.scrollIntoView({ behavior: 'smooth' });
        }, 100);
      }
    }
  });

  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.querySelector('.main-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      nav.classList.toggle('open');
      var expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
    });
  }

  // Auto-dismiss flash messages
  document.querySelectorAll('.messages .alert').forEach(function (el, i) {
    setTimeout(function () {
      el.style.transition = 'opacity .4s ease';
      el.style.opacity = '0';
      setTimeout(function () { el.remove(); }, 400);
    }, 6000 + i * 400);
  });

  // Language switcher: submit form on change
  var langSelect = document.querySelector('.lang-switcher select');
  if (langSelect) {
    langSelect.addEventListener('change', function () {
      this.form.submit();
    });
  }

  // OTP field: numeric-only, auto-focus
  document.querySelectorAll('.otp-field').forEach(function (el) {
    el.addEventListener('input', function () {
      this.value = this.value.replace(/\D/g, '');
    });
    el.focus();
  });

  // Worker sort control on comparison page
  var sortSelect = document.querySelector('[data-sort-control]');
  if (sortSelect) {
    sortSelect.addEventListener('change', function () {
      var url = new URL(window.location.href);
      url.searchParams.set('sort', this.value);
      window.location.href = url.toString();
    });
  }

  // Recurring booking toggle reveals frequency field
  var recurringCheckbox = document.querySelector('#id_is_recurring');
  var freqRow = document.querySelector('[data-recurrence-row]');
  function syncRecurrence() {
    if (!recurringCheckbox || !freqRow) return;
    freqRow.style.display = recurringCheckbox.checked ? 'block' : 'none';
  }
  if (recurringCheckbox) {
    recurringCheckbox.addEventListener('change', syncRecurrence);
    syncRecurrence();
  }
});
