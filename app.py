from flask import Flask, render_template, jsonify, request, redirect
from flask_mail import Mail, Message
from datetime import datetime
import os
import base64
import uuid
import json
import stripe
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Mail credentials — set via environment variables in production:
#   export MAIL_USER=youraddress@gmail.com
#   export MAIL_PASS=your_app_password
app.config['MAIL_SERVER']   = 'smtp.gmail.com'
app.config['MAIL_PORT']     = 587
app.config['MAIL_USE_TLS']  = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USER', 'teomicsa@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASS', 'yxuh qnrw wiok nldh')

STORE_EMAIL = os.environ.get('STORE_EMAIL', 'teomicsa@gmail.com')

mail = Mail(app)

app.secret_key     = os.environ.get('SECRET_KEY', 'couple-designs-dev-secret')
stripe.api_key     = os.environ.get('STRIPE_SECRET_KEY', '')

# Comenzi în așteptarea confirmării plății Stripe (UUID → order_data)
pending_orders = {}

# ── Produse ───────────────────────────────────────────────────
products = [
    {"id": 1, "name": "Tablou",         "price": 50, "rating": 4.9, "reviews": 128, "image": "king_queen.png",   "tag": None},
    {"id": 2, "name": "Anime Love",     "price": 60, "rating": 4.8, "reviews": 96,  "image": "anime_love.png",   "tag": None},
    {"id": 3, "name": "Cartoon 3D",     "price": 70, "rating": 4.9, "reviews": 74,  "image": "cartoon_3d.png",   "tag": "Popular"},
    {"id": 4, "name": "Moonlight Love", "price": 60, "rating": 4.9, "reviews": 63,  "image": "moonlight.png",    "tag": None},
    {"id": 5, "name": "Purple Dream",   "price": 55, "rating": 4.8, "reviews": 52,  "image": "purple_dream.png", "tag": None},
]

# ── Rute ──────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', products=products)

@app.route('/designuri')
def designuri():
    return render_template('designuri.html', products=products)

@app.route('/upload/<int:id>', methods=['GET', 'POST'])
def upload(id):
    product = next((p for p in products if p["id"] == id), None)
    if request.method == 'POST':
        file = request.files.get('image')
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return render_template('upload.html', product=product, filename=filename)
    return render_template('upload.html', product=product)

@app.route('/despre-noi')
def despre_noi():
    return render_template('despre_noi.html')

@app.route('/cum-functioneaza')
def cum_functioneaza():
    return render_template('cum_functioneaza.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/api/cart', methods=['POST'])
def save_cart():
    return jsonify({"status": "ok"})

@app.route('/api/products')
def api_products():
    return jsonify(products)

# ── Contact form (existing working pattern) ───────────────────
@app.route('/send-message', methods=['POST'])
def send_message():
    name    = request.form.get('name', '').strip()
    email   = request.form.get('email', '').strip()
    message = request.form.get('message', '').strip()

    if not name or not email or not message:
        return "All fields are required", 400

    msg = Message(
        subject=f"Mesaj de la {name}",
        sender=app.config['MAIL_USERNAME'],
        reply_to=email,
        recipients=[STORE_EMAIL],
        body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
    )
    mail.send(msg)
    return redirect('/contact')


# ── Checkout ──────────────────────────────────────────────────
# FIX SUMMARY vs old broken version:
#   1. Route was declared AFTER `if __name__ == '__main__'` so Flask never
#      registered it at import time — every POST returned 404. Fixed by
#      moving the route here, before the entry-point guard.
#   2. Old code used raw smtplib with hardcoded placeholder credentials
#      ("YOUR_EMAIL", "APP_PASSWORD") instead of the already-configured
#      flask_mail instance. Now uses flask_mail consistently.
#   3. Cart JS sends item.quantity; old backend read item['qty'] — KeyError
#      caused a 500 or silent zero totals. Now reads both keys safely.
#   4. Added a customer confirmation email matching the contact-form pattern.
#   5. Added proper input validation and error responses.

