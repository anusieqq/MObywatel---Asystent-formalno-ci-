# -*- coding: utf-8 -*-
"""Pętla agenta: Claude (Haiku) + narzędzia. Bezstanowa: klient przechowuje historię rozmowy i stan świata."""
import json, os, re, time, copy, urllib.request, urllib.error, html
import dane, akcje, persony, tlumacz, threading
_JEZ = threading.local()
from narzedzia import WSZYSTKIE, NAZWY_ODCZYTOW, NAZWY_AKCJI, NAZWY_UI, NAZWY_KLIENT

MODELE = [m for m in [os.environ.get('MODEL'), 'claude-haiku-5-5', 'claude-haiku-4-5'] if m]  # dla PROVIDER=anthropic
_model_ok = None
DNI = ['poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela']

SYSTEM = """Jesteś asystentem w aplikacji mObywatel. Rozmawiasz z {zalogowana}: {kto}, PESEL {pesel}, {okolica} (tożsamość potwierdzona mDowodem). Dziś jest {dzis} ({dzien}).{meski}

Działasz na prawdziwych (w tej wersji: demonstracyjnych) danych z rejestrów państwowych przez narzędzia i załatwiasz sprawy w imieniu {dop}. Różnisz się od czatbota z bazą wiedzy tym, że sprawdzasz dane i wykonujesz usługi.

Zasady:
- Pisz wyłącznie po polsku, poprawną polszczyzną i alfabetem łacińskim. Nigdy nie wstawiaj słów z innych języków (np. rosyjskich czy angielskich). Pisz krótko i ciepło: 1–3 zdania w wiadomości. Zwracaj się na „Ty” w formie {forma}. Bez list, nagłówków i tabel: dane pokazują karty w aplikacji. Ważne wartości możesz wyróżnić **pogrubieniem**.
- Dane bierz WYŁĄCZNIE z narzędzi. Nie zgaduj numerów, dat ani kwot. Gdy czegoś brakuje, zapytaj.
- Karta z danymi z narzędzia jest widoczna dla użytkowniczki. Nie powtarzaj wszystkich jej wartości, tylko skomentuj najważniejsze lub zaproponuj krok.
- Każda czynność ze skutkiem prawnym lub finansowym idzie przez narzędzie akcji. Aplikacja sama pokaże kartę potwierdzenia z Face ID, więc NIE pytaj w tekście „czy potwierdzasz?”. Gdy masz komplet danych, od razu wywołaj akcję. Pytaj tylko o brakujące dane albo o wybór, którego nie da się ustalić z rejestrów.
- Gdy brakuje szczegółu, który ma rozsądną wartość domyślną, przyjmij ją i pokaż na karcie potwierdzenia zamiast pytać: urząd do odcisków palców i odbioru dowodu to urząd najbliżej miejsca, gdzie mieszka (może wybrać dowolny w Polsce), odpis aktu elektronicznie do skrzynki e-Doręczeń, płatność BLIK (Apple Pay, Google Pay lub karta tylko tam, gdzie gmina je udostępnia). Miejsce zgłoszenia (sanepid, GIOŚ) bierzesz z jej słów; GPS przyjmij tylko, gdy mówi o miejscu, w którym jest teraz. Użytkowniczka może to zmienić, anulując kartę. Wyjątki, o które zawsze pytasz: imię dziecka (najwyżej dwa imiona, w pełnej formie, nie zdrobnienie: Zofia, nie Zosia), nazwa firmy i forma opodatkowania (skala, liniowy, ryczałt), wybór terminu, a przy kilku pojazdach: którego dotyczy sprawa. Opis zgłoszenia (sanepid, GIOŚ, CERT, internet) bierzesz z jej słów, nie pytaj o więcej szczegółów.
- Jedna akcja naraz. Po wyniku krótko powiedz, co się stało, i zaproponuj sensowny następny krok (zaproponuj_odpowiedzi). Nigdy nie wywołuj kolejnej czynności, o którą użytkowniczka nie poprosiła, zanim się nie zgodzi.
- Gdy akcja zwraca błąd z wyjaśnieniem (np. sprawa wymaga wizyty, termin jeszcze nie biegnie, dokument jest unieważniony), nie ponawiaj jej: przekaż to własnymi słowami i zaproponuj, co da się zrobić (np. gdzie_zalatwic, przypomnienie).
- Prawie każdą odpowiedź kończ wywołaniem zaproponuj_odpowiedzi z 2–4 krótkimi opcjami: gdy pytasz o wybór (np. termin, wariant), gdy proponujesz coś zrobić („Mogę…”), gdy sprawa ma naturalny następny krok. Pomiń je tylko, gdy sprawa jest zamknięta albo pytasz o dane do wpisania (imię, numer). Wybór kilku pozycji naraz: wybor_wielokrotny.
- Gdy użytkowniczka kończy rozmowę („dziękuję, to wszystko”, „nic więcej”, „do widzenia”, inne pożegnanie), ZAWSZE w tej samej odpowiedzi napisz jedno krótkie zdanie pożegnania i wywołaj narzędzie zakoncz_rozmowe (bez zaproponuj_odpowiedzi). Bez tego mikrofon dalej słucha. Samo „dziękuję” po wykonanej sprawie, bez sygnału końca, to jeszcze nie koniec.
- Nie pisz o tym, że coś „wyświetliłaś” albo o przyciskach. Nie używaj długich myślników (—), zamiast nich przecinki lub kropki.
- Myśl jak dobry urzędnik, który zna całą sprawę:
  Zgubiony portfel: zapytaj, co w nim było i czy portfel może się znaleźć. Słowa: „zastrzec” to wpis w bankach (System Dokumenty Zastrzeżone, cofniesz tutaj), „zablokować” to blokada dowodu na 14 dni (odblokujesz tutaj, po 14 dniach bez odblokowania dowód zostanie unieważniony), „unieważnić” to na zawsze. Gdy może się znaleźć: zaproponuj zastrzeżenie dowodu i paszportu w bankach (zastrzez_dokumenty) i blokadę dowodu (zawies_dowod), oba da się cofnąć; jedno po drugim, każde po jej zgodzie; PESEL wtedy nie zastrzega się sam, możesz go zaproponować osobno. Gdy przepadł albo został skradziony: zastrzeż i unieważnij (zastrzez_dokumenty z uniewaznij=true), powiedz, że tego nie da się cofnąć, a PESEL zastrzeże się sam, więc go nie proponuj. Potem zaproponuj wniosek o nowy dowód. Prawa jazdy nie zastrzeżesz ani nie unieważnisz: to wniosek o wtórnik za 100 zł w wydziale komunikacji (gdzie_zalatwic). Karty płatnicze zastrzega bank, nie Ty: w jego aplikacji, na infolinii albo pod numerem +48 828 828 828, jeśli bank jest w systemie Zastrzegam.pl; zastrzeżonej karty bank nie odblokuje, wyda nową. Przy kradzieży doradź zgłoszenie na policji. Gdy dokument się znajdzie: zastrzeżenie w bankach cofniesz (cofnij_zastrzezenie_dokumentu), blokadę zdejmiesz (odwies_dowod), unieważnionego nie: powiedz, że jest już unieważniony, trzeba go oddać w dowolnym urzędzie gminy, a nowy wniosek złożysz tutaj.
  Dowód osobisty: wniosek wyślesz stąd, ale w ciągu 30 dni trzeba pójść do urzędu na odciski palców i wzór podpisu, a dowód odbiera się tam osobiście, do 30 dni po wizycie (dziecko poniżej 12 lat: bez odcisków, przy odbiorze dziecko od 5 lat). Powiedz to, zanim wywołasz akcję, a po wyniku zaproponuj przypomnienie o wizycie.
  Paszport: online złożysz tylko wniosek dla dziecka poniżej 12 lat (wniosek_paszport; zgoda drugiego rodzica, odbiór z dzieckiem od 5 lat). Dorosły, dziecko od 12 lat i paszport tymczasowy: tylko osobiście w punkcie paszportowym (gdzie_zalatwic), potem zaproponuj przypomnienie i listę do zabrania.
  PESEL: gdy jest już zastrzeżony, nie zastrzegaj go ponownie, pokaż status. Zastrzeżenie nie blokuje lekarza, apteki, bankomatu ani urzędu; bank musi je sprawdzić przed kredytem.
  Kupno auta: historia pojazdu (numer rejestracyjny, VIN i data pierwszej rejestracji; gdy ich brak, poproś o nie albo o zdjęcie dowodu rejestracyjnego od sprzedającego), OC (polisa sprzedającego przechodzi na Ciebie i nie przedłuży się sama), czerwone flagi, umowa (podpis zaufany lub osobisty obu stron), PCC-3: 2% wartości rynkowej w 14 dni, bez podatku przy wartości do 1000 zł albo zakupie na fakturę od firmy. Rejestracja w 30 dni w wydziale komunikacji, tablice i dowód rejestracyjny odbiera się osobiście; nie obiecuj rejestracji w aplikacji.
  Narodziny: gratulacje, potem zgłoszenie urodzenia (21 dni od wystawienia karty urodzenia; zgłasza mama albo tata, a tata, który nie jest mężem mamy, tylko po uznaniu ojcostwa). PESEL i odpis aktu przychodzą zwykle następnego dnia roboczego. Potem zaproponuj 800+ (wniosek w ciągu 3 miesięcy od urodzenia daje świadczenie od dnia urodzenia). Przypomnij, że dziecko do ubezpieczenia zdrowotnego zgłasza pracodawca albo sam rodzic w eZUS, w ciągu 7 dni. Przy trzecim dziecku albo gdy rodzina ma już KDR, zaproponuj kartę dla dziecka (gdzie_zalatwic).
  Stłuczka lub wypadek z udziałem kierowców: najpierw zapytaj, czy ktoś jest ranny; jeśli tak, każ dzwonić pod 112 i nie spisuj oświadczenia. mStłuczka działa, gdy oboje macie mObywatela, zgadzacie się, kto jest sprawcą, i oba auta mają polską rejestrację; jeśli nie, spiszcie oświadczenie na papierze albo wezwijcie policję. Gdy sprawcą jest użytkowniczka, szkodę zgłasza druga strona. Gdy ktoś podaje numer rejestracyjny auta, które uszkodziło jej samochód, od razu sprawdź jego OC.
  Podejrzany SMS: analiza, ostrzeżenie, pytanie, czy podała dane, zgłoszenie strony z linku do CERT Polska (zglos_incydent_cert), a sam SMS niech prześle na bezpłatny numer 8080. Mów, że domena jest na Liście Ostrzeżeń CERT, tylko gdy narzędzie to podaje. Jeśli podała dane karty, niech od razu dzwoni do banku; jeśli dane dowodu, zaproponuj unieważnienie dowodu (PESEL zastrzeże się sam).
  Płatności: tutaj płacisz tylko podatki i opłaty lokalne z ePłatności. Składek ZUS, mandatów i podatku w gminie spoza ePłatności nie zapłacisz tutaj; powiedz, gdzie i jak to zrobić (podają to naleznosci i wynik akcji) i zaproponuj przypomnienie.
  Firma: zapytaj o formę opodatkowania, a po wniosku przypomnij, że do ubezpieczeń w ZUS zgłasza się w 7 dni na biznes.gov.pl, a VAT-R składa osobno.
  Głosowanie w innym miejscu: jednorazowo zmienisz je od 44. do 3. dnia przed wyborami, a wybory do Sejmu jeszcze nie są zarządzone, więc zaproponuj przypomnienie. Jeśli mieszka w tej gminie na stałe bez meldunku, możesz już teraz złożyć zmianę stałego obwodu (zmien_miejsce_glosowania, rodzaj=staly; urząd ma 5 dni).
  Podróż: w Odyseuszu dopisujesz dzieci, dorośli zgłaszają się sami; zaproponuj dodanie kraju do obserwowanych. Nie mów, że w kraju nie ma ostrzeżeń, jeśli narzędzie tego nie podaje.
  Dane kontaktowe: po zmianie telefonu lub e-maila poproś o kod z SMS-a lub e-maila i wywołaj akcję ponownie z kodem.
  Ulgi z legitymacji studenckiej: mów tylko o ustawowej uldze kolejowej 51% do 26 lat; resztę ustala przewoźnik lub miasto.
- Procedury, opłaty, terminy, wymagane dokumenty i to, co trzeba zrobić osobiście, bierz z karty_uslugi (oficjalne karty gov.pl). Sprawdź ją, zanim powiesz, jak, gdzie albo czy da się coś załatwić, i trzymaj się jej treści. Gdy karta mówi, że trzeba iść do urzędu (np. odciski palców do dowodu, odbiór dokumentu, tablice rejestracyjne), powiedz to wprost w pierwszym zdaniu i nie obiecuj, że załatwisz to w aplikacji. Gdy karty brak, nie zgaduj: odeślij do gov.pl albo właściwego urzędu.
- Załatwiasz tylko to, na co masz narzędzia. Gdy sprawy nie zrobisz w tej aplikacji, od razu wywołaj gdzie_zalatwic i w pierwszym zdaniu powiedz, gdzie ją załatwić: online na gov.pl lub w innym oficjalnym serwisie (zameldowanie, wymeldowanie, zmiana nazwiska przez e-Doręczenia, Karta Dużej Rodziny na empatia.gov.pl, roczny PIT w Twoim e-PIT, do którego zalogujesz się mObywatelem) albo w urzędzie (ślub, zgłoszenie zgonu, rejestracja pojazdu, prawo jazdy, paszport dla dorosłego). Nie mów, że czegoś nie da się zrobić przez internet, jeśli karta podaje drogę online. Nie zbieraj danych do takiej sprawy i nie udawaj, że ją przygotowujesz. Możesz zaproponować to, co w aplikacji pomoże (np. przypomnienie albo sprawdzenie danych).
- Nie interpretujesz wiążąco przepisów. W sprawach spornych lub nietypowych kieruj do właściwego urzędu. Nie udzielaj porad inwestycyjnych ani medycznych.
- Prośby spoza spraw urzędowych (wiersze, opowiadania, przepisy kulinarne, zadania szkolne, opinie polityczne) uprzejmie odmawiaj jednym zdaniem i powiedz, w czym możesz pomóc. Nie spełniaj ich nawet częściowo.
- Gdy użytkowniczka prosi o pokazanie dokumentu, użyj pokaz_dokument.
- Przekazywanie danych (usługa Potwierdź swoje dane; w tej wersji znak mObywatela zamiast kodu QR) działa jednym skanerem: kto skanuje znak mObywatela, ten przekazuje swoje dane właścicielowi znaku, a zakres danych ustala właściciel znaku. Gdy ktoś inny (strona na komputerze, wypożyczalnia, urzędnik, kasjerka) chce dostać JEJ dane, użyj przekaz_dane: ona zeskanuje znak odbiorcy i potwierdzi Face ID. Gdy ONA chce dostać lub sprawdzić dane innej osoby, użyj przyjmij_dane: pokażesz jej znak, a tamta osoba zeskanuje go u siebie. Przy stłuczce dane drugiego kierowcy pobierasz tak samo (cel=mstluczka). Przed wywołaniem napisz jedno krótkie zdanie, co się zaraz stanie. Po wyniku krótko podsumuj.
- Wiadomość zaczynająca się od [głos] była powiedziana na głos, a Twoje odpowiedzi w tej rozmowie są czytane przez syntezator: pisz krótko, pełnymi zdaniami, bez skrótów i symboli (zamiast „r.” pisz „roku”, zamiast „zł” pisz „złotych”), daty z nazwą miesiąca (29 października), ale liczby i numery zostaw cyframi. Najważniejszą informację z karty powiedz w tekście. Przycisków nie słychać: zanim wywołasz zaproponuj_odpowiedzi albo wybor_wielokrotny, zawsze zadaj pytanie w tekście.
- Wiadomość zaczynająca się od [zdjęcie] zawiera wynik odczytu zdjęcia zrobionego aparatem."""

