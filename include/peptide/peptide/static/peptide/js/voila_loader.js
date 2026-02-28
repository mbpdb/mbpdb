/**
 * voila_loader.js — shared Voilà iframe loader for milk-bioactive peptide DB.
 *
 * Usage (in a Django template):
 *
 *   <script src="{% static 'peptide/js/voila_loader.js' %}"></script>
 *   <script>
 *     initVoilaLoader({
 *       voilaUrl:  '/voila/heatmap/',
 *       cacheKey:  'voila_heatmap',           // unique per page
 *       title:     'Sequence Heatmap Dashboard',
 *       containerId: 'voila-container',       // optional, default 'voila-container'
 *     });
 *   </script>
 *
 * The host page must contain the following skeleton HTML (or equivalent):
 *
 *   <div id="voila-container" style="position:relative; width:100%; height:calc(100vh - 180px);">
 *     <div id="loading-overlay" class="loading-overlay">
 *       <img src="..." alt="Loading..." style="width:50px; height:128px;">
 *       <p id="loading-text">Starting new session...</p>
 *       <button id="retry-btn" class="retry-btn" style="display:none;">Retry Loading</button>
 *     </div>
 *     <iframe id="data-iframe" src="about:blank"
 *             style="width:100%;height:100%;border:none;display:block;" allowfullscreen></iframe>
 *   </div>
 *   <span id="status-text" class="help-note">Loading notebook...</span>
 */
