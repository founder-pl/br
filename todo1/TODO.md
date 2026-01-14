na bazie przeprowadzonych zmian, wyodrebnij moduły, które mogą działac wjako oddzielne biblioteki python
i wyodrebni je do folderu ./ oraz stwórz jako główne fodlery -biblitoeki python
sparwdz czy są komplementarne, stwórz kilka wartsw, aby reużywały miedzy soba różne ustandaryzowane moduły, które tez powinny być oddzielnymi komplementarnymi biblitoekami


Stwórz testy e2e dla http://localhost:81/?page=doc-generator&logs_tab=api&year=2025&month=12
Przetestuj wygenerowane dokumenty, czy są sensnowen, czy zawierają błedy, 
czy renderowanie do html przebiega poprawnie, popraw to co powinno działać poprawnie

Stwórz oddzielny moduł do renderowania markdown do pliku md2html i html2pdf korzystając z już istniejących bibliotek
Przenaalziuj czy wszystkie dokumenty zawierają poprawną struktutr i obliczenia,
czy ich struktura jest zgodna z oczekiwaniami, czy dane są poprawnie pobierane z systemu
dodatkowo do każdej zmiennej w dokumencie dodaj link do systemu z url, gdzie jest ta zmienna pobierana
dodaj do API taką możliwość, aby każda zmienna była pobierana za pomocą specjalnego query
do restapi liub innego API, jak np. graph API albo inne, sprawdz, któ©e będa lepsze do tego zatssoowania
aby np poprzez jeden prosty API URL query otrzymać oczekiwaną zmienną
może to być np do obliczenia wskaznika nexus
CHodzi o to by umowy, geenrowane dokumenty były weryfikowalne i wszystkie url były np w formie przypisów

[1](http://localhost:81/api/project/*/variable/*)
[2](http://localhost:81/api/project/*/variable/*)
Tak aby łatwo można było zwalidować czy dana zmienna została poprawnie pobrana,
jak rozwiązać kwestie dostępu, czy wystarczy token, czy auth basic, jeśli jestem zalogowany do systsmeu  a korzystam z konsoli 
czy może lepiej przypisać key ssh? jak przy połączeniu  ssh?wóœczas nie beðzie roznicy czy rpzez przegladarke, czy 
przez curl i bedzie dostepna dana dla kazdego typu polaczenia

Stworz takie rozwiazanie, aby mozna było łatwo otryzmywać konkretne zmienne potrzebne do obliczeń
oraz bezposredni dostep do danych faktur, z OCR jako json lub plain text
curl http://localhost:81/api/invoice/*/variable/*