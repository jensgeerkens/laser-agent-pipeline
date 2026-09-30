# Designregeln für Laser-Cut-Vorlagen

Diese Regeln stammen aus konkreten Fehlern beim Bau der Beispielmöbel (Bett in vier Versionen,
Stehlampe, Sofa). Jede Regel beschreibt eine Fehlerklasse, die ohne sie wieder auftritt. Der
`laser-architect` muss sie vor jedem Entwurf laden.

## 1. 3D-Verifikation vor der Ausgabe

Jede Verbindung besteht aus Tab und Slot. Beide müssen in Position, Maß und Richtung im Raum
zusammenpassen. Für jedes Teil wird festgehalten: Wo sitzt es in 3D, wo sitzen seine Tabs und
Slots, und lässt es sich in dieser Lage einsetzen, ohne dass andere Teile im Weg sind? Die
**Montagereihenfolge** wird ausdrücklich aufgeschrieben. Ist sie unmöglich, ist das Design
kaputt, auch wenn jeder einzelne Slot stimmt.

## 2. Durchsteckverbindung mit geschlossenem Slot ist fatal

Hat Teil A einen schmalen Hals zwischen zwei breiteren Bereichen und Teil B einen geschlossenen
Slot (Innenrechteck), kommt B nie über die breiten Bereiche von A. So entstand der Kopfteil-Fehler
im Bett v2. Lösungen: Slot kantenoffen machen, Teil in zwei Teile trennen oder die Konstruktion
ändern.

## 3. One-sided Tabs

Pro Verbindung trägt genau EIN Teil den Tab und das ANDERE den Slot. In den ersten Fassungen aller
vier Box-Möbel trugen Seitenwände hinten Tabs UND die Rückwand links und rechts Tabs, mit Kollision
als Folge. Funktionierende Konvention für Box-Möbel:

- **Seitenwände** tragen ALLE Tabs (oben, unten, hinten)
- **Deckel, Boden, Einlegeböden** tragen NUR Slots
- **Rückwand** hat Tabs oben und unten, Innen-Slots links und rechts

Umgesetzt in `make_finger_box()` in `pipeline/lib.py`.

## 4. Cross-Lap-Kerben müssen kantenoffen sein

`slot_rect(...)` erzeugt ein geschlossenes Innenrechteck. Für Kreuzverbindungen funktioniert das
nicht; sie brauchen eine Kerbe von der Kante bis zur Mitte als Teil der Außenkontur. Das war der
Fehler der Stehlampe v1.

## 5. Wände auf dem Boden oder Boden zwischen den Wänden

**(a) Wände stehen auf dem Bodenpanel:** Wände mit Tabs nach unten durch das Bodenpanel. Einfach,
aber die Wände enden eine Materialstärke über dem Boden und wirken schwebend.

**(b) Wände reichen bis zum Boden, das Bodenpanel liegt innen:** Die vier Wände verbinden sich an
den Ecken (zwei Tabs pro Ecke gegen Verdrehen), das Bodenpanel ist um zweimal die Materialstärke
kleiner und liegt lose im Rahmen. Wirkt realistischer, braucht Regel 6.

Für sichtbare Möbel (b), für verdeckte Boxen genügt (a).

## 6. Corner-Ownership

Bei (b) besitzt eine Wandrichtung die Ecken (volle Länge), die andere ist um `2 × THICKNESS`
kürzer. Beim Bett: Kopf- und Fußteil volle Breite (133 mm), Seitenteile Innenlänge (161 mm).
Wird das nicht einheitlich gehandhabt, überlappen sich die Wände an den Ecken.

## 7. Kerf nicht blind übernehmen

`SLOT_W = THICKNESS - KERF` ist die Formel, aber KERF hängt von Maschine und Material ab. Der
Startwert 0,15 mm ist geschätzt. Vor einer größeren Serie ein Testteil schneiden, die Passung
prüfen, KERF nachstellen und erst dann den Rest erzeugen (siehe `agents/laser-calibrator.md`).

## 8. LightBurn ist Y-UP

LightBurn nutzt ein mathematisches Koordinatensystem (Y nach oben), PIL und Bildformate Y nach
unten. Code in Y-UP schreiben, Bitmaps vor dem Einbetten vertikal spiegeln, vertikalen Text mit
+90 Grad drehen.

