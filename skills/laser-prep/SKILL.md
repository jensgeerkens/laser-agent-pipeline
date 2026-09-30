---
name: laser-prep
description: Bereitet ein Bild für die Foto-Gravur auf Schiefer mit einem CO2-Laser vor und erzeugt fertige LightBurn-.lbrn2-Dateien. Pipeline mit optionaler Hintergrundentfernung (rembg), Auto-Crop im 2:3-Hochformat, Graustufen, Kontrast, Schärfen, Auflösungsprüfung und Einbettung in eine Vorlage. Auslöser z. B. "Bild für Schiefer vorbereiten", ".lbrn2 aus Foto bauen".
---

# laser-prep: Schiefer-Gravur-Pipeline

## Zielformate

| Format | Schiefer | Bildgröße (mm) | Hinweis |
|---|---|---|---|
| `10x10` | 10 × 10 cm | 66,67 × 100,00 | rechteckig |
| `round10` | Ø 10 cm rund | 55,50 × 83,20 | mit Referenzkreis auf einem nicht ausgegebenen Werkzeug-Layer |
| `15x20` | 15 × 20 cm | 133,33 × 200,00 | rechteckig |

Alle im 2:3-Hochformat, Zielauflösung 254 DPI (Zeilenabstand 0,1 mm).

## Aufruf

```bash
python skills/laser-prep/prep.py <bild> <format> [<format> ...] [optionen]
```

- `--model birefnet-portrait` (Standard) oder `--model u2net_human_seg`
- `--no-bgremove`: Bild ist schon freigestellt (weißer oder transparenter Hintergrund); fast weiße Pixel werden schwarz
- `--name <basis>`: Ausgabename (Standard: Dateiname der Quelle)
- `--out-dir <ordner>`: Standard `./laser-prep-out`; PNG und Vorschau liegen in `<out-dir>/png`

Beispiel mit dem synthetischen Testmotiv aus `examples/laser-prep/`:

```bash
python skills/laser-prep/prep.py examples/laser-prep/testmotiv.png 10x10 round10 \
       --no-bgremove --name testmotiv --out-dir examples/laser-prep
```

## Ablauf

1. Bildpfad und Formate klären und kurz bestätigen.
2. `prep.py` ausführen.
3. Vorschau `<basis>_preview.jpg` zeigen (links Zuschnitt, rechts Gravurbild) und Zuschnitt sowie Tonwerte bestätigen lassen.
4. Erzeugte `.lbrn2`-Dateien auflisten.

## Regeln aus der Praxis

- **Schiefer-Logik:** Helle Pixel = Laser feuert = hell graviert. Dunkle Pixel = kein Abtrag = Schiefer bleibt dunkel. Der Hintergrund muss deshalb SCHWARZ sein; das Skript setzt ihn automatisch.
- **Nicht invertieren.** Helle Bildbereiche bleiben hell und werden hell graviert.
- **EXIF-Drehung** wird über `ImageOps.exif_transpose` berücksichtigt.
- **Auflösung:** Schiefer trägt nahezu binär ab; 254 bis 318 DPI sind der sinnvolle Bereich. Das Skript warnt, wenn das Quellbild dafür zu klein ist.
- **LightBurn-Skalierung:** Bei XForm-Skala von etwa 0,1 gilt W/H-Attribut = Anzeigemaß in mm × 10. Das Skript setzt die Werte über die Vorlage.
- **Layer-Werte der Vorlage:** Jarvis-Dithering, 350 mm/s, 18 % Leistung als konservativer Startwert. Vor dem ersten echten Auftrag per Materialtest auf der eigenen Maschine anpassen.
- **Keine lokalen Pfade in der Ausgabe:** In der `.lbrn2` steht nur der Dateiname des PNG, die Bilddaten sind eingebettet.

## Vorlage

`template.lbrn2` enthält als Platzhalter nur einen synthetischen Graustufen-Verlauf und wird mit `python tools/make_prep_template.py` reproduzierbar erzeugt.

## Wenn die Freistellung Probleme macht

- Motivteile fehlen: `--model u2net_human_seg` probieren.
- Hintergrundreste: vorher manuell freistellen, dann `--no-bgremove`.
