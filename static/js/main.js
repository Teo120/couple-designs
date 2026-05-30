// ============================================================
// COUPLE DESIGNS — main.js  (versiune curată, fără duplicate)
// ============================================================

// ── Helpers localStorage ─────────────────────────────────────
function getCart() {
    try {
        return JSON.parse(localStorage.getItem("cart")) || [];
    } catch {
        return [];
    }
}

function saveCart(cart) {
    localStorage.setItem("cart", JSON.stringify(cart));
    window.dispatchEvent(new Event("cartUpdated"));

    fetch("/api/cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cart)
    }).catch(console.error);
}

// ── Adaugă produs ─────────────────────────────────────────────
function addToCart(product) {
    const cart = getCart();
    const existing = cart.find(p => p.id === product.id);
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({ ...product, quantity: 1 });
    }
    saveCart(cart);
}

// ── Modifică cantitate ────────────────────────────────────────
function changeQty(id, delta) {
    let cart = getCart();
    const item = cart.find(p => p.id === id);
    if (!item) return;
    item.quantity += delta;
    if (item.quantity <= 0) cart = cart.filter(p => p.id !== id);
    saveCart(cart);
}

// ── Șterge produs ─────────────────────────────────────────────
function removeItem(id) {
    saveCart(getCart().filter(p => p.id !== id));
    showToast("Produs șters din coș 🗑");
}

// ── Badge navbar ──────────────────────────────────────────────
function updateCartBadge() {
    const cart = getCart();
    const total = cart.reduce((sum, item) => sum + item.quantity, 0);
    ["cart-count", "cart-badge"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = total;
    });
}

// ── Toast ──────────────────────────────────────────────────────
function showToast(message) {
    document.querySelectorAll(".toast-main").forEach(t => t.remove());
    const toast = document.createElement("div");
    toast.className = "toast toast-main";
    toast.textContent = message;
    document.body.appendChild(toast);
    requestAnimationFrame(() => {
        requestAnimationFrame(() => toast.classList.add("show"));
    });
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 350);
    }, 2200);
}

// ── Click .cart-quick-btn ──────────────────────────────────────
document.addEventListener("click", function (e) {
    const btn = e.target.closest(".cart-quick-btn");
    if (!btn) return;
    e.stopPropagation();

    const product = {
        id:    parseInt(btn.dataset.id),
        name:  btn.dataset.name,
        price: parseFloat(btn.dataset.price),
        image: btn.dataset.image
    };

    addToCart(product);

    btn.classList.add("added");
    setTimeout(() => btn.classList.remove("added"), 650);

    showToast(product.name + " adăugat în coș ✔");

    if (window.gtag) {
        gtag("event", "add_to_cart", {
            currency: "RON", value: product.price,
            items: [{ item_name: product.name, price: product.price, quantity: 1 }]
        });
    }
});

// ── Wishlist toggle ────────────────────────────────────────────
document.addEventListener("click", function (e) {
    const btn = e.target.closest(".wishlist-btn");
    if (!btn) return;
    e.stopPropagation();
    btn.classList.toggle("active");
    const isActive = btn.classList.contains("active");
    showToast(isActive ? "Adăugat la favorite ❤️" : "Eliminat din favorite");
});

// ── Init ───────────────────────────────────────────────────────
window.addEventListener("cartUpdated", updateCartBadge);
document.addEventListener("DOMContentLoaded", updateCartBadge);
