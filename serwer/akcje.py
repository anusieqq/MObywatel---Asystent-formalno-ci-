# -*- coding: utf-8 -*-
"""Akcje ze skutkiem prawnym lub finansowym. Każda: podglad(a, s) -> karta potwierdzenia,
wykonaj(a, s) -> (dane, karta wyniku). Wykonanie następuje WYŁĄCZNIE po potwierdzeniu Face ID w aplikacji.
Gdy akcji nie da się wykonać (np. sprawa wymaga wizyty albo termin jeszcze nie biegnie), podglad zgłasza
ValueError z wyjaśnieniem dla modelu; agent przekazuje je jako błąd narzędzia i nie pokazuje karty."""
import datetime, random, re
from dane import DOKUMENTY, OSOBA, POJAZD, NALEZNOSCI, DRUGA_STRONA, DZIS, pl, d, zl, KURSY, rodz, imie_nazwisko, norm_rej, sylw
from persony import P

def nr(p): return '%s/2026/%03d %03d' % (p, random.randint(100, 999), random.randint(100, 999))
def teraz(): return datetime.datetime.now().strftime('%H:%M')
def plus(dni): return pl(DZIS + datetime.timedelta(days=dni))
NAZWY = {'dowod': 'Dowód osobisty', 'paszport': 'Paszport', 'prawo_jazdy': 'Prawo jazdy', 'legitymacja': 'Legitymacja studencka', 'kdr': 'Karta Dużej Rodziny'}
DOK_SDZ = ('dowod', 'paszport')  # System Dokumenty Zastrzeżone (ZBP); prawa jazdy tu nie ma
def pesel_maska(): p = OSOBA['pesel']; return p[:6] + '•••' + p[-2:]

A = {}
def _czysc(k): return {x: y for x, y in k.items() if y is not None} if isinstance(k, dict) else k
def akcja(nazwa):
    """Rejestruje podglad/wykonaj; z kart usuwa puste pola (np. note=None)."""
    def reg(f):
        def g(a, s):
            r = f(a, s)
            return (r[0], _czysc(r[1])) if isinstance(r, tuple) else _czysc(r)
        g.__name__ = f.__name__
        A.setdefault(nazwa, {})[f.__name__] = g
        return f
    return reg

# --- pomocnicze
def st(s):
    """Klucze stanu wspólne z dane.py (PLAN p.3)."""
    s.setdefault('zastrzezone', []); s.setdefault('uniewaznione', []); s.setdefault('zawieszone', {}); s.setdefault('sprawy', [])
    return s

def pelnoletnia():
    try: u = datetime.datetime.strptime(OSOBA['data_urodzenia'], '%d.%m.%Y').date()
    except (ValueError, TypeError, KeyError): return True
    return DZIS.year - u.year - ((DZIS.month, DZIS.day) < (u.month, u.day)) >= 18

def e_dowod():
    """Czy dowód ma warstwę elektroniczną: jawne pole e_dowod albo data wydania (ważność 10 lat) od 04.03.2019."""
    v = DOKUMENTY['dowod'] if 'dowod' in DOKUMENTY else {}
    if 'e_dowod' in v: return bool(v['e_dowod'])
    try:
        w = d(v['wazny_do'])
        return datetime.date(w.year - 10, w.month, min(w.day, 28)) >= datetime.date(2019, 3, 4)
    except (ValueError, TypeError, KeyError):
        return True

def pesel_zastrzezony(s): return str(s.get('pesel', '')).startswith('zastrzeżony')

def przedsiebiorca(): return isinstance((P().get('firma') or {}).get('ceidg'), dict)

def dziecko(a):
    """None = wniosek dla siebie; dict = małoletnie dziecko z rejestru PESEL; ValueError, gdy osoby nie ma wśród małoletnich dzieci."""
    o = (a.get('osoba') or '').strip().lower()
    ja = OSOBA['imie'].lower()
    if not o or o in ('ja', 'mnie', 'siebie', 'dla mnie') or o.split()[0] == ja: return None
    dzieci = [r for r in P()['rodzina'] if r.get('rola') in ('syn', 'córka') and r.get('wiek') is not None and r['wiek'] < 18]
    x = next((r for r in dzieci if r['imie'].lower().startswith(o.split()[0][:2])), None)
    if not x:
        if not dzieci: raise ValueError('W rejestrze PESEL nie masz małoletnich dzieci. Dorosła osoba składa wniosek sama.')
        raise ValueError('Taką sprawę załatwisz tu tylko dla siebie albo swojego małoletniego dziecka (%s). Dorosła osoba składa wniosek sama.'
                         % ', '.join(r['imie'].split()[0] for r in dzieci))
    return x

def kanal(x):
    """Kanał płatności należności: eplatnosci (płatne tutaj), zus, mandat (przelew z instrukcji) albo przelew (gmina spoza ePłatności)."""
    if x.get('kanal'): return x['kanal']
    if x['id'].startswith('ZUS'): return 'zus'
    if x['id'].startswith('MK'): return 'mandat'
    return 'eplatnosci' if x.get('eplatnosci', True) else 'przelew'

def gdzie_zaplacisz(x):
    k = kanal(x)
    if k == 'zus': return '%s: zapłacisz w mZUS dla Płatnika albo przelewem na Twój rachunek składkowy (opłata za kreator 0,55 zł)' % x['tytul']
    if k == 'mandat': return '%s: zapłacisz przelewem według instrukcji z mandatu (odbiorca: %s, do %s); w aplikacji widzisz go w usłudze Mandaty' % (x['tytul'], x.get('wierzyciel', 'urząd wojewódzki'), pld_(x.get('termin')))
    if k == 'przelew': return '%s: zapłacisz przelewem na rachunek z decyzji podatkowej, %s nie jest jeszcze w ePłatnościach' % (x['tytul'], x.get('wierzyciel', 'ta gmina'))
    return x['tytul']

# --- dokumenty: zastrzeżenie w bankach (SDZ), unieważnienie w rejestrze, zawieszenie e-dowodu
def _do_zastrzezenia(a, s):
    dd = [x for x in (a.get('dokumenty') or []) if x in DOK_SDZ and x in DOKUMENTY and not DOKUMENTY[x].get('uniewazniony') and x not in s['uniewaznione']]
    if not dd:
        raise ValueError('Brak ważnego dowodu ani paszportu do zastrzeżenia. Prawa jazdy tu nie zastrzeżesz ani nie unieważnisz: to wniosek o wtórnik (gdzie_zalatwic).')
    return dd

