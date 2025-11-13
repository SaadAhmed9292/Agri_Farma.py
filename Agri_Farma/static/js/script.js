/* AgriFarma - Global JS */

// 1) Auto-hide Bootstrap alerts after a delay
(function autoHideAlerts() {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach((el) => {
    // Skip if marked persistent
    if (el.dataset.persistent === '1') return;
    setTimeout(() => {
      const alert = bootstrap.Alert.getOrCreateInstance(el);
      alert.close();
    }, 4000);
  });
})();

// 2) Smooth scroll for anchor links with [data-scroll]
document.addEventListener('click', (e) => {
  const a = e.target.closest('a[data-scroll]');
  if (!a) return;
  const target = document.querySelector(a.getAttribute('href'));
  if (target) {
    e.preventDefault();
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
});

// 3) Cart badge sync helper
function updateCartBadge(count) {
  const badge = document.getElementById('cart-count');
  if (!badge) return;
  const n = Number(count) || 0;
  badge.textContent = n;
  badge.style.display = n > 0 ? 'inline-block' : 'none';
}

// 4) AJAX add-to-cart hooks (progressive enhancement)
// - Works only if buttons have .ajax-add-to-cart and data-product-id
// - Falls back to normal form POST if JavaScript disabled
(function ajaxAddToCart() {
  const buttons = document.querySelectorAll('.ajax-add-to-cart');
  if (!buttons.length) return;

  buttons.forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const productId = btn.dataset.productId;
      const qty = btn.dataset.qty ? Number(btn.dataset.qty) : 1;

      try {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Adding...';
        const resp = await fetch(`/shop/add-to-cart/${productId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ quantity: qty })
        });

        // Heuristic: if redirected, just reload to get server-side flash/cart
        if (resp.redirected) {
          window.location = resp.url;
          return;
        }

        // Optional JSON support if you later return JSON
        const text = await resp.text();
        // Basic client-side feedback
        createToast('Added to cart', 'success');
        // Increment badge as a UX hint (server is source of truth)
        const current = Number(document.getElementById('cart-count')?.textContent || 0);
        updateCartBadge(current + qty);
      } catch (err) {
        console.error(err);
        createToast('Failed to add to cart', 'danger');
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-cart-plus"></i> Add to Cart';
      }
    });
  });
})();

// 5) Price range UI helper on shop filters (if present)
(function priceRangeUI() {
  const range = document.getElementById('priceRange');
  const maxLabel = document.getElementById('maxPrice');
  if (!range || !maxLabel) return;
  const fmt = (n) => `Rs. ${Number(n).toLocaleString()}`;
  maxLabel.textContent = fmt(range.value);
  range.addEventListener('input', () => {
    maxLabel.textContent = fmt(range.value);
  });
})();

// 6) Simple toast creator using Bootstrap 5
function createToast(message, type = 'info') {
  // Ensure container
  let container = document.querySelector('.toast-container.position-fixed.top-0.end-0.p-3');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    document.body.appendChild(container);
  }
  const el = document.createElement('div');
  el.className = `toast align-items-center text-bg-${type} border-0`;
  el.role = 'alert';
  el.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>
  `;
  container.appendChild(el);
  const t = new bootstrap.Toast(el, { delay: 2500 });
  t.show();
  el.addEventListener('hidden.bs.toast', () => el.remove());
}

// 7) Form helpers: confirm destructive actions
document.addEventListener('submit', (e) => {
  const form = e.target;
  if (form.matches('[data-confirm]')) {
    const msg = form.getAttribute('data-confirm') || 'Are you sure?';
    if (!confirm(msg)) e.preventDefault();
  }
});

// 8) Disable submit button on submit to avoid double-posts
document.addEventListener('submit', (e) => {
  const submitBtn = e.target.querySelector('button[type="submit"], input[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.dataset.originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Processing...';
  }
});

// 9) Restore submit button if page is kept alive (e.g., PJAX/failure)
// Not strictly necessary; full reload usually restores state.
window.addEventListener('pageshow', () => {
  document.querySelectorAll('button[disabled][data-original-text]').forEach((b) => {
    b.disabled = false;
    b.innerHTML = b.dataset.originalText;
  });
});
