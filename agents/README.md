# Agenten

Acht spezialisierte Subagenten für die Erstellung von Laser-Cut-Vorlagen (LightBurn `.lbrn2`,
SVG, DXF). Format: Markdown mit YAML-Frontmatter (`name`, `description`, `tools`, `model`), wie es
Claude-Code-Subagenten erwarten. Ein Orchestrator (die Hauptsitzung) ruft sie nacheinander auf und
verkettet ihre Ergebnisse.

| Agent | Zweck | Wann | Modell |
|---|---|---|---|
| `laser-researcher` | Vorhandene Vorlagen und boxes.py-Generatoren finden | Vor jedem neuen Design | sonnet |
| `laser-architect` | Geometrie, Verbindungen, 3D-Aufbau | Neue Vorlage | opus |
| `laser-simulator` | 3D-Kollisions- und Montageprüfung, Pflicht-Gate | Nach jeder Design-Iteration | opus |
| `laser-codegen` | `.lbrn2`/SVG/DXF mit Format-Eigenheiten | Ausgabedatei schreiben | sonnet |
| `laser-calibrator` | Kerf-Testteil und Auswertung | Neues Material, Passung falsch | sonnet |
| `laser-optimizer` | Nesting, Schnittreihenfolge, Zeitschätzung | Viele Teile, knappe Platte | sonnet |
| `laser-doc-writer` | Montageanleitung, Materialliste | Nach dem Codegen | sonnet |
| `laser-adapter` | Import fremder SVG/DXF/`.lbrn2` | Fremdvorlage anpassen | sonnet |

Die Modellwahl folgt der Aufgabe: Entwurf und Prüfung (Architect, Simulator) brauchen räumliches
Schließen über mehrere Schritte, die übrigen Rollen arbeiten nach klaren Regeln.

## Abläufe

**Neues Stück**
1. `laser-researcher`: gibt es eine Vorlage oder einen boxes.py-Generator?
2. `laser-architect`: Entwurf, nutzt oder erweitert `pipeline/lib.py`
3. `laser-simulator`: 3D-Prüfung; bei FAIL zurück zu 2
4. `laser-codegen`: `<name>_generated.lbrn2` plus Vorschau
5. `laser-doc-writer`: Anleitung

**Fremdvorlage übernehmen:** `laser-adapter` → Sichtung → `laser-architect` → `laser-codegen` → `laser-doc-writer`

**Kerf-Drift:** `laser-calibrator` erzeugt ein Testteil, Schnitt und Rückmeldung, neuer Kerf-Wert in der Kalibrierdatei, Vorlagen neu erzeugen

**Platte zu klein:** `laser-optimizer` verteilt auf mehrere Platten, je Platte eine Datei

## Gemeinsame Grundlagen

- `docs/design-rules.md`: Designregeln und Final-Checkliste, Pflicht für den Architect
- `calibration.example.json`: Format der Kalibrierdatei (Material, Dicke, Kerf, Maschinenwerte)
- `pipeline/lib.py`: `Part`, `make_finger_box()`, `slot_rect()`, `layout_grid()`, `write_lbrn2()`, `render_preview()`, `simulate_assembly()`

## Installation

Die Dateien nach `.claude/agents/` im Projekt oder im Benutzerverzeichnis kopieren. Pfade in den
Definitionen sind relativ zur Wurzel dieses Repositorys.
