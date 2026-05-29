from fastapi import APIRouter, Request
from fastapi.responses import Response, JSONResponse
import base64

router = APIRouter()

ANALYTICS_JS = b"""
// Mock Analytics Service - Lab Test Only (NOT a real analytics service)
// This script simulates a third-party analytics integration for testing purposes.
(function() {
  'use strict';
  window.__labAnalytics = window.__labAnalytics || {
    _queue: [],
    track: function(event, data) {
      this._queue.push({event: event, data: data});
      fetch('/mock/analytics/collect', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({event: event, data: data, ts: Date.now(), url: window.location.href})
      }).catch(function(){});
    },
    pageview: function() {
      this.track('pageview', {title: document.title, referrer: document.referrer});
    }
  };
  // Auto-track pageview on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { window.__labAnalytics.pageview(); });
  } else {
    window.__labAnalytics.pageview();
  }
})();
"""

CRM_JS = b"""
// Mock CRM Integration Script - Lab Test Only
// Simulates CRM form-capture SDK pattern
(function() {
  window.__labCRM = {
    capture: function(formData) {
      fetch('/crm/mock', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(formData)
      }).catch(function(){});
    },
    init: function(config) {
      this._config = config;
      document.querySelectorAll('form[data-crm-capture]').forEach(function(form) {
        form.addEventListener('submit', function(e) {
          var data = {};
          new FormData(form).forEach(function(v, k) { data[k] = v; });
          window.__labCRM.capture(data);
        });
      });
    }
  };
})();
"""

# 1x1 transparent GIF
PIXEL_GIF = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


@router.get("/analytics.js")
async def analytics_js():
    return Response(content=ANALYTICS_JS, media_type="application/javascript")


@router.post("/analytics/collect")
async def analytics_collect(request: Request):
    return JSONResponse({"ok": True})


@router.get("/pixel.gif")
async def tracking_pixel():
    return Response(content=PIXEL_GIF, media_type="image/gif")


@router.get("/crm.js")
async def crm_js():
    return Response(content=CRM_JS, media_type="application/javascript")
