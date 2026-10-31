// Runs inside the embedded poll page. Tells the page that contains the iframe
// how tall this content is, so the iframe can fit it exactly (no blank space).
(function () {
    'use strict';

    function reportHeight() {
        if (window.parent === window) {
            return;
        }

        var height = Math.ceil(
            document.documentElement.getBoundingClientRect().height
        );

        window.parent.postMessage(
            { type: 'community-poll-height', height: height },
            '*'
        );
    }

    window.addEventListener('load', reportHeight);
    window.addEventListener('resize', reportHeight);

    if (window.ResizeObserver) {
        new ResizeObserver(reportHeight).observe(document.body);
    }

    reportHeight();
})();
