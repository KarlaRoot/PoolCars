
PoolCars je jednoducha Flask aplikace pro evidenci firemnich aut, zamestnancu
a rezervaci aut. Aplikace pouziva MySQL databazi, HTML sablony v Jinja2 a
zakladni session prihlaseni s rozlisenim admin/beznym uzivatelem.

## Co je v projektu

```text
PoolCars/
├─ main.py                  # Flask aplikace, routy, session, CSRF a validace formularu
├─ PoolCar.py               # Databazova vrstva pro auta, zamestnance, login a rezervace
├─ weeks.py                 # Pomocna funkce pro vypocet tydnu v mesici
├─ testimport.py            # Jednoducha kontrola importu mysql.connector
├─ requirements.txt         # Python zavislosti
├─ static/
│  └─ style.css             # Spolecny CSS styl pro stranky a formulare
├─ styles/                  # Prazdny adresar, aktualne se v aplikaci nepouziva
└─ templates/
   ├─ index.html            # Uvodni rozcestnik podle stavu prihlaseni
   ├─ login.html            # Prihlasovaci formular
   ├─ auta.html             # Formular pro pridani auta, pouze admin
   ├─ zamestnanci.html      # Formular pro pridani zamestnance, pouze admin
   ├─ rezervace.html        # Formular pro vytvoreni rezervace
   ├─ result.html           # Tabulkovy vypis tydnu v mesici
   └─ logout.html           # Stara odhlasovaci sablona, aktualni route presmeruje na home
```

Ignorovane/generovane soubory jsou hlavne `__pycache__/` a `*.pyc`.

## Hlavni funkcionalita

- Prihlaseni uzivatele pres `/login`.
- Ukladani hesel jako hash pres Werkzeug; stare plaintext heslo se pri uspesnem
  loginu automaticky prevede na hash.
- Rozliseni prav:
  - admin ma pristup k pridani aut a zamestnancu,
  - bezny prihlaseny uzivatel muze pracovat s rezervacemi jen pro sebe.
- CSRF ochrana pro POST/PUT/PATCH/DELETE pozadavky.
- Pridani auta do tabulky `auta`.
- Pridani zamestnance do tabulky `zamestnanci`.
- Vytvoreni rezervace do tabulky `rezervace`.
- Kontrola kolize rezervaci podle SPZ a datumu prevzeti/odevzdani.
- AJAX endpoint pro nacteni informaci o zamestnanci.
- Jednoduchy kalendarni vypis tydnu v mesici.

## Routy

| Route | Metody | Popis |
| --- | --- | --- |
| `/` | GET | Uvodni stranka a navigace |
| `/login` | GET, POST | Prihlaseni uzivatele |
| `/logout` | GET | Vymazani session a navrat na home |
| `/auta` | GET | Formular pro pridani auta, pouze admin |
| `/submit` | POST | Zpracovani formulare auta, pouze admin |
| `/zamestnanci` | GET, POST | Formular a ulozeni zamestnance, pouze admin |
| `/rezervace` | GET | Formular rezervace, pouze prihlaseny uzivatel |
| `/insertRezervace` | POST | Ulozeni rezervace, pouze prihlaseny uzivatel |
| `/getEmployeeInfo` | GET | JSON detail zamestnance s kontrolou opravneni |
| `/result` | POST | Vypis tydnu pro zadany rok a mesic |

## Databaze

Aplikace ocekava MySQL databazi, ve vychozim nastaveni databazi `poolcars`.
Z kodu jsou pouzivane tyto tabulky a sloupce:

- `auta`: `idAuta`, `vin`, `spz`, `znacka`, `model`, `rokVyroby`, `najetoKm`
- `zamestnanci`: `idZamestnance`, `jmeno`, `prijmeni`, `login`, `admin`,
  `heslo`, `email`, `divize`, `oddeleni`
- `rezervace`: `idZamestnance`, `jmeno`, `prijmeni`, `divize`, `oddeleni`,
  `idAuta`, `spz`, `stavRezervace`, `prevzetiDne`, `odevzdaniDne`,
  `kmPredJizdou`, `kmPoJizde`, `najetoKm`, `poskozeni`

SQL migrace/schema neni v tomto adresari ulozene.

## Konfigurace

Konfigurace se bere z promennych prostredi:

| Promenna | Vychozi hodnota | Popis |
| --- | --- | --- |
| `SECRET_KEY` | nahodne v pameti | Flask secret pro session; v produkci nastavit pevne |
| `LOG_LEVEL` | `INFO` | Uroven logovani |
| `FLASK_ENV` | prazdne | Pri `development` zapne Flask debug mode |
| `DB_HOST` | `localhost` | Host MySQL |
| `DB_PORT` | prazdne | Port MySQL, pokud je potreba |
| `DB_USER` | `root` | Uzivatel MySQL |
| `DB_PASSWORD` | prazdne | Heslo MySQL |
| `DB_NAME` | `poolcars` | Nazev databaze |
| `DB_CONNECTION_TIMEOUT` | `3` | Timeout pripojeni v sekundach |
| `PASSWORD_HASH_METHOD` | `pbkdf2:sha256` | Metoda hashovani hesel |

