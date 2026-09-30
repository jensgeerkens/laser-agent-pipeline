"""Erzeugt skills/laser-prep/template.lbrn2 neu.

Das Template enthält als Platzhalter nur einen synthetischen Graustufen-Verlauf
(kein Foto). prep.py ersetzt Bilddaten, Maße und Position beim Aufruf.

Aufruf:  python tools/make_prep_template.py
"""
import base64
import io
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "skills" / "laser-prep" / "template.lbrn2"


def placeholder_png(w: int = 40, h: int = 60) -> bytes:
    """Kleiner vertikaler Graustufen-Verlauf im 2:3-Format."""
    im = Image.new("L", (w, h))
    im.putdata([int(255 * y / (h - 1)) for y in range(h) for _ in range(w)])
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<LightBurnProject AppVersion="2.0.05" DeviceName="" FormatVersion="1" MaterialHeight="0" MirrorX="False" MirrorY="False">
    <VariableText>
        <Start Value="0"/>
        <End Value="999"/>
        <Current Value="0"/>
        <Increment Value="1"/>
        <AutoAdvance Value="0"/>
    </VariableText>
    <UIPrefs>
        <Optimize_ByLayer Value="0"/>
        <Optimize_ByGroup Value="-1"/>
        <Optimize_ByPriority Value="1"/>
        <Optimize_WhichDirection Value="0"/>
        <Optimize_InnerToOuter Value="1"/>
        <Optimize_ByDirection Value="0"/>
        <Optimize_ReduceTravel Value="1"/>
        <Optimize_HideBacklash Value="0"/>
        <Optimize_ReduceDirChanges Value="0"/>
        <Optimize_ChooseCorners Value="0"/>
        <Optimize_AllowReverse Value="1"/>
        <Optimize_RemoveOverlaps Value="0"/>
        <Optimize_OptimalEntryPoint Value="0"/>
        <Optimize_OverlapDist Value="0.025"/>
    </UIPrefs>
    <CutSetting_Img type="Image">
        <index Value="0"/>
        <name Value="C00"/>
        <maxPower Value="18"/>
        <maxPower2 Value="18"/>
        <speed Value="350"/>
        <priority Value="0"/>
        <ditherMode Value="jarvis"/>
        <interval Value="0.1"/>
    </CutSetting_Img>
    <Shape Type="Bitmap" CutIndex="0" W="1333.334" H="2000.0011" Gamma="1" Contrast="0" Brightness="0" EnhanceAmount="0" EnhanceRadius="0" EnhanceDenoise="0" File="" SourceHash="0" Data="{data}">
        <XForm>0.099999964 0 0 0.099999964 150 120</XForm>
    </Shape>
    <Notes ShowOnLoad="0" Notes=""/>
</LightBurnProject>
"""


def main():
    data = base64.b64encode(placeholder_png()).decode("ascii")
    OUT.write_text(TEMPLATE.format(data=data), encoding="utf-8")
    print(f"[ok] {OUT.relative_to(REPO)} ({OUT.stat().st_size} Bytes)")


if __name__ == "__main__":
    main()
