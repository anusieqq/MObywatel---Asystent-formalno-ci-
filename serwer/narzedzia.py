# -*- coding: utf-8 -*-
"""Definicje narzędzi dla Claude (JSON Schema)."""

def S(t='string', d=None, e=None, items=None):
    x = {'type': t}
    if d: x['description'] = d
    if e: x['enum'] = e
    if items: x['items'] = items
    return x
ARR = lambda d=None, e=None: S('array', d, items=S('string', e=e))
def T(name, desc, props=None, req=None):
    return {'name': name, 'description': desc, 'input_schema': {'type': 'object', 'properties': props or {}, 'required': req or []}}

DOK = ['dowod', 'paszport']

ODCZYTY = [
    T('gdzie_zalatwic', 'Gdy sprawy nie załatwisz w tej aplikacji (część z nich da się zrobić online na gov.pl): zwraca, gdzie i jak to załatwić. Np. zameldowanie, wymeldowanie, rejestracja auta, wniosek o prawo jazdy, wtórnik lub wymiana prawa jazdy, paszport dla dorosłego lub dziecka od 12 lat, paszport tymczasowy, badanie techniczne, ślub, zmiana nazwiska, zgon, L4, roczny PIT, Karta Dużej Rodziny, zgłoszenie dziecka do ubezpieczenia, wizyta u lekarza, wniosek o emeryturę. Wywołaj od razu, zanim o cokolwiek zapytasz.', {'sprawa': S()}, ['sprawa']),
    T('karta_uslugi', 'Oficjalne karty usług z gov.pl i biznes.gov.pl: czy sprawę da się załatwić przez internet, co trzeba zrobić osobiście w urzędzie, dokumenty, opłaty, terminy, podstawa prawna. Użyj ZANIM powiesz, jak lub gdzie coś załatwić, ile to kosztuje, ile trwa albo czy da się to zrobić w aplikacji.', {'zapytanie': S(d='nazwa sprawy po polsku, np. wniosek o dowód osobisty, zameldowanie, rejestracja pojazdu używanego')}, ['zapytanie']),
    T('do_zalatwienia', 'Zbiorcza lista spraw z terminami: pisma do odpowiedzi, płatności, OC i badania, ważność dokumentów. Użyj na pytania typu „co mam do załatwienia”, „czy coś mi się kończy”.'),
    T('moje_dane', 'Dane z rejestru PESEL: adres, kontakt (Rejestr Danych Kontaktowych), małżonek, rodzice i małoletnie dzieci (danych dorosłych dzieci i rodzeństwa nie widzisz).'),
    T('moje_dokumenty', 'Lista dokumentów (dowód, paszport, prawo jazdy, KDR) z numerami, ważnością i statusem: ważny, zastrzeżony w bankach, zawieszony, unieważniony. Przed zastrzeżeniem NIE jest potrzebne.'),
    T('status_pesel', 'Status zastrzeżenia PESEL, historia zmian i historia weryfikacji (kto i kiedy sprawdzał PESEL).', {'z_historia': S('boolean', 'domyślnie true: z historią zmian i weryfikacji')}),
    T('sprawdz_pesel_osoby', 'Sprawdza, czy PESEL innej osoby jest zastrzeżony (np. najemcy, kontrahenta). Wymaga PESEL, serii i numeru jej ostatniego dowodu osobistego lub paszportu oraz celu sprawdzenia. Ta osoba zobaczy w historii, że sprawdzałaś.',
      {'pesel': S(), 'numer_dokumentu': S(d='seria i numer ostatniego dowodu osobistego lub paszportu tej osoby'), 'cel': S(d='np. zawarcie umowy najmu')}, ['pesel', 'numer_dokumentu', 'cel']),
    T('sprawdz_dowod', 'Sprawdza, czy dowód osobisty (seria i numer, np. znaleziony) jest w wykazie unieważnionych lub zawieszonych. Odpowiedź „nie ma w wykazie” nie potwierdza, że dowód jest prawdziwy.', {'numer': S()}, ['numer']),
    T('twoje_sprawy', 'Status spraw urzędowych użytkowniczki (wnioski, zgłoszenia, wezwania).'),
    T('skrzynka', 'Skrzynka e-Doręczeń: pisma z urzędów z treścią, datą odebrania i terminem odpowiedzi (termin biegnie od odebrania pisma).'),
    T('moje_pliki', 'Pliki użytkowniczki w aplikacji (faktury, umowy PDF). Użyj, gdy potrzebne są załączniki lub dokument do podpisu.', {'szukaj': S(d='słowa kluczowe')}),
    T('naleznosci', 'Do zapłaty: podatki i opłaty lokalne (ePłatności, tylko w gminach, które są w programie), składki ZUS (płaci się je w mZUS lub przelewem na rachunek składkowy) oraz mandaty z usługi Mandaty (Policja, KAS). Mandatów z fotoradarów GITD tu nie ma.'),
    T('emerytura', 'Stan konta w ZUS i prognoza emerytury dla wieku przejścia.', {'wiek_przejscia': S('integer')}),
    T('terminy_zus', 'Wolne terminy e-wizyty (wideorozmowy) w ZUS.', {'temat': S(d='np. zasiłek macierzyński, emerytura, 800+')}, ['temat']),
    T('moje_pojazdy', 'Pojazdy użytkowniczki z CEPiK: OC (ubezpieczyciel, koniec umowy), badanie techniczne, licznik. Rejestr nie wie, czy umowa OC przedłuży się sama.'),
    T('punkty_karne', 'Punkty karne kierowcy, wykroczenia i daty wygaśnięcia. Limit: 20 pkt w pierwszym roku od wydania pierwszego prawa jazdy, potem 24 pkt; okres próbny to osobna sprawa.'),
    T('historia_pojazdu', 'Historia pojazdu z historiapojazdu.gov.pl (np. kupowanego): liczba właścicieli, przebiegi z badań, szkody istotne, OC, badania, kradzież, czerwone flagi. Wymaga numeru rejestracyjnego, VIN i daty pierwszej rejestracji (z dowodu rejestracyjnego, np. ze zdjęcia). Gdy ich brakuje, poproś o nie.',
      {'nr_rejestracyjny': S(), 'vin': S(), 'data_pierwszej_rejestracji': S(d='DD.MM.RRRR')}, ['nr_rejestracyjny', 'vin', 'data_pierwszej_rejestracji']),
    T('sprawdz_oc', 'Czy pojazd o danym numerze rejestracyjnym miał ważne OC w danym dniu i u kogo (baza UFG, np. sprawca szkody).', {'nr_rejestracyjny': S(), 'data_zdarzenia': S(d='DD.MM.RRRR; domyślnie dziś')}, ['nr_rejestracyjny']),
    T('uprawnienia_kierowcy', 'Uprawnienia innego kierowcy (np. kierowcy autokaru): status dokumentu i kategorie. Wymaga imienia, nazwiska oraz serii i numeru blankietu prawa jazdy (kierowca może je podać albo pokazać mPrawo jazdy).', {'imie': S(), 'nazwisko': S(), 'numer_blankietu': S()}, ['imie', 'nazwisko', 'numer_blankietu']),
    T('bezpieczny_autobus', 'Badanie techniczne i ważność OC autobusu/autokaru po numerze rejestracyjnym. Tylko pojazdy zarejestrowane w Polsce.', {'nr_rejestracyjny': S()}, ['nr_rejestracyjny']),
    T('recepty', 'Aktywne e-recepty z IKP: Twoje, dzieci, do których kont masz dostęp, i osób, które upoważniły Cię w IKP. Kod dla farmaceuty działa razem z PESEL pacjenta.', {'osoba': S(d='np. Zofia; puste = wszystkie')}),
    T('jakosc_powietrza', 'Jakość powietrza oraz ostrzeżenia meteorologiczne i powodziowe dla lokalizacji.', {'miejscowosc': S()}),
    T('szkolenia_obronne', 'Szkolenia obronne MON (program wGotowości) z wolnymi miejscami. Dla pełnoletnich, bezpłatne, w jednostkach wojskowych.', {'rodzaj': S(e=['podstawowy', 'przetrwania', 'medyczny', 'cyberhigiena'])}),
    T('poradnik', 'Poradnik bezpieczeństwa MSWiA, MON i RCB: np. lista do plecaka ewakuacyjnego (plecak dla każdego domownika) albo zapasy w domu.', {'temat': S(), 'liczba_osob': S('integer')}),
    T('informacje_o_kraju', 'Informacje MSZ o kraju podróży (Odyseusz, Informacje o krajach): wizy, wymagania paszportowe, ostrzeżenia, plus ważność paszportów rodziny. Gdy nie ma danych dla kraju, odeślij do aktualnego komunikatu MSZ.', {'kraj': S()}, ['kraj']),
    T('wybory', 'Twój obwód i lokal wyborczy z Centralnego Rejestru Wyborców oraz najbliższe wybory.'),
    T('firma', 'Działalność gospodarcza w CEIDG oraz podmioty w KRS, w których użytkowniczka jest w zarządzie, prokurentką lub w radzie nadzorczej.'),
    T('szukaj_pkd', 'Dobiera kody PKD 2025 do opisu działalności.', {'opis': S()}, ['opis']),
    T('ksiegi_wieczyste', 'Księgi wieczyste, w których jesteś właścicielką, współwłaścicielką lub współużytkowniczką wieczystą, i cennik dokumentów.'),
    T('partnerzy_kdr', 'Ulgi ustawowe i partnerzy Karty Dużej Rodziny (wyszukiwarka partnerów na empatia.gov.pl).', {'kategoria': S()}),
    T('analizuj_wiadomosc', 'Analizuje podejrzanego SMS-a lub e-mail: sprawdza domeny na Liście Ostrzeżeń CERT Polska i osobno ocenia typowe cechy oszustwa.', {'tresc': S()}, ['tresc']),
    T('bilety', 'Bilety kolejowe z połączonego konta Bilkom. Bilet kupisz w Bilkomie lub u przewoźnika, nie tutaj.'),
    T('ustaw_przypomnienie', 'Ustawia przypomnienie w aplikacji (bez potwierdzania).', {'kiedy': S(d='np. 25.10.2026, 9:00'), 'tresc': S()}, ['kiedy', 'tresc']),
]