@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Invalid request"}), 400

    # Validate required fields
    required = ['firstName', 'lastName', 'email', 'telefon']
    missing  = [f for f in required if not str(data.get(f, '')).strip()]
    if missing:
        return jsonify({"success": False, "error": f"Campuri lipsa: {', '.join(missing)}"}), 422

    cart_items = data.get('cart', [])
    if not cart_items:
        return jsonify({"success": False, "error": "Cosul este gol"}), 422

    # Build order data
    first_name = data['firstName'].strip()
    last_name  = data['lastName'].strip()
    full_name  = f"{first_name} {last_name}"
    email_addr = data['email'].strip()
    telefon    = data['telefon'].strip()
    adresa     = data['adresa'].strip()
    oras       = data['oras'].strip()
    judet      = data['judet'].strip()
    timestamp  = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

    # Build product rows — handles both `quantity` and legacy `qty`
    total = 0
    rows_html = ""
    rows_text = ""
    for item in cart_items:
        name     = item.get('name', 'Produs necunoscut')
        price    = float(item.get('price', 0))
        qty      = int(item.get('quantity', item.get('qty', 1)))
        subtotal = price * qty
        total   += subtotal
        rows_html += f"""
          <tr>
            <td style="padding:10px 12px;border-bottom:1px solid #2a2a2a;">{name}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #2a2a2a;text-align:center;">{qty}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #2a2a2a;text-align:right;">{price:.2f} RON</td>
            <td style="padding:10px 12px;border-bottom:1px solid #2a2a2a;text-align:right;">{subtotal:.2f} RON</td>
          </tr>"""
        rows_text += f"  - {name}  x{qty}  --  {subtotal:.2f} RON\n"

    # ── HTML email → store ────────────────────────────────────
    html_store = f"""<!DOCTYPE html>
<html lang="ro">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Helvetica Neue',Arial,sans-serif;color:#e0e0e0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#111;border-radius:16px;overflow:hidden;max-width:600px;">

        <tr>
          <td style="background:linear-gradient(135deg,#ff4d6d,#ff758f);padding:30px 40px;text-align:center;">
            <h1 style="margin:0;color:#fff;font-size:24px;">Comanda Noua</h1>
            <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">{timestamp}</p>
          </td>
        </tr>

        <tr>
          <td style="padding:30px 40px;">
            <h2 style="margin:0 0 16px;font-size:15px;color:#ff4081;text-transform:uppercase;letter-spacing:1px;">Date client</h2>
            <table width="100%" cellpadding="0" cellspacing="0" style="font-size:14px;line-height:2;">
              <tr><td style="color:#888;width:130px;">Nume</td><td style="color:#fff;">{full_name}</td></tr>
              <tr><td style="color:#888;">Email</td><td><a href="mailto:{email_addr}" style="color:#ff4081;">{email_addr}</a></td></tr>
              <tr><td style="color:#888;">Telefon</td><td style="color:#fff;">{telefon}</td></tr>
              <tr><td style="color:#888;">Adresa</td><td style="color:#fff;">{adresa}</td></tr>
              <tr><td style="color:#888;">Oras / Judet</td><td style="color:#fff;">{oras}, {judet}</td></tr>
            </table>
          </td>
        </tr>

        <tr>
          <td style="padding:0 40px 30px;">
            <h2 style="margin:0 0 16px;font-size:15px;color:#ff4081;text-transform:uppercase;letter-spacing:1px;">Produse comandate</h2>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="font-size:14px;border-collapse:collapse;background:#1a1a1a;border-radius:10px;overflow:hidden;">
              <thead>
                <tr style="background:#222;">
                  <th style="padding:10px 12px;text-align:left;color:#888;font-weight:500;">Produs</th>
                  <th style="padding:10px 12px;text-align:center;color:#888;font-weight:500;">Cant.</th>
                  <th style="padding:10px 12px;text-align:right;color:#888;font-weight:500;">Pret/buc</th>
                  <th style="padding:10px 12px;text-align:right;color:#888;font-weight:500;">Subtotal</th>
                </tr>
              </thead>
              <tbody>{rows_html}</tbody>
              <tfoot>
                <tr style="background:#222;">
                  <td colspan="3" style="padding:12px;text-align:right;font-weight:700;color:#fff;">TOTAL</td>
                  <td style="padding:12px;text-align:right;font-weight:700;color:#ff4081;font-size:16px;">{total:.2f} RON</td>
                </tr>
              </tfoot>
            </table>
          </td>
        </tr>

        <tr>
          <td style="padding:20px 40px;border-top:1px solid #222;text-align:center;font-size:12px;color:#555;">
            Couple Designs &middot; contact@coupledesigns.ro &middot; +40 749 675 105
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    # ── Plain-text confirmation → customer ────────────────────
    text_customer = f"""Buna ziua, {first_name}!

Comanda ta la Couple Designs a fost primita si este in curs de procesare.

