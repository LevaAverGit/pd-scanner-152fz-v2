/**
 * ДемоКорп Enterprise Demo Lab — app.js
 * Vanilla JS, no external dependencies.
 */

(function () {
  'use strict';

  // ---- Cookie banner ----
  function initCookieBanner() {
    var banner = document.getElementById('cookie-banner');
    if (!banner) return;
    if (localStorage.getItem('cookieConsent')) {
      banner.style.display = 'none';
    }
  }

  // ---- Multi-step form for request-demo ----
  function initMultiStepForm() {
    var form = document.querySelector('.main-form[data-multistep]');
    if (!form) return;

    var steps = form.querySelectorAll('[data-step]');
    if (!steps.length) return;

    var currentStep = 0;

    function showStep(n) {
      steps.forEach(function (s, i) {
        s.style.display = i === n ? 'block' : 'none';
      });
      var indicator = document.querySelector('.step-indicator');
      if (indicator) {
        indicator.textContent = 'Шаг ' + (n + 1) + ' из ' + steps.length;
      }
    }

    showStep(0);

    form.addEventListener('click', function (e) {
      if (e.target.dataset.next) {
        // Validate current step inputs
        var stepEl = steps[currentStep];
        var inputs = stepEl.querySelectorAll('input[required], textarea[required], select[required]');
        var valid = true;
        inputs.forEach(function (inp) {
          if (!inp.checkValidity()) {
            inp.reportValidity();
            valid = false;
          }
        });
        if (valid) {
          currentStep++;
          showStep(currentStep);
        }
      }
      if (e.target.dataset.prev) {
        currentStep--;
        showStep(currentStep);
      }
    });
  }

  // ---- Analytics track helper ----
  function trackEvent(category, action, label) {
    if (window.__labAnalytics) {
      window.__labAnalytics.track(category + ':' + action, {label: label, url: window.location.pathname});
    }
  }

  // ---- Auto-track outbound privacy links ----
  function trackPrivacyLinks() {
    document.querySelectorAll('a[href="/privacy"], a[href="/privacy.pdf"], a[href="/privacy.docx"]').forEach(function (a) {
      a.addEventListener('click', function () {
        trackEvent('privacy', 'link_click', a.href);
      });
    });
  }

  // ---- Track form starts ----
  function trackFormInteractions() {
    document.querySelectorAll('form').forEach(function (form) {
      var tracked = false;
      form.addEventListener('focusin', function () {
        if (!tracked) {
          tracked = true;
          trackEvent('form', 'start', form.id || form.action || 'unknown');
        }
      });
    });
  }

  // ---- Init CRM SDK if available (bad_compliance mode) ----
  function initCRM() {
    if (window.__labCRM && window.__labCRM.init) {
      window.__labCRM.init({source: 'democorp_web'});
    }
  }

  // ---- DOM ready ----
  function onReady(fn) {
    if (document.readyState !== 'loading') { fn(); }
    else { document.addEventListener('DOMContentLoaded', fn); }
  }

  onReady(function () {
    initCookieBanner();
    initMultiStepForm();
    trackPrivacyLinks();
    trackFormInteractions();
    initCRM();
  });

})();