(function () {
    'use strict';

    window.initVoilaLoader = function (config) {
        var VOILA_URL      = config.voilaUrl;
        var CACHE_KEY      = config.cacheKey || 'voila_notebook';
        var CONTAINER_ID   = config.containerId || 'voila-container';

        var lastLoadKey    = CACHE_KEY + '_last_load';
        var failureKey     = CACHE_KEY + '_last_failure';

        var DEBOUNCE_MS             = 4000;
        var COOLDOWN_AFTER_FAILURE  = 8000;
        var LOAD_TIMEOUT_MS         = 90000;   // 90 s — new kernels are slow
        var MAX_ATTEMPTS            = 3;

        // ---- DOM references ---------------------------------------------------
        var iframe      = document.getElementById('data-iframe');
        var overlay     = document.getElementById('loading-overlay');
        var loadingText = document.getElementById('loading-text');
        var retryBtn    = document.getElementById('retry-btn');
        var statusText  = document.getElementById('status-text');

        var loadAttempts         = 0;
        var loadTimeout          = null;
        var contentCheckInterval = null;
        var isLoading            = false;

        // ---- Overlay helpers --------------------------------------------------
        function hideOverlay() {
            overlay.style.display = 'none';
            if (statusText) {
                statusText.textContent = 'Notebook loaded successfully';
                statusText.style.color = '#4caf50';
            }
            clearInterval(contentCheckInterval);
        }

        function showOverlay() {
            overlay.style.display = 'flex';
            retryBtn.style.display = 'none';
        }

        function showRetry(message) {
            loadingText.textContent = message;
            retryBtn.style.display = 'block';
            if (statusText) {
                statusText.textContent = 'Failed to load — click Retry or hard refresh (Ctrl+Shift+R)';
                statusText.style.color = '#f44336';
            }
        }

        // ---- Content detection ------------------------------------------------
        function checkForRawCode() {
            try {
                var doc = iframe.contentDocument || iframe.contentWindow.document;
                if (!doc || !doc.body) return false;
                var bodyText = doc.body.innerText || '';
                var bodyHTML = doc.body.innerHTML || '';

                var codePatterns = [
                    /^import\s+\w+/m,
                    /^from\s+\w+\s+import/m,
                    /^def\s+\w+\s*\(/m,
                    /^class\s+\w+/m,
                    /widgets\.VBox|widgets\.HBox|ipywidgets/,
                    /display\s*\(\s*\w+\s*\)/,
                ];

                for (var i = 0; i < codePatterns.length; i++) {
                    if (codePatterns[i].test(bodyText) && bodyText.length > 500) {
                        if (!bodyHTML.includes('jupyter-widgets') &&
                            !bodyHTML.includes('widget-subarea')) {
                            return true;
                        }
                    }
                }

                if (bodyText.includes('502 Bad Gateway') ||
                    bodyText.includes('503 Service')) {
                    return true;
                }
            } catch (e) { /* cross-origin — ignore */ }
            return false;
        }

        function checkContentRendered() {
            try {
                var doc = iframe.contentDocument || iframe.contentWindow.document;
                if (doc && doc.body) {
                    return doc.body.innerHTML.includes('jupyter-widgets') ||
                           doc.body.innerHTML.includes('widget-subarea') ||
                           doc.body.innerHTML.includes('jp-OutputArea');
                }
            } catch (e) { /* cross-origin — ignore */ }
            return false;
        }

        // ---- Load / retry logic -----------------------------------------------
        window.reloadIframe = function () {
            if (isLoading) return;
            isLoading = true;
            loadAttempts++;

            showOverlay();
            loadingText.textContent = loadAttempts > 1
                ? 'Retrying… (attempt ' + loadAttempts + '/' + MAX_ATTEMPTS + ')'
                : 'Starting new session (this may take 15–30 seconds)…';
            if (statusText) {
                statusText.textContent = 'Starting new session…';
                statusText.style.color = '#777';
            }

            iframe.src = 'about:blank';
            var retryDelay = loadAttempts > 1 ? 3000 : 1500;

            setTimeout(function () {
                iframe.src = VOILA_URL + '?t=' + Date.now();
                sessionStorage.setItem(lastLoadKey, Date.now().toString());

                clearTimeout(loadTimeout);
                clearInterval(contentCheckInterval);

                loadTimeout = setTimeout(function () {
                    isLoading = false;
                    if (loadAttempts < MAX_ATTEMPTS) {
                        loadingText.textContent = 'Taking longer than expected, retrying…';
                        window.reloadIframe();
                    } else {
                        sessionStorage.setItem(failureKey, Date.now().toString());
                        showRetry('Notebook failed to load. Please wait a moment before retrying.');
                    }
                }, LOAD_TIMEOUT_MS);

                isLoading = false;
            }, retryDelay);
        };

        iframe.onload = function () {
            clearTimeout(loadTimeout);
            var checkCount = 0;
            var maxChecks  = 10;

            clearInterval(contentCheckInterval);
            contentCheckInterval = setInterval(function () {
                checkCount++;

                if (checkForRawCode()) {
                    clearInterval(contentCheckInterval);
                    if (loadAttempts < MAX_ATTEMPTS) {
                        loadingText.textContent = 'Notebook not rendered correctly, retrying…';
                        setTimeout(window.reloadIframe, 2000);
                    } else {
                        showRetry('Notebook failed to render correctly');
                    }
                    return;
                }

                if (checkContentRendered() || checkCount >= maxChecks) {
                    clearInterval(contentCheckInterval);
                    setTimeout(hideOverlay, 1500);
                }
            }, 500);
        };

        iframe.onerror = function () {
            clearTimeout(loadTimeout);
            clearInterval(contentCheckInterval);
            isLoading = false;
            if (loadAttempts < MAX_ATTEMPTS) {
                loadingText.textContent = 'Connection error, retrying…';
                setTimeout(window.reloadIframe, 3000);
            } else {
                showRetry('Connection error');
            }
        };

        // Wire up the retry button (may be added by the template)
        if (retryBtn) {
            retryBtn.addEventListener('click', window.reloadIframe);
        }

        // ---- Initial load with debounce / cooldown ----------------------------
        function initialLoad() {
            var lastLoad      = parseInt(sessionStorage.getItem(lastLoadKey)  || '0');
            var lastFailure   = parseInt(sessionStorage.getItem(failureKey)   || '0');
            var sinceLastLoad = Date.now() - lastLoad;
            var sinceFailure  = Date.now() - lastFailure;

            var delay = 500;
            if (sinceFailure < COOLDOWN_AFTER_FAILURE) {
                delay = COOLDOWN_AFTER_FAILURE - sinceFailure + 1000;
                loadingText.textContent = 'Cooling down after error…';
            } else if (sinceLastLoad < DEBOUNCE_MS) {
                delay = DEBOUNCE_MS - sinceLastLoad + 500;
                loadingText.textContent = 'Preparing notebook…';
            } else {
                loadingText.textContent = 'Preparing notebook…';
            }

            setTimeout(function () {
                loadAttempts = 0;
                window.reloadIframe();
            }, delay);
        }

        if (document.readyState === 'complete') {
            initialLoad();
        } else {
            window.addEventListener('load', initialLoad);
        }
    };
}());
