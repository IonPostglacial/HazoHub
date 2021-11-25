self.addEventListener("fetch", function fetcher (event) {
    /** @type {string} */
    const requestUrl = event.request.url;

    if (/(.jpeg|.jpg|.png|.svg)$/i.test(requestUrl)) {
        event.respondWith(
            caches.match(event.request).then(function(response) {
                // return from cache, otherwise fetch from network
                return response || fetch(requestUrl);
            })
        );
    }
// otherwise: ignore event
});