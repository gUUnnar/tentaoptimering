# Arbetsinstruktioner för Codex

## Omfattning

Detta repo är en PoC för analys och senare optimering av tentamenslokaler.

## Överordnade acceptanskriterier – får inte kompromissas bort

**1. NOLL OPLACERADE TENTANDER.** Alla tentamina och tentander inom den uttryckligt definierade PoC-omfattningen är obligatorisk efterfrågan. Optimeraren får INTE minska kostnaden genom att avstå från att placera en tenta, en grupp eller en deltagare. En rapport med t.ex. 1 246 av 1 258 placerade poster är **inte ett giltigt eller lyckat optimeringsresultat**, även om lösaren tekniskt returnerar `FEASIBLE` för en relaxerad modell. Om kraven inte går att uppfylla ska resultatet rapporteras som *ingen fullständig genomförbar lösning inom valda villkor*, med tydlig förklaring av vilka villkor som orsakar konflikten och vilka verksamhetsparametrar som kan ändras. Partiell placering får endast användas som **diagnostik**, aldrig som bas för påstådd besparing. Redovisa vilka stödbehov som explicit ligger utanför PoC, utan att tyst stryka dem.

**2. OPTIMERA TENTAMENSKALENDERN, INTE MINUTFÖRSKJUTNINGAR.** Huvudproblemet är när under minst en **hel termin** tentamina genomförs, hur topparna fördelas över olika dagar/perioder, vilka skrivpass som används, hur salar samutnyttjas och vad denna planering innebär för långsiktiga lokalkostnader och personal. Historiska starttider med `±60 minuter` är **inte** en lämplig huvudmodell eller den flexibilitet verksamheten efterfrågar. Tillåtna dagar, perioder, eventuella helger, antal pass per dag och andra verksamhetsparametrar ska vara konfigurerbara utan godtyckligt snäva intervall. De gamla minut-/dag-offsetparametrarna får inte styra lösningens arkitektur. En tenta kan byta dag eller pass om scenariot tillåter det; behåll ursprungsläget när ändring inte är motiverad.

**3. EN GEMENSAM ÅRSKOSTNAD – INGEN SUBOPTIMERING.** Optimera datum, pass, lokaler och tentamensvakter tillsammans. Det kan vara rationellt att anlita fler vakter eller acceptera mer bomtid om lokalkostnaden sjunker mer. Dagens 86 vakter är en nulägesreferens, inte ett tak. All obligatorisk efterfrågan och alla hårda lag-/kapacitets-/format-/ortskrav måste uppfyllas.

**4. VÄNTA MED KODÄNDRING.** Aktuellt uppdrag till Codex är enbart lokal inventering, kodnära gap-analys och förslag till minimal korrekt integrerad modell; ingen refaktorering/implementation förrän användaren godkänt förslaget. Den lokala OR-Tools-koden kan avvika från GitHub-`main`; kontrollera och skydda lokala ändringar.

Läs `docs/KONCEPTUELL_KRAVSPECIFIKATION.md`, `docs/GAP_ANALYS_MOT_KRAVSPECIFIKATION.md` och `docs/KODGRANSKNING_OCH_CODEX_UPPDRAG_2026-10-08.md` innan något förslag ges.

## Källdata

- Originaldata finns i `C:\lokalt\tentalokaler\underlag` och är alltid read-only.
- Lägg aldrig Excel-, CSV- eller databasexporter från källmappen i Git.
- Normaliserade tabeller under `data/processed` är reproducerbara och ska inte versionshanteras.

## Modellregler

- Skilj beställning/tentamenstillfälle, fysisk salplacering och särskilt stöd.
- Anta inte att Ladoks `ANTAL_TOT` är faktisk närvaro utan verifierad definition.
- Anta inte att preliminär internhyra är en realiserbar besparing.
- Hårdkoda inte verksamhetsparametrar eller scenariointervall. Värden ska komma från det maskinläsbara parameterregistret eller en uttrycklig beställning.
- Aktuellt steg är endast kodinventering och designförslag. Ingen ny implementation förrän användaren godkänner förslaget. PoC ska därefter kunna köras med kvalificerade, redovisade och lätt utbytbara antaganden medan fler data inväntas.

## Verifiering

Använd Python 3.11 eller senare och kör före leverans:

```powershell
python -m tentaoptimering.cli
python -m unittest discover -s tests -v
```

Kontrollera att källdata förblir oförändrade och att genererade radantal stämmer mot baslinjen.