def system_prompt():
    p = persony.P(); k = p['plec'] == 'K'
    s = SYSTEM.format(dzis=dane.pl(dane.DZIS), dzien=DNI[dane.DZIS.weekday()], kto=p['osoba']['imie'] + ' ' + p['osoba']['nazwisko'], pesel=p['osoba']['pesel'],
        okolica=p['okolica'], dop=p['dop'], zalogowana='zalogowaną użytkowniczką' if k else 'zalogowanym użytkownikiem',
        forma='żeńskiej (np. „zgubiłaś”)' if k else 'męskiej (np. „zgubiłeś”)',
        meski='' if k else '\nUWAGA: rozmawiasz z mężczyzną. Gdzie poniższe zasady i opisy narzędzi mówią „użytkowniczka”, „ona”, „jej”, chodzi o niego. Zawsze używaj form męskich.')
    return s

def klucz(nazwa, env):
    if os.environ.get(env): return os.environ[env]
    try:
        import subprocess
        return subprocess.check_output(['security', 'find-generic-password', '-s', nazwa, '-w'], stderr=subprocess.DEVNULL).decode().strip() or None
    except Exception:
        return None

def bez_myslnikow(t):
    return re.sub(r'\s*—\s*', ', ', re.sub(r'\s+–\s+', ', ', t)).replace(', ,', ',').replace(', .', '.')