@akcja('zastrzez_dokumenty')
def podglad(a, s):
    st(s); dd = _do_zastrzezenia(a, s)
    if not a.get('uniewaznij'):
        return dict(icon='shield', title='Zastrzeżenie dokumentów', source='System Dokumenty Zastrzeżone (ZBP)', rows=[[NAZWY[x], DOKUMENTY[x]['numer']] for x in dd],
                    note='Banki i operatorzy od razu zobaczą, że dokument jest zastrzeżony. Jeśli go znajdziesz, cofniesz to tutaj.', label='Zastrzeż')
    rej = (['Rejestr Dowodów Osobistych'] if 'dowod' in dd else []) + (['Rejestr Dokumentów Paszportowych'] if 'paszport' in dd else [])
    rows = [[NAZWY[x], DOKUMENTY[x]['numer'] + ', unieważnienie'] for x in dd]
    pesel_sam = 'dowod' in dd and pelnoletnia() and not pesel_zastrzezony(s)
    if pesel_sam: rows.append(['PESEL', 'zastrzeże się automatycznie'])
    note = 'Unieważnienia nie da się cofnąć, nawet gdy dokument się znajdzie.'
    if pesel_sam: note += ' Twój PESEL zostanie zastrzeżony automatycznie.'
    if 'dowod' in dd: note += ' Zaświadczenie o utracie przyjdzie do skrzynki e-Doręczeń, ważne do 2 miesięcy, ale nie jest dokumentem tożsamości.'
    return dict(icon='shield', title='Zastrzeżenie i unieważnienie', source=', '.join(['System Dokumenty Zastrzeżone'] + rej), rows=rows, note=note, label='Zastrzeż i unieważnij')

@akcja('zastrzez_dokumenty')
def wykonaj(a, s):
    st(s); dd = _do_zastrzezenia(a, s); uw = bool(a.get('uniewaznij'))
    s['zastrzezone'] = sorted(set(s['zastrzezone']) | set(dd))
    pesel_sam = False
    if uw:
        s['uniewaznione'] = sorted(set(s['uniewaznione']) | set(dd))
        for x in dd: s['zawieszone'].pop(x, None)
        if 'dowod' in dd and pelnoletnia() and not pesel_zastrzezony(s):
            s['pesel'] = 'zastrzeżony z urzędu'; pesel_sam = True
    rows = [[NAZWY[x], 'unieważniony' if uw else 'zastrzeżony w bankach'] for x in dd]
    if pesel_sam: rows.append(['PESEL', 'zastrzeżony z urzędu'])
    if uw and 'dowod' in dd: rows.append(['Zaświadczenie o utracie', 'w skrzynce e-Doręczeń'])
    dane = dict(zastrzezono_w_bankach=dd, uniewazniono=dd if uw else [], godzina=teraz(), pesel_zastrzezony_z_urzedu=pesel_sam,
                mozna_cofnac='nie, unieważnienie jest nieodwracalne' if uw else 'tak, zastrzeżenie w bankach cofniesz tutaj',
                nastepne=['wniosek o nowy dowód (wniosek_dowod)'] if uw and 'dowod' in dd else [])
    return dane, dict(icon='check', tone='ok', title='Dokumenty zastrzeżone i unieważnione' if uw else 'Dokumenty zastrzeżone',
                      source='Potwierdzenie z godz. ' + teraz(), rows=rows)

@akcja('zawies_dowod')
def podglad(a, s):
    st(s)
    if 'dowod' in s['uniewaznione']: raise ValueError('Dowód jest już unieważniony, zablokować go nie można.')
    if 'dowod' in s['zawieszone']: raise ValueError('Dowód jest już zablokowany do %s.' % s['zawieszone']['dowod'])
    if not e_dowod():
        raise ValueError('Ten dowód nie ma warstwy elektronicznej (wydany przed marcem 2019), więc nie można go zablokować. Zaproponuj zastrzeżenie w bankach (zastrzez_dokumenty), a gdy przepadł, unieważnienie.')
    return dict(icon='shield', title='Blokada dowodu osobistego', source='Rejestr Dowodów Osobistych',
                rows=[['Dowód osobisty', DOKUMENTY['dowod']['numer']], ['Blokada do', plus(14)]],
                note='Dowodem nie posłużysz się przez ten czas. Jeśli go znajdziesz, odblokujesz go tutaj. Po 14 dniach bez odblokowania zostanie unieważniony.', label='Zablokuj dowód')

@akcja('zawies_dowod')
def wykonaj(a, s):
    st(s); do = plus(14)
    s['zawieszone']['dowod'] = do
    return dict(zablokowano='dowod', do=do, potem='bez odblokowania dowód zostanie unieważniony', pesel='bez zmian, możesz go zastrzec osobno'), \
        dict(icon='check', tone='ok', title='Dowód zablokowany', source='Rejestr Dowodów Osobistych',
             rows=[['Dowód osobisty', 'zablokowany do ' + do], ['Odblokowanie', 'tutaj, do ' + do]])

@akcja('odwies_dowod')
def podglad(a, s):
    st(s)
    if 'dowod' in s['uniewaznione']: raise ValueError('Dowód jest unieważniony i nie da się go przywrócić. Oddaj go w dowolnym urzędzie gminy, nowy wniosek złożysz tutaj.')
    if 'dowod' not in s['zawieszone']: raise ValueError('Dowód nie jest zablokowany, nie ma czego odblokować.')
    return dict(icon='shield', title='Odblokowanie dowodu osobistego', source='Rejestr Dowodów Osobistych',
                rows=[['Dowód osobisty', DOKUMENTY['dowod']['numer']], ['Blokada do', s['zawieszone']['dowod']]],
                note='Dowód znów będzie ważny od razu.' + (' Zastrzeżenie w bankach cofniesz osobno.' if 'dowod' in s['zastrzezone'] else ''), label='Odblokuj dowód')

@akcja('odwies_dowod')
def wykonaj(a, s):
    st(s); s['zawieszone'].pop('dowod', None)
    return dict(odblokowano='dowod', zastrzezony_w_bankach='dowod' in s['zastrzezone']), dict(icon='check', tone='ok', title='Dowód odblokowany', source='Rejestr Dowodów Osobistych',
        rows=[['Dowód osobisty', 'ważny, możesz go znów używać']] + ([['W bankach', 'nadal zastrzeżony, cofniesz to osobno']] if 'dowod' in s['zastrzezone'] else []))

@akcja('cofnij_zastrzezenie_dokumentu')
def podglad(a, s):
    st(s); x = a.get('dokument')
    if x in s['uniewaznione']:
        raise ValueError('%s jest unieważniony i nie da się go przywrócić. Powiedz: oddaj go w dowolnym urzędzie gminy, nowy wniosek złożysz tutaj.' % NAZWY.get(x, x))
    if x not in s['zastrzezone']:
        raise ValueError('W aplikacji nie ma zastrzeżenia tego dokumentu w bankach. Zastrzeżenie zrobione w banku cofniesz tylko w banku.' +
                         (' Dowód jest zablokowany: odblokujesz go akcją odwies_dowod.' if x in s['zawieszone'] else ''))
    return dict(icon='shield', title='Cofnięcie zastrzeżenia', source='System Dokumenty Zastrzeżone',
                rows=[[NAZWY.get(x, x), DOKUMENTY.get(x, {}).get('numer', '')], ['Cofnę', 'zastrzeżenie w bankach']],
                note='Cofniesz tylko zastrzeżenie zrobione w aplikacji. Zastrzeżenie z banku cofniesz w banku. Unieważnionego dowodu ani paszportu nie da się przywrócić.' +
                     (' Blokadę dowodu zdejmiesz osobno.' if x in s['zawieszone'] else ''), label='Cofnij')

