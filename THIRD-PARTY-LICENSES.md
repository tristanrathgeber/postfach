# Drittanbieter-Lizenzen

Postfach wird als fertiges macOS-Bundle (`Postfach.app`) ausgeliefert. In diesem Bundle
steckt nicht nur eigener Code: PyInstaller packt die Python-Abhängigkeiten mit hinein,
und das gebaute Frontend (`frontend/dist`) enthält kompiliertes JavaScript sowie die
Web-Schriften als `.woff`/`.woff2`-Dateien. Alle diese Bestandteile werden mitverteilt.

Die meisten dieser Lizenzen (MIT, BSD, Apache-2.0, OFL-1.1, MPL-2.0) verlangen, dass
Lizenztext und Copyright-Vermerk **auch bei reiner Binärverteilung** beiliegen. Genau
dafür gibt es diese Datei.

Postfach selbst steht unter der MIT-Lizenz — siehe [LICENSE](LICENSE).

Stand: Postfach 0.11.0. Jede Angabe unten wurde aus der jeweils installierten
Lizenzdatei bzw. den Paket-Metadaten ausgelesen, nicht aus dem Gedächtnis ergänzt.
Wie man die Liste neu erzeugt, steht ganz unten.

---

## Übersicht

### Schriften (im Frontend-Bundle, als woff/woff2 mitgeliefert)

| Komponente | Version | Lizenz | Zweck |
| --- | --- | --- | --- |
| `@fontsource-variable/instrument-sans` | 5.3.0 | OFL-1.1 | Schriftart (UI) |
| `@fontsource/ibm-plex-mono` | 5.3.0 | OFL-1.1 | Schriftart (Monospace) |
| `@fontsource/newsreader` | 5.3.0 | OFL-1.1 | Schriftart (Serif) |

### JavaScript (in `frontend/dist` einkompiliert)

