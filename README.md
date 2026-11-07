# mObywatel.ai: pełna wersja prototypu do uruchomienia u siebie

Instrukcja konkursowa z opisem projektu, uruchomieniem, technologiami i
przygotowaniem publicznego prototypu znajduje się w
[`INSTRUKCJA_KONKURSOWA.txt`](INSTRUKCJA_KONKURSOWA.txt). Testy regresji można
uruchomić poleceniem `python -m unittest discover -s tests -v`.

To prototyp aplikacji, w której zamiast menu i formularzy jest asystent AI: rozmawiasz z nim tekstem albo głosem,
a on sprawdza dane w (fikcyjnych) rejestrach i załatwia sprawy, każdą czynność potwierdzasz na karcie.
Wersja na stronie mobywatel.ai działa bez asystenta AI (scenariusze ze skryptu). Ta paczka zawiera pełną wersję:
serwer w Pythonie z asystentem, rozpoznawaniem i syntezą mowy oraz front aplikacji.

**Ważne:** to prototyp z fikcyjnymi danymi (osoby, numery PESEL, dokumenty, pojazdy i płatności są zmyślone).
To nie jest usługa administracji publicznej ani aplikacja mObywatel, nie łączy się z żadnym rejestrem państwowym
i nie wolno w nim wpisywać prawdziwych danych osobowych. Teksty z kart usług gov.pl i biznes.gov.pl w katalogu
`serwer/wiedza/` to kopia publicznych stron z dnia ich pobrania, mogą być nieaktualne.

## Co jest w paczce

- `serwer/`: serwer HTTP w Pythonie (sama biblioteka standardowa, bez `pip install`), asystent, narzędzia, fikcyjne dane.
  - `serwer/i18n/`: słowniki interfejsu (15 języków poza polskim),
  - `serwer/glosariusz/`: słowniczek dla tłumaczenia rozmowy z asystentem,
  - `serwer/wiedza/`: baza wiedzy z kart usług gov.pl (wyszukiwanie lokalne, bez sieci).
- `mockup/`: front aplikacji (HTML, CSS, JavaScript, grafiki).
- `Dockerfile`, `docker-compose.yml`, `.env.example`.

## Wymagania

- Python 3.9 lub nowszy (Linux, macOS albo Windows), bez dodatkowych bibliotek, albo Docker.
- Przeglądarka. Głos wymaga dostępu do mikrofonu, a przeglądarki dają go tylko pod adresem `localhost`/`127.0.0.1` albo przez HTTPS.
- Klucze API (patrz niżej). Wywołania modeli są płatne według cennika dostawcy i obciążają Twoje konto.

## Klucze API: co jest obowiązkowe, a co opcjonalne

| Zmienna | Czy potrzebna | Do czego |
|---|---|---|
| `OPENAI_API_KEY` | zalecana (domyślny dostawca) | asystent (`PROVIDER=openai`), rozpoznawanie i synteza mowy, tłumaczenie rozmowy na inne języki |
| `ELEVENLABS_API_KEY` | opcjonalna | lepszy polski głos i rozpoznawanie mowy; bez klucza albo po błędzie serwer używa OpenAI |
| `ANTHROPIC_API_KEY` | opcjonalna | asystent na modelu Claude (`PROVIDER=anthropic`) |
| `MODEL_API_KEY` | opcjonalna | klucz do API zgodnego z OpenAI (`PROVIDER=zgodny`), jeśli serwer modelu go wymaga |

Co działa bez kluczy:

- **Bez żadnego klucza** aplikacja się uruchomi w trybie skryptowym, tak jak na stronie: gotowe scenariusze, bez asystenta i bez głosu.
- **Tylko `OPENAI_API_KEY`**: wszystko (asystent, głos, tłumaczenie rozmowy).
- **Tylko `ANTHROPIC_API_KEY` z `PROVIDER=anthropic`**: asystent działa po polsku, ale bez głosu i bez tłumaczenia rozmowy na inne języki (interfejs dalej jest tłumaczony ze słowników).
- **Tylko model zgodny z OpenAI (`PROVIDER=zgodny`)**: jak wyżej, asystent tak, głos i tłumaczenie rozmowy nie.

