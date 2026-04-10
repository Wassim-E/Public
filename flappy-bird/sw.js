// Service Worker for Flappy Bird PWA
const CACHE_NAME = 'flappy-bird-v1';
const STATIC_CACHE_URLS = [
  '/flappy-bird/',
  '/flappy-bird/index.html',
  '/flappy-bird/style.css',
  '/flappy-bird/game.js',
  '/flappy-bird/pwa.js',
  '/flappy-bird/manifest.json',
  '/flappy-bird/icon-192.png',
  '/flappy-bird/icon-512.png'
];

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('Service Worker installing.');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Caching static assets');
        return cache.addAll(STATIC_CACHE_URLS);
      })
      .then(() => {
        console.log('Service Worker installed');
        return self.skipWaiting();
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker activating.');
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('Service Worker activated');
      return self.clients.claim();
    })
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }
  
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }
  
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached response if found
        if (response) {
          console.log('Serving from cache:', event.request.url);
          return response;
        }
        
        // Otherwise fetch from network
        console.log('Fetching from network:', event.request.url);
        return fetch(event.request)
          .then(response => {
            // Don't cache non-successful responses
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // Clone the response
            const responseToCache = response.clone();
            
            // Cache the new response
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
            
            return response;
          })
          .catch(error => {
            console.error('Fetch failed:', error);
            
            // For HTML requests, return offline page
            if (event.request.headers.get('accept').includes('text/html')) {
              return caches.match('/flappy-bird/index.html');
            }
            
            // For other requests, return error
            return new Response('Network error', {
              status: 408,
              headers: { 'Content-Type': 'text/plain' }
            });
          });
      })
  );
});

// Background sync for high scores (if supported)
if ('sync' in self.registration) {
  self.addEventListener('sync', event => {
    if (event.tag === 'sync-high-scores') {
      console.log('Background sync for high scores');
      // In a real app, you would sync scores with a server here
    }
  });
}

// Periodic background sync (if supported)
if ('periodicSync' in self.registration) {
  self.addEventListener('periodicsync', event => {
    if (event.tag === 'update-assets') {
      console.log('Periodic sync for updating assets');
      event.waitUntil(updateAssets());
    }
  });
}

// Update assets function
async function updateAssets() {
  const cache = await caches.open(CACHE_NAME);
  const requests = STATIC_CACHE_URLS.map(url => new Request(url));
  
  const responses = await Promise.all(
    requests.map(request => fetch(request).catch(() => null))
  );
  
  await Promise.all(
    responses.map((response, index) => {
      if (response && response.ok) {
        return cache.put(requests[index], response);
      }
    })
  );
  
  console.log('Assets updated');
}

// Push notifications (if supported)
self.addEventListener('push', event => {
  console.log('Push notification received:', event);
  
  const options = {
    body: event.data ? event.data.text() : 'New high score! 🎉',
    icon: '/flappy-bird/icon-192.png',
    badge: '/flappy-bird/icon-192.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'play',
        title: 'Play Now'
      },
      {
        action: 'close',
        title: 'Close'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('Flappy Bird', options)
  );
});

self.addEventListener('notificationclick', event => {
  console.log('Notification click received:', event);
  
  event.notification.close();
  
  if (event.action === 'play') {
    event.waitUntil(
      clients.openWindow('/flappy-bird/')
    );
  }
});