| Komponente | Version | Lizenz | Zweck |
| --- | --- | --- | --- |
| react | 18.3.1 | MIT | UI-Bibliothek |
| react-dom | 18.3.1 | MIT | DOM-Renderer |
| scheduler | 0.23.2 | MIT | React-Interna |
| @tanstack/react-query | 5.101.2 | MIT | Server-State/Caching |
| @tanstack/query-core | 5.101.2 | MIT | Server-State/Caching |
| cmdk | 1.1.1 | MIT | Command-Palette |
| @radix-ui/react-dialog u. a. @radix-ui/* (17 Pakete) | 0.0.3–2.1.7 | MIT | Dialog-/A11y-Primitives |
| react-remove-scroll, react-remove-scroll-bar, react-style-singleton, use-sidecar, use-callback-ref, aria-hidden, get-nonce, detect-node-es | div. | MIT | Transitive Helfer von cmdk/Radix |
| loose-envify, js-tokens | 1.4.0 / 4.0.0 | MIT | React-Buildhelfer |
| tslib | 2.8.1 | 0BSD | TypeScript-Runtime-Helfer |

### Python (von PyInstaller ins Bundle gepackt)

| Komponente | Version | Lizenz | Zweck |
| --- | --- | --- | --- |
| fastapi | 0.139.2 | MIT | HTTP-API-Framework |
| starlette | 1.3.1 | BSD-3-Clause | ASGI-Unterbau von FastAPI |
| uvicorn | 0.51.0 | BSD-3-Clause | ASGI-/HTTP-Server |
| click | 8.4.2 | BSD-3-Clause | CLI-Parsing (uvicorn) |
| h11 | 0.16.0 | MIT | HTTP/1.1-Protokoll |
| httpx | 0.28.1 | BSD-3-Clause | HTTP-Client (Ollama, Updates) |
| httpcore | 1.0.9 | BSD-3-Clause | Transport-Layer von httpx |
| certifi | 2026.6.17 | MPL-2.0 | CA-Wurzelzertifikate für TLS |
| idna | 3.18 | BSD-3-Clause | Internationalisierte Domainnamen |
| anyio | 4.14.2 | MIT | Async-Abstraktion |
| pydantic | 2.13.4 | MIT | Datenvalidierung |
| pydantic-core | 2.46.4 | MIT | Validierungs-Kern (Rust) |
| annotated-types | 0.7.0 | MIT | Typ-Annotationen für pydantic |
| annotated-doc | 0.0.4 | MIT | Typ-Annotationen für FastAPI |
| typing-inspection | 0.4.2 | MIT | Typ-Introspektion (pydantic) |
| typing_extensions | 4.16.0 | PSF-2.0 | Typing-Backports |
| PyYAML | 6.0.3 | MIT | Konfigurationsdateien lesen |
| IMAPClient | 3.1.0 | BSD-3-Clause | IMAP-Zugriff auf Postfächer |
| nh3 | 0.3.6 | MIT | HTML-Sanitizing von Mails |
| icalendar | 7.2.2 | BSD-2-Clause | Kalendereinladungen parsen |
| python-dateutil | 2.9.0.post0 | Apache-2.0 (dual mit BSD-3-Clause) | Datumsparsing (icalendar) |
| six | 1.17.0 | MIT | Kompatibilitätshelfer (dateutil) |
| keyring | 25.7.0 | MIT | Passwörter im macOS-Schlüsselbund |
| jaraco.classes | 3.4.0 | MIT | Helfer für keyring |
| jaraco.context | 6.1.2 | MIT | Helfer für keyring |
| jaraco.functools | 4.6.0 | MIT | Helfer für keyring |
| more-itertools | 11.1.0 | MIT | Helfer für jaraco.* |
| pywebview | 6.2.1 | BSD-3-Clause | Nativer WebKit-Fensterrahmen |
| bottle | 0.13.4 | MIT | Interner Server von pywebview |
| proxy_tools | 0.1.0 | MIT | Lazy-Proxies für pywebview |
| pyobjc-core | 12.2.1 | MIT | Python↔Objective-C-Brücke |
| pyobjc-framework-Cocoa | 12.2.1 | MIT | AppKit/Foundation-Bindings |
| pyobjc-framework-Quartz | 12.2.1 | MIT | Quartz-Bindings |
| pyobjc-framework-Security | 12.2.1 | MIT | Schlüsselbund-Bindings |
| pyobjc-framework-WebKit | 12.2.1 | MIT | WebKit-Bindings |
| pyobjc-framework-UniformTypeIdentifiers | 12.2.1 | MIT | UTType-Bindings |
| python-multipart | 0.0.32 | Apache-2.0 | Datei-Uploads/Anhänge |
| packaging | 26.2 | Apache-2.0 ODER BSD-2-Clause | Versionsvergleiche |
| Pygments | 2.20.0 | BSD-2-Clause | Syntax-Highlighting (transitiv) |
| pytest | 9.1.1 | MIT | Testframework (transitiv mitgepackt) |
| pluggy | 1.6.0 | MIT | Plugin-System von pytest |
| iniconfig | 2.3.0 | MIT | INI-Parsing für pytest |
| setuptools | 83.0.0 | MIT | Paket-Runtime-Reste |
| email-agent | 0.1.0 | MIT | Mail-Intelligenz (eigenes Schwesterprojekt) |

> Hinweis zu `pytest`/`pluggy`/`iniconfig`/`Pygments`/`setuptools`: diese Pakete landen
> über `collect_all()` transitiv im PYZ-Archiv, obwohl sie zur Laufzeit nicht gebraucht
> werden. Lizenzrechtlich unkritisch (alle MIT/BSD), aber sie sind mitverteilt und
> deshalb hier aufgeführt.

### Optional, zur Laufzeit geladen (nicht im Bundle)

| Komponente | Version | Lizenz | Zweck |
| --- | --- | --- | --- |
| Ollama | jeweils aktuelles Release | MIT | Lokales LLM für Emilia |

`backend/src/postfach/ollama_setup.py` lädt bei Bedarf das offizielle
`ollama-darwin.tgz` vom GitHub-Release herunter, prüft die SHA-256-Summe und legt die
Lizenz neben das Archiv. Ollama wird **nicht** mitgeliefert.
Lizenztext: <https://github.com/ollama/ollama/blob/main/LICENSE>

---

## SIL Open Font License 1.1 (OFL-1.1)

Alle drei Schriften stehen unter der SIL Open Font License, Version 1.1. Der vollständige
Lizenztext liegt jeweils in `frontend/node_modules/<paket>/LICENSE` und ist außerdem
unter <https://scripts.sil.org/OFL> abrufbar.

Die Copyright-Zeilen, wörtlich aus den jeweiligen `LICENSE`-Dateien:

**Instrument Sans** (`@fontsource-variable/instrument-sans` 5.3.0):

```
Copyright 2022 The Instrument Sans Project Authors (https://github.com/Instrument/instrument-sans) InstrumentSans-Italic[wdth,wght].ttf: Copyright 2022 The Instrument Sans Project Authors (https://github.com/Instrument/instrument-sans)
```

**IBM Plex Mono** (`@fontsource/ibm-plex-mono` 5.3.0):

```
Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-ThinItalic.ttf: Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-ExtraLight.ttf: Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-ExtraLightItalic.ttf: Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-Light.ttf: Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-LightItalic.ttf: Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-Regular.ttf: Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-Italic.ttf: Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-Medium.ttf: Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-MediumItalic.ttf: Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-SemiBold.ttf: Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-SemiBoldItalic.ttf: Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-Bold.ttf: Copyright 2017 IBM Corp. All rights reserved. IBMPlexMono-BoldItalic.ttf: Copyright 2017 IBM Corp. All rights reserved.
```

**Newsreader** (`@fontsource/newsreader` 5.3.0):

```
Copyright 2020 The Newsreader Project Authors (http://github.com/productiontype/Newsreader) Newsreader-Italic[opsz,wght].ttf: Copyright 2020 The Newsreader Project Authors (http://github.com/productiontype/Newsreader)
```

**Reserved Font Name:** In keiner der drei ausgelieferten `LICENSE`-Dateien ist ein
Reserved Font Name deklariert — der Ausdruck kommt dort nur in der Begriffsdefinition
des OFL-Textes selbst vor, nicht im Copyright-Vermerk. Postfach liefert die Schriften
außerdem unverändert aus (Original-Version, nur von fontsource in Subsets
zerlegt/nach woff2 konvertiert), führt also keine abgeleitete Version unter neuem Namen.
Die OFL-Bedingungen sind damit erfüllt, solange dieser Abschnitt der Verteilung beiliegt
und die Schriften nicht separat verkauft werden.

---

## BSD-Lizenzen (2- und 3-Clause)

Der BSD-Text verlangt, dass Copyright-Vermerk, Bedingungen und Haftungsausschluss bei
Binärverteilung in der Begleitdokumentation wiedergegeben werden. Copyright-Zeilen,
wörtlich aus den jeweiligen Lizenzdateien:

| Paket | Lizenz | Copyright |
| --- | --- | --- |
| starlette 1.3.1 | BSD-3-Clause | `Copyright © 2018, [Encode OSS Ltd](https://www.encode.io/).` |
| uvicorn 0.51.0 | BSD-3-Clause | `Copyright © 2017-present, [Encode OSS Ltd](https://www.encode.io/).` |
| httpx 0.28.1 | BSD-3-Clause | `Copyright © 2019, [Encode OSS Ltd](https://www.encode.io/).` |
| httpcore 1.0.9 | BSD-3-Clause | `Copyright © 2020, [Encode OSS Ltd](https://www.encode.io/).` |
| click 8.4.2 | BSD-3-Clause | `Copyright 2014 Pallets` |
| idna 3.18 | BSD-3-Clause | `Copyright (c) 2013-2026, Kim Davies and contributors.` |
| IMAPClient 3.1.0 | BSD-3-Clause | `Copyright (c) 2014, Menno Smits` |
| pywebview 6.2.1 | BSD-3-Clause | `Copyright (c) 2014-2017, Roman Sirokov` |
| icalendar 7.2.2 | BSD-2-Clause | `Copyright (c) 2012-2013, Plone Foundation` |
| Pygments 2.20.0 | BSD-2-Clause | `Copyright (c) 2006-2022 by the respective authors (see AUTHORS file).` |
| packaging 26.2 | BSD-2-Clause (Alternative zu Apache-2.0) | `Copyright (c) Donald Stufft and individual contributors.` |

Der jeweils vollständige Lizenztext liegt im installierten Paket unter
`backend/.venv/lib/python3.12/site-packages/<paket>-<version>.dist-info/licenses/`.

Repräsentativer BSD-3-Clause-Wortlaut, wörtlich aus
`starlette-1.3.1.dist-info/licenses/LICENSE.md` (die anderen 3-Clause-Pakete verwenden
denselben Text, teils mit abweichendem Zeilenumbruch):

```
Copyright © 2018, [Encode OSS Ltd](https://www.encode.io/).
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

Die BSD-2-Clause-Pakete (icalendar, Pygments, packaging) verwenden denselben Text ohne
die dritte Klausel ("Neither the name of the copyright holder …").

`tslib` 2.8.1 steht unter **0BSD** (BSD Zero Clause). Diese Lizenz verlangt
ausdrücklich *keine* Weitergabe des Vermerks; sie ist der Vollständigkeit halber
genannt.

---

## Apache License 2.0

Apache-2.0 verlangt (§4), dass Empfänger eine Kopie der Lizenz erhalten und vorhandene
Copyright-/`NOTICE`-Angaben erhalten bleiben.

| Paket | Copyright |
| --- | --- |
| python-multipart 0.0.32 | Die mitgelieferte `LICENSE.txt` enthält den unveränderten Apache-2.0-Text ohne ausgefüllte Copyright-Zeile. Urheber laut Paket-Metadaten: Andrew Dunham <andrew@du.nham.ca>, Projekt: <https://github.com/Kludex/python-multipart>. Eine `NOTICE`-Datei ist nicht enthalten. |
| python-dateutil 2.9.0.post0 | `Copyright 2017- Paul Ganssle <paul@ganssle.io>` / `Copyright 2017- dateutil contributors (see AUTHORS file)` / `Copyright (c) 2003-2011 - Gustavo Niemeyer <gustavo@niemeyer.net>` — dual lizenziert unter Apache-2.0 und BSD-3-Clause |
| packaging 26.2 | `Apache-2.0 OR BSD-2-Clause`; die BSD-Variante trägt `Copyright (c) Donald Stufft and individual contributors.` Der Apache-Text liegt als `LICENSE.APACHE` bei. |

Lizenztext: <https://www.apache.org/licenses/LICENSE-2.0>, außerdem als
`LICENSE.txt` / `LICENSE.APACHE` in den jeweiligen `dist-info`-Verzeichnissen.

---

## Mozilla Public License 2.0 (MPL-2.0)

**certifi 2026.6.17** — enthält das CA-Wurzelzertifikatsbündel aus dem Mozilla-Projekt.
Wörtlich aus `certifi-2026.6.17.dist-info/licenses/LICENSE`:

```
This package contains a modified version of ca-bundle.crt:

ca-bundle.crt -- Bundle of CA Root Certificates

This is a bundle of X.509 certificates of public Certificate Authorities
(CA). These were automatically extracted from Mozilla's root certificates
file (certdata.txt).  This file can be found in the mozilla source tree:
https://hg.mozilla.org/mozilla-central/file/tip/security/nss/lib/ckfw/builtins/certdata.txt
It contains the certificates in PEM format and therefore
can be directly used with curl / libcurl / php_curl, or with
an Apache+mod_ssl webserver for SSL client authentication.
Just configure this file as the SSLCACertificateFile.#

***** BEGIN LICENSE BLOCK *****
This Source Code Form is subject to the terms of the Mozilla Public License,
v. 2.0. If a copy of the MPL was not distributed with this file, You can obtain
one at http://mozilla.org/MPL/2.0/.

***** END LICENSE BLOCK *****
@(#) $RCSfile: certdata.txt,v $ $Revision: 1.80 $ $Date: 2011/11/03 15:11:58 $
```

Die MPL-2.0 ist datei-basiertes Copyleft: sie betrifft nur die MPL-lizenzierten Dateien
selbst (hier das Zertifikatsbündel), das unveränderte Mitverteilen in einem größeren Werk
ist ausdrücklich erlaubt (MPL-2.0 §3.3). Postfach verändert `certifi` nicht.
Vollständiger Lizenztext: <https://mozilla.org/MPL/2.0/>

---

## Python Software Foundation License 2.0

**typing_extensions 4.16.0** — steht unter der PSF-2.0 (derselben Lizenz wie CPython).
Copyright-Zeile aus `typing_extensions-4.16.0.dist-info/licenses/LICENSE`:

```
Copyright (c) 1991 - 1995, Stichting Mathematisch Centrum Amsterdam,
The Netherlands.  All rights reserved.
```

Die PSF-2.0 ist eine permissive Lizenz; sie verlangt die Weitergabe des Vermerks und
einer Zusammenfassung etwaiger Änderungen. Postfach nimmt keine Änderungen vor.
Vollständiger Text: <https://docs.python.org/3/license.html>

---

## MIT-Lizenz

Auch die MIT-Lizenz verlangt, dass Copyright- und Erlaubnisvermerk bei jeder Verteilung
beiliegen. Copyright-Zeilen der mitgelieferten MIT-Pakete, wörtlich aus deren
Lizenzdateien:

| Paket | Copyright |
| --- | --- |
| fastapi 0.139.2 | `Copyright (c) 2018 Sebastián Ramírez` |
| annotated-doc 0.0.4 | `Copyright (c) 2025 Sebastián Ramírez` |
| h11 0.16.0 | `Copyright (c) 2016 Nathaniel J. Smith <njs@pobox.com> and other contributors` |
| anyio 4.14.2 | `Copyright (c) 2018 Alex Grönholm` |
| pydantic 2.13.4 | `Copyright (c) 2017 to present Pydantic Services Inc. and individual contributors.` |
| pydantic-core 2.46.4 | `Copyright (c) 2022 Samuel Colvin` |
| annotated-types 0.7.0 | `Copyright (c) 2022 the contributors` |
| typing-inspection 0.4.2 | `Copyright (c) Pydantic Services Inc. 2025 to present` |
| PyYAML 6.0.3 | `Copyright (c) 2017-2021 Ingy döt Net` / `Copyright (c) 2006-2016 Kirill Simonov` |
| nh3 0.3.6 | `Copyright (c) 2021-present Messense Lv` |
| six 1.17.0 | `Copyright (c) 2010-2024 Benjamin Peterson` |
| keyring 25.7.0 | `Copyright (c) 2025 <copyright holders>` (Platzhalter steht so in der Datei) |
| jaraco.context 6.1.2 | `Copyright (c) 2026 <copyright holders>` (Platzhalter steht so in der Datei) |
| jaraco.functools 4.6.0 | `Copyright (c) 2026 <copyright holders>` (Platzhalter steht so in der Datei) |
| jaraco.classes 3.4.0 | keine Lizenzdatei im `dist-info`; Metadaten weisen MIT aus, Urheber Jason R. Coombs |
| more-itertools 11.1.0 | `Copyright (c) 2012 Erik Rose` |
| bottle 0.13.4 | `Copyright (c) 2009-2024, Marcel Hellkamp.` |
| proxy_tools 0.1.0 | keine Lizenzdatei im `dist-info`; Metadaten weisen MIT aus |
| pyobjc-framework-Cocoa / -Quartz / -WebKit 12.2.1 | `Copyright 2002, 2003 - Bill Bumgarner, Ronald Oussoren, Steve Majewski, Lele Gaifax, et.al.` / `Copyright 2003-2025 - Ronald Oussoren` |
| pyobjc-core / -Security / -UniformTypeIdentifiers 12.2.1 | keine Lizenzdatei im `dist-info`; Metadaten weisen MIT aus, Urheber Ronald Oussoren |
| pytest 9.1.1 | `Copyright (c) 2004 Holger Krekel and others` |
| pluggy 1.6.0 | `Copyright (c) 2015 holger krekel (rather uses bitbucket/hpk42)` |
| iniconfig 2.3.0 | `Copyright (c) 2010 - 2023 Holger Krekel and others` |
| setuptools 83.0.0 | Lizenzdatei enthält den MIT-Text ohne Copyright-Zeile; Urheber laut Metadaten: Python Packaging Authority |
| email-agent 0.1.0 | `Copyright (c) 2026 Tristan Rathgeber` (aus `../email-agent/LICENSE`) |
| react, react-dom, scheduler, @tanstack/*, cmdk, @radix-ui/*, sonstige JS-Helfer | MIT; Copyright-Vermerke in den jeweiligen `LICENSE`-Dateien unter `frontend/node_modules/<paket>/` |

MIT-Wortlaut, wörtlich aus `anyio-4.14.2.dist-info/licenses/LICENSE` (stellvertretend für
alle oben genannten MIT-Pakete — der Text ist bei allen identisch, nur die
Copyright-Zeile unterscheidet sich):

```
The MIT License (MIT)

Copyright (c) 2018 Alex Grönholm

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

---

## Build-Werkzeuge (nicht im Bundle)

Diese Pakete erzeugen die App, werden aber nicht mitverteilt und lösen daher keine
Weitergabepflicht aus:

- **PyInstaller 6.21.0** — GPL-2.0-or-later **mit Bootloader-Ausnahme**. Der in
  `Postfach.app` eingebettete Bootloader fällt unter diese Ausnahme; wörtlich aus
  `pyinstaller-6.21.0.dist-info/licenses/COPYING.txt`:

  ```
  Copyright (c) 2010-2023, PyInstaller Development Team
  Copyright (c) 2005-2009, Giovanni Bajo
  Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.

  Bootloader Exception
  --------------------

  In addition to the permissions in the GNU General Public License, the
  authors give you unlimited permission to link or embed compiled bootloader
  and related files into combinations with other programs, and to distribute
  those combinations without any restriction coming from the use of those
  files. (The General Public License restrictions do apply in other respects;
  for example, they cover modification of the files, and distribution when
  not linked into a combined executable.)
  ```

  Die GPL greift also **nicht** auf Postfach durch. Der Bootloader wird nicht verändert.
- pyinstaller-hooks-contrib 2026.6 (Apache-2.0 / GPL-2.0), altgraph 0.17.5 (MIT),
  macholib 1.16.4 (MIT) — reine Buildzeit-Abhängigkeiten von PyInstaller.
- Frontend-Toolchain: vite, typescript, tailwindcss, postcss, autoprefixer, oxlint,
  vitest und deren transitive Pakete (u. a. `lightningcss` MPL-2.0,
  `caniuse-lite` CC-BY-4.0, `typescript` Apache-2.0). Sie erzeugen `frontend/dist`,
  landen aber selbst nicht darin.

---

## Diese Liste neu erzeugen

```bash
# 1) Python: Lizenz aus den Metadaten der tatsächlich aufgelösten Pakete
cd backend && uv run python -c "from importlib.metadata import distributions; [print(d.metadata['Name'], '|', d.metadata['Version'], '|', d.metadata['License-Expression'] or d.metadata['License'] or [c for c in d.metadata.get_all('Classifier') or [] if 'License' in c]) for d in distributions()]"

# 2) Python: welche Pakete wirklich im Bundle landen (nach einem Build)
grep -o "'[A-Za-z0-9_.]*'" build/postfach/PYZ-00.toc | cut -d. -f1 | sort -u
ls dist/Postfach.app/Contents/Frameworks

# 3) Python: Copyright-Zeilen aus den installierten Lizenzdateien
ls backend/.venv/lib/python3.12/site-packages/*.dist-info/licenses/

# 4) Schriften und JavaScript
cd frontend && cat node_modules/@fontsource-variable/instrument-sans/LICENSE
cat node_modules/@fontsource/ibm-plex-mono/LICENSE
cat node_modules/@fontsource/newsreader/LICENSE
npm ls --omit=dev --all          # Laufzeitbaum des Frontends

# 5) Ollama
# Version und Lizenz stammen aus dem GitHub-Release, das
# backend/src/postfach/ollama_setup.py zur Laufzeit lädt:
# https://github.com/ollama/ollama/blob/main/LICENSE
```

Diese Datei bei jedem Abhängigkeits-Update mitpflegen — insbesondere wenn
`backend/pyproject.toml`, `frontend/package.json` oder `postfach.spec` sich ändern.
