# Tentaoptimering – PoC

## Uppdrag
Undersök hur stor den **långsiktiga årliga besparingspotentialen** är vid **gemensam optimering av tentamensschema, lokaler och tentamensvakter** över minst en termin.

Det är **inte** en modell för att endast flytta starttider några minuter eller minimera antalet använda salar. **Alla ingående tentamina och tentander måste få plats.** Om det inte går inom valda ramar ska körningen redovisa att fullständig genomförbar lösning saknas, inte presentera partiell placering som en lyckad optimering.

### Styrande dokument – läs i denna ordning
1. [AGENTS.md](AGENTS.md) – bindande arbetsinstruktioner för Codex.
2. [Konceptuell kravspecifikation](docs/KONCEPTUELL_KRAVSPECIFIKATION.md) – verksamhetens aktuella krav och parametrar.
3. [Gap-analys](docs/GAP_ANALYS_MOT_KRAVSPECIFIKATION.md) – kända skillnader mot målbilden.
4. [Kodgranskning och aktuellt Codex-uppdrag](docs/KODGRANSKNING_OCH_CODEX_UPPDRAG_2026-10-08.md) – **nästa arbetssteg: inspektion av lokal kod, utan att ändra implementationen**.

Övriga dokument i `docs/` beskriver datamodell, kostnadsstruktur eller kvalitetsbrister och är underlag, inte konkurrerande kravspecifikationer.

## Källor och lokal utveckling
Originaldata finns skrivskyddade utanför repot under `C:\lokalt\tentalokaler\underlag`. Lägg aldrig råa Excel-filer, personuppgifter eller återskapade CSV-filer från `data/processed` i Git.

GitHub-`main` innehåller för närvarande den verifierade databaslinjen. En nyare lokal OR-Tools-version har rapporterats men är **inte kodgranskad i GitHub**. Undersök lokalt `C:\lokalt\tentalokaler\PoC` inklusive Git-status och opushade ändringar innan andra åtgärder.

## Databaslinje på main
Den befintliga implementationen importerar, normaliserar och validerar tre Excel-underlag och skapar rapporter. Den är **inte** den gemensamma optimeringsmotorn.

```powershell
python -m pip install -e .
python -m tentaoptimering.cli
python -m unittest discover -s tests -v
```

Databaslinjen skriver `data/processed/bookings.csv`, `ladok_activities.csv`, `lease_rows.csv` samt `reports/baseline.md` och `reports/data_quality.json`.

Kända osäkerheter: en bokningsrad är inte automatiskt en unik tenta; Ladoks `ANTAL_TOT` är inte verifierad faktisk närvaro; interna hyresbelopp är inte automatiskt besparingsbara. **PoC ska ändå kunna köras med kvalificerade, tydligt markerade och lätt ersättbara antaganden.**