def md(t):
    t = html.escape(bez_myslnikow(t.strip()), quote=False)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?m)^\s*[-•]\s+', '• ', t)
    return t.replace('\n\n', '<br><br>').replace('\n', '<br>')

class BladAPI(Exception): pass

def claude(messages, key, log):
    global _model_ok
    tools = copy.deepcopy(WSZYSTKIE)
    tools[-1]['cache_control'] = {'type': 'ephemeral'}
    modele = [_model_ok] if _model_ok else MODELE
    last = None
    for model in modele:
        body = dict(model=model, max_tokens=1200, system=[{'type': 'text', 'text': system_prompt(), 'cache_control': {'type': 'ephemeral'}}],
                    tools=tools, tool_choice={'type': 'auto', 'disable_parallel_tool_use': True}, messages=messages)
        for proba in range(4):
            req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=json.dumps(body).encode(),
                headers={'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    out = json.loads(r.read())
                _model_ok = model
                log(dict(t='llm', model=model, ms=int((time.time() - t0) * 1000), usage=out.get('usage'), stop=out.get('stop_reason')))
                return out
            except urllib.error.HTTPError as e:
                txt = e.read().decode('utf-8', 'replace')
                last = '%s %s' % (e.code, txt[:300])
                if e.code == 404 or (e.code == 400 and 'model' in txt.lower() and len(modele) > 1):
                    break  # spróbuj kolejnego modelu
                if e.code in (429, 500, 502, 503, 529):
                    time.sleep(1.5 * (proba + 1)); continue
                raise BladAPI(last)
            except Exception as e:
                last = str(e); time.sleep(1.0 * (proba + 1))
    raise BladAPI(last or 'brak odpowiedzi')

PROVIDER = os.environ.get('PROVIDER', 'openai')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-6-luna')
OPENAI_TIER = os.environ.get('OPENAI_TIER', 'fast')
OPENAI_EFFORT = os.environ.get('OPENAI_EFFORT', 'low')

def do_responses(messages):
    """Historia w formacie bloków (text/tool_use/tool_result) -> elementy wejścia Responses API."""
    items = []
    for m in messages:
        c = m['content']
        if isinstance(c, str):
            items.append({'role': m['role'], 'content': c}); continue
        for b in c:
            t = b.get('type')
            if t == 'text' and b.get('text', '').strip():
                items.append({'role': m['role'], 'content': b['text']})
            elif t == 'tool_use':
                items.append({'type': 'function_call', 'call_id': b['id'], 'name': b['name'], 'arguments': json.dumps(b.get('input') or {}, ensure_ascii=False)})
            elif t == 'tool_result':
                out = b.get('content')
                items.append({'type': 'function_call_output', 'call_id': b['tool_use_id'], 'output': out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)})
    return items

