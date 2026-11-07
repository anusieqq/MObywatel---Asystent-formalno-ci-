# -*- coding: utf-8 -*-
"""Świat demonstracyjny: dane osoby (z persony.py) i usług (fikcyjne). Każde narzędzie zwraca
(dane_dla_modelu, karta_dla_aplikacji). Akcje mają podgląd (karta potwierdzenia) i wykonanie."""
import hashlib, datetime, re
from persony import P

DZIS = datetime.date(2026, 10, 18)
def d(s): return datetime.datetime.strptime(s, '%Y-%m-%d').date()
def pl(dt): return dt.strftime('%d.%m.%Y')
def pld(s):
    try: return pl(d(s))
    except (ValueError, TypeError): return s
def jest_data(s):
    try: d(s); return True
    except (ValueError, TypeError): return False
def za_ile(s):
    n = (d(s) - DZIS).days
    return 'dziś' if n == 0 else ('za %d dni' % n if n > 0 else '%d dni temu' % -n)
def h(s, n): return int(hashlib.md5(s.encode()).hexdigest(), 16) % n
def zl(x): return ('{:,.2f}'.format(x)).replace(',', ' ').replace('.', ',') + ' zł'
def nr(prefix): return prefix + '/2026/' + str(100000 + h(prefix + str(datetime.datetime.now().microsecond), 899999))[:3] + ' ' + str(h(prefix, 899) + 100)
def K(): return P()['plec'] == 'K'
def rodz(k, m): return k if K() else m
def imie_nazwisko(): o = P()['osoba']; return o['imie'] + ' ' + o['nazwisko']
def odm(n, jeden, kilka, wiele):
    """Odmiana po liczebniku: 1 plecak, 2 plecaki, 5 plecaków."""
    if n == 1: return jeden
    return kilka if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else wiele

class _Widok:
    """Leniwy widok na pole bieżącej persony (żeby `from dane import OSOBA` działało w każdym wątku)."""
    def __init__(s, klucz, f=None): s._k, s._f = klucz, f
    def _v(s): v = P()[s._k]; return s._f(v) if s._f else v
    def __getitem__(s, k): return s._v()[k]
    def __iter__(s): return iter(s._v())
    def __len__(s): return len(s._v())
    def __contains__(s, k): return k in s._v()
    def __add__(s, o): return list(s._v()) + list(o)
    def __bool__(s): return bool(s._v())
    def get(s, k, dflt=None): return s._v().get(k, dflt)
    def keys(s): return s._v().keys()
    def items(s): return s._v().items()
    def values(s): return s._v().values()
OSOBA = _Widok('osoba'); RODZINA = _Widok('rodzina'); DOKUMENTY = _Widok('dokumenty'); NALEZNOSCI = _Widok('naleznosci')
SKRZYNKA = _Widok('skrzynka'); PLIKI = _Widok('pliki'); KURSY = _Widok('kursy'); POJAZDY = _Widok('pojazdy')
POJAZD = _Widok('pojazdy', lambda v: v[0])
DRUGA_STRONA = dict(kierowca='Piotr Nowak', pojazd='Opel Astra, WPI 22R31', model='Opel Astra', kolor='szary', oc='PZU, polisa 1102 774 551, ważne', mobywatel=True)

def stan_poczatkowy():
    """zastrzezone: dokumenty w Systemie Dokumenty Zastrzeżone (banki, ZBP), cofalne w aplikacji;
    uniewaznione: unieważnione w rejestrze państwowym (nieodwracalne); zawieszone: {'dowod': 'DD.MM.RRRR'}."""
    return dict(pesel=P()['pesel_stan'], zastrzezone=[], uniewaznione=[], zawieszone={}, zaplacone=[], pisma_wyslane=[], dzieci_nowe=[])

def sylw(p):
    """Dane do sylwetki pojazdu w aplikacji (model i kolor z CEPiK)."""
    return dict(model=p.get('model') or p.get('marka'), kolor=p.get('kolor'), rok=p.get('rok'), nr=p.get('nr'))

# ------------------------------------------------------------------ odczyty
MALZONEK_RODZICE = ('mąż', 'żona', 'mama', 'tata', 'matka', 'ojciec')
def widoczna_rodzina():
    """Rejestr PESEL pokazuje małżonka, rodziców i małoletnie dzieci. Dorosłych dzieci ani rodzeństwa nie pokazuje."""
    return [x for x in P()['rodzina'] if x['rola'] in MALZONEK_RODZICE or (x['rola'] in ('syn', 'córka') and x.get('wiek', 99) < 18)]

def r_moje_dane(a, s):
    o = P()['osoba']
    dane = dict(o, rodzina=widoczna_rodzina() + [dict(rola='dziecko (nowe)', imie=x) for x in s['dzieci_nowe']])
    rows = [['Imię i nazwisko', imie_nazwisko()], ['PESEL', o['pesel']], ['Adres zameldowania', o['adres']],
            ['Telefon', o['telefon']], ['E-mail', o['email']], ['Rodzina', P()['rodzina_opis']]]
    return dane, dict(icon='id', title='Twoje dane', source='Rejestr PESEL, Rejestr Danych Kontaktowych', rows=rows)

def _rodzaj(nazwa):
    """Końcówka przymiotnika: prawo jazdy (ważne), karta, legitymacja (ważna), dowód, paszport (ważny)."""
    return 'e' if nazwa.startswith('Prawo') else ('a' if nazwa.startswith(('Karta', 'Legitymacja')) else 'y')
def _odm(slowo, k): return slowo[:-1] + k
def status_dokumentu(k, v, s):
    """Status w rejestrze (ważny, zablokowany czyli zawieszony, unieważniony, po terminie) i osobno zastrzeżenie w bankach (SDZ)."""
    g = _rodzaj(v['nazwa'])
    if k in s.get('uniewaznione', []): return _odm('unieważniony', g)
    if v.get('uniewazniony'): return _odm('nieważny', g) + ' od ' + pld(v['wazny_do'])
    if s.get('zawieszone', {}).get(k): return _odm('zablokowany', g) + ' do ' + s['zawieszone'][k]  # zawieszenie e-dowodu; w aplikacji „blokada”
    if k in s.get('zastrzezone', []): return _odm('ważny', g) + ', ' + _odm('zastrzeżony', g) + ' w bankach'
    return _odm('ważny', g)

def r_moje_dokumenty(a, s):
    out, rows = [], []
    for k, v in P()['dokumenty'].items():
        st = status_dokumentu(k, v, s)
        out.append(dict(v, id=k, status=st, wazny_do=pld(v['wazny_do'])))
        if st.startswith('ważn'):
            termin = ('do ' + pld(v['wazny_do'])) if jest_data(v['wazny_do']) else v['wazny_do']
            glowny, _, sdz = st.partition(', ')
            rows.append([v['nazwa'], '%s, %s %s' % (v['numer'], glowny, termin) + (', ' + sdz if sdz else '')])
        else:
            rows.append([v['nazwa'], '%s, %s' % (v['numer'], st)])
    return dict(dokumenty=out), dict(icon='id', title='Twoje dokumenty', source='Rejestr Dowodów Osobistych, Rejestr Paszportowy, CEPiK, System Dokumenty Zastrzeżone', rows=rows)

def r_status_pesel(a, s):
    hist, spr = list(P()['pesel_hist']), P()['pesel_spr']
    if s['pesel'].startswith('zastrzeżony z urzędu'): hist.append([pl(DZIS), 'zastrzeżenie z urzędu po unieważnieniu dowodu'])
    return dict(status=s['pesel'], historia_zmian=hist, historia_weryfikacji=spr), dict(icon='shield', title='PESEL: ' + s['pesel'],
        source='Rejestr Zastrzeżeń PESEL', rows=(hist + [['Historia weryfikacji', '']] + spr) if a.get('z_historia', True) else [['Status', s['pesel']]])

def pesel_ok(p):
    w = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]
    return len(p) == 11 and (10 - sum(int(c) * w[i] for i, c in enumerate(p[:10])) % 10) % 10 == int(p[10])