Moduł **Asystent Formalności** może korzystać z polskiego modelu Bielik przez Fabryka AI (`DOC_AI_BASE_URL=https://fabryka.ai/v1`, `DOC_AI_MODEL=bielik-11b-v3`). Klucz ustaw w lokalnym pliku `.env` jako `DOC_AI_API_KEY`; serwer wczytuje go przy starcie i nie wysyła do przeglądarki. Darmowy plan API jest przeznaczony do testów zgodności (10 zgłoszeń dziennie) i może przechowywać treść do 30 dni. Nie przesyłaj tam prawdziwych pism zawierających dane osobowe. Do odczytu PDF-ów i zdjęć z Bielikiem potrzebne są zależności z `requirements-doc-ai.txt` oraz Tesseract OCR z językiem polskim. W przeglądarce aplikacja przechowuje lokalną kopię dokumentu do ponownej analizy.

Na macOS, gdy zmiennej nie ma, serwer próbuje jeszcze odczytać klucz z pęku kluczy (pozycje `openai_api_key`,
`elevenlabs_api_key`, `anthropic_api_key`). Na Linuksie i w Dockerze liczą się tylko zmienne środowiskowe.

## Uruchomienie lokalne

```bash
cd mobywatel-ai
export OPENAI_API_KEY="..."          # Twój klucz; pozostałe zmienne opcjonalnie
python3 serwer/server.py             # albo: python3 serwer/server.py 8080
```

Otwórz http://127.0.0.1:8790/aplikacja (adres `/` też pokazuje aplikację, `/komputer` to ekran „komputera” do przekazywania danych znakiem).

Możesz też trzymać ustawienia w pliku: `cp .env.example .env`, uzupełnij i uruchom `set -a; . ./.env; set +a; python3 serwer/server.py`.

## Uruchomienie w Dockerze

```bash
cd mobywatel-ai
cp .env.example .env                 # uzupełnij klucze
docker compose up --build
```

Aplikacja będzie pod http://127.0.0.1:8790/aplikacja. Bez Compose:
`docker build -t mobywatel-ai . && docker run --rm --env-file .env -p 127.0.0.1:8790:8790 mobywatel-ai`.

## Ustawienia (zmienne środowiskowe)

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `PROVIDER` | `openai` | dostawca modelu rozmowy: `openai`, `anthropic` albo `zgodny` |
| `OPENAI_MODEL` | `gpt-6-luna` | model asystenta przy `PROVIDER=openai` (API Responses) |
| `OPENAI_TIER`, `OPENAI_EFFORT` | `fast`, `low` | poziom usługi i wysiłek rozumowania; gdy konto ich nie obsługuje, serwer ponawia zapytanie bez nich |
| `MODEL` | | model asystenta przy `PROVIDER=zgodny` (wymagany) albo pierwszy model do wypróbowania przy `PROVIDER=anthropic` |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | adres API zgodnego z OpenAI przy `PROVIDER=zgodny` |
| `MODEL_MAX_TOKENS`, `MODEL_TIMEOUT` | `1500`, `120` | limit długości odpowiedzi i czas oczekiwania (s) przy `PROVIDER=zgodny` |
| `TLUMACZ_MODEL` | `gpt-6-luna` | model OpenAI do tłumaczenia rozmowy na język interfejsu |
| `STT_MODEL`, `TTS_MODEL`, `TTS_VOICE` | `gpt-4o-mini-transcribe`, `gpt-4o-mini-tts`, `coral` | mowa przez OpenAI |
| `EL_VOICE`, `EL_TTS_MODEL`, `EL_STT_MODEL` | głos z biblioteki ElevenLabs, `eleven_flash_v2_5`, `scribe_v2` | mowa przez ElevenLabs; wybrany głos może wymagać płatnego planu, wtedy ustaw własny `EL_VOICE` |
| `HOST`, `PORT` | `127.0.0.1`, `8790` | adres i port serwera (w Dockerze `HOST=0.0.0.0`) |
| `AGENT_LOG` | `serwer/agent.log` | plik dziennika |