@akcja('cofnij_zastrzezenie_dokumentu')
def wykonaj(a, s):
    st(s); x = a.get('dokument')
    if x in s['uniewaznione']:
        return dict(wykonano=False, powod='dokument jest unieważniony, potrzebny nowy'), dict(icon='alert', tone='warn', title='Nie można cofnąć', rows=[[NAZWY.get(x, x), 'unieważniony, złóż wniosek o nowy']])
    s['zastrzezone'] = [y for y in s['zastrzezone'] if y != x]
    return dict(cofnieto=x, nadal_zablokowany=x in s['zawieszone']), dict(icon='check', tone='ok', title='Zastrzeżenie cofnięte',
        rows=[[NAZWY.get(x, x), 'zastrzeżenie w bankach cofnięte']] + ([['Blokada dowodu', 'nadal do ' + s['zawieszone'][x]]] if x in s['zawieszone'] else []))

@akcja('zastrzez_pesel')
def podglad(a, s):
    if pesel_zastrzezony(s):
        raise ValueError('PESEL jest już %s. Nie wywołuj akcji, pokaż status (status_pesel).' % s['pesel'])
    return dict(icon='shield', title='Zastrzeżenie numeru PESEL', source='Rejestr Zastrzeżeń PESEL', rows=[['PESEL', pesel_maska()], ['Od', 'teraz'], ['Do', 'do odwołania']],
                note='Bank czy firma pożyczkowa muszą sprawdzić zastrzeżenie przed udzieleniem kredytu. Do lekarza, apteki czy urzędu pójdziesz jak dotąd. Czasowe odblokowanie zrobisz tutaj w kilka sekund.', label='Zastrzeż PESEL')
@akcja('zastrzez_pesel')
def wykonaj(a, s):
    s['pesel'] = 'zastrzeżony'
    return dict(status='zastrzeżony', od=teraz()), dict(icon='check', tone='ok', title='PESEL zastrzeżony', source='Rejestr Zastrzeżeń PESEL',
        rows=[['Status', 'zastrzeżony od ' + teraz()], ['Historia sprawdzeń', 'zobaczysz tutaj, kto i kiedy sprawdzał']])

def _do_kiedy(a):
    do = (a.get('do_kiedy') or '').strip()
    if do and ':' not in do: do += ', 23:59'
    return do

@akcja('cofnij_zastrzezenie_pesel')
def podglad(a, s):
    if not pesel_zastrzezony(s): raise ValueError('PESEL nie jest zastrzeżony, nie ma czego cofać.')
    do = _do_kiedy(a)
    return dict(icon='shield', title='Cofnięcie zastrzeżenia PESEL', source='Rejestr Zastrzeżeń PESEL',
                rows=[['Od', 'teraz'], ['Do', do or 'na stałe']] + ([['Potem', 'PESEL zastrzeże się sam']] if do else []), label='Odblokuj PESEL')
@akcja('cofnij_zastrzezenie_pesel')
def wykonaj(a, s):
    do = _do_kiedy(a)
    s['pesel'] = 'niezastrzeżony' + (' czasowo do ' + do if do else '')
    return dict(status=s['pesel']), dict(icon='check', tone='ok', title='PESEL odblokowany', source='Rejestr Zastrzeżeń PESEL',
        rows=[['Do', (do + ', potem zastrzeże się sam') if do else 'na stałe']])

POWODY = {'uplyw_waznosci': 'upływ ważności', 'utrata': 'utrata', 'zmiana_danych': 'zmiana danych', 'uszkodzenie': 'uszkodzenie'}
@akcja('wniosek_dowod')
def podglad(a, s):
    dz = dziecko(a)
    pw = POWODY.get(a.get('powod'), a.get('powod', ''))
    urz = a.get('miejsce_odbioru') or P()['urzad']
    rows = ([['Dla', dz['imie']]] if dz else []) + [[rodz('Wnioskodawczyni', 'Wnioskodawca'), imie_nazwisko()], ['Powód', pw], ['Zdjęcie', 'z aparatu, urząd może poprosić o inne'], ['Urząd', urz]]
    if dz and dz['wiek'] < 12:
        rows += [['Odciski palców', 'nie dotyczy (dziecko poniżej 12 lat)'], ['Odbiór', 'osobiście' + (', z dzieckiem' if dz['wiek'] >= 5 else '')]]
        note = 'Dowód będzie gotowy do 30 dni. Odbierzesz go osobiście w tym urzędzie.'
    else:
        rows.append(['Wizyta w urzędzie', 'do %s, %sodciski palców i podpis' % (plus(30), 'z dzieckiem: ' if dz else '')])
        note = 'Bez wizyty w urzędzie wniosek nie zostanie zrealizowany. Dowód odbierzesz osobiście w tym samym urzędzie.'
    rows.append(['Opłata', 'bezpłatnie'])
    return dict(icon='id', title='Wniosek o dowód osobisty', source='Rejestr PESEL, Rejestr Dowodów Osobistych', rows=rows, note=note, label='Podpisz i wyślij')
@akcja('wniosek_dowod')
def wykonaj(a, s):
    st(s); dz = dziecko(a); n = nr('DO')
    urz = a.get('miejsce_odbioru') or P()['urzad']
    kto = (' dla ' + dz['imie'].split()[0]) if dz else ''
    if dz and dz['wiek'] < 12:
        s['sprawy'].append(['Wniosek o dowód osobisty%s %s' % (kto, n), 'w realizacji, gotowy do 30 dni'])
        rows = [['Numer wniosku', n], ['Gotowy', 'do 30 dni'], ['Odbiór', 'osobiście w tym urzędzie' + (', z dzieckiem' if dz['wiek'] >= 5 else '')]]
        return dict(numer_wniosku=n, gotowy='do 30 dni', odbior=urz, wizyta_z_odciskami='nie dotyczy'), \
            dict(icon='check', tone='ok', title='Wniosek złożony', source='Twoje sprawy', rows=rows)
    wiz = plus(30)
    s['sprawy'].append(['Wniosek o dowód osobisty%s %s' % (kto, n), 'czeka na wizytę w urzędzie do ' + wiz])
    rows = [['Numer wniosku', n], ['Teraz', 'idź do urzędu do %s, %sodciski palców i podpis' % (wiz, 'z dzieckiem, ' if dz else '')], ['Gotowy', 'do 30 dni od wizyty'], ['Odbiór', 'osobiście w tym samym urzędzie']]
    rez = P().get('miasto') in ('Warszawa', 'Kraków')
    return dict(numer_wniosku=n, wizyta_do=wiz, cel_wizyty='odciski palców i wzór podpisu', urzad=urz, gotowy='do 30 dni od wizyty', odbior='osobiście w tym samym urzędzie',
                rezerwacja_wizyty='urząd ma rezerwację wizyt online na swojej stronie' if rez else 'zapytaj urząd o termin',
                nastepne=['przypomnienie o wizycie (ustaw_przypomnienie)']), dict(icon='check', tone='ok', title='Wniosek złożony', source='Twoje sprawy', rows=rows)