def norm_dok(x): return re.sub(r'[\s-]+', '', (x or '').upper())
def ladny_dok(n): return (n[:3] + ' ' + n[3:]) if re.fullmatch(r'[A-Z]{3}\d{6}', n) else ((n[:2] + ' ' + n[2:]) if re.fullmatch(r'[A-Z]{2}\d{7}', n) else n)

def r_sprawdz_pesel_osoby(a, s):
    p = re.sub(r'\D', '', a.get('pesel', ''))
    if len(p) != 11: return dict(blad='PESEL musi mieć 11 cyfr'), None
    cel = (a.get('cel') or '').strip()
    if not cel: return dict(blad='usługa wymaga celu sprawdzenia (np. zawarcie umowy najmu); zapytaj o niego'), None
    nd = norm_dok(a.get('numer_dokumentu'))
    if not nd: return dict(blad='usługa wymaga serii i numeru ostatniego dowodu osobistego lub paszportu tej osoby'), None
    src = 'Rejestr Zastrzeżeń PESEL, weryfikacja z dokumentem'
    if not pesel_ok(p) or not re.fullmatch(r'[A-Z]{3}\d{6}|[A-Z]{2}\d{7}', nd):
        return dict(pesel=p, status=None, blad='numer dokumentu nie zgadza się z rejestrem PESEL, rejestr nie poda statusu'), \
            dict(icon='alert', tone='warn', title='Nie można sprawdzić', source=src, rows=[['Powód', 'numer dokumentu nie zgadza się z rejestrem PESEL']])
    z = h(p, 5) == 0
    st = 'zastrzeżony' if z else 'niezastrzeżony'
    return dict(pesel=p, status=st, numer_dokumentu=ladny_dok(nd), cel=cel, uwaga='sprawdzenie trafi do historii weryfikacji tej osoby'), \
        dict(icon='shield', tone='warn' if z else 'ok', title='PESEL ' + p[:6] + '•••' + p[-2:] + ': ' + st, source=src,
             rows=[['Dokument', ladny_dok(nd)], ['Cel', cel], ['Stan na', pl(DZIS)]],
             note=rodz('Ta osoba zobaczy w historii weryfikacji, że sprawdzałaś jej PESEL.', 'Ta osoba zobaczy w historii weryfikacji, że sprawdzałeś jej PESEL.'))

def r_sprawdz_dowod(a, s):
    n = norm_dok(a.get('numer'))
    if not re.fullmatch(r'[A-Z]{3}\d{6}', n): return dict(blad='seria i numer dowodu to 3 litery i 6 cyfr, np. ABC 123456'), None
    nf, src = ladny_dok(n), 'Rejestr Dowodów Osobistych, wykaz unieważnionych i zawieszonych'
    wlasny = norm_dok(P()['dokumenty']['dowod']['numer']) == n
    w_wykazie = ('dowod' in s.get('uniewaznione', []) or 'dowod' in s.get('zawieszone', {})) if wlasny else h(n, 4) != 0
    if w_wykazie:
        return dict(numer=nf, w_wykazie=True, status='w wykazie unieważnionych lub zawieszonych', co_zrobic='Oddaj go w dowolnym urzędzie gminy, na policji albo właścicielowi.'), \
            dict(icon='id', tone='warn', title='Dowód ' + nf + ': unieważniony lub zawieszony', source=src,
                 rows=[['W wykazie', 'tak'], ['Co zrobić', 'oddaj w urzędzie gminy, na policji albo właścicielowi']])
    return dict(numer=nf, w_wykazie=False, status='brak w wykazie', uwaga='brak w wykazie nie potwierdza, że dowód jest prawdziwy'), \
        dict(icon='id', title='Dowód ' + nf + ': nie ma go w wykazie', source=src,
             rows=[['W wykazie', 'nie'], ['Uwaga', 'to nie potwierdza, że dowód jest prawdziwy']])

def r_twoje_sprawy(a, s):
    sp = [list(x) for x in P()['sprawy']]
    for x in s.get('sprawy', []): sp.insert(0, x)
    return dict(sprawy=sp), dict(icon='doc', title='Twoje sprawy', source='Twoje sprawy, mObywatel', rows=sp)

def r_skrzynka(a, s):
    msgs = []
    for m in P()['skrzynka']:
        msgs.append(dict(m, doreczono=pl(d(m['doreczono'])), termin=pl(d(m['termin'])) if m['termin'] else None,
                         odpowiedziano=m['id'] in s['pisma_wyslane']))
    m, src = msgs[0], P()['skrzynka'][0]
    if m['odpowiedziano']: extra = [['Status', 'odpowiedź wysłana']]
    elif m['termin']: extra = [['Termin odpowiedzi', m['termin'] + ' (' + za_ile(src['termin']) + ')']]
    else: extra = [['Odebrano' if src.get('przeczytana') else 'W skrzynce od', m['doreczono']]]
    zrodlo = ('e-Doręczenia, %s, odebrane %s' if src.get('przeczytana') else 'e-Doręczenia, %s, w skrzynce od %s') % (m['od'], m['doreczono'])
    card = dict(icon='mail', title=m['temat'], source=zrodlo, body=m['tresc'], rows=extra)
    return dict(wiadomosci=msgs), card

def r_moje_pliki(a, s):
    q = (a.get('szukaj') or '').lower(); pliki = P()['pliki']
    f = [x for x in pliki if not q or any(w in (x['nazwa'] + x['opis']).lower() for w in q.split())] or pliki
    return dict(pliki=f), dict(icon='doc', title='Pliki', source='Twoje pliki w mObywatelu', rows=[[x['nazwa'], x['opis']] for x in f])

def kanal(x):
    """Gdzie płaci się należność: ePłatności gminy, ZUS, przelew z decyzji, mandat (usługa Mandaty)."""
    return x.get('kanal') or ('zus' if x['id'].startswith('ZUS') else ('mandat' if x['id'].startswith('MK') else 'eplatnosci'))
JAK_ZAPLACIC = {'eplatnosci': 'w aplikacji (ePłatności gminy)', 'zus': 'w mZUS dla Płatnika lub przelewem na Twój rachunek składkowy',
                'przelew': 'przelewem na rachunek z decyzji, ta gmina nie jest w ePłatnościach', 'mandat': 'przelewem według instrukcji z mandatu'}
def r_naleznosci(a, s):
    n = []
    for x in P()['naleznosci']:
        k = kanal(x)
        n.append(dict(x, termin=pl(d(x['termin'])), kwota_tekst=zl(x['kwota']), zaplacone=x['id'] in s['zaplacone'], kanal=k,
                      metody=x.get('metody', ['BLIK'] if k == 'eplatnosci' else []), jak_zaplacic=JAK_ZAPLACIC[k]))
    mand = [m for m in P()['mandaty'] if not any(x['id'].startswith('MK') and x['zaplacone'] for x in n)]
    rows = []
    for x in n:
        if x['zaplacone']: rows.append([x['tytul'], x['kwota_tekst'] + ' zapłacone'])
        elif x['kanal'] == 'eplatnosci': rows.append([x['tytul'], x['kwota_tekst'] + ' do ' + x['termin']])
        else: rows.append([x['tytul'], '%s do %s, %s' % (x['kwota_tekst'], x['termin'], x['jak_zaplacic'])])
    if not mand: rows.append(['Mandaty', 'brak nieopłaconych'])
    zr = {'eplatnosci': 'ePłatności (gmina)', 'zus': 'ZUS', 'przelew': 'decyzja podatkowa gminy'}
    src = ', '.join(list(dict.fromkeys([zr[x['kanal']] for x in n if x['kanal'] in zr])) + ['Mandaty'])
    return dict(naleznosci=n, mandaty=mand), dict(icon='coin', title='Do zapłaty', source=src, rows=rows)

