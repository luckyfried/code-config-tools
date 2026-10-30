# Font licenses

Every font here is licensed under the SIL Open Font License 1.1 (OFL), from the Google Fonts repository
(github.com/google/fonts, `ofl/`). Free for commercial use. Local `.ttf` files only; nothing loads from a CDN.
`styles/<id>/` holds the two faces of the style card `styles/<id>.json` and `OFL.txt`, both families' license text.
A variable file is used at its default instance, which is the weight the card names.

| Style | Family | File | Role | Source |
|---|---|---|---|---|
| editorial-quiet | Instrument Serif | `styles/editorial-quiet/InstrumentSerif-Regular.ttf`, `InstrumentSerif-Italic.ttf` | display, the closing caption in italic | google/fonts/ofl/instrumentserif |
| editorial-quiet | Hanken Grotesk | `styles/editorial-quiet/HankenGrotesk[wght].ttf` | text | google/fonts/ofl/hankengrotesk |
| kinetic-type | Bricolage Grotesque | `styles/kinetic-type/BricolageGrotesque[opsz,wdth,wght].ttf` | display | google/fonts/ofl/bricolagegrotesque |
| kinetic-type | Anton | `styles/kinetic-type/Anton-Regular.ttf` | text, the built name | google/fonts/ofl/anton |
| scrapbook | Caveat Brush | `styles/scrapbook/CaveatBrush-Regular.ttf` | display, hand lettering | google/fonts/ofl/caveatbrush |
| scrapbook | Gloock | `styles/scrapbook/Gloock-Regular.ttf` | text | google/fonts/ofl/gloock |
| analog-home-movie | Young Serif | `styles/analog-home-movie/YoungSerif-Regular.ttf` | display, title cards | google/fonts/ofl/youngserif |
| analog-home-movie | VT323 | `styles/analog-home-movie/VT323-Regular.ttf` | text, the date stamp | google/fonts/ofl/vt323 |
| swiss-grid | Geist | `styles/swiss-grid/Geist[wght].ttf` | display | google/fonts/ofl/geist |
| swiss-grid | Geist Mono | `styles/swiss-grid/GeistMono[wght].ttf` | text, labels | google/fonts/ofl/geistmono |
| cinematic-letterbox | Cinzel | `styles/cinematic-letterbox/Cinzel[wght].ttf` | display | google/fonts/ofl/cinzel |
| cinematic-letterbox | Cormorant | `styles/cinematic-letterbox/Cormorant[wght].ttf` | text | google/fonts/ofl/cormorant |

`route/<id>/` holds static instances of a style's own families at the weights the route sets that style's words in
on a phone (`PHONE` in `scripts/board_drive.py`), each cut from the variable file under `styles/<id>/` at its weight
with fontTools' instancer, and `OFL.txt` beside them; the OFL lets a modified version keep the family's name, since
neither family reserves one.

| Style | Family | File | Weight | Role |
|---|---|---|---|---|
| cinematic-letterbox | Cinzel | `route/cinematic-letterbox/Cinzel-SemiBold.ttf` | 600 | the hook's title, each stop's place and month |
| cinematic-letterbox | Cormorant | `route/cinematic-letterbox/Cormorant-Medium.ttf` | 500 | each stop's caption, the hook's handle |

Full OFL 1.1 text: https://openfontlicense.org/open-font-license-1-1/