def openai(messages, key, log):
    tools = [{'type': 'function', 'name': t['name'], 'description': t['description'], 'parameters': t['input_schema'], 'strict': False} for t in WSZYSTKIE]
    body = dict(model=OPENAI_MODEL, instructions=system_prompt(), input=do_responses(messages), tools=tools, parallel_tool_calls=False,
                max_output_tokens=1500, store=False, prompt_cache_key='mobywatel-agent-' + persony.P()['id'])
    if OPENAI_TIER: body['service_tier'] = OPENAI_TIER
    if OPENAI_EFFORT: body['reasoning'] = {'effort': OPENAI_EFFORT}
    last = None
    for proba in range(4):
        req = urllib.request.Request('https://api.openai.com/v1/responses', data=json.dumps(body).encode(),
            headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read())
        except urllib.error.HTTPError as e:
            txt = e.read().decode('utf-8', 'replace'); last = '%s %s' % (e.code, txt[:400])
            if e.code in (429, 500, 502, 503) and proba < 3:
                time.sleep(1.5 * (proba + 1)); continue
            if e.code == 400 and 'service_tier' in txt and body.get('service_tier'):
                body.pop('service_tier'); continue
            if e.code == 400 and 'reasoning' in txt and body.get('reasoning'):
                body.pop('reasoning'); continue
            raise BladAPI(last)
        except Exception as e:
            last = str(e); time.sleep(1.0 * (proba + 1)); continue
        content = []
        for it in out.get('output', []):
            if it.get('type') == 'message':
                txt = ''.join(p.get('text', '') for p in it.get('content', []) if p.get('type') in ('output_text', 'text'))
                if txt.strip(): content.append({'type': 'text', 'text': txt})
            elif it.get('type') == 'function_call':
                try: args = json.loads(it.get('arguments') or '{}')
                except Exception: args = {}
                content.append({'type': 'tool_use', 'id': it.get('call_id') or it.get('id'), 'name': it.get('name'), 'input': args})
        u = out.get('usage') or {}
        log(dict(t='llm', model=out.get('model', OPENAI_MODEL), tier=out.get('service_tier'), ms=int((time.time() - t0) * 1000),
                 usage=dict(input=u.get('input_tokens'), cached=(u.get('input_tokens_details') or {}).get('cached_tokens'), output=u.get('output_tokens'),
                            reasoning=(u.get('output_tokens_details') or {}).get('reasoning_tokens'))))
        return dict(content=content, stop_reason='tool_use' if any(b['type'] == 'tool_use' for b in content) else 'end_turn')
    raise BladAPI(last or 'brak odpowiedzi')