def r_emerytura(a, s):
    e = P()['emerytura']
    w = int(a.get('wiek_przejscia') or e['wiek'])
    t = e['tabela']; base = min(t)
    r = e.get('krok', 0.09); r = r if r < 1 else 0.09
    kw = t.get(w) or int(round(t[base] * (1 + r) ** (w - base), -1))
    rows = [['Składki zwaloryzowane', e['skladki']], ['Subkonto', e['subkonto']]] + ([['Kapitał początkowy', e['kapital']]] if e.get('kapital') else []) + \
           [['Prognoza (brutto)', '%s zł miesięcznie' % '{:,}'.format(kw).replace(',', ' ')]]
    return dict(skladki=e['skladki'], subkonto=e['subkonto'], kapital_poczatkowy=e.get('kapital'), wiek_emerytalny=e['wiek'], wiek_przejscia=w, prognoza_brutto=kw,
                uwaga='prognoza przy obecnych zarobkach; według ZUS każdy rok pracy dłużej to 8–12% więcej',
                wniosek='EMP, w eZUS albo w placówce ZUS, najwcześniej 30 dni przed osiągnięciem wieku emerytalnego'), \
        dict(icon='coin', title='Prognoza emerytury: %d lat' % w, source='ZUS, konto ubezpieczonego', rows=rows,
             note='Prognoza przy obecnych zarobkach. Według ZUS każdy rok pracy dłużej podnosi świadczenie o 8–12%.')

def r_terminy_zus(a, s):
    t = ['21.10.2026, 10:00', '21.10.2026, 13:30', '22.10.2026, 9:15']
    return dict(temat=a.get('temat'), terminy=t), dict(icon='clock', title='E-wizyta w ZUS: wolne terminy', source='ZUS', rows=[['Temat', a.get('temat', '')]] + [['Termin', x] for x in t])

def krotka_nazwa(p): return p['model'].replace(' Combi', '') if p.get('model') else p['marka']
def oc_tekst(p, krotko=False):
    """OC z CEPiK i UFG: ubezpieczyciel i data końca. Rejestr nie wie, czy umowa się przedłuży, więc tego nie twierdzimy."""
    t = ('OC do %s (%s)' % (pl(d(p['oc_do'])), za_ile(p['oc_do']))) if krotko else ('%s, do %s (%s)' % (p['ubezpieczyciel'], pl(d(p['oc_do'])), za_ile(p['oc_do'])))
    if p.get('leasing'): t += ', auto w leasingu, OC uzgodnij z %s' % p['leasing']
    return t
NOTA_OC = 'Umowa OC zwykle przedłuża się sama na kolejny rok, jeśli jej nie wypowiesz. Sprawdź to u ubezpieczyciela.'
def r_moje_pojazdy(a, s):
    ps = P()['pojazdy']; p = ps[0]
    rows = [['Pojazd', '%s, %d' % (p['marka'], p['rok'])], ['Nr rejestracyjny', p['nr']], ['OC', oc_tekst(p)],
            ['Badanie techniczne', 'do ' + pl(d(p['badanie_do'])) + (' (' + za_ile(p['badanie_do']) + ')' if (d(p['badanie_do']) - DZIS).days < 45 else '')], ['Licznik', p['licznik']]]
    for q in ps[1:]:
        rows.append(['Drugi pojazd', '%s, %s, %s' % (q['marka'], q['nr'], oc_tekst(q, krotko=True))])
    dane = dict(pojazdy=[dict(q, oc_do=pl(d(q['oc_do'])), badanie_do=pl(d(q['badanie_do'])), dni_do_konca_oc=(d(q['oc_do']) - DZIS).days,
                              dni_do_badania=(d(q['badanie_do']) - DZIS).days, rola=('posiadacz, właściciel: ' + q['leasing']) if q.get('leasing') else 'właściciel') for q in ps],
                uwaga='CEPiK i UFG nie wiedzą, czy umowa OC się przedłuży; zwykle przedłuża się sama, jeśli nie została wypowiedziana')
    karta = dict(icon='car', title='%s, %s' % (krotka_nazwa(p), p['nr']), source='CEPiK, UFG', rows=rows, pojazd=sylw(p))
    if any((d(q['oc_do']) - DZIS).days <= 30 and not q.get('leasing') for q in ps): karta['note'] = NOTA_OC
    return dane, karta

def r_punkty_karne(a, s):
    k = P()['punkty']; w = k['wykroczenia']
    def wyg(x):
        if x.get('mandat') and x['mandat'] in s.get('zaplacone', []): return pl(DZIS.replace(year=DZIS.year + 1))
        return x['wygasaja']
    rows = [['Wykroczenie', '%s, %s' % (x['opis'].replace('przekroczenie prędkości o ', 'prędkość +'), x['data'])] for x in w] + [['Wygasają', wyg(x)] for x in w]
    if k.get('pierwszy_rok_do'): rows.append(['Limit', '%d pkt do %s (pierwszy rok), potem %d pkt' % (k['limit'], k['pierwszy_rok_do'], k.get('limit_potem', 24))])
    else: rows.append(['Limit', '%d pkt' % k['limit']])
    if k.get('okres_probny'): rows.append(['Okres próbny', k['okres_probny']])
    if not w: rows.insert(0, ['Wykroczenia', 'brak'])
    return dict(punkty=k['punkty'], wykroczenia=[dict(x, wygasaja=wyg(x)) for x in w], limit=k['limit'], pierwszy_rok_do=k.get('pierwszy_rok_do'),
                limit_potem=k.get('limit_potem'), okres_probny=k.get('okres_probny'),
                uwaga='limit 20 pkt dotyczy pierwszego roku od wydania pierwszego prawa jazdy, potem 24 pkt; punkty wygasają rok po opłaceniu mandatu'), \
        dict(icon='clock', title='Punkty karne: %d' % k['punkty'], source='CEPiK', rows=rows)

def norm_rej(x): return re.sub(r'\s+', '', (x or '').upper())
def norm_data(x):
    c = re.sub(r'\D', '', x or '')
    return c[4:] + c[2:4] + c[:2] if re.match(r'^\d{4}-', (x or '').strip()) else c

MODELE_HIST = [('Skoda Octavia 2.0 TDI, 2018', 'Skoda Octavia', 'srebrny'), ('Toyota Yaris 1.5, 2020', 'Toyota Yaris', 'biały'),
               ('Kia Ceed 1.6, 2019', 'Kia Ceed', 'grafitowy'), ('Ford Focus 1.0, 2017', 'Ford Focus', 'niebieski')]
