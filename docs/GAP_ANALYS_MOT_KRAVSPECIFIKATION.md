TENTALOKALER – GAP-ANALYS MOT BEFINTLIG PoC
Datum 2026-10-08. Arbetsdokument och prioriteringsunderlag.
OBS: Avser skillnaden mellan överenskommen målbild och det vi KAN VERIFIERA i GitHub respektive vad som RAPPORTERATS från nyare lokal körning.

1. VERSIONSSTATUS – KRITISKT
Vid kontroll av gUUnnar/tentaoptimering, branch main, SHA b44bdb473de4fa8fd56f3ebb9ce0c189c1bdc3c2, innehöll repo bl.a. README.md, AGENTS.md, src/tentaoptimering/{cli.py,pipeline.py,loaders.py,normalize.py,validation.py,cost_model.py,reporting.py}, config/{parameters.toml,source_files.toml}, docs/{DATAMODELL.md,KOSTNADSMODELL.md,BLOCKERANDE_DATAGAP.md}, reports/{baseline.md,data_quality.json} samt tester för normalisering och kostnadsmodell.

I det GitHub-trädet syntes INTE den lokala, enligt användaren fungerande OR-Tools-implementationen. Användaren har beskrivit en nyare lokal Windows-PoC med OR-Tools CP-SAT, 8 scenariesalar med 1 179 platser, 1 258 efterfrågeposter och 23 tester. Det lokala källkodsläget har INTE kunnat verifieras genom den granskade GitHub-revisionen. Se därför all specifik kritik mot solverimplementeringen som preliminär tills Codex inspekterat lokala arbetskopian. Ingen programkod ändrades inom ramen för denna analys.

2. AVGÖRANDE MODELLGAP
[KRITISK] Oplacerade studenter: Tidigare rapporterade körningar placerade 1 246 av 1 258 poster; 12 blev oplacerade (med rapporterat 1 707 respektive 1 574 tentander i två körningsvarianter). Den modellen kan inte användas för att påstå att verksamhetens kostnad har minimerats under leveranskravet att alla får skriva. Oplacerade får bara vara diagnostik och lösningen ska inte bedömas som genomförbar om det återstår obligatorisk efterfrågan.

[KRITISK] Suboptimering: Lokalkapacitet och få oplacerade tentor är inte slutmålet. Schemat, strukturellt lokalbestånd, hyrda externa lokaler och personal måste ingå i EN total årlig kostnadsmodell. Varken få lokaler, lite bomtid eller minimalt antal personalpass får ensamt styra.

[KRITISK] Fel tidsabstraktion: Varianter med fasta tider eller ±60 min tar inte höjd för terminer, flexibla tentamensperioder, vidgade kalendertoppar, helger, flera pass per dag eller olika provlängder med ställtid. Behövs kalenderbaserade parametrar utan snävt hårdkodade intervall.

[KRITISK] Ekonomisk mening: Att lämna en långtidshyrd sal tom en timme ger inte motsvarande kontant besparing. PoC:n ska modellera hypotetiskt mindre långsiktigt lokalbestånd, medan externhyra ska räknas efter debiterbara perioder. Visa potential separat från verifierat genomförbar avveckling.

[KRITISK] Personalen saknas eller är otillräckligt integrerad: Vakttimmar, bemanningskrav, olika sluttider inom en sal, arbetsdagar, anställningsmix, bomtid, förberedelsetid, arbetstidsregler, raster och betalda förflyttningar måste ingå i samma övergripande optimering. Dagens 86 vakter är inte ett tak.