# --- PROVIDER=zgodny (dodane w paczce do pobrania): dowolne API zgodne z OpenAI Chat Completions ---
# np. lokalny vLLM albo Ollama z polskim modelem, albo dostawca chmurowy. Dotyczy tylko rozmowy z asystentem:
# rozpoznawanie i synteza mowy oraz tłumaczenie rozmowy dalej idą przez OpenAI (OPENAI_API_KEY), jeśli jest klucz.
OPENAI_BAZA_DOMYSLNA = 'https://api.openai.com/v1'
ZGODNY_BAZA = (os.environ.get('OPENAI_BASE_URL') or OPENAI_BAZA_DOMYSLNA).rstrip('/')
ZGODNY_MODEL = (os.environ.get('MODEL') or '') if PROVIDER == 'zgodny' else ''
ZGODNY_MAX = int(os.environ.get('MODEL_MAX_TOKENS') or 1500)
ZGODNY_TIMEOUT = int(os.environ.get('MODEL_TIMEOUT') or 120)
MYSLI = re.compile(r'(?s)<think>.*?</think>\s*')

def _id9(x):
    """Stały, 9-znakowy identyfikator wywołania (część szablonów czatu wymaga krótkich identyfikatorów)."""
    import hashlib
    return hashlib.sha1(str(x).encode()).hexdigest()[:9]

def do_chat(messages):
    """Historia w formacie bloków (text/tool_use/tool_result) -> wiadomości Chat Completions."""
    out = [{'role': 'system', 'content': system_prompt()}]
    for m in messages:
        c = m['content']
        if isinstance(c, str):
            out.append({'role': m['role'], 'content': c}); continue
        txt = '\n\n'.join(b.get('text', '') for b in c if b.get('type') == 'text' and b.get('text', '').strip())
        if m['role'] == 'assistant':
            calls = [{'id': _id9(b['id']), 'type': 'function', 'function': {'name': b['name'], 'arguments': json.dumps(b.get('input') or {}, ensure_ascii=False)}}
                     for b in c if b.get('type') == 'tool_use']
            if txt or calls:
                msg = {'role': 'assistant', 'content': txt}
                if calls: msg['tool_calls'] = calls
                out.append(msg)
            continue
        for b in c:
            if b.get('type') == 'tool_result':
                o = b.get('content')
                out.append({'role': 'tool', 'tool_call_id': _id9(b['tool_use_id']), 'content': o if isinstance(o, str) else json.dumps(o, ensure_ascii=False)})
        if txt: out.append({'role': 'user', 'content': txt})
    return out

def zgodny(messages, key, log):
    if not ZGODNY_MODEL: raise BladAPI('PROVIDER=zgodny wymaga zmiennej MODEL')
    tools = [{'type': 'function', 'function': {'name': t['name'], 'description': t['description'], 'parameters': t['input_schema']}} for t in WSZYSTKIE]
    body = dict(model=ZGODNY_MODEL, messages=do_chat(messages), tools=tools, tool_choice='auto', parallel_tool_calls=False, max_tokens=ZGODNY_MAX)
    naglowki = {'Content-Type': 'application/json'}
    if key and key != 'bez-klucza': naglowki['Authorization'] = 'Bearer ' + key
    last = None
    for proba in range(4):
        req = urllib.request.Request(ZGODNY_BAZA + '/chat/completions', data=json.dumps(body).encode(), headers=naglowki)
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=ZGODNY_TIMEOUT) as r:
                out = json.loads(r.read())
        except urllib.error.HTTPError as e:
            txt = e.read().decode('utf-8', 'replace'); last = '%s %s' % (e.code, txt[:400])
            if e.code == 400 and 'parallel_tool_calls' in txt and 'parallel_tool_calls' in body:
                body.pop('parallel_tool_calls'); continue
            if e.code in (429, 500, 502, 503) and proba < 3:
                time.sleep(1.5 * (proba + 1)); continue
            raise BladAPI(last)
        except Exception as e:
            last = str(e); time.sleep(1.0 * (proba + 1)); continue
        msg = ((out.get('choices') or [{}])[0] or {}).get('message') or {}
        content = []
        txt = msg.get('content')
        if isinstance(txt, list): txt = ''.join(p.get('text', '') for p in txt if isinstance(p, dict))
        txt = MYSLI.sub('', txt or '').strip()
        if txt: content.append({'type': 'text', 'text': txt})
        for c in (msg.get('tool_calls') or [])[:1]:   # jedna czynność naraz, jak u pozostałych dostawców
            f = c.get('function') or {}
            a = f.get('arguments')
            if not isinstance(a, dict):
                try: a = json.loads(a or '{}')
                except Exception: a = {}
            content.append({'type': 'tool_use', 'id': c.get('id') or 'z%d' % int(time.time() * 1000), 'name': f.get('name'), 'input': a if isinstance(a, dict) else {}})
        u = out.get('usage') or {}
        log(dict(t='llm', model=out.get('model', ZGODNY_MODEL), ms=int((time.time() - t0) * 1000),
                 usage=dict(input=u.get('prompt_tokens'), output=u.get('completion_tokens'))))
        return dict(content=content, stop_reason='tool_use' if any(b['type'] == 'tool_use' for b in content) else 'end_turn')
    raise BladAPI(last or 'brak odpowiedzi')

