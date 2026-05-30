const Cart = (() => {

    let cart = [];

    // 🔌 API CALL
    async function api(url, method = "GET", data = null) {
        try {
            toggleLoader(true);

            const res = await fetch(url, {
                method,
                headers: { "Content-Type": "application/json" },
                body: data ? JSON.stringify(data) : null
            });

            if (!res.ok) throw new Error("Server error");

            return await res.json();

        } catch (err) {
            console.error(err);
            showToast("Eroare conexiune");
        } finally {
            toggleLoader(false);
        }
    }

    function toggleLoader(show) {
        document.getElementById("loader").classList.toggle("hidden", !show);
    }

    function showToast(msg) {
        const t = document.getElementById("toast");
        t.innerText = msg;
        t.classList.add("show");

        setTimeout(() => t.classList.remove("show"), 2000);
    }

    // 🔄 RENDER
    function render() {
        const container = document.getElementById("cart-container");
        const totalEl = document.getElementById("cart-total");

        container.innerHTML = "";
        let total = 0;

        cart.forEach((item, i) => {
            total += item.price * item.quantity;

            const el = document.createElement("div");
            el.className = "cart-item";

            el.innerHTML = `
                <img src="/static/images/${item.image}" width="100">
                <div>
                    <h3>${item.name}</h3>
                    <p>${item.price} RON</p>

                    <div>
                        <button data-action="dec" data-i="${i}">-</button>
                        <span>${item.quantity}</span>
                        <button data-action="inc" data-i="${i}">+</button>
                    </div>

                    <button data-action="remove" data-i="${i}">Șterge</button>
                </div>
            `;

            container.appendChild(el);
        });

        totalEl.innerText = `Total: ${total} RON`;
    }

    // ⚙️ UPDATE STATE
    async function update() {
        localStorage.setItem("cart", JSON.stringify(cart));

        // backend sync
        await api("/api/cart", "POST", cart);

        // Google Shopping
        syncGoogle();

        render();
    }

    // ➕➖❌ HANDLERS (EVENT DELEGATION)
    function handleClick(e) {
        const btn = e.target.closest("button");
        if (!btn) return;

        const i = parseInt(btn.dataset.i);
        const action = btn.dataset.action;

        if (action === "inc") {
            cart[i].quantity++;
            update();
            showToast("Cantitate crescută");
        }

        if (action === "dec") {
            if (cart[i].quantity > 1) {
                cart[i].quantity--;
            } else {
                cart.splice(i, 1);
            }
            update();
        }

        if (action === "remove") {
            const item = btn.closest(".cart-item");
            item.classList.add("removing");

            setTimeout(() => {
                cart.splice(i, 1);
                update();
                showToast("Șters");
            }, 250);
        }
    }

    // 📊 GOOGLE SHOPPING
    function syncGoogle() {
        if (window.gtag) {
            gtag("event", "add_to_cart", {
                currency: "RON",
                value: cart.reduce((t, i) => t + i.price * i.quantity, 0),
                items: cart.map(i => ({
                    item_name: i.name,
                    price: i.price,
                    quantity: i.quantity
                }))
            });
        }
    }

    // 🚀 INIT
    function init() {
        cart = JSON.parse(localStorage.getItem("cart")) || [];

        document
            .getElementById("cart-container")
            .addEventListener("click", handleClick);

        render();
    }

    return { init };

})();

document.addEventListener("DOMContentLoaded", Cart.init);