AKCJE = [
    T('zastrzez_dokumenty', 'Zastrzega utracony dowód lub paszport w systemie Dokumenty Zastrzeżone (banki, operatorzy); to cofniesz w aplikacji. Opcjonalnie unieważnia dowód w Rejestrze Dowodów Osobistych albo paszport w Rejestrze Dokumentów Paszportowych (nieodwracalne; przy dowodzie PESEL zastrzeże się sam). Prawa jazdy tu nie zastrzeżesz: gdzie_zalatwic (wtórnik).',
      {'dokumenty': ARR(e=DOK), 'uniewaznij': S('boolean', 'true tylko, gdy użytkowniczka wie, że dokument przepadł lub został skradziony')}, ['dokumenty']),
    T('zawies_dowod', 'Blokuje (zawiesza) e-dowód na 14 dni, gdy może się znaleźć: przez ten czas nie da się nim posłużyć. W tym czasie odblokujesz go tutaj (odwies_dowod); bez odblokowania po 14 dniach zostanie unieważniony. Tylko e-dowód (z warstwą elektroniczną). PESEL nie zastrzega się wtedy sam.'),
    T('odwies_dowod', 'Odblokowuje zablokowany (zawieszony) e-dowód, gdy się znalazł. Zastrzeżenia w bankach nie cofa (to cofnij_zastrzezenie_dokumentu).'),
    T('cofnij_zastrzezenie_dokumentu', 'Cofa zastrzeżenie dowodu lub paszportu w systemie Dokumenty Zastrzeżone (banki), jeśli zrobiono je w aplikacji. Blokady dowodu nie zdejmuje (to odwies_dowod). Unieważnionego dokumentu nie przywraca.', {'dokument': S(e=DOK)}, ['dokument']),
    T('zastrzez_pesel', 'Zastrzega numer PESEL użytkowniczki. Nie wywołuj, gdy PESEL jest już zastrzeżony (sprawdź status_pesel).'),
    T('cofnij_zastrzezenie_pesel', 'Cofa zastrzeżenie PESEL na stałe albo czasowo do podanej daty i godziny (potem PESEL zastrzeże się sam).', {'do_kiedy': S(d='DD.MM.RRRR, GG:MM; puste = na stałe')}),
    T('wniosek_dowod', 'Wniosek online o nowy dowód osobisty dla użytkowniczki lub jej małoletniego dziecka (dane z rejestru, zdjęcie z aparatu). Potem w ciągu 30 dni trzeba pójść do urzędu na odciski palców i podpis (dziecko poniżej 12 lat: bez odcisków), a dowód odbiera się osobiście.',
      {'powod': S(e=['uplyw_waznosci', 'utrata', 'zmiana_danych', 'uszkodzenie']), 'osoba': S(d='puste = ja; imię dziecka'), 'miejsce_odbioru': S(d='urząd do odcisków i odbioru; domyślnie najbliżej miejsca zamieszkania')}, ['powod']),
    T('wniosek_paszport', 'Wniosek online o paszport dla dziecka poniżej 12 lat. Dorosły, dziecko od 12 lat i paszport tymczasowy: tylko osobiście w punkcie paszportowym, użyj gdzie_zalatwic.', {'osoba': S(d='imię dziecka'), 'miejsce_odbioru': S()}, ['osoba']),
    T('zglos_urodzenie', 'Zgłoszenie urodzenia dziecka do USC (21 dni od wystawienia karty urodzenia). PESEL i akt powstają zwykle następnego dnia roboczego.', {'imie': S(d='pełna forma, nie zdrobnienie'), 'drugie_imie': S(), 'plec': S(e=['K', 'M']), 'miejsce_urodzenia': S(), 'odpis': S(e=['elektronicznie', 'osobiście', 'pocztą'])}, ['imie', 'plec']),
    T('wniosek_800plus', 'Wniosek do ZUS o świadczenie 800+ (800 zł/mies.) na dziecko. Złożony w ciągu 3 miesięcy od urodzenia daje świadczenie od dnia urodzenia.', {'dziecko': S()}, ['dziecko']),
    T('wyslij_pismo', 'Wysyła pismo przez e-Doręczenia (np. odpowiedź na wezwanie) z załącznikami z plików.', {'adresat': S(), 'temat': S(), 'tresc': S(d='pełna treść pisma'), 'zalaczniki': ARR()}, ['adresat', 'temat', 'tresc']),
    T('podpisz_dokument', 'Podpisuje PDF (do 5 MB) z plików podpisem osobistym (e-dowód, CAN i PIN) lub kwalifikowanym (5 bezpłatnych miesięcznie, sprawy prywatne). Oba wymagają e-dowodu i telefonu z NFC.', {'dokument': S(), 'rodzaj': S(e=['osobisty', 'kwalifikowany'])}, ['dokument']),
    T('zamow_odpis_kw', 'Zamawia odpis, wyciąg z jednego działu albo zaświadczenie z księgi wieczystej (płatne BLIK-iem).', {'ksiega': S(), 'rodzaj': S(e=['odpis_zwykly', 'odpis_zupelny', 'wyciag', 'zaswiadczenie_o_zamknieciu'])}, ['rodzaj']),
    T('zaplac', 'Płaci należności z ePłatności: podatki i opłaty lokalne w gminach, które są w programie (podaj id pozycji z narzędzia naleznosci). Składek ZUS ani mandatów tu nie płacisz (mandat: przelew według instrukcji). Metody zależą od gminy, BLIK jest wszędzie.', {'pozycje': ARR(), 'metoda': S(e=['BLIK', 'karta', 'Apple Pay', 'Google Pay'])}, ['pozycje']),
    T('umow_ewizyte_zus', 'Rezerwuje e-wizytę w ZUS (wideorozmowa, link przyjdzie e-mailem).', {'temat': S(), 'termin': S()}, ['temat', 'termin']),
    T('zglos_zbycie_pojazdu', 'Zgłasza sprzedaż (zbycie) pojazdu użytkowniczki w CEPiK (30 dni od umowy). Gdy ma kilka pojazdów, podaj nr_rejestracyjny sprzedawanego; jeśli nie wiesz którego, zapytaj. Pojazdu w leasingu nie zgłasza (robi to leasingodawca).', {'nabywca': S(), 'data': S(d='data umowy, DD.MM.RRRR'), 'nr_rejestracyjny': S()}, ['nabywca']),
    T('umowa_kupna_pojazdu', 'Przygotowuje umowę kupna-sprzedaży pojazdu (PDF) do podpisu zaufanego lub osobistego przez obie strony. Nie rejestruje auta: rejestracja jest w wydziale komunikacji.', {'pojazd': S(), 'sprzedajacy': S(), 'cena': S()}, ['pojazd', 'cena']),
    T('oswiadczenie_kolizji', 'mStłuczka: oświadczenie o zdarzeniu drogowym potwierdzane przez obie strony. Tylko gdy nikt nie jest ranny, obie strony mają mObywatela, zgadzają się, kto jest sprawcą, i oba auta mają polską rejestrację. Wymaga wcześniej przyjmij_dane(cel=mstluczka).', {'sprawca': S(e=['ja', 'druga_strona']), 'okolicznosci': S(), 'miejsce': S()}, ['sprawca', 'okolicznosci']),
    T('zglos_szkode', 'Zgłasza szkodę do ubezpieczyciela sprawcy. Tylko gdy użytkowniczka jest poszkodowana; gdy jest sprawcą, szkodę zgłasza druga strona.', {'ubezpieczyciel': S(), 'oswiadczenie': S(), 'opis': S(), 'zdjecia': S()}, ['ubezpieczyciel']),
    T('zloz_pcc3', 'Składa PCC-3 w e-Urzędzie Skarbowym i płaci 2% wartości rynkowej pojazdu kupionego od osoby prywatnej (14 dni od umowy). NIE wywołuj, gdy auto kupiono na fakturę od firmy (VAT), gdy wartość nie przekracza 1000 zł albo gdy przysługuje zwolnienie z powodu niepełnosprawności.', {'pojazd': S(), 'cena': S('number', 'wartość rynkowa pojazdu, zwykle cena z umowy')}, ['pojazd', 'cena']),
    T('zglos_incydent_cert', 'Zgłasza incydent do CERT Polska przez usługę Bezpiecznie w sieci. Przy SMS-ie zgłoś stronę z linku (Złośliwa strona internetowa), a sam SMS niech użytkowniczka przekaże na bezpłatny numer 8080.',
      {'kategoria': S(e=['Złośliwa strona internetowa', 'Podejrzana wiadomość SMS', 'Podejrzana wiadomość e-mail', 'Oszustwo', 'Inne']), 'adres': S(d='adres strony, jeśli jest'), 'skad': S(d='np. link z SMS-a'), 'opis': S()}, ['kategoria', 'opis']),
    T('zgloszenie', 'Zgłoszenie w mObywatelu: sanepid („Zagrożenie zdrowia publicznego”: obiekt, np. restauracja, albo produkt), GIOŚ („Naruszenie środowiskowe”: porzucone odpady, nielegalne przetwarzanie lub transport odpadów, zanieczyszczenie wody, powietrza lub gleby, inne) albo brak lub słaby internet („Dostęp do internetu”, internet.gov.pl).',
      {'instytucja': S(e=['sanepid', 'gios', 'internet']), 'kategoria': S(), 'miejsce': S(d='z jej słów; GPS tylko, gdy mówi o miejscu, w którym jest teraz'), 'opis': S()}, ['instytucja', 'opis']),
    T('zapisz_na_szkolenie', 'Zapisuje na szkolenie obronne wGotowości (id z szkolenia_obronne).', {'kurs_id': S()}, ['kurs_id']),
    T('zglos_podroz', 'Rejestruje podróż w systemie Odyseusz MSZ.', {'kraj': S(), 'od': S(), 'do': S(), 'osoby': ARR(d='dzieci jadące z Tobą; dorośli zgłaszają się sami')}, ['kraj']),
    T('zmien_miejsce_glosowania', 'Zmiana miejsca głosowania. rodzaj=staly: zmiana stałego obwodu dla osoby, która stale mieszka w gminie bez meldunku na pobyt stały (w każdej chwili, decyzja urzędu w 5 dni, wszystkie wybory). rodzaj=jednorazowy: głosowanie w innym miejscu w konkretnych wyborach, tylko od 44. do 3. dnia przed dniem wyborów.',
      {'rodzaj': S(e=['staly', 'jednorazowy']), 'miejscowosc': S(), 'adres': S(d='adres zamieszkania, przy rodzaj=staly')}, ['rodzaj', 'miejscowosc']),
    T('zaloz_firme', 'Wniosek CEIDG-1 o założenie jednoosobowej działalności (kody PKD 2025). Nazwę firmy i formę opodatkowania MUSI podać użytkowniczka: jeśli ich nie podała, najpierw zapytaj (bez wywoływania tego narzędzia). Zgłoszenia do ubezpieczeń w ZUS i VAT-R nie złożysz w aplikacji.',
      {'nazwa': S(d='nazwa podana przez użytkowniczkę, z jej imieniem i nazwiskiem'), 'pkd': ARR(), 'data_rozpoczecia': S(d='DD.MM.RRRR'), 'forma_opodatkowania': S(e=['skala', 'liniowy', 'ryczałt'])}, ['nazwa', 'pkd', 'data_rozpoczecia', 'forma_opodatkowania']),
    T('aktualizuj_dane_kontaktowe', 'Zmienia telefon lub e-mail w Rejestrze Danych Kontaktowych. Najpierw bez kodu: wysyła kod na nowy numer lub adres. Gdy użytkowniczka poda kod, wywołaj ponownie z kodem, żeby zapisać zmianę.', {'telefon': S(), 'email': S(), 'kod': S(d='kod z SMS-a lub e-maila, gdy już go dostała')}),
]