## 9. Dateiregeln

Neue Vorlagen der Agenten schreiben in `<name>_generated.lbrn2`, nie in eine Datei, die in LightBurn
von Hand bearbeitet wurde. Sonst ist beim nächsten Lauf die Handarbeit (Bild ersetzt, Position
korrigiert) verloren. Ausnahme sind die Beispielskripte in `pipeline/`: Sie schreiben feste Namen nach
`pipeline/output/`, weil diese Dateien reproduzierbare Artefakte sind, die jeder Lauf neu erzeugt.
Wer eine davon in LightBurn weiterbearbeiten will, legt vorher eine Kopie unter eigenem Namen an.

## 10. Eine Quelle für wiederkehrende Konstruktionen

Brauchen mehrere Stücke dieselbe Box-Konstruktion (Schrank, Nachttisch, Kommode, Regal), wird sie
EINMAL als Helfer gebaut (`make_finger_box()`), nicht viermal kopiert. Ein Fix gilt dann für alle,
und Konventionen lassen sich nur an einer Stelle durchsetzen.

## 11. Ehrliche Prüfung

Nicht "sieht sauber aus" melden, ohne jede Verbindung geprüft zu haben. Eine ehrliche Liste offener
Punkte ist wertvoller als ein falsches "alles in Ordnung". Im Zweifel einen weiteren Prüfdurchgang
oder einen echten Testschnitt.

## 12. Externe Hardware dokumentieren

Was der Laser nicht herstellt, gehört in die Anleitung: Scharniere, Schubladenführungen, LED und
Knopfzelle, Stoff, Magnete.

## 13. Montagereihenfolge bei geschlossenen Boxen

Bei Fingerzinken-Boxen gibt es genau eine sinnvolle Reihenfolge:
1. Boden flach hinlegen
2. Rückwand mit dem unteren Tab in den hinteren Boden-Slot stecken
3. Beide Seitenwände einsetzen (Boden-Tabs und Rückwand-Innenslots gleichzeitig)
4. Einlegeböden JETZT einsetzen, später kommen sie nicht mehr hinein
5. Deckel von oben aufsetzen, alle Tabs gleichzeitig einfädeln

## 14. Gravuren nach dem Layout positionieren

`layout_grid` verschiebt die Teile auf dem Sheet. Gravuren, die sich auf ein Teil beziehen
(Schubladenlinien, Polsternähte), werden deshalb NACH dem Layout aus der finalen Teilposition
berechnet.

## 15. Werkzeugkasten

- Python und PIL für Vorlagen und Vorschau (immer eine Vorschau erzeugen, nie nur `.lbrn2`)
- `shapely` für 2D-Boolesche Operationen
- boxes.py für fertige Fingerzinken-Boxen und Mechanik (externe Abhängigkeit, GPL-3.0)
- `.lbrn2`-XML direkt erzeugen für eigene Layouts

## 16. Final-Checkliste

- [ ] Jede Verbindung hat ein Tab-Slot-Paar (nicht Tab + Tab)
- [ ] Montagereihenfolge funktioniert physisch
- [ ] Gesamtmaße stimmen mit der Erwartung, Parameterbedeutung dokumentiert
- [ ] Vorschau erzeugt und angesehen
- [ ] Externe Hardware in der Anleitung
- [ ] Kerf realistisch oder als Kalibrierbedarf markiert
- [ ] Y-UP in der LightBurn-Ausgabe
- [ ] Bitmaps vor dem Einbetten gespiegelt

## Anhang: Schiefer-Gravur

- Bildgröße in LightBurn = XForm-Skala × W-Attribut; bei Skala 0,1 also W-Attribut = Anzeigemaß in mm × 10.
- Schiefer trägt nahezu binär ab; 254 bis 318 DPI sind der sinnvolle Bereich.
- Startwerte Jarvis-Dithering, 350 mm/s, 18 % Leistung (konservativ, unkalibriert).
- EXIF-Drehung vor der Verarbeitung anwenden.
- Hell wird graviert: nicht invertieren, Hintergrund schwarz.
