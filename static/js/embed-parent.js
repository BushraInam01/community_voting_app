// Include this script on the page that holds the poll <iframe>. It listens for
// the height reported by embed-resize.js and resizes the matching iframe.
(function () {
    'use strict';

    var MESSAGE_TYPE = 'community-poll-height';
    var MAX_HEIGHT = 5000;

    function frameOrigin(frame) {
        try {
            return new URL(frame.src, window.location.href).origin;
        } catch (error) {
            return null;
        }
    }

    window.addEventListener('message', function (event) {
        var data = event.data;

        if (!data || data.type !== MESSAGE_TYPE) {
            return;
        }

        var height = Number(data.height);

        if (!isFinite(height) || height <= 0 || height > MAX_HEIGHT) {
            return;
        }

        var frames = document.getElementsByTagName('iframe');

        for (var i = 0; i < frames.length; i++) {
            var frame = frames[i];

            // Only resize the iframe that sent the message, and only if it
            // really is our poll page (same origin as the iframe's src).
            if (
                frame.contentWindow === event.source &&
                frameOrigin(frame) === event.origin
            ) {
                frame.style.height = Math.ceil(height) + 'px';
            }
        }
    });
})();