def llm(messages, keys, log):
    if PROVIDER == 'anthropic': return claude(messages, keys['anthropic'], log)
    if PROVIDER == 'zgodny': return zgodny(messages, keys.get('zgodny'), log)
    return openai(messages, keys['openai'], log)

WYCIEK = re.compile(r'\s*(?:to=)?functions\.(\w+)\s*(\{.*?\})', re.S)
def napraw_wyciek(content):
    """Model czasem wypisuje wywołanie narzędzia w tekście (np. 'to=functions.x {...}'). Zamieniamy to na prawdziwe wywołanie."""
    out = []
    for b in content:
        if b['type'] != 'text' or 'functions.' not in b.get('text', ''):
            out.append(b); continue
        m = WYCIEK.search(b['text'])
        txt = b['text'][:m.start()].strip() if m else re.sub(r'(?s)\s*(?:to=)?functions\..*$', '', b['text']).strip()
        if txt: out.append(dict(type='text', text=txt))
        if m and not any(x['type'] == 'tool_use' for x in content):
            try:
                out.append(dict(type='tool_use', id='wyciek_%d' % int(time.time() * 1000), name=m.group(1), input=json.loads(m.group(2))))
            except Exception:
                pass
    return out

OBCE = re.compile('[\u0370-\u03ff\u0400-\u052f\u0590-\u06ff\u10a0-\u10ff\u3040-\u30ff\u4e00-\u9fff]')
def popraw_jezyk(text, keys, log):
    """Gdy model wtrąci obce słowo (np. cyrylicą), poprawiamy tekst osobnym, krótkim wywołaniem."""
    if not OBCE.search(text): return text
    try:
        if PROVIDER == 'openai':
            body = dict(model=OPENAI_MODEL, instructions='Popraw tekst na poprawną polszczyznę: każde słowo w obcym języku lub alfabecie zastąp właściwym polskim słowem. Nie zmieniaj sensu ani formatowania (**pogrubienia** zostaw). Zwróć wyłącznie poprawiony tekst.',
                        input=text, max_output_tokens=600, store=False, reasoning={'effort': 'low'})
            if OPENAI_TIER: body['service_tier'] = OPENAI_TIER
            req = urllib.request.Request('https://api.openai.com/v1/responses', data=json.dumps(body).encode(), headers={'Authorization': 'Bearer ' + keys['openai'], 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r: out = json.loads(r.read())
            fixed = ''.join(p.get('text', '') for it in out.get('output', []) if it.get('type') == 'message' for p in it.get('content', []) if p.get('type') in ('output_text', 'text')).strip()
        else:
            fixed = ''
        if fixed and not OBCE.search(fixed):
            log(dict(t='jezyk', przed=text, po=fixed)); return fixed
    except Exception as e:
        log(dict(t='jezyk_blad', msg=str(e)))
    for k_, v in {'Если': 'Jeśli', 'если': 'jeśli', 'или': 'lub', 'нет': 'nie', 'да': 'tak', 'но': 'ale', 'и': 'i'}.items():
        text = re.sub(r'(?<![\w])' + k_ + r'(?![\w])', v, text)
    return OBCE.sub('', text).replace('  ', ' ')

def napraw(messages):
    """Każdy tool_use musi mieć tool_result w następnej wiadomości użytkownika."""
    out = []
    for i, m in enumerate(messages):
        out.append(m)
        if m['role'] != 'assistant' or not isinstance(m['content'], list): continue
        ids = [b for b in m['content'] if b.get('type') == 'tool_use']
        if not ids: continue
        nxt = messages[i + 1] if i + 1 < len(messages) else None
        have = set()
        if nxt and isinstance(nxt['content'], list):
            have = {b.get('tool_use_id') for b in nxt['content'] if b.get('type') == 'tool_result'}
        brak = [b for b in ids if b['id'] not in have]
        if not brak or nxt is None: continue
        nowe = []
        for b in brak:
            if b['name'] in NAZWY_AKCJI: tr = 'Użytkowniczka nie potwierdziła tej czynności (NIE wykonano). Zamiast tego napisała wiadomość poniżej.'
            elif b['name'] in NAZWY_KLIENT: tr = 'Skaner zamknięto bez wyniku. Odpowiedź użytkowniczki poniżej.'
            else: tr = 'Wyświetlono. Odpowiedź użytkowniczki poniżej.'
            nowe.append({'type': 'tool_result', 'tool_use_id': b['id'], 'content': tr})
        c = nxt['content'] if isinstance(nxt['content'], list) else [{'type': 'text', 'text': nxt['content']}]
        messages[i + 1] = dict(nxt, content=nowe + c)
    return messages

def wykonaj_odczyt(name, a, stan):
    f = dane.READ.get(name)
    if not f: return dict(blad='nieznane narzędzie'), None
    try:
        return f(a, stan)
    except Exception as e:
        return dict(blad=str(e)), None

PREFIKS = re.compile(r'^(\[(?:głos|zdjęcie)\]\s*)')
KONIEC = re.compile(r'\b(to wszystko|to by było wszystko|nic więcej|do widzenia|do usłyszenia|na razie|pa,? pa|żegnaj|cześć!?$|kończ(ymy|my)?\b|zakończ)', re.I)
def run(messages, stan, confirm=None, keys=None, log=lambda x: None, osoba=None, jezyk='pl'):
    """Zwraca (messages, stan, events, czeka). osoba: id persony (persony.py), jezyk: kod języka interfejsu.
    Agent zawsze pracuje po polsku: wiadomość użytkownika tłumaczymy na polski (i tak zostaje w historii), a odpowiedzi, przyciski i karty na język interfejsu."""
    j = jezyk if jezyk in tlumacz.JEZYKI else 'pl'
    key = (keys or {}).get('openai')
    if j != 'pl' and messages and messages[-1].get('role') == 'user' and isinstance(messages[-1].get('content'), str) and not confirm \
            and not re.search(r'[ąęłśźżĄĘŁŚŹŻ]', PREFIKS.sub('', messages[-1]['content'])):   # wiadomość po polsku idzie bez tłumaczenia (prefiks [głos] ma „ł”)
        t0 = time.time(); txt = messages[-1]['content']; m = PREFIKS.match(txt); pre = m.group(1) if m else ''
        pl_txt = tlumacz.tlumacz_wolne([txt[len(pre):]], 'auto', 'pl', key)[0]
        messages[-1] = dict(messages[-1], content=pre + pl_txt)
        log(dict(t='tlumacz_wej', jezyk=j, ms=int((time.time() - t0) * 1000), przed=txt[:120], po=pl_txt[:120]))
    ostatnia = messages[-1]['content'] if messages and not confirm and isinstance(messages[-1].get('content'), str) else ''
    m, s, ev, cz = _run(messages, stan, confirm, keys, log, osoba)
    if not cz and ev and all(e.get('t') == 'text' for e in ev) and not ev[-1]['plain'].rstrip().endswith('?') and KONIEC.search(PREFIKS.sub('', ostatnia)):
        ev.append(dict(t='koniec')); cz = 'koniec'   # model pożegnał się bez zakoncz_rozmowe
        log(dict(t='koniec_auto'))
    dodaj_mowe(ev)
    if j != 'pl':
        t0 = time.time()
        wolne = [(e, 'md', None) for e in ev if e.get('t') == 'text'] + [(e, 'mow', None) for e in ev if e.get('mow')] \
              + [(e, 'opcje', i) for e in ev if e.get('t') in ('chips', 'multi') for i in range(len(e.get('opcje') or []))]
        teksty = [e[f] if i is None else e['opcje'][i] for e, f, i in wolne]
        wynik = {}
        def karty():
            try: tlumacz.tlumacz_zdarzenia(ev, j, key)
            except Exception as ex: log(dict(t='tlumacz_blad', msg=str(ex)))
        th = threading.Thread(target=karty); th.start()
        if teksty: wynik['t'] = tlumacz.tlumacz_wolne(teksty, 'pl', j, key)
        th.join()
        for (e, f, i), t in zip(wolne, wynik.get('t') or teksty):
            if f == 'md': e.update(md=t, html=md(t), plain=bez_myslnikow(re.sub(r'\*\*', '', t).strip()))
            elif f == 'mow': e['mow'] = t
            else: e['opcje'][i] = t
        for e in ev:
            if e.get('t') in ('chips', 'multi', 'text'): e['tl'] = 1
        log(dict(t='tlumacz_wyj', jezyk=j, ms=int((time.time() - t0) * 1000), n=len(teksty)))
    return m, s, ev, cz

def dodaj_mowe(ev):
    """Tryb głosowy czyta pole mow: przy karcie potwierdzenia i przy przyciskach, gdy w turze nie ma tekstu (inaczej asystent milczy)."""
    for e in ev:
        if e.get('t') == 'confirm':
            e['mow'] = (e['title'].rstrip('.') + '. ' if e.get('title') else '') + 'Sprawdź dane na karcie i potwierdź.'
    if any(e.get('t') == 'text' for e in ev): return
    for e in ev:
        o = [x.rstrip(' .!?') for x in e.get('opcje') or [] if x.strip()]
        if e.get('t') not in ('chips', 'multi') or not o: continue
        e['mow'] = ('Możesz wybrać kilka: ' + ', '.join(o) if e['t'] == 'multi' else 'Do wyboru: ' + (', '.join(o[:-1]) + ' albo ' + o[-1] if len(o) > 1 else o[0])) + '.'

def _run(messages, stan, confirm, keys, log, osoba):
    _JEZ.j = 'pl'
    persony.ustaw(osoba)
    stan = stan or dane.stan_poczatkowy()
    events = []
    if confirm:
        last = messages[-1] if messages else None
        tu = next((b for b in (last or {}).get('content', []) if isinstance(b, dict) and b.get('type') == 'tool_use' and b.get('id') == confirm.get('id')), None)
        if tu and tu['name'] in NAZWY_KLIENT:
            if confirm.get('ok'):
                res = json.dumps(dict(zakonczono=True, wynik=confirm.get('wynik')), ensure_ascii=False)
            else:
                res = 'Użytkowniczka zamknęła swój znak, dane od drugiej osoby nie dotarły.' if tu['name'] == 'przyjmij_dane' else 'Użytkowniczka zamknęła skaner bez przekazania danych.'
            log(dict(t='qr', name=tu['name'], ok=bool(confirm.get('ok'))))
            messages.append({'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': tu['id'], 'content': res}]})
        elif tu and tu['name'] in NAZWY_AKCJI:
            if confirm.get('ok'):
                d, karta = akcje.A[tu['name']]['wykonaj'](tu['input'], stan)
                events.append(dict(t='card', **karta))
                res = json.dumps(dict(wykonano=True, potwierdzono_face_id=True, wynik=d), ensure_ascii=False)
                log(dict(t='akcja', name=tu['name'], input=tu['input'], ok=True))
            else:
                res = 'Użytkowniczka anulowała na karcie potwierdzenia. NIE wykonano.'
                log(dict(t='akcja', name=tu['name'], ok=False))
            messages.append({'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': tu['id'], 'content': res}]})
    napraw(messages)
    po_akcji = bool(confirm)
    czeka = None
    for krok in range(10):
        out = llm(messages, keys, log)
        content = napraw_wyciek([b for b in out['content'] if b.get('type') in ('text', 'tool_use')])
        for b in content:
            if b['type'] == 'text': b['text'] = popraw_jezyk(b['text'], keys, log)
        content = [dict(type='text', text=b['text']) if b['type'] == 'text' else dict(type='tool_use', id=b['id'], name=b['name'], input=b.get('input') or {}) for b in content if b['type'] != 'text' or b['text'].strip()]
        if not content:
            messages.append({'role': 'assistant', 'content': [dict(type='text', text='(brak odpowiedzi)')]}); break
        messages.append({'role': 'assistant', 'content': content})
        wyniki = []
        for b in content:
            if b['type'] == 'text':
                events.append(dict(t='text', md=b['text'], html=md(b['text']), plain=bez_myslnikow(re.sub(r'\*\*', '', b['text']).strip())))
                continue
            n, a = b['name'], b['input']
            log(dict(t='tool', name=n, input=a))
            if n in NAZWY_ODCZYTOW:
                d, karta = wykonaj_odczyt(n, a, stan)
                if karta and a.get('pokaz_karte', True) is not False:
                    if karta.get('t') == 'qr':
                        events.append(dict(karta, t='qr'))
                    else:
                        events.append(dict(t='card', **karta))
                wyniki.append({'type': 'tool_result', 'tool_use_id': b['id'], 'content': json.dumps(d, ensure_ascii=False) + ('' if not karta else ' [karta wyświetlona]')})
            elif n == 'pokaz_dokument':
                events.append(dict(t='doc', id={'dowod': 'dowod', 'prawo_jazdy': 'pj', 'kdr': 'kdr', 'pojazd': 'auto', 'legitymacja': 'leg'}.get(a.get('dokument'), 'dowod')))
                wyniki.append({'type': 'tool_result', 'tool_use_id': b['id'], 'content': 'Dokument wyświetlony z przyciskiem Potwierdź swoje dane.'})
            elif n in NAZWY_KLIENT:
                events.append(dict(t='qrflow', id=b['id'], mode='scan' if n == 'przekaz_dane' else 'show', cel=a.get('cel') or 'tozsamosc', kto=a.get('kto'), dok=a.get('dokument')))
                czeka = 'qr'
            elif n == 'zakoncz_rozmowe':
                events.append(dict(t='koniec'))
                czeka = 'koniec'
            elif n in ('zaproponuj_odpowiedzi', 'wybor_wielokrotny'):
                opcje = [str(x) for x in (a.get('opcje') or [])][:6]
                events.append(dict(t='chips' if n == 'zaproponuj_odpowiedzi' else 'multi', opcje=opcje))
                czeka = 'odpowiedz'
            elif n in NAZWY_AKCJI and po_akcji:
                log(dict(t='blokada_lancucha', name=n))
                wyniki.append({'type': 'tool_result', 'tool_use_id': b['id'], 'is_error': True,
                               'content': 'NIE wykonano. Przed chwilą zakończyła się inna czynność. Najpierw krótko powiedz jej wynik i zapytaj, czy użytkowniczka chce tego kroku (zaproponuj_odpowiedzi). Kolejną czynność wywołaj dopiero po jej odpowiedzi.'})
            elif n in NAZWY_AKCJI:
                try:
                    karta = akcje.A[n]['podglad'](a, stan)
                except Exception as e:
                    wyniki.append({'type': 'tool_result', 'tool_use_id': b['id'], 'content': 'Błąd danych: %s' % e, 'is_error': True}); continue
                events.append(dict(t='confirm', id=b['id'], **karta))
                czeka = 'potwierdzenie'
            else:
                wyniki.append({'type': 'tool_result', 'tool_use_id': b['id'], 'content': 'Nieznane narzędzie', 'is_error': True})
        if czeka or out.get('stop_reason') != 'tool_use' or not wyniki:
            break
        messages.append({'role': 'user', 'content': wyniki})
    return messages, stan, events, czeka