@akcja('wniosek_paszport')
def podglad(a, s):
    dz = dziecko(a)
    if not dz or dz['wiek'] >= 12:
        raise ValueError('Paszport dla dorosłego i dla dziecka od 12 lat składa się tylko osobiście w punkcie paszportowym (odciski palców). Paszport tymczasowy też tylko osobiście. '
                         'Online złożysz wniosek wyłącznie dla dziecka poniżej 12 lat. Użyj gdzie_zalatwic i zaproponuj przypomnienie albo listę do zabrania.')
    kdr = 'kdr' in DOKUMENTY
    oplata = '15 zł' if kdr else '30 zł'
    drugi = P()['drugi_rodzic']
    rows = [['Dla', dz['imie']], ['Zdjęcie', 'z aparatu, musi spełniać wymogi gov.pl'], ['Odbiór', (a.get('miejsce_odbioru') or P()['urzad_paszportowy']) + (', z dzieckiem' if dz['wiek'] >= 5 else '')],
            ['Opłata', oplata + (' z Kartą Dużej Rodziny' if kdr else '')]]
    if drugi: rows.append(['Zgoda drugiego rodzica', '%s, poproszę o nią w %s mObywatelu' % (drugi, 'jego' if P()['plec'] == 'K' else 'jej')])
    return dict(icon='id', title='Wniosek o paszport dla dziecka', source='Rejestr PESEL, Rejestr Dokumentów Paszportowych', rows=rows,
                note='Drugi rodzic da zgodę online w usłudze Wyraź zgodę na wydanie paszportu. Bez niej paszport nie zostanie wydany.' if drugi else None,
                label='Podpisz i zapłać ' + oplata)
@akcja('wniosek_paszport')
def wykonaj(a, s):
    st(s); dz = dziecko(a); n = nr('PA')
    drugi = P()['drugi_rodzic']; z = ', z dzieckiem' if dz['wiek'] >= 5 else ''
    s['sprawy'].append(['Wniosek o paszport dla %s %s' % (dz['imie'].split()[0], n), 'czeka na zgodę drugiego rodzica' if drugi else 'w realizacji'])
    return dict(numer_wniosku=n, gotowy='ok. miesiąca', odbior='osobiście' + z, zgoda=('czeka na zgodę ' + P()['drugi_rodzic_dop']) if drugi else 'nie dotyczy'), \
        dict(icon='check', tone='ok', title='Wniosek o paszport złożony', source='Twoje sprawy',
             rows=[['Numer wniosku', n]] + ([['Zgoda', drugi + ': czeka']] if drugi else []) + [['Gotowy', 'ok. miesiąca, dam znać'], ['Odbiór', 'osobiście' + z]])

# --- rodzina
@akcja('zglos_urodzenie')
def podglad(a, s):
    if P()['plec'] == 'M' and not P()['drugi_rodzic']:
        raise ValueError('Ojciec, który nie jest mężem mamy dziecka, zgłosi urodzenie online dopiero po uznaniu ojcostwa w USC. Zgłoszenie może też wysłać mama. Powiedz to i nie zbieraj danych.')
    im = (a.get('imie', '') + ' ' + (a.get('drugie_imie') or '')).strip()
    naz = P()['nazwisko_dziecka'][0] if a.get('plec') == 'K' else P()['nazwisko_dziecka'][1]
    odp = a.get('odpis') or 'elektronicznie'
    return dict(icon='baby', title='Zgłoszenie urodzenia dziecka', source='Rejestr PESEL, USC',
                rows=[['Dziecko', im + ' ' + naz], ['Rodzice', P()['rodzice']], ['Miejsce urodzenia', a.get('miejsce_urodzenia') or P()['szpital']],
                      ['Zameldowanie', P()['zameldowanie_krotko']], ['Odpis skrócony aktu', 'bezpłatnie, do Twojej skrzynki' if odp == 'elektronicznie' else 'bezpłatnie, ' + odp],
                      ['Termin', '21 dni od wystawienia karty urodzenia'], ['Opłata', 'bezpłatnie']], label='Podpisz i wyślij')
@akcja('zglos_urodzenie')
def wykonaj(a, s):
    s.setdefault('dzieci_nowe', []).append(a.get('imie', ''))
    ub = 'zgłosisz w eZUS (ZUS ZCNA) w ciągu 7 dni' if przedsiebiorca() else 'zgłosi pracodawca (ZUS ZCNA), przekaż mu PESEL dziecka w ciągu 7 dni'
    dzieci = len([r for r in P()['rodzina'] if r.get('rola') in ('syn', 'córka')]) + len(s['dzieci_nowe'])
    nast = ['800+ (wniosek_800plus; w ciągu 3 miesięcy od urodzenia daje świadczenie od dnia urodzenia)', 'zgłoszenie do ubezpieczenia zdrowotnego (gdzie_zalatwic)']
    if 'kdr' in DOKUMENTY or dzieci >= 3: nast.append('Karta Dużej Rodziny dla dziecka (gdzie_zalatwic)')
    return dict(zgloszono=True, pesel_nadany=False, pesel='po sporządzeniu aktu, zwykle następny dzień roboczy', odpis='bezpłatny odpis skrócony do skrzynki e-Doręczeń',
                ubezpieczenie_zdrowotne=ub, nastepne=nast), dict(icon='check', tone='ok', title='Urodzenie zgłoszone', source=P()['usc'],
        rows=[['Status', 'zgłoszenie wysłane do USC'], ['PESEL i akt', 'zwykle następnego dnia roboczego'], ['Odpis skrócony aktu', 'bezpłatnie, do Twojej skrzynki'],
              ['Ubezpieczenie zdrowotne', ub]])

def _noworodek(a, s):
    x = (a.get('dziecko') or '').strip().lower()
    return bool(x) and any(n and x.split()[0] == n.strip().lower().split()[0] for n in s.get('dzieci_nowe', []))

@akcja('wniosek_800plus')
def podglad(a, s):
    nowe = _noworodek(a, s)
    return dict(icon='coin', title='Wniosek o świadczenie 800+', source='ZUS, rejestr PESEL',
                rows=[['Dziecko', a.get('dziecko', '')], ['Kwota', '800 zł miesięcznie'], ['Od kiedy', 'od dnia urodzenia, jeśli wyślesz w ciągu 3 miesięcy' if nowe else 'od miesiąca złożenia wniosku'],
                      ['Okres', 'do 31.05.2027, potem nowy wniosek od 1 lutego'], ['Konto do wypłaty', P()['konto']]], label='Wyślij do ZUS')
@akcja('wniosek_800plus')
def wykonaj(a, s):
    nowe = _noworodek(a, s)
    return dict(zlozony=True, rozpatrzenie='zwykle do 1 miesiąca, najdłużej 2', odpowiedz='informacja w eZUS i e-mail, bez decyzji papierowej'), \
        dict(icon='check', tone='ok', title='Wniosek wysłany do ZUS',
             rows=[['Odpowiedź', 'na Twoje konto w eZUS, zwykle w ciągu miesiąca'], ['Wypłata', 'z wyrównaniem od dnia urodzenia' if nowe else 'na konto z wniosku']])

# --- korespondencja
@akcja('wyslij_pismo')
def podglad(a, s):
    zal = a.get('zalaczniki') or []
    return dict(icon='mail', title='Wysyłka przez e-Doręczenia', source='Do: ' + a.get('adresat', ''), body=a.get('tresc', ''),
                rows=[['Temat', a.get('temat', '')], ['Załączniki', '%d plików' % len(zal) if zal else 'brak'], ['Podpis', 'podpis zaufany']], label='Podpisz i wyślij')
