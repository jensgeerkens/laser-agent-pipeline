# Allgemeine Hinweise zur Montage

Diese Anleitungen gelten für alle 9 Möbelstücke der Puppenhaus-Kollektion (Maßstab 1:12).

## Material

- **3 mm Sperrholz** (Birke oder Pappel, glatt, ohne große Astlöcher)
- **Holzleim** (PVA-Weißleim, z.B. Ponal), für permanente Verbindungen
- **Schleifpapier** Körnung 240, Kanten entgraten
- **Pinzette**: zum Einfädeln kleiner Zapfen

## Laser-Einstellungen (Monport Reno 65 Pro, 3 mm Sperrholz)

| Layer | Funktion | Speed | Power | Passes |
|-------|----------|-------|-------|--------|
| C00 Cut | Außenkontur + Slots | 10 mm/s | 85 % | 2 |
| C02 Score | Gravur-Details | 100 mm/s | 35 % | 1 |

## Allgemeines Vorgehen

1. **Alle Teile vom Sperrholz lösen**: bei 2 Passes sollten alle Cuts durch sein, sonst Cutter-Messer verwenden
2. **Kanten entgraten**: leicht mit Schleifpapier abrunden, dann passt jeder Steck-Joint besser
3. **Trocken-Test**: erst ohne Leim zusammenstecken, prüfen ob alles passt
4. **Verleimung**: kleine Tropfen Leim in jeden Slot, Stück zusammenstecken, 30 Min trocknen lassen

## Kerf-Toleranz

Slots sind **kerfkompensiert** (= SLOT_W ≈ 2,85 mm bei 3 mm Material). Das ergibt einen leichten Press-Fit. Wenn deine Slots zu eng sind:

- Material könnte dicker sein als 3 mm (Sperrholz-Toleranz: ±0,2 mm)
- Mit Schleifpapier den Zapfen leicht abschmirgeln
- Oder im Code `KERF = 0.20` (statt 0.15) setzen und neu generieren

Wenn deine Slots zu LOCKER sind: `KERF = 0.10` versuchen.
