# Dokumentation

**Status:** kanonisk dokumentationsingång.
**Senast avstämd:** 2026-10-15 mot grenen `feature/forklarad-totalbesparing` (efter PR #21).

Dokumentationen är indelad i styrande dokument, tekniska referenser,
verksamhetsunderlag och historik. Ett historiskt dokument beskriver ett tidigare
läge och får inte användas för att bedöma dagens implementation.

## Läsordning

1. [A, B och C](ABC_SCENARIOMODELL.md) – gällande begreppsmodell för faktisk
   bokning, grundoptimering och egna körningar.
2. [Konceptuell kravspecifikation](KONCEPTUELL_KRAVSPECIFIKATION.md) – målbild
   och bindande verksamhetskrav.
3. [Krav och aktuell status](KRAV_OCH_STATUS.md) – enda aktuella
   kravuppfyllnadsmatrisen.
4. [Gemensam optimeringsdesign](GEMENSAM_OPTIMERINGSDESIGN.md) och
   [oberoende eftervalidering](OBEROENDE_EFTERVALIDERING.md) – motor- och
   valideringskontrakt.
5. [Datamodell](DATAMODELL.md), [kostnadsmodell](KOSTNADSMODELL.md) och
   [blockerande datagap](BLOCKERANDE_DATAGAP.md) – vad resultaten betyder och
   vad som ännu inte kan verifieras.

## Styrande dokument

| Dokument | Funktion |
|---|---|
| [ABC_SCENARIOMODELL.md](ABC_SCENARIOMODELL.md) | Överordnad definition av A, B, C och referensoptimering med låsta datum. |
| [KONCEPTUELL_KRAVSPECIFIKATION.md](KONCEPTUELL_KRAVSPECIFIKATION.md) | Bindande målbild och acceptanskrav. |
| [KRAV_OCH_STATUS.md](KRAV_OCH_STATUS.md) | Aktuell status per krav, med begränsning och bevis. |
| [GEMENSAM_OPTIMERINGSDESIGN.md](GEMENSAM_OPTIMERINGSDESIGN.md) | Teknisk design för den enda optimeringsmotorn. |
| [OBEROENDE_EFTERVALIDERING.md](OBEROENDE_EFTERVALIDERING.md) | Kontrakt och regler för fristående eftervalidering. |
| [KOSTNADSMODELL.md](KOSTNADSMODELL.md) | Skillnaden mellan historisk kostnad, modellkostnad, potential och realiserbar besparing. |

Om styrande dokument motsäger varandra gäller ordningen ovan. En teknisk
implementation får aldrig sänka ett bindande krav; avvikelsen ska i stället
redovisas som `delvis`, `saknas`, `datablockerat` eller `inte verifierat` i
statusmatrisen.

## Tekniska referenser

| Dokument | Funktion |
|---|---|
| [DATAMODELL.md](DATAMODELL.md) | Datakorn, nycklar, önskemål, täckning och läsvyer. |
| [PARAMETERKATALOG.md](PARAMETERKATALOG.md) | Parameterkontrakt, grund, redigerbarhet och motorstöd. |
| [OPTIMERINGSSTRATEGI.md](OPTIMERINGSSTRATEGI.md) | Dekomponerad lösningsstrategi, mätningar och begränsningar. |
| [PERIODVAL_OCH_SNABBA_KORNINGAR.md](PERIODVAL_OCH_SNABBA_KORNINGAR.md) | Periodval, korta körningar och reservationsmodellen för fasta bokningar. |
| [LOKALT_GRANSSNITT.md](LOKALT_GRANSSNITT.md) | Aktuellt lokalt gränssnitt, API och paketering. |
| [ARKITEKTURPRINCIPER_DATAKVALITET.md](ARKITEKTURPRINCIPER_DATAKVALITET.md) | Separation mellan verksamhetsmodell, datakvalitet och policy. |
| [FILOVERSIKT.md](FILOVERSIKT.md) | Ansvar per versionshanterad fil. |

## Verksamhets- och dataunderlag

| Dokument | Funktion |
|---|---|
| [BLOCKERANDE_DATAGAP.md](BLOCKERANDE_DATAGAP.md) | Uppgifter som blockerar operativt tillförlitliga slutsatser. |
| [FRAGOR_TILL_DATAAGARE.md](FRAGOR_TILL_DATAAGARE.md) | Frågor vars svar kan bli verifierade regler eller källdata. |
| [VERKSAMHETSUNDERLAG_2026-10-02.md](VERKSAMHETSUNDERLAG_2026-10-02.md) | Källtrogen återgivning av presentationen den 2 oktober 2026. |
| [ANALYS_KOLLEKTIVAVTAL.md](ANALYS_KOLLEKTIVAVTAL.md) | Vad det lokala kollektivavtalet faktiskt styrker och inte styrker. |

## Historik

Tidigare granskningsrapporter och leveransögonblicksbilder finns under
[historik/](historik/README.md). De bevaras som revisionsunderlag men är inte
aktuella krav-, arkitektur- eller statusdokument. Ersatta arbetsorder, planer,
kravmatriser, prototyper och råa experimentloggar har tagits bort; de finns kvar
i Git-historiken.
