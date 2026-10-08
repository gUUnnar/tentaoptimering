# Arbetsinstruktioner för Codex

## Projektets mål
Bygg en PoC som uppskattar den lägsta långsiktiga årskostnaden för Uppsala universitets tentamensverksamhet genom **gemensam optimering av schemaläggning, lokalbestånd, externhyror och tentamensvakter**. Minsta planeringsenhet är en hel termin. Modellen ska kunna justera kalenderdatum, tentamensperioder, dagar och skrivpass inom valda verksamhetsregler.

## Obligatoriska acceptanskriterier
1. **Fullständig efterfrågetäckning.** Varje tentamen och varje dimensionerande tentand inom uttryckligen vald omfattning ska placeras. En lösning med oplacerad obligatorisk efterfrågan är inte godkänd. Vid brist på fullständig genomförbarhet redovisas status och blockerande krav; en partiell placering får endast förekomma i separat diagnostik.
2. **Terminsövergripande planering.** Optimeraren ska kunna fördela tentamina över tillåtna kalenderperioder och skrivpass, inklusive justerbara verksamhetsvillkor om helger och tentamensperioder. Ursprungligt schema bevaras när förändring saknar tillräcklig nytta.
3. **Gemensam totalkostnad.** Datum, salar och bemanning optimeras tillsammans. Personalkostnader, bomtid och transporter får öka om lägre lokalkostnader mer än kompenserar. Bemanningsstyrkans storlek är en kostnadsvariabel.
4. **Hårda villkor.** Fysisk sal-/formatkapacitet; digital kompatibilitet; skilda planeringsområden Uppsala och Visby; kurs- och programkrockar; tillämpliga lagar, avtal och arbetstidsvillkor.
5. **Spårbara data.** Använd kvalificerade antaganden när data saknas. Alla antaganden ska deklareras och kunna ersättas genom kompletterande data utan större kodändringar. Håll isär faktisk kostnad, teoretisk årlig potential och verifierad realiserbar besparing.

## Läsordning
1. `README.md`
2. `docs/KONCEPTUELL_KRAVSPECIFIKATION.md`
3. `docs/KODGRANSKNING_OCH_CODEX_UPPDRAG_2026-10-08.md`
4. Vid behov: `docs/DATAMODELL.md`, `docs/KOSTNADSMODELL.md`, `docs/BLOCKERANDE_DATAGAP.md` och relevanta kod- och konfigurationsfiler.

## Aktuellt uppdrag
Inventera den **lokala** implementationen i `C:\lokalt\tentalokaler\PoC`, inklusive arbetskopians Git-status, opushade ändringar, solver, CLI, tester, parametrar och rapporter. Redovisa kodnära kravuppfyllnad, återanvändbara delar och föreslagen minimal gemensam optimeringsarkitektur. **Ingen ändring av programkod, källdata eller lokal Git-status utan nytt godkännande.**

## Hantering av data och Git
- Originaldata ligger skrivskyddat i `C:\lokalt\tentalokaler\underlag`.
- Lägg inte original-Excel, personuppgifter eller genererade `data/processed`-filer i Git.
- Hantera beställning/tentamensbehov, salplacering och Ladokaktivitet som olika datakorn.
- Kontrollera lokala ocommittade filer och commits före synkning; ingen okontrollerad reset, pull, merge eller rebase.
- Verksamhetsparametrar och antaganden ska vara konfigurerade och versionsspårade.

## Verifiering
För databaslinjen på GitHub-main:
```powershell
python -m tentaoptimering.cli
python -m unittest discover -s tests -v
```

Kontrollera att rådata inte förändras. Validera dessutom alla hårda regler och full efterfrågetäckning i solverns separata testsvit när den lokala implementationen har inventerats.
