# Dokončení PR #1 – podklad ke kontrole

## Porovnané revize

Kontrola 28. 10. 2026:

| Reference | Commit |
| --- | --- |
| Aktuální main | `f7d3aa23f59e759a4d7df414a65fa6fa5abafb5e` |
| PR #1 | `ec6e2e7d3bff30d14d96b7efc96862f5948765fb` |
| Společný základ | `dd665837c56d3fb3129a12c7f6eeee05a1cee44f` |

`git rev-list --left-right --count origin/main...origin/agent/improve-poolcars-app`
vrací `10 2`. Samotný REST snapshot PR uváděl jako base starší `07c2886...`;
porovnání jen proti němu by nesprávně ukazovalo 2 místo 10 novějších commitů.
Pro rozhodnutí je použitá skutečná reference `origin/main`.

## Konflikt a zachované změny

`git merge-tree --write-tree origin/main origin/agent/improve-poolcars-app`
hlásí pouze obsahový konflikt `README.md`. Nebyl vytvořen merge commit a žádná
větev na GitHubu nebyla sloučená.

Deset commitů na main mění README a přidává/přejmenovává galerii `Images/`.
Od společného základu na main nejsou změny aplikačního kódu. Oba commity PR
přinášejí bezpečnostní přepracování a následně reset formuláře a zpětnou vazbu
rezervací. Přímé nahrazení celého stromu main stromem PR by odstranilo galerii.

Kontrolní větev vychází z posledního main; přebírá kód a šablony PR, ručně
sjednocuje README a zachovává všechny čtyři soubory Images beze změn. Odstranění
nepoužívaného `tyden.py` přebírá z PR a navíc odstraňuje verzované `.pyc`;
`.gitignore` nezruší sledování již verzovaných binárních souborů samo.
Původní PR #1 i jeho dva commity zůstávají nedotčené.

## Opravy nad rámec původního PR

| Problém | Oprava a důvod |
| --- | --- |
| Hash mohl projít jako heslo | Hashové hodnoty se ověřují pouze hashovacím algoritmem; plaintext migrace je explicitně zapínaná. Původní fallback `stored == supplied` po neúspěšném ověření přijal i zadaný hash. |
| Změna hesla během migrace | Podmíněný UPDATE a kontrola počtu změněných řádků zabrání přepsání souběžné změny hesla. |
| Pevný / náhodný klíč bez sdílení | `SECRET_KEY` je povinný; veřejný původní klíč dovoloval padělání session, náhodný klíč při každém startu rozbíjel více procesů. |
| Pravdivost řetězce `"0"` | Admin je explicitně vyhodnocen z 1/true; řetězec `"0"` nesmí přidělit práva. |
| Odhlášení přes GET | POST s CSRF zabraňuje změně session pouhým otevřením odkazu. |
| Ne-ASCII CSRF token způsobil výjimku | Porovnávají se UTF-8 bytes; neplatný token vrací 400. |
| Prázdné nebo záporné kilometry | Prázdné hodnoty jdou jako NULL, ostatní jsou validované; rozdíl tachometru se kontroluje na serveru. |
| Zámek celé tabulky | Transakce zamyká existující řádek auta a provádí aktuální zamykací kontrolu překryvu. Nevyžaduje LOCK TABLES a různé vozy nemají společný globální zámek. |
| Kolize s HTTP 200 | HTTP 409 jednoznačně odliší konflikt od úspěchu. |
| Rok mimo rozsah `date` | Kalendářní vstup je omezen na 1901–9999, aby nevyvolal chybu 500. |
| Zastaralé přímé závislosti | Flask 3.1.3, Werkzeug 3.1.9 a MySQL Connector 26.10.0; kompatibilita aplikace se ověřuje testy, existující server je třeba ověřit zvlášť. |

Referenční `schema.sql` zpřístupňuje čistou lokální instalaci a integrační testy.
Nenahrazuje zjištění skutečné struktury existující DB a nesmí se na ni slepě aplikovat.

## Ověření a zbývající podmínky

Lokálně: 35 automatických testů prošlo, 3 integrační MySQL testy byly přeskočené,
protože místní prostředí nemá samostatný MySQL server. `pip check`, kompilace
Python souborů a `git diff --check` jsou součástí kontroly před odesláním.
CI je připravené pro Python 3.10 a 3.12 a samostatnou MySQL 8.4 službu; skutečný
výsledek je nutné odečíst z GitHub Actions, nelze ho odvozovat z konfigurace.

Před schválením:

1. Zkontrolovat změny a zelené unit i MySQL CI, zejména souběh dvou rezervací.
2. Na kopii vlastní DB prověřit InnoDB, klíče, délku hesel, NULL kilometry a stará
   nekonzistentní data podle README. Bez znalosti DB nelze tvrdit, že upgrade je hotový.
3. Ručně projít přihlášení admina a běžného účtu, načtení SPZ, rezervaci,
   konflikt, neoprávněný přístup a odhlášení.
4. Teprve po výslovném schválení zvolit, zda použít kontrolní PR jako náhradu #1,
   nebo přenést schválený výsledek do původní větve. Automaticky se nic neslučuje
   a původní PR se nezavírá.

Do sloučení kontrolního PR zůstává rozpor na původním main zachovaný.
Jeho oprava je součástí navržené změny, nikoli již provedený zásah do main.
