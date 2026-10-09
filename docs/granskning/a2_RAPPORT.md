# Revision av datalinjen (A2): ursprungsfiler till optimeringsmodell

Alla siffror är omräknade från originalfilerna i `C:\lokalt\tentalokaler\underlag` (skrivskyddat). Skript s1..s24 ligger i samma mapp. Kör med `.venv\Scripts\python.exe` (PYTHONIOENCODING=utf-8). Repot är orört (`git status` ren). Pipelinen kördes två gånger mot kopior i `rerun1/` och `rerun2/` med PYTHONDONTWRITEBYTECODE=1.

## A. Verifierat korrekt
1. Radantal i originalen: bokningar 8 466 rader (35 kolumner, blad "Data i systemet"), Ladok 1 525 aktiviteter (xlsx och csv har samma tal), hyresrapport 41 rader. (s1, s2, s4)
2. Bokningar: Klar 8 089, Avbokad 364, Under behandling 10, Ändring begärd 3. Alla 8 466 har Ort=Uppsala. 5 498 unika prefix plus 8 rader utan prefix ger 5 506 "tillfällen" i `exam_events.csv`. Av dem har 5 141 datum; 365 saknar datum och tid (364 avbokade och 1 "Klar" dugga, prefix MDSXF). Varje order har exakt ett datum och en tid. (s2, s3, s23)
3. Kedjan stämmer exakt: 1 525 aktiviteter, 1 258 included, 267 unresolved (170 tvetydiga, 71 utan bokning, 25 saknat värde, 1 utan nyckel), 1 283 behovsposter (25 utan värde), 1 255 med lokal (tre hemma-behov, 94 pers). Summorna 46 698 och 46 604 stämmer. (s7, s18)
4. Matchningsregeln är kurskod, datum och starttid (första klockslaget i "Inbokad tid"). Min oberoende implementation (på csv-versionen av Ladok) ger 1 285 otvetydiga mot pipelinens 1 283; skillnaden är två aktiviteter, se B1.
5. Stickprov om 45 slumpade matchningar (seed 20261009) mot originalen: `stickprov_45.csv`. Alla 45 har rätt kurskod, datum och starttid och exakt ett bokat tillfälle. Behovsvärdet är lika med Ladok VARAV_ANTAL_ANMALDA i alla 45.
6. Matchkvalitet för de 1 283 behoven (s13): ordinarie/omtenta motstridiga i 30 fall (2,3 %, 138 pers; många är definitionsskillnader som uppsamling); digital-flagga (Ladok LIS mot bokningens E-tenta) skiljer i 21 (1,6 %); Ladok-LOKAL stämmer inte med bokad adress i 11 (0,9 %, varav fem stavfel eller hemtentor). Falska matchningar bedöms ligga under cirka 1-2 % (indikation, inte bevis).
7. Fältbetydelse i Ladok: VARAV_ANTAL_ANMALDA är antalet nu anmälda. ANTAL_TOT är i regel anmälda plus avanmälda (867 av 991 fullständiga rader). Tomt anmälda-fält betyder noll: i 21 av 22 rader är ANTAL_TOT lika med avanmälda. Inga negativa värden.
8. Tid och datum: inga datum med klockslag, ingen skrivtid över midnatt (0 rader), naiva datum (ingen tidszonsfråga). Veckodag stämmer med datum i alla rader. Bokat intervall är lika med fältet "Längd" i 8 087 av 8 101 rader (14 skiljer). De 365 oparsbara tiderna är "-" och hör till de 365 rader utan datum.
9. Manifestet stämmer: källfil-, konfig- och artefakthashar och radantal OK. Pipelinen är deterministisk: två omkörningar ger byte-identiska csv och identiskt manifest, samma som repots. (s21 + omkörning)
10. Publicerade kapaciteter i `room_register.toml` stämmer mot uu.se (hämtad 2026-10-09, sidan uppdaterad 2026-09-24; sammanfattad av hämtningsverktyget). Sju rum summerar 1 119; Klostergatan 41 för anläggningen; B40 60 "bokas i systemet från VT27". Sidans total 1 446 stämmer inte med radsumman 1 220 (registret flaggar redan detta).
11. Efterfrågetopparna omräknade: 1 586 platser 2026-01-15 för 1 255 behov, 1 604 den 16 januari för 1 258 (Ladok-registrerade, bokat intervall, utan ställtid).

