"""PyInstaller-Einstiegspunkt: startet das native Postfach-Fenster.

Bewusst ein eigenständiges Skript (kein relativer Import), damit PyInstaller
einen klaren Entry-Point hat; die eigentliche Logik liegt in postfach.desktop.
"""

from postfach.desktop import main

if __name__ == "__main__":
    main()
