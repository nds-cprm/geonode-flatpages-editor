"""Compila os .po do pacote em .mo sem depender do gettext (msgfmt): python scripts/compilemessages.py"""
import pathlib

import polib

root = pathlib.Path(__file__).resolve().parent.parent / "geonode_flatpages_editor" / "locale"
for po_path in root.glob("*/LC_MESSAGES/*.po"):
    polib.pofile(str(po_path)).save_as_mofile(str(po_path.with_suffix(".mo")))
    print(f"compilado: {po_path.relative_to(root.parent.parent)}")