def r_historia_pojazdu(a, s):
    """historiapojazdu.gov.pl: wymaga numeru rejestracyjnego, VIN i daty pierwszej rejestracji (własne pojazdy znamy z CEPiK)."""
    n = norm_rej(a.get('nr_rejestracyjny'))
    if not n: return dict(blad='podaj numer rejestracyjny'), None
    for p in P()['pojazdy']:
        if n == norm_rej(p['nr']):
            wl = 'firma' if p.get('leasing') else 'osoba prywatna'
            dane = dict(pojazd='%s, %d' % (p['marka'], p['rok']), typ_wlasciciela=wl, oc='ważne do ' + pl(d(p['oc_do'])), badanie='ważne do ' + pl(d(p['badanie_do'])), szkody_istotne='brak', czerwona_flaga=None)
            return dane, dict(icon='car', tone='ok', title=dane['pojazd'], source='Historia pojazdu: CEPiK, UFG',
                rows=[['Nr rejestracyjny', p['nr']], ['Właściciel', wl], ['OC', dane['oc']], ['Badanie techniczne', dane['badanie']], ['Przebieg', p['licznik']]], pojazd=sylw(p))
    vin, dt = norm_rej(a.get('vin')), norm_data(a.get('data_pierwszej_rejestracji'))
    if not vin or not dt:
        return dict(blad='historia pojazdu wymaga też VIN i daty pierwszej rejestracji (są w dowodzie rejestracyjnym); poproś o nie albo o zdjęcie dowodu rejestracyjnego'), None
    nie_ma = (dict(blad='nie znaleziono pojazdu: numer rejestracyjny, VIN i data pierwszej rejestracji nie pasują do siebie'),
              dict(icon='alert', tone='warn', title='Nie znaleziono pojazdu', source='Historia pojazdu: CEPiK',
                   rows=[['Powód', 'numer rejestracyjny, VIN i data pierwszej rejestracji nie pasują do siebie']]))
    if n == 'WE4K221':
        if vin != 'WVWZZZAUZKW118204' or dt != '14032019': return nie_ma
        dane = dict(pojazd='Volkswagen Golf 1.5 TSI, 2019', vin='WVWZZZAUZKW118204', pierwsza_rejestracja='14.03.2019', wlasciciele='3, ostatnia zmiana 08.2026', typ_wlasciciela='osoba prywatna',
                    oc='ważne do 02.2027', badanie='ważne do 05.2027', szkody_istotne='1 (2022), zgłosił ubezpieczyciel', kradziez='brak',
                    przebiegi={'2022': '61 300 km', '2024': '112 300 km', '2025': '87 400 km'}, czerwona_flaga='przebieg spadł między 2024 a 2025: możliwe cofnięcie licznika')
        return dane, dict(icon='car', title='Volkswagen Golf 1.5 TSI, 2019', source='Historia pojazdu: CEPiK, UFG',
            rows=[['Właściciele', dane['wlasciciele']], ['OC', dane['oc']], ['Badanie techniczne', dane['badanie']], ['Szkoda istotna', dane['szkody_istotne']], ['Kradzież, zatrzymanie', 'brak']],
            flag='Przebieg się nie zgadza: w 2024 r. 112 300 km, w 2025 r. 87 400 km. Możliwe cofnięcie licznika.',
            pojazd=dict(model='Volkswagen Golf VII', kolor='biały', rok=2019, nr='WE 4K221'))
    if len(vin) != 17: return nie_ma
    m, model, kolor = MODELE_HIST[h(n, 4)]
    dane = dict(pojazd=m, wlasciciele=str(1 + h(n, 3)), oc='ważne', badanie='ważne', szkody_istotne='brak', kradziez='brak', przebieg='rośnie równomiernie', czerwona_flaga=None)
    return dane, dict(icon='car', tone='ok', title=m, source='Historia pojazdu: CEPiK, UFG',
        rows=[['Nr rejestracyjny', a.get('nr_rejestracyjny')], ['Właściciele', dane['wlasciciele']], ['OC i badanie', 'ważne'], ['Szkoda istotna, kradzież', 'brak'], ['Przebieg', 'bez rozbieżności']],
        pojazd=dict(model=model, kolor=kolor, nr=a.get('nr_rejestracyjny')))

MODELE_OC = ['Opel Astra', 'Skoda Fabia', 'Toyota RAV4', 'Renault Clio', 'Hyundai Tucson', 'Dacia Duster']
def r_sprawdz_oc(a, s):
    n = norm_rej(a.get('nr_rejestracyjny'))
    for p in P()['pojazdy']:
        if n == norm_rej(p['nr']):
            dane, karta = r_moje_pojazdy(a, s)
            if p is not P()['pojazdy'][0]:
                karta = dict(icon='car', title='%s, %s' % (krotka_nazwa(p), p['nr']), source='CEPiK, UFG', pojazd=sylw(p),
                             rows=[['OC', oc_tekst(p)], ['Polisa', p['polisa']]])
            return dane, karta
    ub = ['PZU', 'Warta', 'Ergo Hestia', 'Allianz', 'Generali', 'Link4'][h(n, 6)] if n != 'NE7KX21' else 'PZU'
    pol = '%03d %03d %03d' % (h(n + 'p', 900) + 100, h(n + 'q', 1000), h(n + 'r', 1000))
    dz = (a.get('data_zdarzenia') or '').strip() or pl(DZIS)
    return dict(nr=a.get('nr_rejestracyjny'), oc='ważne na dzień ' + dz, ubezpieczyciel=ub, polisa=pol, na_dzien=dz), \
        dict(icon='car', tone='ok', title='OC ważne: ' + (a.get('nr_rejestracyjny') or ''), source='UFG, baza polis OC', rows=[['Ubezpieczyciel', ub], ['Polisa', pol], ['Na dzień', dz]],
             pojazd=dict(model=MODELE_OC[h(n, len(MODELE_OC))], kolor=['srebrny', 'czarny', 'biały', 'niebieski', 'czerwony'][h(n + 'k', 5)], nr=a.get('nr_rejestracyjny')))

def r_uprawnienia_kierowcy(a, s):
    kim = ('%s %s' % (a.get('imie', ''), a.get('nazwisko', ''))).strip()
    if not a.get('imie') or not a.get('nazwisko') or not (a.get('numer_blankietu') or '').strip():
        return dict(blad='usługa wymaga imienia, nazwiska oraz serii i numeru blankietu prawa jazdy (kierowca może je podać albo pokazać mPrawo jazdy)'), None
    return dict(kierowca=kim, status='ważny, nie jest zatrzymany', kategorie='B, C, D, D+E', stan_na='wczoraj', uwaga='usługa nie podaje szczegółów zakazów'), \
        dict(icon='id', tone='ok', title='Uprawnienia: ' + kim, source='CEPiK, uprawnienia kierowców',
             rows=[['Status dokumentu', 'ważny, nie jest zatrzymany'], ['Kategorie', 'B, C, D, D+E'], ['Stan na', 'wczoraj']])

def r_bezpieczny_autobus(a, s):
    n = a.get('nr_rejestracyjny', '')
    return dict(nr=n, pojazd='Mercedes-Benz Tourismo, 2017', badanie='ważne do 03.12.2026', oc='ważne', miejsca=49, kradziez='brak', uwaga='tylko pojazdy zarejestrowane w Polsce'), \
        dict(icon='car', tone='ok', title='Autokar ' + n, source='CEPiK, UFG',
             rows=[['Pojazd', 'Mercedes-Benz Tourismo, 2017'], ['Badanie techniczne', 'ważne do 03.12.2026'], ['OC', 'ważne'], ['Miejsca', '49'], ['Kradzież, wyrejestrowanie', 'brak']],
             pojazd=dict(model='Mercedes-Benz Tourismo', kolor='biały', nr=n))

ROLE_SLOWA = [('mam', 'mama'), ('matk', 'mama'), ('tat', 'tata'), ('ojc', 'tata'), ('mąż', 'mąż'), ('męż', 'mąż'), ('maz', 'mąż'), ('żon', 'żona'), ('zon', 'żona'),
              ('cór', 'córka'), ('cor', 'córka'), ('syn', 'syn'), ('siostr', 'siostra'), ('brat', 'brat')]
ZAIMKI = ('moja', 'mój', 'moj', 'moje', 'mojego', 'mojej', 'mojemu', 'moich', 'mojego', 'dla', 'od', 'mojej')
def _kto(o):
    """Ustala, o kogo pyta użytkownik: 'ja', osoba z rodziny (dict), lista osób (np. dzieci) albo None."""
    slowa = [w for w in re.findall(r'[\wąćęłńóśźż]+', o.lower()) if w not in ZAIMKI]
    ja = P()['osoba']['imie'].lower()
    if not slowa or slowa[0] in ('ja', 'mnie', 'siebie', 'mi', 'ty') or slowa[0].startswith(ja[:4]): return 'ja'
    o = slowa[0]
    rodzina = P()['rodzina']
    if o.startswith('dziec') or o.startswith('dzieck'): return [y for y in rodzina if y['rola'] in ('syn', 'córka')]
    for stem, rola in ROLE_SLOWA:
        if o.startswith(stem):
            x = [y for y in rodzina if y['rola'] == rola]
            return x[0] if len(x) == 1 else (x or None)
    for y in rodzina:
        im = y['imie'].split()[0].lower()
        if o[:3] == im[:3] or (len(o) >= 2 and o[:2] == im[:2] and sum(1 for z in rodzina if z['imie'][:2].lower() == o[:2]) == 1): return y
    return None
