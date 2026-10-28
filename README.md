# PoolCars

Flask aplikace pro evidenci firemních aut, zaměstnanců a rezervací v MySQL.

Tento README popisuje kód **této větve**. Opravy vycházejí z rozpracovaného
[PR #1](https://github.com/KarlaRoot/PoolCars/pull/1) a z `main` na commitu
`f7d3aa23f59e759a4d7df414a65fa6fa5abafb5e`. Dokud změny nejsou schválené a
sloučené, původní `main` neobsahuje zde popsané bezpečnostní opravy.
Podrobné porovnání a postup kontroly jsou v [docs/PR1-review.md](docs/PR1-review.md).

## Co aplikace umí

- Přihlášení pomocí parametrizovaného SQL a hashů Werkzeug. Nová hesla se hashují.
- Administrátor přidává auta a zaměstnance. Běžný uživatel rezervuje pouze za sebe
  a může načítat jen vlastní osobní údaje.
- Všechny měnící HTTP požadavky včetně odhlášení vyžadují CSRF token.
- Rezervace ověřuje existenci zaměstnance a auta, pořadí dat a nezáporné celé
  kilometry. Pokud jsou vyplněné oba stavy tachometru, vzdálenost musí odpovídat
  jejich rozdílu; prázdné číselné údaje se ukládají jako SQL `NULL`.
- Údaje zaměstnance a ID auta přebírá server z databáze, nikoli ze skrytých polí.
- Kontrola překryvu i vložení rezervace běží v jedné transakci. Zámek řádku auta
  serializuje požadavky pro stejné auto; vyžaduje tabulky InnoDB.
- Intervaly rezervací zahrnují oba krajní dny. Vrácení a další převzetí stejného
  auta ve stejný den je kolize. Všechny uložené stavy rezervace blokují termín;
  rušení rezervací a workflow stavů zatím implementované nejsou.
- Pomocná funkce `weeks.py` a `/result` zobrazují týdny měsíce. Nejde o přehled
  dostupnosti aut ani správu existujících rezervací.

## Soubory a routy

| Soubor / adresář | Účel |
| --- | --- |
| `main.py` | Flask routy, session, oprávnění, CSRF, validace |
| `PoolCar.py` | Připojení, parametrizované SQL, hesla a transakce |
| `requirements.txt` | Přímé závislosti s pevnými verzemi |
| `schema.sql` | Referenční schéma pro novou prázdnou databázi |
| `templates/`, `static/` | Jinja šablony a CSS |
| `weeks.py` | Kalendářní týdny |
| `tests/` | Unit testy a volitelné integrační testy MySQL |
| `.github/workflows/tests.yml` | CI pro Python 3.10/3.12 a MySQL 8.4 |
| `Images/` | Zachované starší snímky obrazovek |

| Route | Metoda | Přístup / výsledek |
| --- | --- | --- |
| `/` | GET | Rozcestník |
| `/login` | GET, POST | Přihlášení; POST vyžaduje CSRF |
| `/logout` | POST | Smazání session; vyžaduje CSRF |
| `/auta`, `/submit` | GET, POST | Formulář auta / uložení; pouze admin |
| `/zamestnanci` | GET, POST | Zaměstnanci; pouze admin |
| `/rezervace`, `/insertRezervace` | GET, POST | Formulář / uložení; přihlášení |
| `/getEmployeeInfo` | GET | JSON; vlastní ID, admin libovolné ID |
| `/result` | POST | Týdny měsíce; CSRF |

Úspěšný zápis přesměruje na formulář (POST/Redirect/GET); kolize rezervace vrací
HTTP 409, neplatné vstupy 400 a chyba při ukládání 500.

## Lokální spuštění

Vyžaduje Python 3.10+ a MySQL 8.4 s InnoDB. Integrační CI používá MySQL 8.4.
Následující příkazy jsou pro Bash; v PowerShellu aktivuj `.venv\\Scripts\\Activate.ps1`
a proměnné nastavuj pomocí `$env:JMENO = "hodnota"`.

```bash
git clone https://github.com/KarlaRoot/PoolCars.git
cd PoolCars
# Před sloučením oprav přepni na větev uvedenou v kontrolním PR.
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=poolcars_app
export DB_PASSWORD='vlastni-heslo'
export DB_NAME=poolcars
python main.py
```

Před startem založ databázi a samostatného databázového uživatele. Aplikace
potřebuje SELECT/INSERT/UPDATE; nepotřebuje `LOCK TABLES` ani správu databází.
Do **nové prázdné** databáze může její správce načíst `schema.sql`, například
`mysql -h 127.0.0.1 -u SPRAVCE -p poolcars < schema.sql`.
Schéma neobsahuje demo účty ani hesla. Prvního zaměstnance vytvoř přes
`Databaze.insert_employee(...)` v Pythonu s nastavenými DB proměnnými a jeho
`admin=1` nastav správcem databáze; běžný webový formulář admin práva nepřiděluje.

Aplikace se bez `SECRET_KEY` nespustí. Pro opakované starty a všechny procesy
používej stejnou náhodnou hodnotu uloženou mimo Git. Její změna zneplatní session.
Flask vývojový server slouží k lokálnímu ověření. Veřejné nasazení vyžaduje HTTPS,
WSGI server, vypnutý debug, omezení pokusů o přihlášení a provozní konfiguraci;
projekt zatím neobsahuje rate limiting ani kompletní produkční nasazení.

## Konfigurace a existující data

| Proměnná | Výchozí hodnota | Význam |
| --- | --- | --- |
| `SECRET_KEY` | žádná, povinná | Sdílený náhodný klíč pro podepsané session |
| `SESSION_COOKIE_SECURE` | `0` | Na HTTPS nastav `1`; lokálně HTTP ponech `0` |
| `DB_HOST` / `DB_NAME` | `localhost` / `poolcars` | MySQL host a databáze |
| `DB_USER` / `DB_PASSWORD` | `root` / žádné | Použij vlastní účet s omezenými právy |
| `DB_PORT` | výchozí port konektoru | Volitelný port |
| `DB_CONNECTION_TIMEOUT` | `3` | Timeout připojení v sekundách |
| `PASSWORD_HASH_METHOD` | `pbkdf2:sha256` | Hashování nových a migrovaných hesel |
| `ALLOW_LEGACY_PASSWORDS` | `0` | Jen dočasná migrace starých plaintext hesel |
| `LOG_LEVEL` | `INFO` | Úroveň logů |
| `FLASK_ENV` | prázdná | `development` zapne debug při `python main.py` |

Referenční schéma není automatická migrace existující databáze. Před přechodem
zálohuj a ověř její skutečnou strukturu: tabulky `auta`, `zamestnanci`, `rezervace`
musí být InnoDB; `auta.id` je primární klíč (Python ho vrací jako `idAuta`),
`rezervace.idAuta` na něj odkazuje; `heslo` musí mít kapacitu alespoň 255 znaků,
`login` a SPZ musí být jednoznačné. Volitelné kilometrové sloupce musí povolovat
NULL. Index `(idAuta, prevzetiDne, odevzdaniDne)` omezuje rozsah kontroly překryvu.
Staré duplicitní účty, překryvy a neplatné reference vyřeš před změnou omezení.

Plaintext hesla jsou standardně odmítaná. Po kontrole délky sloupce a záloze lze
**dočasně** nastavit `ALLOW_LEGACY_PASSWORDS=1`: úspěšný login staré heslo nahradí
hashem. Poté režim vypni a zbývající účty resetuj. Staré plaintext heslo obsahující
`$` vyžaduje reset, protože je záměrně považované za hash. Neznámý či poškozený
hash se nikdy neověřuje jako plaintext. Migrace se na databázi nespouští automaticky.
Při přechodu z veřejně známého původního Flask klíče nastav nový náhodný klíč,
aby se zneplatnily dřívější session.

## Ověření

```bash
python -m pip check
python -m py_compile main.py PoolCar.py weeks.py
python -m unittest discover -v
```

Běžný běh nepotřebuje MySQL: obsahuje 35 testů přihlášení, oprávnění, CSRF,
rezervací a databázových chyb; 3 MySQL testy jsou výslovně přeskočené.
Mockované testy samy neprokazují chování databázových zámků.

Pro integrační běh připrav **samostatnou prázdnou databázi** s názvem končícím
`_test`, nastav DB proměnné na ni a spusť:

```bash
export DB_NAME=poolcars_test
export RUN_MYSQL_TESTS=1
python -m unittest tests.test_mysql -v
```

Testy si vytvoří tabulky, ověří skutečné hashované přihlášení, SQL injection,
překryvy i dva souběžné požadavky a své tabulky odstraní. Odmítnou neprázdnou
databázi. Nesměřuj je na provozní data. CI spouští totéž v dočasné MySQL službě.

Před schválením ještě ručně ověř v testovací aplikaci: admin přidá auto a
zaměstnance, běžný uživatel se přihlásí a vidí jen sebe a dostupné SPZ, uloží
rezervaci, opakovaný překryv dostane chybu a po odhlášení už chráněné stránky
neotevře. Prázdný formulář po uložení a při návratu z Home je záměrné chování
převzaté z druhého commitu PR #1.

## Ukázky aplikace

Starší snímky z `main` jsou zachované jako ilustrace. Nejsou důkazem aktuálního
bezpečnostního chování ani výsledkem automatických testů.

### Přihlašovací obrazovka

![Přihlašovací obrazovka](Images/login)

### Hlavní nabídka

![Hlavní nabídka aplikace](Images/menu)

### Rezervace vozidla

![Formulář rezervace vozidla](Images/rezervace)