## Visby-fyndet (huvudfråga)
**Bekräftat.** 1 179 = 1 119 (sju Uppsalasalar) + 60 (`uu-campus-gotland-b40`, Visby). Belägg: `optimization_rooms.csv` har 8 rader, summa 1 179, Uppsala 1 119, B40 med `observed_in_booking_period=False`.

Var rummet kommer in:
- `config/room_register.toml:108-123`: city="Visby", capacity_seats=60, kontext "campus_gotland_from_spring_2027".
- `model_inputs._build_optimization_rooms` (`model_inputs.py:248-282`): urvalet är enbart `capacity_seats.notna() & capacity_scope=="room"`. Ort, tillgänglighetskontext och observation i bokningsperioden prövas inte. Alla rader får `eligible_for_exploratory_capacity_poc` = policyflaggan (True) (rad 273).
- `integrated_inputs.load_term_model_inputs` (`integrated_inputs.py:40, 63-66`): filtrerar på `eligible…`; B40 blir ett `IntegratedRoom` med plan_area "Visby" och rumskostnad 60 x kostnad per plats.
- `model_inputs.py` (metrics, cirka rad 459-461): `optimization_room_capacity_sum_ready_for_exploratory_poc` = 1 179, vidare till `reports/optimization_readiness.{md,json}` och `tests/test_model_inputs.py:79` (testet låser 1 179 och 8 rum).
- `config/scenarios/reference.toml:24` och `flexible_start_60m.toml:24` listar B40 i `allowed_room_ids`; `optimizer_model._prepare_inputs` (rad 42-47) kräver att alla listade rum finns.

Påverkan:
- **Terminsmotorn (`term_run.py`) är i praktiken opåverkad.** Alla behov har plan_area "Uppsala" (`observed_cities`), så `relevant_rooms` (`term_run.py:57`) och `room_is_compatible` (`term_rules.py:17`) sorterar bort B40. Portföljvalet och kostnaden ändras inte.
- CP-SAT (`integrated_term.py:90`): B40 skapas men kan inte användas av Uppsalabehov.
- Äldre optimeraren: med `enforce_historical_city=true` (`optimizer_time.py:75-76`) räknas Uppsala utan Visby; om flaggan stängs av summeras alla rum till "__all__" = 1 179.
- **"Dagar över kapacitet" och prototypen/dokumenten är påverkade.** Mot 1 179: 4 av 73 dagar, högst 407 över (`MALARKITEKTUR_ANALYS` rad 74, 114, 174; `DATAANALYS_S0` rad 91; `docs/prototyp/index.html` rad 252, hårdkodad). Mot korrekta 1 119: **5 av 73 dagar** (även 2026-01-12 med 1 127) och **467 över** (485 för 1 258 behov). Dessa tal beräknas inte av produktionskod i repot utan i scratch-förprov och handskrivna dokument; min egen svepning är s18.

**Visby-tentor:** finns inte i något underlag. Bokningar har Ort=Uppsala på alla 8 466 rader. Ladok-LOKAL och namn har noll träffar på Visby/Gotland, hyresrapporten likaså. Det som finns är fritext: cirka 108 koordineringskommentarer ("Studenter på Gotland", "tentan går parallellt på Gotland") och sju om 2JF071 ("kan skriva på Campus Gotland"). Ingen Visby-efterfrågan går att modellera.

## B. Fel som måste rättas
**B1. Teckenkodsfel (mojibake) i Ladok-xlsx.** `Utsökning Ladok…xlsx` har texten dubbelkodad i sharedStrings.xml ("RÃ¥byvÃ¤gen" 34 fall; kurskoderna 3ÖN002/3ÖN003 blir `3Ã–N00x`, 7 tecken). Csv-versionen är korrekt UTF-8 (0 skadade rader). Pipelinen läser xlsx (`loaders.py:94-97`; `paths.py` SourceFiles.ladok). Följder: 745 rader i `ladok_activities.csv` har skadad text; 411 location_key blir `r-byv-gen-95-…`, så `location_key_equal` kan aldrig bli sant för Råbyvägen; två aktiviteter (`ladok-000923/924`, 2026-02-28) matchas inte, och med csv hade 1 258 blivit 1 259 och 46 698 blivit 46 706 (+8 pers). Åtgärd: läs csv eller reparera vid inläsning (`encode("cp1252").decode("utf-8")`) och testa efter tecknet "Ã".