def r_recepty(a, s):
    """e-Recepty z IKP: własne, małoletnich dzieci i osób, które upoważniły użytkownika w IKP. Nic więcej."""
    r = P()['recepty']; ja = P()['osoba']['imie']
    o = (a.get('osoba') or '').strip()
    src = 'IKP, e-Recepta'
    brak_dostepu = (dict(recepty=[], uwaga='brak dostępu: ta osoba nie upoważniła Cię w IKP albo to nie Twoje małoletnie dziecko'),
                    dict(icon='doc', title='Brak dostępu do recept', source=src, rows=[['Dostęp', 'brak, potrzebne upoważnienie tej osoby w IKP']]))
    if o:
        kto = _kto(o)
        if kto == 'ja': r = [x for x in r if x['osoba'].split()[0] == ja]
        elif isinstance(kto, dict):
            im = kto['imie'].split()[0]
            dostep = (kto['rola'] in ('syn', 'córka') and kto.get('wiek', 99) < 18) or kto['imie'] in P().get('upowaznienia_ikp', [])
            if not dostep: return brak_dostepu
            r = [x for x in r if x['osoba'].split()[0] == im]
        elif isinstance(kto, list):
            ok = [y for y in kto if (y['rola'] in ('syn', 'córka') and y.get('wiek', 99) < 18) or y['imie'] in P().get('upowaznienia_ikp', [])]
            if not ok: return brak_dostepu
            r = [x for x in r if any(x['osoba'].split()[0] == y['imie'].split()[0] for y in ok)]
        else:
            r = [x for x in r if o[:3].lower() in x['osoba'].lower()]
            if not r: return brak_dostepu
    if not r: return dict(recepty=[]), dict(icon='doc', title='Brak aktywnych recept', source=src, rows=[['Recepty', 'brak aktywnych']])
    return dict(recepty=r, uwaga='w aptece potrzebny jest kod i PESEL pacjenta'), dict(icon='doc', title='Aktywne recepty', source=src,
        rows=[[x['osoba'], '%s, ważna do %s, kod %s + PESEL pacjenta' % (x['lek'], x['wazna_do'], x['kod'])] for x in r])

def r_jakosc_powietrza(a, s):
    m = a.get('miejscowosc') or P()['okolica']
    return dict(miejsce=m, pm25='12 µg/m³', pm10='19 µg/m³', ocena='dobra', ostrzezenia_imgw='brak', ostrzezenia_hydro='brak'), \
        dict(icon='check', tone='ok', title='Powietrze: dobra jakość', source='Edukacyjna Sieć Antysmogowa, IMGW', rows=[['Miejsce', m], ['PM2,5', '12 µg/m³'], ['PM10', '19 µg/m³'], ['Ostrzeżenia', 'brak']])

def r_szkolenia_obronne(a, s):
    r = (a.get('rodzaj') or '').lower(); kursy = P()['kursy']
    k = [x for x in kursy if not r or r[:4] in x['rodzaj']] or kursy
    return dict(kursy=k, program='wGotowości (MON)', czas='ok. 8 godzin', koszt='bezpłatnie', kto='pełnoletni obywatele z mDowodem, bez przysięgi i bez wcielenia do rezerwy'), \
        dict(icon='shield', title='Szkolenia obronne: wolne miejsca', source='MON, program wGotowości',
             rows=[['%s, %s' % (x['termin'], x['miejsce']), '%d %s' % (x['wolne'], odm(x['wolne'], 'miejsce', 'miejsca', 'miejsc'))] for x in k])

def r_poradnik(a, s):
    n = int(a.get('liczba_osob') or P()['liczba_osob'])
    temat = a.get('temat') or 'plecak ewakuacyjny'
    lista = ['woda butelkowana w małych butelkach, filtr lub tabletki do uzdatniania', 'jedzenie gotowe do zjedzenia na 3 dni (batony, bakalie)', 'apteczka i leki stałe',
             'latarka, radio na baterie lub korbkę, powerbank', 'dokumenty lub ich kopie w wodoodpornym etui, gotówka w drobnych', 'odzież na zmianę, koc termiczny, śpiwór',
             'zapałki, scyzoryk, taśma, worki na śmieci']
    rows = [[str(i + 1), x] for i, x in enumerate(lista)]
    dane = dict(temat=temat, lista=lista, plecaki=n, uwaga='plecak ewakuacyjny ma wystarczyć na 72 godziny; każdy domownik, także dziecko, ma swój')
    if re.search(r'zapas|w domu|domow', temat.lower()):
        rows.append(['Woda w domu', '%d l na tydzień (2 l na osobę na dobę, RCB)' % (14 * n)]); dane['woda_w_domu_l'] = 14 * n
    tytul = 'Plecak ewakuacyjny' if n == 1 else 'Plecak ewakuacyjny: %d %s, po jednym na osobę' % (n, odm(n, 'plecak', 'plecaki', 'plecaków'))
    return dane, dict(icon='shield', title=tytul, source='Poradnik bezpieczeństwa (MSWiA, MON, RCB)', rows=rows)

UE_EOG = r'niemc|franc|hiszpan|włoch|wloch|portugal|holand|niderland|belgi|luksemburg|austri|czech|słowacj|slowacj|słoweni|sloweni|chorwac|węgr|wegr|rumuni|bułgar|bulgar|grecj|cypr|malt|dani|szwecj|finland|estoni|łotw|lotw|litw|irlandi|islandi|norwegi|liechtenstein|szwajcar'
def r_informacje_o_kraju(a, s):
    k = a.get('kraj', '')
    zr = 'MSZ, Odyseusz: Informacje o krajach'
    if 'egip' in k.lower():
        dane = dict(kraj='Egipt', wiza='e-visa online lub wiza po przylocie (25 USD)', paszport='ważny min. 6 miesięcy od wjazdu',
                    msz='zachowaj ostrożność; MSZ odradza podróże w niektóre regiony (m.in. północny Synaj, pogranicze z Libią i Sudanem)')
        rows, tone = [['Wiza', dane['wiza']], ['Paszport', dane['paszport']], ['Ostrzeżenia MSZ', dane['msz']]], None
    elif re.search(UE_EOG, k.lower()):
        dane = dict(kraj=k, wiza='nie potrzebujesz', dokument='wystarczy ważny dowód osobisty', msz='sprawdź komunikat MSZ przed wyjazdem')
        rows, tone = [['Wiza', dane['wiza']], ['Dokument', dane['dokument']], ['Ostrzeżenia MSZ', dane['msz']]], None
    else:
        dane = dict(kraj=k, wiza='nie mam danych dla tego kraju', paszport='sprawdź w Informacjach o krajach', msz='sprawdź aktualny komunikat MSZ przed wyjazdem',
                    uwaga='brak danych o tym kraju; nie mów, że nie ma ostrzeżeń')
        rows, tone = [['Wiza', dane['wiza']], ['Paszport', dane['paszport']], ['Ostrzeżenia MSZ', 'sprawdź przed wyjazdem, zmieniają się często']], 'warn'
    rows.append(['Twój paszport', P()['paszport_opis']])
    if P()['dzieci_paszporty'] not in ('nie dotyczy', 'dzieci są dorosłe'): rows.append(['Dzieci', P()['dzieci_paszporty']])
    dane['twoj_paszport'] = P()['paszport_opis']
    karta = dict(icon='doc', title='Podróż: ' + dane['kraj'], source=zr, rows=rows, note='Ostrzeżenia zmieniają się często. Sprawdź je jeszcze przed wyjazdem.')
    if tone: karta['tone'] = tone
    return dane, karta

def r_wybory(a, s):
    w = P()['wybory']
    return dict(obwod=w['obwod'], lokal=w['lokal'], najblizsze='wybory do Sejmu i Senatu jesienią 2027 r., termin jeszcze nie jest zarządzony'), \
        dict(icon='doc', title='Twój lokal wyborczy', source='Centralny Rejestr Wyborców, urząd gminy',
             rows=[['Obwód', w['obwod']], ['Lokal', w['krotko']], ['Najbliższe wybory', 'Sejm i Senat, jesień 2027 (termin ogłosi Prezydent)']])

def r_firma(a, s):
    f = P()['firma']
    return dict(ceidg=f['ceidg'], krs=f['krs']), dict(icon='doc', title='Firma i KRS', source='CEIDG, KRS', rows=f['rows'])

