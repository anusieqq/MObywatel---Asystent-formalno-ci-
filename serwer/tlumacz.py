# -*- coding: utf-8 -*-
"""Wersje językowe: słowniki interfejsu (tłumaczone przez Claude, patrz ../tlumaczenia/README.md) i tłumaczenie rozmowy z asystentem w locie (tańszy model OpenAI).
Teksty są szablonami: liczby, daty i godziny zamieniamy na {0}, {1}…, więc „Za 11 dni, 29.10” i „Za 12 dni, 30.10” to jeden wpis.
Interfejsu nie tłumaczymy maszynowo: tekst bez tłumaczenia zostaje po polsku i trafia do rejestru _zrodla.json."""
import json, os, re, threading, time, urllib.request, sys
from concurrent.futures import ThreadPoolExecutor

# kod: (nazwa po angielsku dla modelu, nazwa własna do wyboru, kod mowy dla STT lub None)
JEZYKI = {
    'pl': ('Polish', 'Polski', 'pl'), 'en': ('English', 'English', 'en'), 'de': ('German', 'Deutsch', 'de'), 'fr': ('French', 'Français', 'fr'),
    'es': ('Spanish', 'Español', 'es'), 'it': ('Italian', 'Italiano', 'it'), 'pt': ('Portuguese (European)', 'Português', 'pt'),
    'nl': ('Dutch', 'Nederlands', 'nl'), 'cs': ('Czech', 'Čeština', 'cs'), 'sk': ('Slovak', 'Slovenčina', 'sk'), 'sl': ('Slovenian', 'Slovenščina', 'sl'),
    'hu': ('Hungarian', 'Magyar', 'hu'), 'ro': ('Romanian', 'Română', 'ro'), 'el': ('Greek', 'Ελληνικά', 'el'), 'sv': ('Swedish', 'Svenska', 'sv'),
    'uk': ('Ukrainian', 'Українська', 'uk'),
}
KAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'i18n')
os.makedirs(KAT, exist_ok=True)
NUM = re.compile(r'\d+(?:[.,:/]\d+)*')
LITERA = re.compile(r'[^\W\d_]', re.U)
_lock = threading.Lock()
_cache = {}
_lang_locks = {k: threading.Lock() for k in JEZYKI}

def szablon(s):
    nums = []
    def rep(m): nums.append(m.group(0)); return '{%d}' % (len(nums) - 1)
    return NUM.sub(rep, s), nums
def wypelnij(t, nums): return re.sub(r'\{(\d+)\}', lambda m: nums[int(m.group(1))] if int(m.group(1)) < len(nums) else m.group(0), t)
SKROTY = re.compile(r'\b(OC|PESEL|ZUS|KDR|UFG)\b')
def do_tlumaczenia(s): return bool(s and s.strip() and (SKROTY.search(s) or (LITERA.search(s) and re.search(r'[a-ząćęłńóśźż]', s))))

_mtime = {}
def slownik(lang):
    """Słownik języka; doczytuje zmiany z dysku (np. po tłumaczeniu wsadowym w innym procesie)."""
    with _lock:
        p = os.path.join(KAT, lang + '.json')
        try: mt = os.path.getmtime(p)
        except OSError: mt = None
        if lang not in _cache or (mt and mt != _mtime.get(lang)):
            try:
                d = json.load(open(p, encoding='utf-8'))
                if lang in _cache: d.update({k_: v for k_, v in _cache[lang].items() if k_ not in d})
                _cache[lang] = d
            except Exception: _cache.setdefault(lang, {})
            _mtime[lang] = mt
        return _cache[lang]
def _zapisz(lang):
    """Zapis z połączeniem z plikiem (serwer i tłumaczenie wsadowe mogą pisać równolegle)."""
    p = os.path.join(KAT, lang + '.json'); tmp = p + '.tmp.%d' % os.getpid()
    try:
        dysk = json.load(open(p, encoding='utf-8'))
        for k_, v in dysk.items(): _cache[lang].setdefault(k_, v)
    except Exception: pass
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(_cache[lang], f, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, p)
    try: _mtime[lang] = os.path.getmtime(p)
    except OSError: pass
def zrodla():
    try: return set(json.load(open(os.path.join(KAT, '_zrodla.json'), encoding='utf-8')))
    except Exception: return set()