=====================================
  REZUMAT COMANDA -- {timestamp}
=====================================

Date livrare:
  Nume:    {full_name}
  Email:   {email_addr}
  Telefon: {telefon}
  Adresa:  {adresa}, {oras}, {judet}

Produse:
{rows_text}
  TOTAL: {total:.2f} RON

Plata prin transfer bancar:
  IBAN: ROZBR TEST TEST TEST
  Va rugam sa mentionati numele in detaliile platii.

=====================================
Te vom contacta in cel mai scurt timp.

Cu drag,
Echipa Couple Designs
contact@coupledesigns.ro | +40 749 675 105
"""

    # ── Imaginile de personalizare din sessionStorage ──────────────────────────
    # Frontul trimite: [{ productId, productName, name, type, dataUrl }, ...]
    # dataUrl = "data:<mime>;base64,<data>" — dezasamblat la atașare.
    session_images = data.get('sessionImages', [])

    # Secțiune HTML cu miniaturi pentru email-ul de notificare al merchantului
    images_html_section = ""
    if session_images:
        thumbs = ""
        for img in session_images[:20]:
            thumbs += (
                "<td style=\"padding:4px;\">"
                "<img src=\"" + img.get('dataUrl','') + "\"" 
                " width=\"80\" height=\"80\""
                " style=\"object-fit:cover;border-radius:6px;border:1px solid #2a2a2a;\"" 
                " alt=\"" + img.get('name','') + "\"></td>"
            )
        count = len(session_images)
        images_html_section = (
            "<tr><td style=\"padding:0 40px 30px;\">"
            "<h2 style=\"margin:0 0 16px;font-size:15px;color:#ff4081;"
            "text-transform:uppercase;letter-spacing:1px;\">"
            f"Imagini personalizate ({count} poze)</h2>"
            "<p style=\"font-size:13px;color:#777;margin:0 0 14px;\">"
            "Pozele trimise de client pentru personalizarea designului:</p>"
            "<table cellpadding=\"0\" cellspacing=\"0\"><tr>"
            + thumbs +
            "</tr></table></td></tr>"
        )

    # Injectează secțiunea de imagini în email înainte de footer
    footer_marker = (
        "        <tr>\n"
        "          <td style=\"padding:20px 40px;border-top:1px solid #222;"
        "text-align:center;font-size:12px;color:#555;\">\n"
        "            Couple Designs &middot; contact@coupledesigns.ro &middot; +40 749 675 105\n"
        "          </td>\n"
        "        </tr>"
    )
    html_store = html_store.replace(
        footer_marker,
        images_html_section + footer_marker
    )

    try:
        # 1. Notifică merchantul — cu imagini inline în HTML + atașate ca fișiere
        store_msg = Message(
            subject=f"[Comanda Noua] {full_name} -- {total:.2f} RON",
            sender=app.config['MAIL_USERNAME'],
            reply_to=email_addr,
            recipients=[STORE_EMAIL],
            html=html_store,
        )

        # Atașează fiecare imagine ca fișier separat — merchantul le poate descărca
        for idx, img in enumerate(session_images):
            data_url = img.get('dataUrl', '')
            img_name = img.get('name', f'imagine_{idx+1}.jpg')
            img_type = img.get('type', 'image/jpeg')
            if data_url and ',' in data_url:
                b64_data = data_url.split(',', 1)[1]
                try:
                    img_bytes = __import__('base64').b64decode(b64_data)
                    store_msg.attach(
                        filename=img_name,
                        content_type=img_type,
                        data=img_bytes,
                        disposition='attachment'
                    )
                except Exception as attach_err:
                    app.logger.warning(f"Imagine {img_name} nu s-a putut atasa: {attach_err}")

        mail.send(store_msg)

        # 2. Confirmare client (fără imagini — email simplu)
        customer_msg = Message(
            subject="Comanda ta la Couple Designs -- confirmare",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email_addr],
            body=text_customer,
        )
        mail.send(customer_msg)

    except Exception as e:
        app.logger.error(f"Checkout email error: {e}")
        # Return success anyway so the customer isn't stuck —
        # the error is logged server-side for manual follow-up.
        return jsonify({"success": True, "warning": "Email delivery issue noted."})

    return jsonify({"success": True})


# ── Helper: trimite emailuri după plată ───────────────────────
def send_order_confirmation(order_data):
    first_name     = order_data.get('firstName', '').strip()
    last_name      = order_data.get('lastName', '').strip()
    full_name      = f"{first_name} {last_name}"
    email_addr     = order_data.get('email', '').strip()
    telefon        = order_data.get('telefon', '').strip()
    cart_items     = order_data.get('cart', [])
    session_images = order_data.get('sessionImages', [])
    timestamp      = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

    total = 0
    rows_html = ""
    rows_text = ""
    for item in cart_items:
        name     = item.get('name', 'Produs')
        price    = float(item.get('price', 0))
        qty      = int(item.get('quantity', item.get('qty', 1)))
        subtotal = price * qty
        total   += subtotal
        rows_html += (
            f"<tr>"
            f"<td style='padding:10px 12px;border-bottom:1px solid #2a2a2a;'>{name}</td>"
            f"<td style='padding:10px 12px;border-bottom:1px solid #2a2a2a;text-align:center;'>{qty}</td>"
            f"<td style='padding:10px 12px;border-bottom:1px solid #2a2a2a;text-align:right;'>{price:.2f} RON</td>"
            f"<td style='padding:10px 12px;border-bottom:1px solid #2a2a2a;text-align:right;'>{subtotal:.2f} RON</td>"
            f"</tr>"
        )
        rows_text += f"  - {name}  x{qty}  --  {subtotal:.2f} RON\n"

    thumbs_html = "".join(
        f"<td style='padding:4px;'><img src='{img.get('dataUrl','')}' width='80' height='80'"
        f" style='object-fit:cover;border-radius:6px;border:1px solid #2a2a2a;'"
        f" alt='{img.get('name','')}' /></td>"
        for img in session_images[:20]
    )
    images_section = (
        f"<tr><td style='padding:0 40px 30px;'>"
        f"<h2 style='margin:0 0 16px;font-size:15px;color:#ff4081;text-transform:uppercase;letter-spacing:1px;'>"
        f"Imagini personalizate ({len(session_images)} poze)</h2>"
        f"<table cellpadding='0' cellspacing='0'><tr>{thumbs_html}</tr></table>"
        f"</td></tr>"
    ) if thumbs_html else ""

    html_store = f"""<!DOCTYPE html>