@akcja('wyslij_pismo')
def wykonaj(a, s):
    s.setdefault('pisma_wyslane', []).append(P()['skrzynka'][0]['id'])
    return dict(doreczono=True, dowod_otrzymania=True), dict(icon='check', tone='ok', title='Pismo doręczone', source='e-Doręczenia, dowód otrzymania',
        rows=[['Adresat', a.get('adresat', '')], ['Dowód otrzymania', 'w skrzynce, godz. ' + teraz()], ['Termin', 'zachowany']])

@akcja('podpisz_dokument')
def podglad(a, s):
    r = a.get('rodzaj') or ('osobisty' if e_dowod() else 'zaufany')
    uwaga = None
    if r in ('osobisty', 'kwalifikowany') and not e_dowod():
        r = 'zaufany'; uwaga = 'Twój dowód nie ma warstwy elektronicznej, więc podpiszesz podpisem zaufanym.'
    if r == 'osobisty': p = 'osobisty: przyłóż e-dowód do telefonu, CAN i PIN do podpisu'
    elif r == 'kwalifikowany': p = 'kwalifikowany, bezpłatny: zostały 4 z 5 w tym miesiącu'; uwaga = 'Bezpłatny podpis kwalifikowany jest do spraw prywatnych. Potrzebny jest e-dowód z warstwą elektroniczną.'
    else: p = 'podpis zaufany'
    return dict(icon='doc', title='Podpis dokumentu', source='Twoje pliki', rows=[['Dokument', a.get('dokument', '')], ['Podpis', p], ['Plik', 'PDF do 5 MB']], note=uwaga, label='Podpisz')
@akcja('podpisz_dokument')
def wykonaj(a, s):
    return dict(podpisano=True, plik=a.get('dokument', '') + ' (podpisany)'), dict(icon='check', tone='ok', title='Dokument podpisany', rows=[['Plik', a.get('dokument', '') + ', podpisany'], ['Udostępnij', 'e-mail, e-Doręczenia lub AirDrop']])

CENY_KW = {'odpis_zwykly': '30 zł', 'odpis_zupelny': '75 zł', 'wyciag': '10 zł', 'zaswiadczenie_o_zamknieciu': '10 zł'}
NAZWY_KW = {'odpis_zwykly': 'odpis zwykły', 'odpis_zupelny': 'odpis zupełny', 'wyciag': 'wyciąg z jednego działu', 'zaswiadczenie_o_zamknieciu': 'zaświadczenie o zamknięciu księgi'}
@akcja('zamow_odpis_kw')
def podglad(a, s):
    r = a.get('rodzaj', 'odpis_zwykly')
    c = CENY_KW.get(r, '30 zł')
    return dict(icon='doc', title='Zamówienie z księgi wieczystej', source='Centralna Informacja Ksiąg Wieczystych',
                rows=[['Księga', a.get('ksiega') or (P()['ksiegi'][0]['numer'] if P()['ksiegi'] else '')], ['Rodzaj', NAZWY_KW.get(r, r)], ['Opłata', c], ['Płatność', 'BLIK']], label='Zapłać ' + c)
@akcja('zamow_odpis_kw')
def wykonaj(a, s):
    k = (a.get('ksiega') or (P()['ksiegi'][0]['numer'] if P()['ksiegi'] else 'KW')).replace('/', '_')
    return dict(gotowe=True, plik='odpis_%s.pdf' % k), dict(icon='check', tone='ok', title='Odpis gotowy',
        rows=[['Plik', 'odpis_%s.pdf' % k], ['Moc prawna', 'jak dokument z sądu'], ['Dostęp', 'w Zamówionych dokumentach przez 2 lata']])

# --- finanse
def _platnosc(a):
    ids = a.get('pozycje') or [x['id'] for x in NALEZNOSCI]
    p = [x for x in NALEZNOSCI if x['id'] in ids] or list(NALEZNOSCI)
    tak = [x for x in p if kanal(x) == 'eplatnosci']
    nie = [x for x in p if x not in tak]
    if not tak:
        raise ValueError('Tego nie zapłacisz w aplikacji. ' + '; '.join(gdzie_zaplacisz(x) for x in nie) + '. Możesz zaproponować przypomnienie.')
    metody = None
    for x in tak:
        m = x.get('metody') or ['BLIK']
        metody = [y for y in (metody or m) if y in m]
    metody = metody or ['BLIK']
    chce = a.get('metoda')
    metoda = chce if chce in metody else metody[0]
    return tak, nie, metoda, metody, bool(chce and chce not in metody)

@akcja('zaplac')
def podglad(a, s):
    tak, nie, metoda, metody, zmiana = _platnosc(a)
    suma = sum(x['kwota'] for x in tak)
    rows = [[x['tytul'], zl(x['kwota'])] for x in tak] + [['Metoda', metoda + (' (w tej gminie tylko BLIK)' if zmiana and metody == ['BLIK'] else '')]]
    note = ' '.join(gdzie_zaplacisz(x) + '.' for x in nie) or None
    return dict(icon='coin', title='Płatność', source='ePłatności', rows=rows, note=note, label='Zapłać ' + zl(suma))
@akcja('zaplac')
def wykonaj(a, s):
    tak, nie, metoda, metody, zmiana = _platnosc(a)
    ids = [x['id'] for x in tak]; suma = sum(x['kwota'] for x in tak)
    s['zaplacone'] = sorted(set(s.get('zaplacone', [])) | set(ids))
    return dict(zaplacono=ids, metoda=metoda, potwierdzenie='EP/2026/7 214 088', niezaplacone=[gdzie_zaplacisz(x) for x in nie]), \
        dict(icon='check', tone='ok', title='Zapłacono', source='ePłatności',
             rows=[['Potwierdzenie', 'EP/2026/7 214 088'], ['Kwota', zl(suma)], ['Prowizja', 'brak']])

def kod_pocztowy():
    m = re.search(r'\d{2}-\d{3}', OSOBA['adres'] or '')
    return m.group(0) if m else ''

@akcja('umow_ewizyte_zus')
def podglad(a, s):
    return dict(icon='clock', title='E-wizyta w ZUS', source='ZUS',
                rows=[['Temat', a.get('temat', '')], ['Termin', a.get('termin', '')], ['Forma', 'wideorozmowa z doradcą ZUS'], ['Kod pocztowy', kod_pocztowy()], ['E-mail', OSOBA['email']]], label='Zarezerwuj')
@akcja('umow_ewizyte_zus')
def wykonaj(a, s):
    return dict(zarezerwowano=True, link='w e-mailu od ZUS i przycisk Dołącz w aplikacji'), dict(icon='check', tone='ok', title='E-wizyta zarezerwowana',
        rows=[['Termin', a.get('termin', '')], ['Link', 'w e-mailu od ZUS i przycisk Dołącz w aplikacji'], ['Przypomnienie', 'e-mail lub SMS od ZUS']])

# --- pojazdy
def wybrany_pojazd(a, wymagaj=False):
    ps = P()['pojazdy']
    n = norm_rej(a.get('nr_rejestracyjny') or a.get('pojazd') or '')
    p = next((p for p in ps if n and (norm_rej(p['nr']) in n or norm_rej(p.get('model', '')) in n or n in norm_rej(p['marka']) or (len(n) >= 4 and n[:5] in norm_rej(p['marka'])))), None)
    if p: return p
    if len(ps) == 1 or not wymagaj: return ps[0]
    raise ValueError('Nie wiem, który pojazd: %s. Zapytaj: „Który pojazd sprzedajesz?”' % ', '.join('%s %s' % (krotka(q), q['nr']) for q in ps))