def r_szukaj_pkd(a, s):
    """Kody i nazwy według PKD 2025 (Dz.U. 2024 poz. 1936)."""
    q = (a.get('opis') or '').lower()
    if re.search(r'stron|www|program|aplikac|\bit\b|informaty', q):
        k = [['62.10.B', 'Pozostała działalność w zakresie programowania'], ['63.10.D', 'Pozostała działalność w zakresie hostingu i przetwarzania danych (jeśli utrzymujesz strony klientów)']]
    elif 'fryz' in q or 'kosmet' in q:
        k = ([['96.21.Z', 'Fryzjerstwo']] if 'fryz' in q else []) + ([['96.22.Z', 'Zabiegi kosmetyczne']] if 'kosmet' in q else [])
    elif any(w in q for w in ['hydraul', 'instalac']): k = [['43.22.Z', 'Wykonywanie instalacji wodno-kanalizacyjnych, cieplnych, gazowych i klimatyzacyjnych']]
    elif any(w in q for w in ['korepet', 'nauk', 'lekcj']): k = [['85.59.D', 'Pozostałe pozaszkolne formy edukacji, gdzie indziej niesklasyfikowane']]
    else: k = [['70.20.Z', 'Doradztwo w zakresie prowadzenia działalności gospodarczej i pozostałe doradztwo w zakresie zarządzania']]
    return dict(propozycje=k), dict(icon='doc', title='Proponowane kody PKD', source='Klasyfikacja PKD 2025', rows=k)

CENNIK_KW = {'odpis_zwykly': '30 zł', 'odpis_zupelny': '75 zł', 'wyciag': '10 zł (jeden dział)', 'zaswiadczenie_o_zamknieciu': '10 zł'}  # od 31.03.2026, Dz.U. 2026 poz. 410
def r_ksiegi_wieczyste(a, s):
    kw = P()['ksiegi']; cennik = dict(CENNIK_KW)
    uw = 'w aplikacji widać księgi, w których jesteś właścicielem, współwłaścicielem lub współużytkownikiem wieczystym; płatność BLIK; zamówione dokumenty są dostępne przez 2 lata'
    ceny = [['Odpis zwykły / zupełny', '30 zł / 75 zł'], ['Płatność', 'BLIK']]
    if not kw: return dict(ksiegi=[], cennik=cennik, uwaga=uw), dict(icon='doc', title='Księgi wieczyste', source='Centralna Informacja Ksiąg Wieczystych', rows=[['Twoje księgi', 'brak nieruchomości na Twoje nazwisko']] + ceny)
    return dict(ksiegi=kw, cennik=cennik, uwaga=uw), \
        dict(icon='doc', title='Twoje księgi wieczyste', source='Centralna Informacja Ksiąg Wieczystych', rows=[[x['numer'], x['opis'].replace('lokal mieszkalny', 'lokal')] for x in kw] + ceny)

def r_partnerzy_kdr(a, s):
    p = P()['partnerzy_kdr']
    if not p: return dict(partnerzy=[], uwaga='brak Karty Dużej Rodziny'), dict(icon='coin', title='Karta Dużej Rodziny', source='Karta Dużej Rodziny', rows=[['Twoja karta', 'brak, nie przysługuje']])
    return dict(partnerzy=p, uwaga='to ulgi ustawowe i ogólnopolskie; lokalnych partnerów i aktualne zniżki pokazuje wyszukiwarka na empatia.gov.pl'), \
        dict(icon='coin', title='Zniżki z Kartą Dużej Rodziny', source='Karta Dużej Rodziny, wyszukiwarka partnerów (empatia.gov.pl)', rows=p)

# Lista Ostrzeżeń CERT Polska: w demo stała lista domen (w produkcji zapytanie do listy).
LISTA_OSTRZEZEN_DEMO = {'poczta-dostawa24.top', 'inpost-doplata.info', 'paczka-oplata.xyz', 'mobywatel-weryfikacja.top', 'pge-zwrot-nadplaty.info'}
CECHY_OSZUSTWA = [(r'dopła|dopla|opłać|oplac|zaległ|zaleg|nadpłat', 'nacisk na szybką dopłatę'), (r'zablokow|blokad|zatrzyman|wstrzyman', 'groźba blokady'),
                  (r'\bblik\b', 'prośba o kod BLIK'), (r'kliknij|wejdź w link|wejdz w link', 'prośba o kliknięcie w link'),
                  (r'\.(top|xyz|info|click|shop)\b', 'nietypowa domena')]
def r_analizuj_wiadomosc(a, s):
    t = a.get('tresc', ''); tl = t.lower()
    dom = re.findall(r'([a-z0-9-]+(?:\.[a-z0-9-]+)+)(?:/|\b)', tl)
    dom = list(dict.fromkeys(x for x in dom if not re.match(r'^\d', x)))
    na_liscie = [x for x in dom if x in LISTA_OSTRZEZEN_DEMO or any(x.endswith('.' + y) for y in LISTA_OSTRZEZEN_DEMO)]
    cechy = [opis for wz, opis in CECHY_OSZUSTWA if re.search(wz, tl)]
    obce = [x for x in dom if not (x.endswith('.gov.pl') or x == 'gov.pl')]
    zal = 'nie klikaj; SMS prześlij na bezpłatny numer 8080 (CERT Polska); stronę zgłosisz w usłudze Bezpiecznie w sieci'
    if na_liscie:
        wz = 'fałszywa dopłata do przesyłki' if re.search(r'paczk|przesył|przesyl|poczt|kurier', tl) else ('fałszywa blokada konta' if re.search(r'zablokow|blokad', tl) else 'wyłudzenie danych')
        return dict(domeny=dom, ocena='phishing: domena na Liście Ostrzeżeń CERT Polska', na_liscie_ostrzezen_cert=True, cechy=cechy, zalecenie=zal), \
            dict(icon='alert', tone='warn', title='To oszustwo (phishing)', source='Lista Ostrzeżeń CERT Polska',
                 rows=[['Domena', ', '.join(na_liscie)], ['Na Liście Ostrzeżeń', 'tak'], ['Wzorzec', wz]])
    if (obce and cechy) or len(cechy) >= 2:
        return dict(domeny=dom, ocena='podejrzana: typowe cechy oszustwa, domeny nie ma jeszcze na Liście Ostrzeżeń', na_liscie_ostrzezen_cert=False, cechy=cechy, zalecenie=zal), \
            dict(icon='alert', tone='warn', title='Wygląda na oszustwo', source='Ocena asystenta, Lista Ostrzeżeń CERT Polska',
                 rows=[['Domena', ', '.join(dom) or 'brak linku'], ['Na Liście Ostrzeżeń', 'nie ma jej jeszcze' if dom else 'brak linku do sprawdzenia'], ['Podejrzane', ', '.join(cechy)]])
    return dict(domeny=dom, ocena='brak typowych cech oszustwa', na_liscie_ostrzezen_cert=False, cechy=cechy,
                zalecenie='nawet przy adresie gov.pl lepiej wejść do usługi z aplikacji niż z linku w SMS-ie'), \
        dict(icon='check', tone='ok', title='Nie widzę cech oszustwa', source='Lista Ostrzeżeń CERT Polska',
             rows=[['Domeny', ', '.join(dom) or 'brak linków'], ['Na Liście Ostrzeżeń', 'nie' if dom else 'brak linku do sprawdzenia']])

def r_bilety(a, s):
    b = P()['bilety'][0]
    return dict(bilety=P()['bilety']), dict(icon='doc', title='Bilet: ' + b['trasa'].replace(' Centralna', '').replace(' Główny', ''), source='Bilkom (bilety kolejowe w mObywatelu)',
        rows=[['Kiedy', b['kiedy']], ['Miejsce', b['miejsce']], ['Pociąg', b['pociag']]])

def r_ustaw_przypomnienie(a, s):
    return dict(ustawiono=True, kiedy=a.get('kiedy'), tresc=a.get('tresc')), dict(icon='bell', tone='ok', title='Przypomnienie ustawione', rows=[['Kiedy', a.get('kiedy', '')], ['O czym', a.get('tresc', '')]])