Nazwy modeli mogą się zmieniać u dostawców: jeśli domyślny model nie jest dostępny na Twoim koncie, ustaw własny.

## Polskie modele (Bielik, PLLuM i inne)

Asystenta można podpiąć do dowolnego API zgodnego z OpenAI Chat Completions (`/v1/chat/completions`), na przykład
do polskiego modelu uruchomionego lokalnie (vLLM, Ollama) albo u dostawcy chmurowego:

```bash
export PROVIDER=zgodny
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"   # adres serwera modelu (wzór; vLLM domyślnie: port 8000, Ollama: http://127.0.0.1:11434/v1)
export MODEL="<nazwa-modelu-na-tym-serwerze>"
export MODEL_API_KEY="..."                         # tylko jeśli serwer wymaga klucza
python3 serwer/server.py
```

W Dockerze serwer modelu działający na Twoim komputerze jest pod adresem `http://host.docker.internal:<port>/v1`.

Zastrzeżenia, zanim zaczniesz:

- Asystent działa przez **wywoływanie narzędzi** (tool calling): ma do dyspozycji kilkadziesiąt narzędzi i sam decyduje, które wywołać.
  Model i serwer muszą to obsługiwać (w vLLM trzeba włączyć automatyczny wybór narzędzi i parser wywołań właściwy dla modelu, zgodnie z dokumentacją).
  Model bez tej obsługi będzie tylko rozmawiał, bez sprawdzania danych i bez załatwiania spraw.
- Opisy narzędzi i instrukcje zajmują sporo kontekstu (kilkanaście tysięcy tokenów), więc model potrzebuje odpowiednio dużego okna kontekstu.
- Instrukcje i narzędzia były dopracowywane pod modele OpenAI i Anthropic. Na innych modelach jakość rozmów,
  trafność wyboru narzędzi i polszczyzna mogą być wyraźnie inne, w obie strony.
- Przy `PROVIDER=zgodny` przez wskazane API idzie tylko rozmowa z asystentem. Głos i tłumaczenie rozmowy dalej korzystają z OpenAI,
  jeśli podasz `OPENAI_API_KEY`, a bez tego klucza są wyłączone.

## Bezpieczeństwo i prywatność

- Serwer nie ma logowania ani limitów. Każdy, kto dostanie się do jego adresu, korzysta z Twoich kluczy API.
  Domyślnie słucha tylko na `127.0.0.1`, a `docker-compose.yml` wystawia port tylko lokalnie. Nie wystawiaj go do internetu bez własnej ochrony.
- Serwer zapisuje dziennik (`serwer/agent.log`): wiadomości wpisane do asystenta, rozpoznany tekst nagrań, użyte narzędzia i czasy odpowiedzi.
  Nagrania głosu nie są zapisywane na dysku, ale trafiają do dostawcy rozpoznawania mowy.
- Treść rozmów trafia do wybranego dostawcy modelu na jego zasadach.

## Licencja

Kod prototypu (pliki `.py`, `.js`, `.html`, `.css`, słowniki interfejsu i pliki konfiguracyjne) jest udostępniony na licencji MIT.
Pełny tekst jest w pliku `LICENSE`. Możesz go używać, zmieniać i rozpowszechniać, także komercyjnie,
pod warunkiem zachowania informacji o autorze i treści licencji.

Licencja MIT nie obejmuje:
- godła Rzeczypospolitej Polskiej, nazwy, logo i oznaczeń mObywatela ani wyglądu dokumentów
  (m.in. `mockup/assets/icon-mobywatel.svg`, `logo-mobywatel*`, `card-*`, `strip-*`, `mdowod-ekran.png`).
  Są w prototypie wyłącznie w celach pokazowych, a ich użycie podlega odrębnym przepisom i prawom ich właścicieli;
- zdjęć osób z pokazu (`mockup/assets/foto-*.jpg`);
- opisów usług w `serwer/wiedza/`, które pochodzą z serwisu gov.pl. Przy ich ponownym wykorzystaniu sprawdź warunki podane na gov.pl.

Osoby i dane w prototypie są fikcyjne. Projekt nie jest usługą administracji publicznej ani oficjalną aplikacją mObywatel.
