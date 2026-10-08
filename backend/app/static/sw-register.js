// Service Worker Client Registration & Truthful Build Stamp (Directive P2)
(function() {
  fetch('/api/v1/build')
    .then(res => res.json())
    .then(data => {
      if (data) {
        const el = document.getElementById('buildStamp');
        if (el) {
          el.textContent = `build: ${data.git_hash} | static: ${data.static_hash} | id: ${data.build_id}`;
        }
      }
      if (!('serviceWorker' in navigator)) return;
      if (data && (data.mode === 'dev' || data.dev_mode)) {
        console.log('[SW] Service Worker running in DEV_MODE stub');
        initSW();
        return;
      }
      initSW();
    })
    .catch(() => {
      if ('serviceWorker' in navigator) initSW();
    });

  function initSW() {
    navigator.serviceWorker.register('/sw.js').then((reg) => {
      reg.addEventListener('updatefound', () => {
        const newWorker = reg.installing;
        if (!newWorker) return;
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            showUpdateBanner();
          }
        });
      });
    }).catch(err => {
      console.warn('[SW] Registration failed:', err);
    });
  }

  function showUpdateBanner() {
    if (document.getElementById('swUpdateBanner')) return;
    const banner = document.createElement('div');
    banner.id = 'swUpdateBanner';
    banner.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#065f46;color:#ffffff;padding:12px 18px;border-radius:12px;box-shadow:0 10px 25px rgba(0,0,0,0.25);z-index:99999;font-size:13px;font-family:sans-serif;display:flex;align-items:center;gap:12px;';
    banner.innerHTML = '<span>🚀 একটি নতুন সংস্করণ উপলব্ধ রয়েছে।</span><button onclick="window.location.reload()" style="background:#ffffff;color:#065f46;border:none;padding:6px 12px;border-radius:8px;font-weight:700;cursor:pointer;">রিলোড করুন</button>';
    document.body.appendChild(banner);
  }
})();