def r_do_zalatwienia(a, s):
    p = []
    for m in P()['skrzynka']:
        if m['termin'] and m.get('krotko') and m['id'] not in s['pisma_wyslane']:
            p.append([m['krotko'], 'odpowiedź do %s (%s)' % (pl(d(m['termin'])), za_ile(m['termin']))])
    for q in P()['pojazdy']:
        dni = (d(q['oc_do']) - DZIS).days
        if dni <= 30:
            p.append(['OC %s %s' % (q.get('dop', ''), q['nr']),
                      'kończy się %s (%s), %s' % (pl(d(q['oc_do'])), za_ile(q['oc_do']),
                                                  ('auto w leasingu, OC uzgodnij z %s' % q['leasing']) if q.get('leasing') else 'umowa zwykle przedłuża się sama, jeśli jej nie wypowiesz')])
        if (d(q['badanie_do']) - DZIS).days <= 30:
            p.append(['Badanie techniczne %s %s' % (q.get('dop', ''), q['nr']), 'ważne do %s (%s)' % (pl(d(q['badanie_do'])), za_ile(q['badanie_do']))])
    for x in P()['naleznosci']:
        if x['id'] not in s['zaplacone']: p.append([x['tytul'].split(',')[0].replace(' (działalność)', '').split(' MK')[0], '%s do %s' % (zl(x['kwota']).replace(',00', ''), pl(d(x['termin'])))])
    dw = P()['dokumenty']['dowod']
    if 'dowod' in s.get('uniewaznione', []): p.append(['Dowód osobisty', 'unieważniony, złóż wniosek o nowy'])
    elif s.get('zawieszone', {}).get('dowod'): p.append(['Dowód osobisty', 'zablokowany do %s, odblokuj go, jeśli się znajdzie' % s['zawieszone']['dowod']])
    elif (d(dw['wazny_do']) - DZIS).days < 200:
        n = (d(dw['wazny_do']) - DZIS).days
        p.append(['Dowód osobisty', 'traci ważność %s, %s' % (pl(d(dw['wazny_do'])), ('złóż wniosek do ' + pl(d(dw['wazny_do']) - datetime.timedelta(days=30))) if n < 90 else 'wniosek najlepiej w styczniu')])
    p += P()['zalatwienia_extra']
    return dict(sprawy=p), dict(icon='bell', title='Do załatwienia', source='Skrzynka, ePłatności, CEPiK, Rejestr Dowodów', rows=p)

