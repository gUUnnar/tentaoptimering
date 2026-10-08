# Teknisk status – Tentaoptimering

**Granskningsdatum:** 2026-10-08  
**Källa:** GitHub-`main` samt uppgifter från lokala provkörningar.  
**Syfte:** identifiera vilka tekniska komponenter som finns och vad som återstår att verifiera inför implementation av [kravspecifikationen](KONCEPTUELL_KRAVSPECIFIKATION.md).

## Verifierad implementation i GitHub-main

| Del | Status | Underlag |
|---|---|---|
| Import av boknings-, Ladok- och lokaldata | Finns | `loaders.py`, `pipeline.py` |
| Normalisering av data och preliminära identifierare | Finns | `normalize.py` |
| Datakvalitetskontroller och baslinjerapport | Finns | `validation.py`, `reporting.py` |
| Parameterregister | Finns som struktur | `config/parameters.toml` |
| Representation av kostnadskomponenter | Finns som struktur | `cost_model.py` |
| Gemensam solver för kalender, lokaler och personal | Inte verifierad i GitHub-main | Granskad trädstruktur |
| Körbar terminsoptimering med full efterfrågetäckning | Inte verifierad | Lokal kod återstår att granska |

Normaliseringens `exam_order_id`, `placement_id` och `activity_id` är preliminära identifierare. Relationen mellan ett unikt tentamensbehov, en fysisk salplacering och en Ladokaktivitet behöver säkerställas innan volymer aggregeras.

Valideringen beskriver även att Ladokutdraget inte har ett verifierat fält för faktisk närvaro och att lokalrapportens rader inte automatiskt representerar separata tentamenssalar.

## Lokal kod – inventering återstår

En nyare lokal PoC med OR-Tools CP-SAT har rapporterats från `C:\lokalt\tentalokaler\PoC`. Den lokala kodbasen har inte inspekterats i denna granskning. Rapporterade provkörningar omfattade cirka 1 258 behovsposter och visade 1 246 placerade poster. Dessa är uppgifter från körningar, inte oberoende verifierade resultat.

Nästa uppgift är att avgöra vilka lokala moduler som finns och vilka krav de uppfyller. Kontrollera revisionsstatus innan eventuell synkning mellan lokal kod och GitHub.

## Komponenter att verifiera inför fortsatt utveckling

| Komponent | Krav på färdig PoC | Verifieringsfråga |
|---|---|---|
| Efterfrågan | Samtliga ingående tentamina och tentander tilldelas genomförbara platser | Fungerar identifiering, aggregering och obligatorisk tilldelning? |
| Kalender | Minst en termin, med valbara datum, perioder, dagar och skrivpass | Hur representeras tillåtna datum och pass? |
| Salar | Absoluta kapacitetstak, digital kompatibilitet, samlokalisering och ställtid | Hur hanteras samtidigt pågående tentor med olika sluttider? |
| Geografi | Uppsala och Visby separeras | Är ortskravet ett hårt villkor? |
| Krockar | Samma kurs och program får inte ha överlappande tentamina | Vilka kurs-/programrelationer finns i underlaget? |
| Personal | Anonymiserade resurser, bemanning, betald tid, förflyttningar och vila | Vilka personalvillkor och kostnader är implementerade? |
| Lokalkostnader | Långsiktig portföljkostnad samt debiterbara externa hyresperioder | Vilka lokalalternativ och hyresuppgifter finns? |
| Ekonomi | Gemensam långsiktig årskostnad för schema, lokaler och personal | Är alla beslut kopplade till samma målfunktion? |
| Antaganden | Spårbara och utbytbara preliminära värden | Kan nya data ersätta antaganden utan kodändring? |
| Resultat | Efterfrågetäckning, status, kostnad, antaganden, solvergap | Kan körningen reproduceras och granskas? |

## Nästa steg

Codex ska genomföra den lokala inventeringen enligt [uppdraget](KODGRANSKNING_OCH_CODEX_UPPDRAG_2026-10-08.md), lämna en verifierad kravmatris och föreslå en minimal gemensam optimeringsarkitektur. Ingen programändring ingår i detta steg.