def krotka(p): return (p.get('model') or p['marka']).replace(' Combi', '')

@akcja('zglos_zbycie_pojazdu')
def podglad(a, s):
    p = wybrany_pojazd(a, wymagaj=True)
    if p.get('leasing'):
        raise ValueError('%s jest w leasingu, jego właścicielem jest %s. Sprzedaż zgłasza leasingodawca, nie Ty.' % (krotka(p), p['leasing']))
    return dict(icon='car', title='Zgłoszenie zbycia pojazdu', source='CEPiK',
                rows=[['Pojazd', p['marka'] + ', ' + p['nr']], ['VIN', p.get('vin', '')], ['Nabywca', a.get('nabywca', '')], ['Data umowy', a.get('data') or pl(DZIS)],
                      ['Załącznik', 'umowa sprzedaży (z Twoich plików lub zdjęcie)'], ['Do', P()['wydzial_komunikacji']]],
                note='Masz na to 30 dni od umowy. Spóźnienie grozi karą od 200 do 1000 zł.', label='Zgłoś zbycie', pojazd=sylw(p))
@akcja('zglos_zbycie_pojazdu')
def wykonaj(a, s):
    p = wybrany_pojazd(a, wymagaj=True)
    return dict(zgloszono=True, uwaga='powiadom ubezpieczyciela (%s) o sprzedaży w ciągu 30 dni' % p['ubezpieczyciel']), dict(icon='check', tone='ok', title='Zbycie zgłoszone',
        rows=[['Adresat', P()['wydzial_komunikacji']], ['Pamiętaj', 'powiadom ubezpieczyciela (%s) o sprzedaży w ciągu 30 dni' % p['ubezpieczyciel']]])

@akcja('umowa_kupna_pojazdu')
def podglad(a, s):
    return dict(icon='doc', title='Umowa kupna-sprzedaży pojazdu', source='Twoje pliki, rejestr PESEL',
                rows=[['Pojazd', a.get('pojazd', '')], ['Sprzedający', a.get('sprzedajacy', '')], [rodz('Kupująca', 'Kupujący'), imie_nazwisko()], ['Cena', a.get('cena', '')],
                      ['Podpis', 'podpis zaufany lub osobisty, Twój i sprzedającego']], label='Wyślij do podpisu')
@akcja('umowa_kupna_pojazdu')
def wykonaj(a, s):
    return dict(wyslano=True, dalej='PCC-3 w 14 dni (tutaj), rejestracja w wydziale komunikacji w 30 dni, tablice i dowód rejestracyjny odbiera się osobiście'), \
        dict(icon='check', tone='ok', title='Umowa wysłana do sprzedającego', source='Czeka na podpis sprzedającego',
             rows=[['Dalej', 'PCC-3 w 14 dni, złożysz tutaj'], ['Rejestracja', 'w wydziale komunikacji w 30 dni, tablice i dowód odbierzesz osobiście']])

@akcja('oswiadczenie_kolizji')
def podglad(a, s):
    spr = a.get('sprawca', '')
    ja = imie_nazwisko() + ', ' + POJAZD['nr']
    return dict(icon='car', title='Oświadczenie o zdarzeniu drogowym', source='mStłuczka, CEPiK, rejestr PESEL',
                rows=[['Sprawca', ja if spr == 'ja' else DRUGA_STRONA['kierowca'] + ', WPI 22R31'], ['Poszkodowany', DRUGA_STRONA['kierowca'] + ', WPI 22R31' if spr == 'ja' else ja],
                      ['Okoliczności', a.get('okolicznosci', '')], ['Miejsce', a.get('miejsce') or 'parking, lokalizacja z GPS'], ['Potwierdzenie', 'obie strony w mObywatelu']],
                note='Dostaniecie oboje PDF z pieczęcią elektroniczną ministra cyfryzacji.', label='Potwierdź oświadczenie')
@akcja('oswiadczenie_kolizji')
def wykonaj(a, s):
    return dict(numer='MS/2026/10/25 118', zapisane=True, ubezpieczyciel_sprawcy=POJAZD['ubezpieczyciel'] if a.get('sprawca') == 'ja' else 'PZU',
                szkode_zglasza='druga strona' if a.get('sprawca') == 'ja' else 'Ty, z aplikacji (zglos_szkode)'), \
        dict(icon='check', tone='ok', title='Oświadczenie potwierdzone', source='mStłuczka',
             rows=[['Numer', 'MS/2026/10/25 118'], ['PDF', 'u obu kierowców, z pieczęcią ministra cyfryzacji']])

@akcja('zglos_szkode')
def podglad(a, s):
    return dict(icon='car', title='Zgłoszenie szkody', source='Do: ' + a.get('ubezpieczyciel', 'PZU'), rows=[['Oświadczenie', a.get('oswiadczenie') or 'MS/2026/10/25 118'], ['Zdjęcia', a.get('zdjecia') or 'z rozmowy'], ['Opis', a.get('opis', '')]], label='Zgłoś szkodę')
@akcja('zglos_szkode')
def wykonaj(a, s):
    return dict(numer_szkody='2026/11/553 017', dalej='ubezpieczyciel potwierdzi i zacznie likwidację w 7 dni, wypłata zwykle do 30 dni'), dict(icon='check', tone='ok', title='Szkoda zgłoszona', source='Przekazane do ubezpieczyciela',
        rows=[['Numer szkody', '2026/11/553 017'], ['Dalej', 'ubezpieczyciel potwierdzi i zacznie likwidację w 7 dni'], ['Wypłata', 'zwykle do 30 dni']])

def _wartosc(a): return float(str(a.get('cena', 0)).replace(' ', '').replace(' ', '').replace('zł', '').replace(',', '.') or 0)
@akcja('zloz_pcc3')
def podglad(a, s):
    c = _wartosc(a)
    if c <= 1000: raise ValueError('Przy wartości do 1000 zł nie płacisz PCC i nie składasz deklaracji.')
    return dict(icon='coin', title='Deklaracja PCC-3', source='e-Urząd Skarbowy',
                rows=[['Pojazd', a.get('pojazd', '')], ['Wartość rynkowa', zl(c)], ['Podatek 2%', zl(round(c * 0.02))], ['Termin', '14 dni od podpisania umowy'], ['Urząd', 'urząd skarbowy właściwy dla Twojego adresu']],
                note='Podatek liczy się od wartości rynkowej. Jeśli cena jest dużo niższa, urząd może ją podnieść. Nie płacisz go, gdy kupujesz auto od firmy z fakturą.', label='Złóż i zapłać ' + zl(round(c * 0.02)))
@akcja('zloz_pcc3')
def wykonaj(a, s):
    c = _wartosc(a)
    return dict(zlozono=True, zaplacono=zl(round(c * 0.02)), upo='PCC/2026/10/77 104'), dict(icon='check', tone='ok', title='PCC-3 złożone i zapłacone', rows=[['Podatek', zl(round(c * 0.02)) + ', zapłacony'], ['UPO', 'PCC/2026/10/77 104']])