**B2. "Bokat ≈ 1,38 x registrerade" (MALARKITEKTUR rad 72-ish) är fel.** Siffran kommer från `optimization_placements.csv`, där aktiviteter som delar tillfälle ger dubbletter: 179 dubblettrader, 2 214 rader mot 2 035 unika placeringar. Summan över de inkluderade behoven är 64 300 (64 300/46 698 = 1,377). Med unika placeringar är det 57 986 bokade platser = **1,24 x**. Alla som summerar `booked_places` i den filen utan dedupe på `placement_id` räknar fel.

**B3. "5 506 bokningsordrar" (DATAANALYS §5) är fel benämning.** 5 506 är tillfällen: 5 498 prefix plus 8 prefixlösa rader, varav 365 saknar datum. Schemalagda tillfällen är 5 141; 357 prefix är bara avbokade.

**B4. Kapacitetsbaslinje för Uppsala är 1 119, inte 1 179**, och bokningsandelarna i dokumenten stämmer inte. I terminsfönstret (2026-01-12..03-31, ej avbokade, 67 961 bokade platser) ligger 79,3 % i de sju rummen med kapacitet; 3,1 % Klostergatan 3, 7,3 % Danmarksgatan 30, 8,4 % Fyrishov D-F, 1,1 % hemma, 0,8 % Fyrislundsgatan 80 utan sal. Alltså 15,7 % av platserna i rum utan kapacitetsuppgift. Helår (209 590 platser): 83,1 % / 3,2 % / 6,7 % / 4,7 % / 1,5 % / 0,7 %. "68,3 % av bokade platser i de åtta salarna" (DATAANALYS §6) går inte att reproducera; närmast är 68,2 % (46 323 platser i sju rum för inkluderade tillfällen delat med alla 67 961 fönsterplatser, en blandning av baser).

**B5. Scenariots antagande stämmer inte med data.** `integrated_term_exploratory.toml:20` har `latest_end_time="18:00"` och rad 66 påstår att det täcker längsta observerade skrivtid. Av de 1 283 behoven slutar 104 efter 18:00 och 4 efter 19:00 (vanligaste pass 14:00-19:00). De kan aldrig behålla sin ursprungstid, vilket spräcker "Nuläge".

**B6. Behov är inte tentor.** De 1 258 behoven är 1 171 fysiska tillfällen (87 fler). 79 tillfällen har 2-5 behov (166 behov), alla `co_exam=Ja`. Motorn kan placera samtentor på olika tid och i olika salar. "1 255 tentor" ska läsas som 1 255 aktiviteter.

**B7. Samtentor saknar del av deltagarna:** 152 av 1 171 inkluderade tillfällen listar fler kurskoder än matchade Ladok-aktiviteter; de övriga kursernas deltagare ingår inte i efterfrågan.