## Spusteni lokalne

```powershell
cd C:\Users\rek11\Documents\Doc\GitHub\PoolCars
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:SECRET_KEY = "dev-secret-change-me"
$env:DB_HOST = "localhost"
$env:DB_USER = "root"
$env:DB_PASSWORD = "heslo"
$env:DB_NAME = "poolcars"
$env:FLASK_ENV = "development"

python main.py
```

## Testovani a overeni

Automaticka testovaci sada zatim v projektu neni. `python -m unittest discover`
nasel 0 testu.

Provedene kontroly 2026-07-10:

- `python -m py_compile main.py PoolCar.py weeks.py testimport.py` proslo.
- `python -m compileall .` proslo.
- Flask test client:
  - `GET /` vraci 200.
  - `GET /login` vraci 200.
  - `GET /auta` bez admin session presmeruje s 302.
  - `GET /rezervace` bez login session presmeruje s 302.
  - `POST /result` s validnim CSRF tokenem vraci 200.
  - `POST /result` bez CSRF tokenu vraci 400.
  - `POST /login` s prazdnymi udaji vraci 400.
  - Admin `GET /auta` a `GET /zamestnanci` vraci 200.
  - Admin validace neplatneho auta na `/submit` vraci 400.
  - Admin validace prazdneho formulare `/zamestnanci` vraci 400.
  - Bezny uzivatel na `/getEmployeeInfo?employee_id=2` mimo vlastni ID vraci 403.
- `weeks.get_weeks_of_month(2026, 7)` vraci ocekavanou tabulku tydnu a mesic
  mimo rozsah vyvola `ValueError`.

Databazove zapisy a prihlaseni proti realnym uzivatelum nebyly spusteny,
protoze k nim je potreba pripravena MySQL databaze se schematem a daty.

## Poznamky

- Projekt ma vlastni `.git` adresar primo v `PoolCars/`.
- Soubor `logout.html` je v projektu, ale aktualni `/logout` route ho nepouziva.
- CSS obsahuje par starsich komentaru s poskozenym kodovanim, funkcne to ale
  neblokuje spusteni aplikace.
PoolCars/
├─ main.py                  # Flask aplikace, routy, session, CSRF a validace formularu
├─ PoolCar.py               # Databazova vrstva pro auta, zamestnance, login a rezervace
├─ weeks.py                 # Pomocna funkce pro vypocet tydnu v mesici
├─ testimport.py            # Jednoducha kontrola importu mysql.connector
├─ requirements.txt         # Python zavislosti
├─ static/
│  └─ style.css             # Spolecny CSS styl pro stranky a formulare
├─ styles/                  # Prazdny adresar, aktualne se v aplikaci nepouziva
└─ templates/
   ├─ index.html            # Uvodni rozcestnik podle stavu prihlaseni
   ├─ login.html            # Prihlasovaci formular
   ├─ auta.html             # Formular pro pridani auta, pouze admin
   ├─ zamestnanci.html      # Formular pro pridani zamestnance, pouze admin
   ├─ rezervace.html        # Formular pro vytvoreni rezervace
   ├─ result.html           # Tabulkovy vypis tydnu v mesici
   └─ logout.html           # Stara odhlasovaci sablona, aktualni route presmeruje na home
+-- main.py                  # Flask aplikace, routy, session, CSRF a validace formularu
+-- PoolCar.py               # Databazova vrstva pro auta, zamestnance, login a rezervace
+-- weeks.py                 # Pomocna funkce pro vypocet tydnu v mesici
+-- testimport.py            # Jednoducha kontrola importu mysql.connector
+-- requirements.txt         # Python zavislosti
+-- static/
|   +-- style.css            # Spolecny CSS styl pro stranky a formulare
+-- styles/                  # Prazdny adresar, aktualne se v aplikaci nepouziva
+-- templates/
    +-- index.html           # Uvodni rozcestnik podle stavu prihlaseni
    +-- login.html           # Prihlasovaci formular
    +-- auta.html            # Formular pro pridani auta, pouze admin
    +-- zamestnanci.html     # Formular pro pridani zamestnance, pouze admin
    +-- rezervace.html       # Formular pro vytvoreni rezervace
    +-- result.html          # Tabulkovy vypis tydnu v mesici
    +-- logout.html          # Stara odhlasovaci sablona, aktualni route presmeruje na home
```