# --- bezpieczeństwo, zgłoszenia
def _cert(a):
    kat = a.get('kategoria', ''); opis = a.get('opis', '')
    adres = a.get('adres') or next(iter(re.findall(r'([a-z0-9-]+(?:\.[a-z0-9-]+)+)(?:/|\b)', opis.lower())), '')
    sms = 'sms' in (kat + ' ' + (a.get('skad') or '') + ' ' + opis).lower()
    return kat, opis, adres, sms
@akcja('zglos_incydent_cert')
def podglad(a, s):
    kat, opis, adres, sms = _cert(a)
    rows = [['Kategoria', kat]] + ([['Adres', adres]] if adres else []) + ([['Skąd', a['skad']]] if a.get('skad') else ([['Skąd', 'link z SMS-a']] if sms and adres else []))
    if not adres: rows.append(['Szczegóły', opis])
    return dict(icon='shield', title='Zgłoszenie do CERT Polska', source='Bezpiecznie w sieci', rows=rows, label='Wyślij zgłoszenie')
@akcja('zglos_incydent_cert')
def wykonaj(a, s):
    kat, opis, adres, sms = _cert(a)
    return dict(przekazano=True, sms_przekaz_na_8080=sms), dict(icon='check', tone='ok', title='Zgłoszenie wysłane', source='Bezpiecznie w sieci',
        rows=[['Status', 'przekazane do CERT Polska']] + ([['SMS', 'prześlij go jeszcze na bezpłatny numer 8080']] if sms else []))

ZGL = {'sanepid': ('Zagrożenie zdrowia publicznego', 'Państwowa Inspekcja Sanitarna'), 'gios': ('Naruszenie środowiskowe', 'Główny Inspektorat Ochrony Środowiska'),
       'internet': ('Dostęp do internetu', 'internet.gov.pl, Ministerstwo Cyfryzacji')}
@akcja('zgloszenie')
def podglad(a, s):
    i = a.get('instytucja')
    t, src = ZGL.get(i, ('Zgłoszenie', a.get('instytucja', '')))
    m = a.get('miejsce') or (P()['zameldowanie_krotko'] if i == 'internet' else 'Twoja lokalizacja z GPS')
    return dict(icon='alert', title=t, source=src, rows=[['Kategoria', a.get('kategoria', '')], ['Miejsce' if i != 'internet' else 'Adres', m], ['Opis', a.get('opis', '')]], label='Wyślij zgłoszenie')
@akcja('zgloszenie')
def wykonaj(a, s):
    i = a.get('instytucja')
    rows = {'sanepid': [['Status', 'wysłane do sanepidu'], ['Wynik kontroli', 'dostaniesz na podany telefon lub e-mail']],
            'gios': [['Status', 'wysłane do GIOŚ'], ['Zdjęcie i miejsce', 'dołączone']],
            'internet': [['Status', 'zapisane w internet.gov.pl'], ['Dalej', 'operatorzy mogą przysłać ofertę, ale nie muszą']]}.get(i, [['Status', 'wysłane']])
    return dict(numer=nr('ZG'), wyslano=True), dict(icon='check', tone='ok', title='Zgłoszenie wysłane', rows=rows)

@akcja('zapisz_na_szkolenie')
def podglad(a, s):
    k = next((x for x in KURSY if x['id'] == a.get('kurs_id')), KURSY[0])
    return dict(icon='shield', title='Zapis: kurs ' + k['rodzaj'], source='MON, wGotowości', rows=[['Termin', k['termin']], ['Miejsce', k['miejsce']], ['Czas', 'ok. 8 godzin'], ['Koszt', 'bezpłatnie']], label='Zapisz mnie')
@akcja('zapisz_na_szkolenie')
def wykonaj(a, s):
    return dict(zapisano=True), dict(icon='check', tone='ok', title='Zapisano na kurs', rows=[['Status', 'zapisano'], ['Przypomnienie', 'dzień wcześniej']])

def _osoby_podrozy(a):
    dorosli = {r['imie'].split()[0].lower(): r['imie'] for r in P()['rodzina'] if r.get('wiek') is None or r['wiek'] >= 18}
    ja = imie_nazwisko(); os_, sami = [ja], []
    for o in a.get('osoby') or []:
        k = (o or '').strip().split()[0].lower() if (o or '').strip() else ''
        if not k or k == OSOBA['imie'].lower(): continue
        if k in dorosli: sami.append(dorosli[k])
        else: os_.append(o)
    return os_, sami
@akcja('zglos_podroz')
def podglad(a, s):
    os_, sami = _osoby_podrozy(a)
    rows = [['Kraj', a.get('kraj', '')]] + ([['Termin', 'od %s do %s' % (a.get('od', ''), a.get('do', ''))]] if a.get('od') or a.get('do') else []) + \
           [['Osoby', ', '.join(os_)], ['Komunikaty MSZ', 'SMS i e-mail']]
    return dict(icon='doc', title='Zgłoszenie podróży (Odyseusz)', source='MSZ', rows=rows,
                note=('%s zgłosi się sam w swoim mObywatelu.' if P()['plec'] == 'K' else '%s zgłosi się sama w swoim mObywatelu.') % ', '.join(sami) if sami else None, label='Zgłoś podróż')
@akcja('zglos_podroz')
def wykonaj(a, s):
    os_, sami = _osoby_podrozy(a)
    return dict(zgloszono=True, osoby=os_, dorosli_zglaszaja_sie_sami=sami, powiadomienia='dodaj kraj do obserwowanych, wtedy push przez 6 miesięcy'), \
        dict(icon='check', tone='ok', title='Podróż zgłoszona', rows=[['MSZ', 'skontaktuje się z Tobą w razie zagrożenia'], ['Powiadomienia', 'dodaj %s do obserwowanych' % a.get('kraj', 'kraj')]])

def _glosowanie(a):
    rodzaj = a.get('rodzaj') or 'jednorazowy'
    m = (a.get('miejscowosc') or '').strip()
    w = P()['wybory']
    if rodzaj == 'jednorazowy':
        dw = w.get('data_wyborow')
        dni = (d(dw) - DZIS).days if dw else None
        if dni is None or not 3 <= dni <= 44:
            raise ValueError('Jednorazową zmianę miejsca głosowania złożysz od 44. do 3. dnia przed dniem wyborów. ' +
                             ('Wybory do Sejmu i Senatu (jesień 2027) nie są jeszcze zarządzone. ' if not dw else '') +
                             'Zaproponuj przypomnienie (ustaw_przypomnienie), a jeśli mieszka w tej gminie na stałe bez meldunku, zmianę stałego obwodu (rodzaj=staly).')
        return rodzaj, m, None, None, dw
    if m and m[:4].lower() in (w.get('lokal', '') + ' ' + w.get('obwod', '')).lower():
        raise ValueError('Jesteś już w rejestrze wyborców w tej gminie (%s), zmiana stałego obwodu nie jest potrzebna.' % w.get('krotko', ''))
    adres = a.get('adres') or (OSOBA['adres'].split(', pobyt')[0] if m and m[:4].lower() in OSOBA['adres'].lower() else '')
    if not adres: raise ValueError('Do zmiany stałego obwodu potrzebny jest adres, pod którym mieszkasz na stałe w tej gminie. Zapytaj o niego.')
    zal = next((x['nazwa'] for x in P()['pliki'] if 'najm' in x['nazwa'].lower() and (not m or m[:4].lower() in (x['nazwa'] + x['opis'] + adres).lower())), None)
    urz = P()['urzad'].split(',')[0] if m and m[:4].lower() == (P().get('miasto') or '')[:4].lower() else 'urząd gminy ' + m
    return rodzaj, m, adres, (zal, urz), None