## C. Osäkert / otestat
1. Ladok-utdragets urval ("tentander från tidigare termin"). Täckning i fönstret: 1 171 av 1 473 tillfällen (79,5 %), 57 986 av 67 961 bokade platser (85,3 %). 302 tillfällen (9 975 platser) står utanför, bland dem några av de största (1FA105 420 platser, 2JJ303 360, 2JJ325 293). Topparna underskattas därmed. Orsak (urval eller tvetydighet) ej avgjord.
2. Ladok-registrerade ligger under bokningens Antal tentander: mediankvot 0,87; 126 av 1 092 enkla tillfällen har kvot under 0,5 (t.ex. 2HR203 2 mot 20; 4PE197 50 mot 140). Kan vara delgrupper.
3. 178 aktiviteter där ANTAL_TOT - avanmälda ≠ anmälda (summa 1 341 pers). Oförklarat; ANTAL_OMREG förklarar bara 18. ANTAL_TILLAGDA finns på 2 rader.
4. Boländerna-hyran (1 810 m², 4,15 MSEK, `MOT01.01-02`) saknar rumskoppling. Hypotes, ej verifierad: motsvarar Danmarksgatan 30 (7,3 % av platserna, ingen kapacitet). Alla hyreslänkar är `no_room_name_candidate`.
5. Bokad historik överstiger publicerad kapacitet: 23 av 1 259 bokningar i fönstret (72 av 4 712 på året, max 280 mot 229). Faktiskt samtidigt bokat nådde 2 158 platser (exkl. hemma, 2026-01-16): Fyrishov D-F 902 och Danmarksgatan 333 samtidigt, medan de sju publicerade rummen som mest hade 1 092 samtidigt hela året. Dagar "över kapacitet" beror alltså på inhyrda lokaler utan kapacitetsuppgift (datagap), inte på verklig brist.
6. Typer i modellen: ordinarie 721, omtenta 497, dugga 22, hybrid 16, hemtenta 2; 801 digitala och 457 icke-digitala. Ladok-hemtentamen (1 aktivitet, 22 pers) ingår inte. Digital kompatibilitet är antagen.
7. Stödplatser: Klostergatan 3 (anläggning, ej optimeringssal) har 633 av de inkluderade placeringarna (1 852 platser, 3,2 %), men Ladok-efterfrågan skiljer inte ut stödstudenter; de krävs rymmas i de sju rummen.
8. Pivotbladet "Summering" i bokningsfilen (Bokade platser 203 944; Antal tentander 195 524) skiljer sig från radsummorna (209 590; 201 369). Använd inte.
9. Webbsidan lästes via ett verktyg som sammanfattar; ej läst ordagrant.

## D. Bör ersättas
- Ladok-inläsning från xlsx till csv (eller teckenreparation) plus test.
- `optimization_placements.csv`: behov-till-tillfälle och tillfälle-till-placering som skilda tabeller (eller andelskolumn) så att summering inte dubblerar.
- `_build_optimization_rooms`: ortfilter och `available_from`-datum (B40: VT27) i stället för bara "kapacitet finns".
- Tvetydiga matchningar: 76 av 85 tvetydiga nycklar är "flera Ladok-aktiviteter mot ett tillfälle" (summeringsbara, 5 038 registrerade). `canonical_demand` har strukturen men används inte.
- Hårdkodade siffror i prototyp och dokument ersätts av beräknade värden.

## E. Beslut som krävs
1. Kapacitetsbaslinje Uppsala: (a) 1 119 publicerat; (b) 1 160 med Klostergatan; (c) 1 119 plus beslutad kapacitet för Danmarksgatan 30 och Fyrishov (användes samtidigt 333 respektive 902); (d) observerat samtidigt max 2 158 (bevisat nyttjat, inte kapacitet).
2. Ska B40 ligga kvar med tillgänglighetsdatum eller tas ur PoC-underlaget tills Visby-efterfrågan finns?
3. Ska samtentor vara ett behov eller flera?
4. Ska tvetydiga aktiviteter (5 038 registrerade) summeras per tillfälle, och ska Ladok-urvalet utredas hos dataägaren?
5. Ska scenariots sluttid 18:00 utökas till 20:00?

## F. Kunde inte verifiera
- Vad "tentander från tidigare termin" innebär och definitionen av ANTAL_OMREG och de 178 differenserna.
- Verklig lokaltillgänglighet och kapacitet 2025/26 (registret gäller 2026-09-24).
- Kollektivavtals-PDF och kostnadsantaganden (utanför denna revision).
- Studentöverlapp och programkrockar (data saknas).
- Dokumentens "4 av 73"/1 586/1 604 mot deras egna scratch-förprov; jag har bara reproducerat talen med egen svepning (s18).

## Reproduktion
Kör i `...\scratchpad\audit\a2`: s2_bookings.py, s4_ladok.py, s5/s6, s7_chain.py, s8_indep.py (oberoende matchning), s9_visby_rooms.py, s10_rooms.py, s11/s12 (kedja, samtentor), s13 (matchkvalitet), s14 (stickprov, `stickprov_45.csv`), s15/s16 (täckning, tvetydighet), s17 (tid), s18 (toppar), s19 (kapacitetsdefinitioner), s20 (hyror), s21 (manifest), s22 (mojibake), s23 (övrigt). Omkörning: `python -B -c "...run_pipeline(underlag, rerunN/processed, rerunN/reports)"` och jämför sha256 (alla lika).
