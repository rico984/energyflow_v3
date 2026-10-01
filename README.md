# SENEC Hybrid-Inverter Streamlit-Prototyp

## Start unter Windows

1. ZIP entpacken.
2. `start_app.bat` doppelklicken.
3. Beim ersten Start werden virtuelle Umgebung und Pakete eingerichtet.

Manuell:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Der Prototyp ist ein Näherungsmodell, kein Firmware-Emulator.

## Erweiterte Grenzen

- SOC-Minimum und SOC-Maximum mit linearer Abregelzone
- Getrennte Temperaturfenster für Laden und Entladen
- BMS-Freigaben für Laden und Entladen
- Separate maximale BMS-Lade- und Entladeströme
- Anzeige der verfügbaren, genutzten und abgeregelten PV-Leistung sowie der Abregelquote

## Mehrtagessimulation

- Simulationsdauer von 1 bis 72 Stunden, entsprechend maximal 3 Tagen
- Wählbare Auflösung von 1, 2, 5, 10, 15, 30 oder 60 Minuten
- Frei wählbares Startdatum und Startzeit
- Tagesabhängiges PV-Profil mit Sonnenaufgang um 06:00 Uhr, Maximum um 12:00 Uhr und Sonnenuntergang um 18:00 Uhr
- Datums- und Uhrzeitachse im Diagramm und im CSV-Export

## AC-Fahrplan

- Drei aktivierbare, täglich wiederkehrende Zeitfenster mit Start, Ende und statischer AC-Leistung
- Zeitfenster über Mitternacht werden unterstützt
- Bei Überschneidungen gilt die Priorität Zeitfenster 1, danach 2, danach 3
- Positive Fahrplanwerte werden exakt gehalten, sofern PV und Batterie genügend Leistung liefern
- Bei fehlender Quellleistung darf die positive AC-Abgabe unter den Sollwert fallen
- Negative Fahrplanwerte fordern Netzbezug; PV-Export ist dann gesperrt
- Ist die Batterie voll oder anderweitig nicht ladefähig, wird überschüssige PV-Leistung auf 0 W Nutzleistung abgeregelt