@akcja('zmien_miejsce_glosowania')
def podglad(a, s):
    rodzaj, m, adres, x, dw = _glosowanie(a)
    if rodzaj == 'jednorazowy':
        return dict(icon='doc', title='Zmiana miejsca głosowania', source='Centralny Rejestr Wyborców, przez e-Doręczenia',
                    rows=[['Miejscowość', m], ['Adres w dniu wyborów', a.get('adres') or m], ['Dotyczy', 'wyborów %s' % pld_(dw)]], label='Złóż wniosek')
    zal, urz = x
    return dict(icon='doc', title='Zmiana stałego obwodu głosowania', source=urz + ', przez e-Doręczenia',
                rows=[['Adres zamieszkania', adres], ['Załącznik', zal or 'oświadczenie o stałym zamieszkaniu'], ['Decyzja urzędu', 'do 5 dni'], ['Dotyczy', 'wszystkich wyborów, także samorządowych w gminie %s' % m]],
                note='Oświadczasz, że mieszkasz pod tym adresem na stałe. Urząd może poprosić o dodatkowy dowód.', label='Złóż wniosek')
@akcja('zmien_miejsce_glosowania')
def wykonaj(a, s):
    rodzaj, m, adres, x, dw = _glosowanie(a)
    st(s)
    if rodzaj == 'jednorazowy':
        s['sprawy'].append(['Zmiana miejsca głosowania: ' + m, 'wniosek złożony'])
        return dict(zlozono=True, rodzaj=rodzaj), dict(icon='check', tone='ok', title='Wniosek złożony', rows=[['Status', 'wniosek złożony'], ['Obwód i lokal', 'przyjdą do skrzynki e-Doręczeń']])
    s['sprawy'].append(['Zmiana stałego obwodu głosowania: ' + m, 'decyzja urzędu do 5 dni'])
    return dict(zlozono=True, rodzaj=rodzaj, decyzja='do 5 dni, do skrzynki e-Doręczeń'), dict(icon='check', tone='ok', title='Wniosek złożony',
        rows=[['Status', 'wniosek złożony'], ['Decyzja', 'przyjdzie do skrzynki e-Doręczeń w ciągu 5 dni']])
def pld_(s):
    try: return pl(d(s))
    except (ValueError, TypeError): return s or ''

FORMY = {'skala': 'skala podatkowa', 'liniowy': 'podatek liniowy 19%', 'ryczałt': 'ryczałt od przychodów ewidencjonowanych'}
def _start(a):
    t = (a.get('data_rozpoczecia') or '').strip()
    for f in ('%d.%m.%Y', '%Y-%m-%d'):
        try: return datetime.datetime.strptime(t, f).date()
        except ValueError: pass
    return None
@akcja('zaloz_firme')
def podglad(a, s):
    return dict(icon='doc', title='Wniosek CEIDG-1', source='CEIDG',
                rows=[['Nazwa', a.get('nazwa', '')], ['PKD 2025', ', '.join(a.get('pkd') or [])], ['Start', a.get('data_rozpoczecia', '')], ['Adres', OSOBA['adres']],
                      ['Podatek', FORMY.get(a.get('forma_opodatkowania'), a.get('forma_opodatkowania') or 'skala podatkowa')], ['e-Doręczenia', 'założę adres do e-Doręczeń firmy'],
                      ['NIP i REGON', 'nadane automatycznie'], ['Podpis', 'profil zaufany']],
                note='Do ubezpieczeń w ZUS zgłosisz się w 7 dni od startu na biznes.gov.pl. VAT-R składasz osobno, jeśli będziesz płacić VAT.', label='Podpisz i wyślij')
@akcja('zaloz_firme')
def wykonaj(a, s):
    t = _start(a)
    zus = pl(t + datetime.timedelta(days=7)) if t else None
    return dict(zlozono=True, wpis='najpóźniej następnego dnia roboczego', zus_do=zus or '7 dni od startu', vat_r='osobno, przed pierwszą sprzedażą z VAT',
                nastepne=['przypomnienie o zgłoszeniu do ZUS (ustaw_przypomnienie)']), dict(icon='check', tone='ok', title='Wniosek o wpis do CEIDG złożony',
        rows=[['Wpis w CEIDG', 'najpóźniej następnego dnia roboczego'], ['NIP i REGON', 'trafią do wpisu automatycznie'],
              ['Zgłoszenie do ubezpieczeń w ZUS', ('do ' + zus if zus else 'w 7 dni od startu') + ', na biznes.gov.pl']])

def _kontakt(a, s):
    k = s.get('kontakt_kod') or {}
    tel = a.get('telefon') or (k.get('telefon') if a.get('kod') else None)
    em = a.get('email') or (k.get('email') if a.get('kod') else None)
    if not tel and not em: raise ValueError('Podaj nowy numer telefonu albo adres e-mail.')
    return tel, em
@akcja('aktualizuj_dane_kontaktowe')
def podglad(a, s):
    tel, em = _kontakt(a, s)
    r = ([['Telefon', tel]] if tel else []) + ([['E-mail', em]] if em else [])
    kod = re.sub(r'\D', '', str(a.get('kod') or ''))
    if a.get('kod'):
        if not 4 <= len(kod) <= 8: raise ValueError('Kod powinien składać się z cyfr z SMS-a lub e-maila. Poproś o niego jeszcze raz.')
        return dict(icon='id', title='Potwierdzenie danych kontaktowych', source='Rejestr Danych Kontaktowych', rows=r + [['Kod', kod]], label='Zapisz')
    return dict(icon='id', title='Zmiana danych kontaktowych', source='Rejestr Danych Kontaktowych',
                rows=r + [['Potwierdzenie', 'kodem wysłanym na nowy numer' if tel else 'kodem wysłanym na nowy adres']], label='Wyślij kod')
@akcja('aktualizuj_dane_kontaktowe')
def wykonaj(a, s):
    tel, em = _kontakt(a, s)
    r = ([['Telefon', tel]] if tel else []) + ([['E-mail', em]] if em else [])
    if a.get('kod'):
        s.pop('kontakt_kod', None)
        return dict(zapisano=True), dict(icon='check', tone='ok', title='Dane kontaktowe zaktualizowane', source='Rejestr Danych Kontaktowych', rows=r)
    s['kontakt_kod'] = dict(telefon=tel, email=em)
    return dict(kod_wyslany=True, zapisano=False, dalej='poproś o kod i wywołaj tę akcję ponownie z parametrem kod; kod jest ważny 24 godziny'), \
        dict(icon='check', tone='ok', title='Kod wysłany', source='Rejestr Danych Kontaktowych',
             rows=r + [['Potwierdź', 'kodem z SMS-a, w ciągu 24 godzin' if tel else 'kodem z e-maila, w ciągu 24 godzin']])