<html lang="ro"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Helvetica Neue',Arial,sans-serif;color:#e0e0e0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:30px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0"
       style="background:#111;border-radius:16px;overflow:hidden;max-width:600px;">
  <tr><td style="background:linear-gradient(135deg,#ff4d6d,#ff758f);padding:30px 40px;text-align:center;">
    <h1 style="margin:0;color:#fff;font-size:24px;">Comanda Noua ✅ Platita</h1>
    <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">{timestamp}</p>
  </td></tr>
  <tr><td style="padding:30px 40px;">
    <h2 style="margin:0 0 16px;font-size:15px;color:#ff4081;text-transform:uppercase;letter-spacing:1px;">Date client</h2>
    <table width="100%" cellpadding="0" cellspacing="0" style="font-size:14px;line-height:2;">
      <tr><td style="color:#888;width:130px;">Nume</td><td style="color:#fff;">{full_name}</td></tr>
      <tr><td style="color:#888;">Email</td><td><a href="mailto:{email_addr}" style="color:#ff4081;">{email_addr}</a></td></tr>
      <tr><td style="color:#888;">Telefon</td><td style="color:#fff;">{telefon}</td></tr>
    </table>
  </td></tr>
  <tr><td style="padding:0 40px 30px;">
    <h2 style="margin:0 0 16px;font-size:15px;color:#ff4081;text-transform:uppercase;letter-spacing:1px;">Produse comandate</h2>
    <table width="100%" cellpadding="0" cellspacing="0"
           style="font-size:14px;border-collapse:collapse;background:#1a1a1a;border-radius:10px;overflow:hidden;">
      <thead><tr style="background:#222;">
        <th style="padding:10px 12px;text-align:left;color:#888;font-weight:500;">Produs</th>
        <th style="padding:10px 12px;text-align:center;color:#888;font-weight:500;">Cant.</th>
        <th style="padding:10px 12px;text-align:right;color:#888;font-weight:500;">Pret/buc</th>
        <th style="padding:10px 12px;text-align:right;color:#888;font-weight:500;">Subtotal</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
      <tfoot><tr style="background:#222;">
        <td colspan="3" style="padding:12px;text-align:right;font-weight:700;color:#fff;">TOTAL</td>
        <td style="padding:12px;text-align:right;font-weight:700;color:#ff4081;font-size:16px;">{total:.2f} RON</td>
      </tr></tfoot>
    </table>
  </td></tr>
  {images_section}
  <tr><td style="padding:20px 40px;border-top:1px solid #222;text-align:center;font-size:12px;color:#555;">
    Couple Designs &middot; contact@coupledesigns.ro &middot; +40 749 675 105
  </td></tr>
