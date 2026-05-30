# Couple Designs - Site Flask

## Instalare și rulare

### 1. Instalează dependențele
```bash
pip install flask
```
sau
```bash
pip install -r requirements.txt
```

### 2. Pornește serverul
```bash
python app.py
```

### 3. Deschide în browser
Mergi la: **http://localhost:5000**

---

## Structura proiectului
```
couple_designs/
├── app.py                  # Aplicația Flask principală
├── requirements.txt        # Dependențe Python
├── templates/
│   ├── base.html           # Template de bază (navbar + footer)
│   ├── index.html          # Pagina principală
│   ├── designuri.html      # Pagina cu toate designurile
│   ├── despre_noi.html     # Pagina Despre noi
│   ├── cum_functioneaza.html
│   └── contact.html
└── static/
    ├── css/
    │   └── style.css       # Stiluri principale
    └── js/
        └── main.js         # JavaScript
```

## Pagini disponibile
- `/` - Acasă (Hero + Produse populare + Features)
- `/designuri` - Toate designurile
- `/despre-noi` - Despre noi
- `/cum-functioneaza` - Cum funcționează
- `/contact` - Contact
- `/api/products` - API JSON cu produse