3. ÖVRIGA KRAV SOM BEHÖVER KONTROLLERAS
• Kurs- och programkrockar ska vara hårda begränsningar; ofullständigt utbildningsprogramunderlag ska flaggas.
• Uppsala/Visby måste strikt separeras. Ingen mellanortsplacering eller personalförflyttning.
• Flera tentor med olika sluttider får dela sal med gemensam start, men inte löpande nyinsläpp. Turnaround gäller efter sista skrivande.
• Digital kompatibilitet är hårt krav; scenario för ökad digital andel och deltagarvariation ska ingå.
• Publicerade salplatser är absoluta tak; avgränsning för särskilt stöd är explicit och konsekvent.
• Tentamenslängd får inte ändras tyst; maxlängd är ett uttryckligt policyexperiment.
• Ursprungsschema ska bevaras om förändring saknar tillräcklig nytta. Skilj verkliga ombokningskostnader från mjuk preferens.
• Rapportera skillnader mellan nuläge, teoretiskt nytt långsiktigt kostnadsläge och ännu inte realiserbar besparing.
• CLI/rapporter måste innehålla status, efterfrågetäckning, antaganden, kostnadsuppdelning, versionsuppgifter och solvergap.

4. BEHÅLL DET SOM VERKLIGEN FUNGERAR
I GitHub-main finns en användbar struktur för datainläsning, korn/normalisering, validering, parametrar, kostnadsunderlag, kostnadsmodell och rapportering. Dessa komponenter kan behållas efter granskning, snarare än skrivas om på reflex. Lokal CP-SAT-kod kan också vara återanvändbar men måste först källkodsgranskas. Inga slutsatser om lokal kods detaljförmåga får dras enbart från main-trädet.

5. HANTERING AV SAKNADE DATA – DESIGNKRAV
PoC:n ska gå att köra före kompletterande leveranser. Placera alla preliminära värden i ett explicit antaganderegister med nyckel, värde, enhet, källa/grund, giltighet och flagga preliminär/verifierad. Scenarierna refererar till samma parametrar. Nya närvaro-, personal-, hyres- och kompatibilitetsdata ska ersätta antaganden utan att kodstrukturen ändras. Använd inte historisk Ladokanmäld mängd som om den vore verifierad närvaro. Ge tillräcklig kvalitetsrapportering för att se hur robust årsbesparingen är.

6. PRIORITERAD NÄSTA INSATS FÖR CODEX (EJ UTFÖRD)
1. Kontrollera faktiskt lokalt repo, branch, ej committade filer och eventuellt opushade commits innan några ändringar. Bevara allt.
2. Gör kodnära inventering av datamodell, solver, kostnadsfunktion, CLI och tester och jämför med detta dokument och kravspecifikationen.
3. Föreslå den enklaste korrekta GEMENSAMMA matematiska modellen och en etappindelad omställning – inte ännu fler specialfall på en tvivelaktig modell.
4. Testa först små deterministiska syntetiska scenarier där rätt svar är känt: alla placerade eller infeasible; kurs-/programkrock; absolut kapacitet; gemensam start/olika sluttider; ställtid; digital kompatibilitet; transport och raster; ett dyrare personalalternativ som möjliggör billigare lokaler.
5. Kör först därefter en termin med dagens data och redovisade antaganden. Redovisa solverstatus och osäkerhet.
6. Gör om körningarna när kompletterande data anländer, utan att ändra optimeringsmotorn.

7. VAD VI INTE SKA BYGGA ÄNNU
Ingen individbaserad persondatabas över tentamensvakter, ingen lösning för särskilt stöd i PoC, inget nytt produktions-GUI eller egen webbtjänst, ingen generell investeringsmodell för korttidslokaler, ingen genomgång av samtliga övergångsavtal förrän potentialen är begripligt uppskattad.

8. UNDERLAG OCH TILLFÖRLITLIGHET
Verifierad GitHub-struktur: main vid SHA ovan (trädinventering). Lokala CP-SAT-körningar: användaruppgifter från tidigare projektkonversationer, inte verifierat lokalt källkodsinnehåll. Övrigt: verksamhetsintervju avslutad 2026-10-08, projektets PM, rektorsprinciper, mötesanteckningar, presentationen Utvecklingsarbete 2-10-26 samt tre angivna kalkylfiler. Bemanningstabell, hyresvillkor, närvarodata och avtalstillämpning kräver fortsatt faktakontroll. Denna analys är en KONCEPTUELL gap-analys, inte en fullständig oberoende kodrevision.