def _dodaj_zrodla(xs):
    with _lock:
        z = zrodla(); n = len(z); z |= set(xs)
        if len(z) != n: json.dump(sorted(z), open(os.path.join(KAT, '_zrodla.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)


TLUMACZ_MODEL = os.environ.get('TLUMACZ_MODEL', 'gpt-6-luna')   # model tłumaczenia rozmowy (gpt-5.4-mini był tańszy, ale słabszy)
GLOS_KAT = os.environ.get('MOB_GLOSARIUSZ') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'glosariusz')
_glos = {}
def glosariusz(lang):
    """Skrót słowniczka języka do instrukcji tłumacza rozmowy (nazwy w oryginale, ustalone słowa, cztery pojęcia)."""
    if lang in _glos: return _glos[lang]
    try: g = json.load(open(os.path.join(GLOS_KAT, lang + '.json'), encoding='utf-8'))
    except Exception: _glos[lang] = ''; return ''
    nazwy = '; '.join(f'{k} ({v})' if v else k for k, v in g.get('nazwy', {}).items() if '/' not in k and ',' not in k)
    terminy = '; '.join(f'{k} = {v}' for k, v in g.get('terminy', {}).items())
    trzy = '; '.join(f'{k} = {v.get("bezokolicznik")} / {v.get("rzeczownik")} / {v.get("stan")}' for k, v in g.get('trzy', {}).items())
    _glos[lang] = (f'Keep these names in the original Latin form; at the first mention in a longer reply add the short explanation in parentheses: {nazwy}. '
                   f'Fixed terms (always use them): {terminy}. Four distinct concepts, never mix their words: {trzy}. ')
    return _glos[lang]

def przetlumacz(lang, teksty, key=None, zrodlo=True):
    """teksty: lista szablonów po polsku. Zwraca {szablon: tłumaczenie} tylko ze słownika. Braki trafiają do rejestru _zrodla.json."""
    if lang not in JEZYKI or lang == 'pl': return {}
    teksty = [t for t in dict.fromkeys(teksty) if do_tlumaczenia(t) and len(t) <= 700]
    sl = slownik(lang)
    if zrodlo: _dodaj_zrodla([t for t in teksty if t not in sl])
    return {t: sl[t] for t in teksty if t in sl}

def tlumacz_teksty(lang, teksty, key):
    """Pełne teksty (z liczbami) -> przetłumaczone pełne teksty, w tej samej kolejności."""
    if lang == 'pl' or lang not in JEZYKI: return list(teksty)
    sz = [szablon(t) for t in teksty]
    d = przetlumacz(lang, [s for s, _ in sz if do_tlumaczenia(s)], key)
    return [wypelnij(d[s], n) if s in d else t for (s, n), t in zip(sz, teksty)]

INSTR_WOLNY = ('Translate each string of the JSON array from {src} into {dst}. These are messages of the AI assistant of mObywatel, the Polish government app, '
               'or short reply buttons. Keep meaning, tone and brevity. Keep **bold** markers, numbers, dates, amounts, names of people (never transliterate them, keep Latin script), streets, companies, licence plates, '
               'document numbers unchanged; keep Polish institution and service names in the original. {glos}Address the user informally in the second person singular (German du, French tu, Ukrainian ти…), like the Polish "Ty". '
               'Answer with JSON {{"t": [...]}} with exactly one translation per input string, same order.')
def _json_call(instr, teksty, key, tokens=4000):
    import agent
    body = dict(model=TLUMACZ_MODEL, instructions=instr, input=json.dumps(teksty, ensure_ascii=False), max_output_tokens=tokens, store=False,
                reasoning={'effort': 'low'}, text={'format': {'type': 'json_schema', 'name': 'tlumaczenia', 'strict': True,
                    'schema': {'type': 'object', 'properties': {'t': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['t'], 'additionalProperties': False}}})
    if agent.OPENAI_TIER: body['service_tier'] = agent.OPENAI_TIER
    for proba in range(3):
        req = urllib.request.Request('https://api.openai.com/v1/responses', data=json.dumps(body).encode(), headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r: out = json.loads(r.read())
            txt = ''.join(p.get('text', '') for it in out.get('output', []) if it.get('type') == 'message' for p in it.get('content', []) if p.get('type') in ('output_text', 'text'))
            res = json.loads(txt)['t']
            if len(res) == len(teksty): return res
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')
            if e.code == 400 and 'service_tier' in msg and 'service_tier' in body: body.pop('service_tier', None); continue
            if e.code == 400 and 'reasoning' in msg and 'reasoning' in body: body.pop('reasoning', None); continue
            if e.code in (400, 401, 403, 404): return None
            time.sleep(1.5 * (proba + 1))
        except Exception:
            time.sleep(1.5 * (proba + 1))
    return None

def tlumacz_wolne(teksty, src, dst, key):
    """Jednorazowe tłumaczenie zdań (bez zapisu w słowniku). src/dst: kody języków albo 'auto' dla src."""
    if not teksty or not key: return list(teksty)
    s = 'the source language (detect it)' if src == 'auto' else JEZYKI[src][0]
    res = _json_call(INSTR_WOLNY.format(src=s, dst=JEZYKI[dst][0], glos='' if dst == 'pl' else glosariusz(dst)), list(teksty), key)
    return res if res else list(teksty)

POLA = ('title', 'source', 'body', 'flag', 'note', 'label')
def tlumacz_zdarzenia(events, lang, key):
    """Karty z rejestrów (po polsku) tłumaczymy na język interfejsu."""
    if lang == 'pl' or lang not in JEZYKI: return events
    miejsca = []
    for e in events:
        if e.get('t') not in ('card', 'confirm', 'qr'): continue
        for f in POLA:
            if isinstance(e.get(f), str): miejsca.append((e, f, None))
        for i, r in enumerate(e.get('rows') or []):
            for j in (0, 1):
                if j < len(r) and isinstance(r[j], str): miejsca.append((e, 'rows', (i, j)))
        e['tl'] = 1
    if not miejsca: return events
    teksty = [e[f] if k is None else e['rows'][k[0]][k[1]] for e, f, k in miejsca]
    przekl = tlumacz_teksty(lang, teksty, key)
    for (e, f, k), t in zip(miejsca, przekl):
        if k is None: e[f] = t
        else:
            e['rows'][k[0]] = list(e['rows'][k[0]]); e['rows'][k[0]][k[1]] = t
    return events