# Sprawy, których nie załatwisz w tej aplikacji: (wzorzec, sprawa, gdzie, co przygotować, tryb).
# Tryb mówi modelowi, czy jest droga online w innym oficjalnym kanale: 'online', 'online, odbiór osobiście', 'online lub osobiście', 'osobiście'.
# Kolejność ma znaczenie: pierwszy pasujący wiersz wygrywa.
POZA_APLIKACJA = [
    (r'wymel', 'Wymeldowanie',
     'online na gov.pl, usługa „Wymelduj się” (profil zaufany lub e-dowód), albo urząd gminy. Możesz też wymeldować się przy zameldowaniu w nowym miejscu',
     'bezpłatnie, najpóźniej w dniu wyprowadzki. Wymeldowanie siebie i dziecka działa od razu', 'online'),
    (r'(?<!wy)(zamel|meldun|meldow)', 'Zameldowanie',
     'online na gov.pl, usługa „Zamelduj się” (profil zaufany lub e-dowód), albo urząd gminy (w Warszawie: urząd dzielnicy)',
     'masz 30 dni od zamieszkania. Właściciel z księgi wieczystej zamelduje się od razu, najemca dołącza umowę najmu albo oświadczenie właściciela. Zameldowanie jest bezpłatne, zaświadczenie o pobycie czasowym kosztuje 17 zł', 'online'),
    (r'(zgubi|utrat|utraci|ukrad|kradzie|zniszcz|wt[oó]rnik|duplikat)\w*.*praw\w* jazdy|praw\w* jazdy.*(zgubi|utrat|utraci|ukrad|skradzi|kradzie|zniszcz|wt[oó]rnik|duplikat)', 'Wtórnik prawa jazdy',
     'wniosek o wtórnik przez ePUAP (profil zaufany) albo w wydziale komunikacji starostwa lub urzędu miasta. Prawa jazdy nie zastrzeżesz ani nie unieważnisz w tej aplikacji',
     'zdjęcie, potwierdzenie opłaty 100 zł (część urzędów dolicza 0,50 zł), zniszczony dokument, jeśli go masz. Gotowe do 9 dni roboczych, odbiór w urzędzie albo pocztą', 'online, odbiór osobiście'),
    (r'wymi\w* praw\w* jazdy|praw\w* jazdy.*(wymi|wymian|traci ważn|traci wazn|wygas|bezterminow)', 'Wymiana prawa jazdy',
     'wydział komunikacji właściwy dla Twojego adresu (starostwo lub urząd miasta), osobiście albo pocztą',
     'wniosek, zdjęcie, dotychczasowe prawo jazdy, dowód osobisty, opłata 100 zł; orzeczenie lekarskie tylko, jeśli Twoje uprawnienia go wymagają. Gotowe do miesiąca. Bezterminowe prawo jazdy trzeba wymienić do 19.01.2033, harmonogram ustali minister', 'osobiście'),
    (r'praw\w* jazdy.*(wnios|zrobi|wyrobi|uzyska|zdoby)|(wnios|zrobi|wyrobi|uzyska|zdoby)\w*.*praw\w* jazdy|zda\w* (na )?prawo|kurs\w* (na )?praw\w* jazdy|\bpkk\b|profil\w* kandydata', 'Wniosek o prawo jazdy (PKK)',
     'najpierw badanie u lekarza uprawnionego, potem profil kandydata na kierowcę (PKK) w wydziale komunikacji właściwym dla Twojego adresu, osobiście. Potem kurs i egzaminy w WORD',
     'orzeczenie lekarskie, zdjęcie, dowód osobisty, a jeśli nie masz 18 lat, zgoda rodzica. Za wydanie prawa jazdy po zdanym egzaminie zapłacisz 100 zł, odbierzesz je w urzędzie albo pocztą', 'osobiście'),
    (r'rejestr(?!acyjn)\w*.*(aut|pojazd|samoch)|(aut|pojazd|samoch)\w*.*rejestr(?!acyjn)|zarejestr|przerejestr', 'Rejestracja pojazdu',
     'wydział komunikacji starostwa lub urzędu miasta (w Warszawie: urząd dzielnicy), w 30 dni od zakupu. Wniosek wyślesz online tylko tam, gdzie urząd to umożliwia. Po tablice i dowód rejestracyjny idziesz osobiście. Wniosek w mObywatelu ma ruszyć 18.01.2027, odbiór nadal w urzędzie',
     'wniosek, umowa kupna lub faktura, dotychczasowy dowód rejestracyjny z ważnym badaniem i tablice (numer możesz zachować), potwierdzenie opłat. OC wykup przed rejestracją. PCC-3 (2%, 14 dni) złożysz tutaj', 'osobiście'),
    (r'badani\w* techniczn|przegl[aą]d(?!ar)', 'Badanie techniczne',
     'dowolna stacja kontroli pojazdów, osobiście, z dowodem rejestracyjnym',
     'samochód osobowy 149 zł, z instalacją LPG 245 zł. Wynik trafi do CEPiK, nowy termin zobaczysz tutaj', 'osobiście'),
    (r'paszport\w* tymczasow', 'Paszport tymczasowy',
     'dowolny punkt paszportowy w urzędzie wojewódzkim, osobiście, tylko w pilnej sytuacji',
     'zdjęcie, dowód osobisty, opłata 30 zł, dokument potwierdzający pilną potrzebę; dla dziecka zgoda obojga rodziców. Ważny do 365 dni', 'osobiście'),
    (r'^(?!.*(zgubi|utrat|ukrad|kradzie|zniszcz)).*paszport', 'Paszport dla dorosłego lub dziecka od 12 lat',
     'dowolny punkt paszportowy w urzędzie wojewódzkim, osobiście, z odciskami palców. Wizytę umówisz na stronie urzędu wojewódzkiego. Dla dziecka poniżej 12 lat wniosek złożysz tutaj',
     'zdjęcie sprzed najwyżej 6 miesięcy, dotychczasowy paszport lub dowód, dowód opłaty: 140 zł; 70 zł z KDR, dla studenta lub dziecka 12 do 17 lat; 35 zł dla dziecka 12 do 17 lat z KDR; od 70 lat bezpłatnie. Dziecko idzie z Tobą, potrzebna zgoda obojga rodziców. Odbiór osobiście po około miesiącu', 'osobiście'),
    (r'zmi[ae]n\w* (moje\w* |swoje\w* )?(nazwisk|imi)|nazwisk\w* (po|przed) ślub|nazwisk\w* (po|przed) slub|powr\w* do (panieńsk\w* |panienski\w* )?nazwisk', 'Zmiana imienia lub nazwiska',
     'wniosek do dowolnego urzędu stanu cywilnego: osobiście, pocztą albo przez e-Doręczenia. Po rozwodzie powrót do nazwiska to oświadczenie w USC, masz na nie 3 miesiące od uprawomocnienia wyroku',
     'wniosek z uzasadnieniem, opłata 37 zł (powrót do nazwiska: 11 zł). Potem złóż wniosek o nowy dowód, stary straci ważność po 120 dniach', 'online lub osobiście'),
    (r'ślub|slub|małżeńst|malzenst', 'Ślub i akt małżeństwa',
     'dowolny urząd stanu cywilnego. Oboje idziecie osobiście złożyć zapewnienie o braku przeszkód, ślub może być najwcześniej miesiąc później',
     'dowody osobiste obojga. Opłata za akt małżeństwa 84 zł, ślub poza urzędem dodatkowo 1000 zł. Zapewnienie jest ważne 6 miesięcy', 'osobiście'),
    (r'zgon|zmarł|zmarl|pogrzeb', 'Zgłoszenie zgonu',
     'urząd stanu cywilnego właściwy dla miejsca zgonu, w 3 dni od wystawienia karty zgonu. Często załatwia to zakład pogrzebowy na podstawie pełnomocnictwa',
     'karta zgonu od lekarza, dowód osobisty zmarłego i Twój dokument. Bezpłatnie. Potem zasiłek pogrzebowy z ZUS: 7000 zł, wniosek do 12 miesięcy', 'osobiście'),
    (r'\bl4\b|zwolnieni\w* lekarsk|zasiłek chorob|zasilek chorob|e-?zla', 'Zwolnienie lekarskie i zasiłek chorobowy',
     'L4 wystawia lekarz, także podczas teleporady. Nie musisz go nikomu nosić, trafi samo do ZUS i pracodawcy. Zobaczysz je w eZUS i w IKP',
     'jako pracownik nic nie składasz. Prowadzisz firmę: zasiłek dostaniesz, jeśli płacisz dobrowolną składkę chorobową i nie masz zaległości w ZUS', 'online'),
    (r'zeznani\w* (roczn|podatk)|rozlicz\w* (się )?(z )?(pit|podat|roczn)|\bpit\b(?!-?\d)|e-?pit\b', 'Roczne zeznanie PIT',
     'Twój e-PIT w e-Urzędzie Skarbowym (podatki.gov.pl lub aplikacja e-Urząd Skarbowy), zalogujesz się mObywatelem, profilem zaufanym albo przez bank',
     'zeznanie za 2026 r. złożysz od 15.02 do 30.04.2027. PIT-37 i PIT-38 zaakceptują się same 30 kwietnia, PIT-36, PIT-36L i PIT-28 trzeba zaakceptować samodzielnie. Korektę złożysz tam w każdej chwili', 'online'),
    (r'skierowan|wizyt\w* (u|do) lekarz|zapis\w* (się )?do lekarz|umów\w* (mnie )?(do|na) (lekarz|wizyt|badani)|szczepien|e-?rejestracj', 'Wizyty, skierowania, szczepienia',
     'wizytę u lekarza rodzinnego umówisz w swojej przychodni. Przez centralną e-rejestrację w IKP umówisz mammografię, test HPV i pierwszą wizytę u kardiologa',
     'skierowania, recepty i szczepienia zobaczysz w IKP', 'online lub osobiście'),
    (r'emerytur\w*.*(wnios|złoż|zloz|przejś|przejs)|wnios\w* o emeryt|przej\w* na emeryt', 'Wniosek o emeryturę',
     'eZUS (wniosek EMP) albo placówka ZUS, najwcześniej 30 dni przed osiągnięciem wieku emerytalnego',
     'świadectwa pracy, jeśli ZUS ich nie ma. Wniosek złożony wcześniej ZUS odrzuci. Jeśli pracujesz na etacie, rozwiąż umowę z obecnym pracodawcą, inaczej ZUS zawiesi wypłatę (potem możesz znów się zatrudnić)', 'online lub osobiście'),
    (r'(wnios|dopis|wyrobi|uzyska|przyzna|złoż|zloz)\w*.*(dużej rodziny|duzej rodziny|\bkdr\b)|(dużej rodziny|duzej rodziny|\bkdr\b).*(dla (dzieck|córk|corki|syn)|dopis)|(dużej rodziny|duzej rodziny|\bkdr\b) dla ', 'Karta Dużej Rodziny',
     'online na empatia.gov.pl (eWnioski, profil zaufany) albo w urzędzie gminy',
     'PESEL członków rodziny i oświadczenie o władzy rodzicielskiej. Karta jest bezpłatna, mKDR pojawi się w mObywatelu po przyznaniu przez gminę', 'online'),
    (r'ubezpiecz\w* (zdrowotn\w* )?(dla )?(dzieck|córk|corki|syn)|zgło\w* (dzieck|córk|corki|syn)\w* do (zus|nfz|ubezp)|zgl\w* (dzieck|corki|syn)\w* do (zus|nfz|ubezp)|\bzcna\b', 'Zgłoszenie dziecka do ubezpieczenia zdrowotnego',
     'u pracodawcy (druk ZUS ZCNA) albo sama w eZUS, gdy prowadzisz firmę; w ciągu 7 dni',
     'PESEL dziecka. Dziecko do 18 lat ma prawo do leczenia na NFZ także przed zgłoszeniem', 'online'),
]
def r_gdzie_zalatwic(a, s):
    q = (a.get('sprawa') or '').lower()
    for pat, nazwa, gdzie, co, tryb in POZA_APLIKACJA:
        if re.search(pat, q):
            if P()['miasto'] != 'Warszawa': gdzie = gdzie.replace(' (w Warszawie: urząd dzielnicy)', '')
            if nazwa.startswith('Zgłoszenie dziecka') and not K(): gdzie = gdzie.replace('albo sama w eZUS', 'albo sam w eZUS')
            rows = [['Gdzie', gdzie]] + ([['Przygotuj', co]] if co else [])
            return dict(dostepne_w_aplikacji=False, online=tryb != 'osobiście', tryb=tryb, sprawa=nazwa, gdzie=gdzie, potrzebne=co), \
                dict(icon='doc', title='%s: gdzie załatwić' % nazwa, source='gov.pl', rows=rows)
    return dict(dostepne_w_aplikacji=False, sprawa=a.get('sprawa'), gdzie='gov.pl (wyszukiwarka usług) albo właściwy urząd', uwaga='sprawdź kartę usługi (karta_uslugi), zanim podasz procedurę'), \
        dict(icon='doc', title='Gdzie załatwić', source='gov.pl', rows=[['Gdzie', 'gov.pl albo właściwy urząd']])

def r_karta_uslugi(a, s):
    """Oficjalne karty usług gov.pl / biznes.gov.pl z bazy wiedzy (wiedza.py)."""
    import wiedza
    w = wiedza.szukaj(a.get('zapytanie') or a.get('sprawa') or '', n=2, wariantow=3, znakow=700)
    if not w: return dict(znaleziono=False, uwaga='brak karty w bazie; nie zgaduj procedury, odeślij do gov.pl albo właściwego urzędu'), None
    out = []
    for k in w:
        out.append(dict(usluga=k['usluga'], url=k['url'], aktualizacja=k['aktualizacja'], instytucja=k['instytucja'],
                        warianty=[dict(wariant=v['wariant'], sekcje={x['sekcja']: re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', x['tresc']).replace('**', '') for x in v['sekcje']}) for v in k['warianty']]))
    return dict(znaleziono=True, karty=out), None

READ = {k[2:]: v for k, v in list(globals().items()) if k.startswith('r_')}
