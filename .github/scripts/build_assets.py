#!/usr/bin/env python3
"""Draws the banner and the section headings. Run once, the nightly job only redraws the kitchen."""
from html import escape
from pathlib import Path
from kitchen import font

OUT = Path(__file__).parent.parent.parent / "assets"
FONTS = font("Chewy-sub.ttf", "Chewy") + font("PatrickHand-sub.ttf", "Patrick Hand")

# the crayon filter and the Captain, drawn once and reused with <use>
CAPTAIN = '''<filter id="crayon" filterUnits="userSpaceOnUse" x="-20" y="-20" width="340" height="340">
  <feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed="4" result="w"/>
  <feDisplacementMap in="SourceGraphic" in2="w" scale="6" result="d"/>
  <feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="2" seed="11" result="g"/>
  <feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -12 9.9" result="speck"/>
  <feComposite in="d" in2="speck" operator="in"/>
 </filter>
 <filter id="crayonWide" filterUnits="userSpaceOnUse" x="0" y="0" width="900" height="300">
  <feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed="4" result="w"/>
  <feDisplacementMap in="SourceGraphic" in2="w" scale="6" result="d"/>
  <feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="2" seed="11" result="g"/>
  <feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -12 9.9" result="speck"/>
  <feComposite in="d" in2="speck" operator="in"/>
 </filter>
 <symbol id="base" viewBox="0 0 300 300">
  <g filter="url(#crayon)" stroke="#2a1d17" stroke-width="7" stroke-linejoin="round" stroke-linecap="round">
   <circle cx="150" cy="172" r="94" fill="#f2b865"/>
   <path d="M70 215 q80 70 160 0" fill="none" stroke="#d98f3f" stroke-width="12" opacity=".6"/>
   <ellipse cx="92" cy="190" rx="16" ry="10" fill="#ff9aa8" stroke="none" opacity=".85"/>
   <ellipse cx="208" cy="190" rx="16" ry="10" fill="#ff9aa8" stroke="none" opacity=".85"/>
   <path d="M62 120 q88 -90 176 0 z" fill="#243a6b"/>
   <path d="M52 124 q98 22 196 0 q-4 -18 -22 -14 q-76 14 -152 0 q-18 -4 -22 14z" fill="#16264a"/>
   <circle cx="150" cy="82" r="15" fill="#ffc93c"/><path d="M143 82 l7 -7 l7 7 l-7 7z" fill="none" stroke-width="4"/>
  </g>
 </symbol>
 <symbol id="bacon" viewBox="0 0 300 300">
  <g filter="url(#crayon)" fill="none" stroke-linecap="round">
   <path d="M88 206 q30 -22 62 -4 q32 -18 62 4" stroke="#2a1d17" stroke-width="32"/>
   <path d="M88 206 q30 -22 62 -4 q32 -18 62 4" stroke="#ec4b34" stroke-width="20"/>
   <path d="M92 204 q28 -18 58 -4 q30 -14 58 4" stroke="#ffc4b0" stroke-width="5" stroke-dasharray="14 10"/>
  </g>
 </symbol>
 <symbol id="happy" viewBox="0 0 300 300"><g filter="url(#crayon)" stroke="#2a1d17" stroke-width="7" stroke-linecap="round" fill="none">
  <circle cx="115" cy="165" r="7" fill="#2a1d17"/><circle cx="185" cy="165" r="7" fill="#2a1d17"/>
  <path d="M122 232 q28 26 56 0" stroke-width="6"/></g></symbol>
 <symbol id="wink" viewBox="0 0 300 300"><g filter="url(#crayon)" stroke="#2a1d17" stroke-width="7" stroke-linecap="round" fill="none">
  <circle cx="115" cy="165" r="7" fill="#2a1d17"/><path d="M172 166 q13 -12 26 0"/>
  <path d="M122 234 q32 20 62 -6" stroke-width="6"/><path d="M262 120 l8 -14 M272 138 l14 -6" stroke="#ffc93c" stroke-width="6"/></g></symbol>
 <symbol id="sleepy" viewBox="0 0 300 300"><g filter="url(#crayon)" stroke="#2a1d17" stroke-width="7" stroke-linecap="round" fill="none">
  <path d="M102 168 q13 10 26 0 M172 168 q13 10 26 0"/>
  <ellipse cx="150" cy="236" rx="9" ry="7" fill="#2a1d17"/>
  <text x="238" y="100" font-family="Chewy" font-size="34" fill="#243a6b" stroke="none">z</text>
  <text x="258" y="70" font-family="Chewy" font-size="26" fill="#243a6b" stroke="none">z</text></g></symbol>
'''


def svg(w, h, body, label, fonts=FONTS):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{escape(label)}">'
            f'<defs><style>{fonts}</style>{CAPTAIN}'
            f'<filter id="wide" filterUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="{h}"><feTurbulence type="fractalNoise" baseFrequency=".03" numOctaves="2" seed="4" result="w"/><feDisplacementMap in="SourceGraphic" in2="w" scale="5"/></filter></defs>'
            f'{body}</svg>')


def shadowed(x, y, size, text, fill, anchor="start"):
    t = f'x="{x}" y="{y}" font-family="Chewy" font-size="{size}" text-anchor="{anchor}"'
    return (f'<text {t} fill="#2a1d17" transform="translate(5 6)">{escape(text)}</text>'
            f'<text {t} fill="{fill}" stroke="#2a1d17" stroke-width="3" paint-order="stroke">{escape(text)}</text>')


def banner():
    tiles = "".join(f'<rect x="{x}" y="262" width="60" height="38"/>' for x in range(0, 900, 120))
    body = (f'<rect width="900" height="300" fill="#e8452f"/><g fill="#fff" opacity=".18"><path d="M0 250h900" stroke="#fff" stroke-width="3"/>{tiles}</g>'
            '<g transform="translate(40 14) scale(.95)"><use href="#base" width="300" height="300"/><use href="#happy" width="300" height="300"/><use href="#bacon" width="300" height="300"/></g>'
            '<g filter="url(#wide)">' + shadowed(360, 130, 70, "Captain Pancake", "#fff1d6") + shadowed(360, 200, 52, "with Bacon", "#ffc93c")
            + '<text x="362" y="250" font-family="Patrick Hand" font-size="26" fill="#fff1d6">Gijs · student dev · open 24 hours, mostly syrup</text></g>')
    return svg(900, 300, body, "Captain Pancake with Bacon")


def heading(text):
    body = f'<g filter="url(#wide)">{shadowed(6, 50, 46, text, "#e8452f")}</g>'
    return svg(520, 70, body, text, font("Chewy-sub.ttf", "Chewy"))


if __name__ == "__main__":
    (OUT / "banner.svg").write_text(banner())
    for slug, text in [("menu", "Today's Menu"), ("kitchen", "The Kitchen"), ("stove", "On the stove"), ("tools", "Kitchen tools"), ("slip", "The bill")]:
        (OUT / f"h-{slug}.svg").write_text(heading(text))
    print("ok")