UI = [
    T('przekaz_dane', 'Usługa „Potwierdź swoje dane”: gdy KTOŚ INNY (strona internetowa na komputerze, wypożyczalnia, hotel, urzędnik, kasa muzeum, kasjerka, druga osoba z telefonem) chce dostać lub sprawdzić dane UŻYTKOWNICZKI. Otwiera skaner: ona skanuje znak mObywatela odbiorcy (na jego telefonie, stronie albo w okienku), widzi, kto prosi i o jakie dane (zakres ustala odbiorca), i potwierdza Face ID. Zwraca wynik (komu i co przekazano albo że odmówiła). Nie wymaga osobnej akcji.',
      {'kto': S(d='kto prosi o dane, jeśli wiadomo, np. Wypożyczalnia samochodów'), 'dokument': S(e=['dowod', 'pj', 'kdr', 'auto', 'legitymacja'], d='który dokument jest sprawdzany; domyślnie dowod')}),
    T('przyjmij_dane', 'Gdy UŻYTKOWNICZKA chce dostać lub sprawdzić dane INNEJ osoby: tożsamość (tozsamosc), pełnoletność np. klienta w sklepie (pelnoletnosc; funkcja zapowiadana, dziś w mObywatelu sprawdza się cały mDowód), prawo jazdy (prawo_jazdy), a przy stłuczce dane drugiego kierowcy (mstluczka). Pokazuje na jej ekranie duży znak mObywatela z wybranym zakresem; tamta osoba skanuje go w swoim mObywatelu przyciskiem Potwierdź swoje dane i potwierdza u siebie. Zwraca otrzymane dane.',
      {'cel': S(e=['tozsamosc', 'pelnoletnosc', 'prawo_jazdy', 'mstluczka'])}, ['cel']),
    T('zaproponuj_odpowiedzi', 'Pokazuje 2–4 przyciski z odpowiedziami lub następnymi krokami. Wywołaj NA KOŃCU swojej wypowiedzi, gdy zadajesz pytanie zamknięte lub proponujesz dalsze kroki. Po tym czekasz na użytkowniczkę.',
      {'opcje': S('array', items=S(), d='krótkie etykiety, maks. 4 słowa')}, ['opcje']),
    T('wybor_wielokrotny', 'Pokazuje listę do zaznaczenia kilku pozycji (np. co było w portfelu) z przyciskiem Dalej. Po tym czekasz na odpowiedź.',
      {'opcje': S('array', items=S())}, ['opcje']),
    T('pokaz_dokument', 'Wyświetla dokument z portfela w rozmowie.', {'dokument': S(e=['dowod', 'prawo_jazdy', 'kdr', 'pojazd', 'legitymacja'])}, ['dokument']),
    T('zakoncz_rozmowe', 'Kończy rozmowę i wraca na ekran główny aplikacji (w rozmowie głosowej wyłącza mikrofon). Wywołaj, gdy użytkowniczka żegna się albo mówi, że to wszystko i nie ma więcej spraw, po krótkim pożegnaniu w tekście.'),
]
for t in ODCZYTY:
    if t['name'] not in ('ustaw_przypomnienie',):
        t['input_schema']['properties']['pokaz_karte'] = S('boolean', 'domyślnie true: pokazuje kartę z danymi; false, gdy dane są potrzebne tylko Tobie')

NAZWY_ODCZYTOW = {t['name'] for t in ODCZYTY}
NAZWY_AKCJI = {t['name'] for t in AKCJE}
NAZWY_UI = {t['name'] for t in UI}
NAZWY_KLIENT = {'przekaz_dane', 'przyjmij_dane'}
WSZYSTKIE = ODCZYTY + AKCJE + UI
