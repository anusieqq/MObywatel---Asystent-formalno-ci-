"""Baza wiedzy z kart usług gov.pl i biznes.gov.pl (zescrapowane w projekcie govpl-kb).
Wyszukiwanie BM25 po fragmentach kart (sekcja karty = fragment), bez zależności zewnętrznych.
Użycie: szukaj('wniosek o dowód osobisty', n=5) -> lista kart z najlepiej pasującymi sekcjami."""
import json, math, os, re, threading, unicodedata
from collections import Counter, defaultdict

KAT = os.environ.get('WIEDZA_KAT', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wiedza'))
_lock = threading.Lock()
_idx = None

STOP = set('i w z na do o od się nie że to jak co czy lub albo oraz a ale po przez dla jest są być może musisz możesz twoje twój twoja twoim swoje jeśli gdy ten ta te tym tego które który która jako przy także też już tylko ma mają dane danych'.split())

def _bez(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).replace('ł', 'l').replace('Ł', 'L')

def tokeny(s):
    out = []
    for w in re.findall(r'[0-9a-ząćęłńóśźż+\-]+', s.lower()):
        w = w.strip('-')
        if len(w) < 2 or w in STOP: continue
        w = _bez(w)
        out.append(w[:6])          # prosty „rdzeń”: polska fleksja zmienia głównie końcówki
    return out

def _sekcje(k):
    v = k.get('sekcje') or '[]'
    if not isinstance(v, str): return v
    try: return json.loads(v)
    except Exception:
        import ast
        try: return ast.literal_eval(v)
        except Exception: return []

def _warunki(k):
    v = k.get('warunki') or '[]'
    if isinstance(v, str):
        try: v = json.loads(v)
        except Exception:
            import ast
            try: v = ast.literal_eval(v)
            except Exception: v = []
    return '; '.join('%s: %s' % (x.get('pytanie', ''), x.get('odpowiedź', '')) for x in v)

def _wczytaj():
    global _idx
    with _lock:
        if _idx is not None: return _idx
        karty, frag = {}, []
        pk, pf = os.path.join(KAT, 'cards.jsonl'), os.path.join(KAT, 'chunks.jsonl')
        if not (os.path.exists(pk) and os.path.exists(pf)):
            _idx = dict(karty={}, frag=[], df={}, avg=1, N=0, post={}, tyt={}); return _idx
        pliki_k = [pk] + [os.path.join(KAT, f) for f in sorted(os.listdir(KAT)) if f.endswith('_cards.jsonl')]
        pliki_f = [pf] + [os.path.join(KAT, f) for f in sorted(os.listdir(KAT)) if f.endswith('_chunks.jsonl')]
        def linie(pliki):
            for p_ in pliki:
                with open(p_, encoding='utf-8') as source_file:
                    for line in source_file:
                        if line.strip(): yield line
        for l in linie(pliki_k):
            r = json.loads(l); karty[r['id']] = r
        df = Counter(); dl = 0; post = defaultdict(list); tyt = {}
        for l in linie(pliki_f):
            r = json.loads(l)
            if r.get('język', 'pl') != 'pl': continue
            tf = Counter(tokeny(r['tekst']))
            i = len(frag)
            frag.append(dict(karta_id=r['karta_id'], sekcja=r.get('sekcja', ''), url=r.get('url', ''), usluga=r.get('usługa', ''), wariant=r.get('wariant', ''), n=sum(tf.values()) or 1))
            for t, f in tf.items(): post[t].append((i, f))
            df.update(tf.keys()); dl += frag[-1]['n']
            u = r.get('url', '')
            if u not in tyt: tyt[u] = set(tokeny(r.get('usługa', '')))
        _idx = dict(karty=karty, frag=frag, df=df, avg=dl / max(len(frag), 1), N=len(frag), post=post, tyt=tyt)
        return _idx

def szukaj(zapytanie, n=4, wariantow=3, znakow=1500):
    """Zwraca n usług (grupowanych po adresie karty): nazwa, url, data aktualizacji, instytucja i warianty z kluczowymi sekcjami."""
    I = _wczytaj()
    q = list(dict.fromkeys(tokeny(zapytanie)))
    if not q or not I['N']: return []
    idf = {t: math.log(1 + (I['N'] - I['df'].get(t, 0) + .5) / (I['df'].get(t, 0) + .5)) for t in q}
    k1, b = 1.4, 0.75
    sc = defaultdict(float)
    for t in q:
        for i, f in I['post'].get(t, ()):
            sc[i] += idf[t] * (f * (k1 + 1)) / (f + k1 * (1 - b + b * I['frag'][i]['n'] / I['avg']))
    po_url = defaultdict(list)
    for i, s in sc.items(): po_url[I['frag'][i]['url']].append((s, i))
    wyniki = []
    for u, lst in po_url.items():
        lst.sort(reverse=True)
        tt = I['tyt'].get(u, set())
        trafienie = sum(idf[t] for t in q if t in tt)            # słowa zapytania w nazwie usługi
        nadmiar = sum(1 for t in tt if t not in idf)             # słowa nazwy, których nie było w pytaniu (np. „dziecka”)
        w = lst[0][0] + 0.3 * sum(x[0] for x in lst[1:4]) + 2.2 * trafienie - 0.6 * nadmiar
        wyniki.append((w, u, lst))
    wyniki.sort(key=lambda x: -x[0])
    out = []
    wazne = ('Co musisz zrobić', 'Kto może', 'Ile zapłacisz', 'Ile będziesz czekać', 'Co musisz przygotować', 'Gdzie', 'Jak odbierzesz', 'Termin')
    for w, u, lst in wyniki[:n]:
        kid = [I['frag'][i]['karta_id'] for _, i in lst]
        warianty = list(dict.fromkeys(kid))[:wariantow]
        trafione = {I['frag'][i]['sekcja'] for _, i in lst[:6]}
        wv = []
        for k_id in warianty:
            k = I['karty'].get(k_id, {})
            sek = [dict(sekcja=x.get('tytuł', ''), tresc=re.sub(r'\n{3,}', '\n\n', x.get('treść_md', ''))[:znakow])
                   for x in _sekcje(k) if x.get('tytuł', '') in trafione or any(x.get('tytuł', '').startswith(z) for z in wazne)]
            wv.append(dict(wariant=_warunki(k), sekcje=sek[:7]))
        k0 = I['karty'].get(warianty[0], {})
        out.append(dict(usluga=k0.get('usługa', ''), url=u, aktualizacja=(k0.get('ostatnia_aktualizacja') or '')[:10],
                        instytucja=k0.get('instytucja_usługa', ''), zrodlo=k0.get('źródło', ''), opis=(k0.get('opis_md') or '')[:600], warianty=wv))
    return out

if __name__ == '__main__':
    import sys
    import time; t = time.time(); _wczytaj(); print('wczytanie %.1fs' % (time.time() - t)); t = time.time()
    w = szukaj(' '.join(sys.argv[1:]) or 'wniosek o dowód osobisty'); print('zapytanie %.2fs' % (time.time() - t))
    for k in w:
        print('##', k['usluga'], '|', k['url'], '|', k['aktualizacja'])
        for v in k['warianty']:
            print('  >>', v['wariant'])
            for s in v['sekcje']: print('     --', s['sekcja'], ':', s['tresc'][:160].replace('\n', ' '))
