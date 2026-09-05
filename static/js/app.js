function getCookie(name) {
  var match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return match ? decodeURIComponent(match.pop()) : '';
}

document.addEventListener('DOMContentLoaded', function () {
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

  // Admin More Dropdown Toggle
  document.querySelectorAll('.dropdown-toggle').forEach(function(toggle) {
    toggle.addEventListener('click', function(e) {
      e.stopPropagation();
      var dropdown = this.closest('.nav-dropdown');
      dropdown.classList.toggle('open');
    });
  });

  document.addEventListener('click', function() {
    document.querySelectorAll('.nav-dropdown.open').forEach(function(dropdown) {
      dropdown.classList.remove('open');
    });
  });

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

  // AI Chat Logic
  var chatToggle = document.getElementById('ai-chat-toggle');
  var chatWindow = document.getElementById('ai-chat-window');
  var chatClose = document.getElementById('ai-chat-close');
  var chatSend = document.getElementById('ai-chat-send');
  var chatInput = document.getElementById('ai-chat-input');
  var chatMessages = document.getElementById('ai-chat-messages');

  if (chatToggle && chatWindow) {
    chatToggle.addEventListener('click', function() {
      chatWindow.classList.toggle('open');
    });
  }

  if (chatClose) {
    chatClose.addEventListener('click', function() {
      chatWindow.classList.remove('open');
    });
  }

  function addMessage(text, sender) {
    var msg = document.createElement('div');
    msg.className = sender === 'user' ? 'user-msg' : 'ai-msg';
    msg.textContent = text;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  if (chatSend) {
    chatSend.addEventListener('click', function() {
      var text = chatInput.value.trim();
      if (!text) return;

      addMessage(text, 'user');
      chatInput.value = '';

      // Mock AI Response
      setTimeout(function() {
        var replies = [
          "I'm here to help! Co-opSeva ensures fair work and fixed prices.",
          "You can browse verified services in the Catalog section.",
          "Our cooperative model ensures workers get a fair share of the earnings.",
          "Need help with bookings? Just let me know!",
          "Co-opSeva is currently piloting in Delhi-NCR."
        ];
        var randomReply = replies[Math.floor(Math.random() * replies.length)];
        addMessage(randomReply, 'ai');
      }, 800);
    });
  }

  if (chatInput) {
    chatInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') chatSend.click();
    });
  }
});