</table>
</td></tr></table>
</body></html>"""

    text_customer = f"""Buna ziua, {first_name}!

Comanda ta la Couple Designs a fost platita cu succes si este in curs de procesare.

=====================================
  REZUMAT COMANDA -- {timestamp}
=====================================

Date contact:
  Nume:    {full_name}
  Email:   {email_addr}
  Telefon: {telefon}

Produse:
{rows_text}
  TOTAL: {total:.2f} RON

Plata a fost efectuata cu succes prin card.
Te vom contacta in cel mai scurt timp pentru detalii.

Cu drag,
Echipa Couple Designs
contact@coupledesigns.ro | +40 749 675 105
"""

    store_msg = Message(
        subject=f"[Comanda Platita] {full_name} -- {total:.2f} RON",
        sender=app.config['MAIL_USERNAME'],
        reply_to=email_addr,
        recipients=[STORE_EMAIL],
        html=html_store,
    )
    for idx, img in enumerate(session_images):
        data_url = img.get('dataUrl', '')
        img_name = img.get('name', f'imagine_{idx+1}.jpg')
        img_type = img.get('type', 'image/jpeg')
        if data_url and ',' in data_url:
            try:
                img_bytes = base64.b64decode(data_url.split(',', 1)[1])
                store_msg.attach(filename=img_name, content_type=img_type,
                                 data=img_bytes, disposition='attachment')
            except Exception as e:
                app.logger.warning(f"Imagine {img_name} nu s-a putut atasa: {e}")
    mail.send(store_msg)

    customer_msg = Message(
        subject="Comanda ta la Couple Designs — platita cu succes",
        sender=app.config['MAIL_USERNAME'],
        recipients=[email_addr],
        body=text_customer,
    )
    mail.send(customer_msg)


# ── Stripe: creare sesiune de plată ──────────────────────────
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.get_json(silent=True)
    if not data or not data.get('cart'):
        return jsonify({"error": "Coșul este gol"}), 400

    if not stripe.api_key:
        return jsonify({"error": "Plata online nu este configurată încă."}), 503

    order_id = str(uuid.uuid4())
    pending_orders[order_id] = data

    first_name = data.get('firstName', '')[:100]
    last_name  = data.get('lastName', '')[:100]
    telefon    = data.get('telefon', '')[:50]

    line_items = [
        {
            'price_data': {
                'currency': 'ron',
                'product_data': {'name': item.get('name', 'Produs')},
                'unit_amount': int(float(item.get('price', 0)) * 100),
            },
            'quantity': int(item.get('quantity', 1)),
        }
        for item in data['cart']
    ]

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=data.get('email', ''),
            metadata={
                'order_id': order_id,
                'firstName': first_name,
                'lastName': last_name,
                'telefon': telefon,
            },
            success_url=request.host_url.rstrip('/') + '/payment-success',
            cancel_url=request.host_url.rstrip('/') + '/cart',
        )
        return jsonify({'url': session.url})
    except stripe.error.StripeError as e:
        app.logger.error(f"Stripe error: {e}")
        return jsonify({"error": "Eroare la procesarea plății. Încearcă din nou."}), 400


# ── Stripe: webhook (confirmare plată) ───────────────────────
@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload    = request.get_data()
    sig_header = request.headers.get('Stripe-Signature', '')
    wh_secret  = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

    try:
        if wh_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, wh_secret)
        else:
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except Exception as e:
        app.logger.error(f"Webhook parse error: {e}")
        return jsonify({'error': 'Invalid payload'}), 400

    if event['type'] == 'checkout.session.completed':
        stripe_session = event['data']['object']
        try:
            meta       = stripe_session.get('metadata', {})
            order_id   = meta.get('order_id', '')
            first_name = meta.get('firstName', '')
            last_name  = meta.get('lastName', '')
            email_addr = stripe_session.get('customer_email', '') or meta.get('email', '')
            telefon    = meta.get('telefon', '')

            order_data = pending_orders.pop(order_id, None)
            if order_data:
                send_order_confirmation(order_data)
            elif email_addr:
                # pending_orders expirat (Railway restart) — email minimal din metadata
                send_minimal_confirmation(first_name, last_name, email_addr, telefon, stripe_session)
        except Exception as e:
            app.logger.error(f"Webhook email error: {e}")

    return jsonify({'status': 'ok'})


def send_minimal_confirmation(first_name, last_name, email_addr, telefon, stripe_session):
    full_name = f"{first_name} {last_name}".strip() or "Client"
    timestamp = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    amount    = stripe_session.get('amount_total', 0) / 100

    store_msg = Message(
        subject=f"[Comanda Platita] {full_name} — {amount:.2f} RON",
        sender=app.config['MAIL_USERNAME'],
        reply_to=email_addr,
        recipients=[STORE_EMAIL],
        body=f"Comanda platita!\nNume: {full_name}\nEmail: {email_addr}\nTelefon: {telefon}\nTotal: {amount:.2f} RON\nData: {timestamp}",
    )
    mail.send(store_msg)

    customer_msg = Message(
        subject="Comanda ta la Couple Designs — platita cu succes",
        sender=app.config['MAIL_USERNAME'],
        recipients=[email_addr],
        body=f"Buna ziua, {first_name}!\n\nComanda ta a fost platita cu succes ({amount:.2f} RON).\nTe vom contacta curand.\n\nEchipa Couple Designs",
    )
    mail.send(customer_msg)


# ── Stripe: pagina succes (fara apeluri externe - nu poate da 500) ──
@app.route('/payment-success')
def payment_success():
    return (
        '<!DOCTYPE html><html lang="ro"><head><meta charset="UTF-8">'
        '<title>Plata reusita - Couple Designs</title>'
        '<style>'
        '*{box-sizing:border-box;margin:0;padding:0;}'
        'body{font-family:Helvetica Neue,Arial,sans-serif;background:#0a0a0a;color:#fff;'
        'min-height:100vh;display:flex;align-items:center;justify-content:center;padding:40px 20px;}'
        '.wrap{max-width:520px;text-align:center;}'
        '.icon{font-size:4rem;margin-bottom:24px;}'
        'h1{font-size:2rem;font-weight:800;margin-bottom:14px;}'
        '.sub{color:#888;font-size:1rem;line-height:1.6;margin-bottom:40px;}'
        '.steps{background:#111;border-radius:16px;padding:24px;text-align:left;'
        'margin-bottom:36px;display:flex;flex-direction:column;gap:18px;}'
        '.step{display:flex;gap:14px;align-items:flex-start;}'
        '.si{font-size:1.4rem;flex-shrink:0;}'
        '.step strong{display:block;color:#fff;font-size:.95rem;margin-bottom:3px;}'
        '.step p{font-size:.83rem;color:#666;line-height:1.5;margin:0;}'
        '.actions{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;}'
        '.btn-p{background:linear-gradient(135deg,#ff4d6d,#ff758f);color:#fff;'
        'padding:13px 28px;border-radius:10px;font-weight:700;font-size:.95rem;text-decoration:none;}'
        '.btn-g{color:#aaa;padding:13px 20px;border-radius:10px;font-size:.95rem;'
        'text-decoration:none;border:1px solid rgba(255,255,255,.1);}'
        '</style></head>'
        '<body><div class="wrap">'
        '<div class="icon">&#x2705;</div>'
        '<h1>Plata reusita!</h1>'
        '<p class="sub">Comanda ta a fost inregistrata si plata a fost procesata cu succes.</p>'
        '<div class="steps">'
        '<div class="step"><span class="si">&#x1F4E7;</span><div>'
        '<strong>Confirmare pe email</strong>'
        '<p>Vei primi in cateva minute un email cu rezumatul comenzii.</p>'
        '</div></div>'
        '<div class="step"><span class="si">&#x1F3A8;</span><div>'
        '<strong>Design personalizat</strong>'
        '<p>Echipa noastra va crea tabloul tau manual, cu grija si atentie la detalii.</p>'
        '</div></div>'
        '<div class="step"><span class="si">&#x1F4E6;</span><div>'
        '<strong>Livrare</strong>'
        '<p>Te vom contacta pentru a stabili detaliile de livrare.</p>'
        '</div></div>'
        '</div>'
        '<div class="actions">'
        '<a href="/designuri" class="btn-p">Exploreaza mai multe</a>'
        '<a href="/" class="btn-g">Inapoi acasa</a>'
        '</div></div></body></html>'
    )


# ── Entry point ───────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
