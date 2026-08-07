"""Genera la fuente de iconos empaquetada a partir de Material Symbols Outlined.

La fuente original de Google es variable y pesa ~10 MB, demasiado para empaquetar
en el instalador. Este script la reduce a una fuente estática de unos pocos KB con
solo los iconos que usa la aplicación.

Uso:

    python scripts/build_icon_font.py

Genera dos archivos:

- ``app/assets/fonts/MaterialSymbolsOutlined.ttf`` — fuente recortada.
- ``app/components/theme/icon_codepoints.py`` — mapa nombre → codepoint.

Requiere ``fonttools`` (solo en desarrollo, no en tiempo de ejecución) y descarga
la fuente original a una carpeta de caché temporal la primera vez.

Para añadir un icono nuevo: agregar su nombre a ``ICON_NAMES`` y volver a ejecutar.
"""

from __future__ import annotations

import sys
import tempfile
import urllib.request
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

REPO_ROOT = Path(__file__).resolve().parent.parent
FONT_OUT = REPO_ROOT / "app" / "assets" / "fonts" / "MaterialSymbolsOutlined.ttf"
CODEPOINTS_OUT = REPO_ROOT / "app" / "components" / "theme" / "icon_codepoints.py"

_BASE = (
    "https://github.com/google/material-design-icons/raw/master/variablefont/"
    "MaterialSymbolsOutlined%5BFILL%2CGRAD%2Copsz%2Cwght%5D"
)
FONT_URL = f"{_BASE}.ttf"
CODEPOINTS_URL = f"{_BASE}.codepoints"

# Instancia estática que queremos: contorno sin relleno, grosor regular, 24 px.
AXIS_VALUES = {"FILL": 0, "GRAD": 0, "opsz": 24, "wght": 400}

# Iconos usados por la aplicación. Los nombres son los de Material Symbols.
ICON_NAMES = [
    # Shell: barra lateral y superior
    "document_scanner", "folder_open", "photo_library", "local_shipping",
    "history", "download", "terminal", "info", "logout", "settings",
    "search", "notifications", "dashboard", "grid_view",
    # Visor de imagen
    "zoom_in", "zoom_out", "crop", "fit_screen", "rotate_left",
    "rotate_right", "aspect_ratio", "image",
    # Panel de extracción
    "auto_awesome", "bolt", "save", "refresh", "person", "map", "mail",
    "phone", "place", "sticky_note_2", "numbers", "badge", "apartment",
    "data_object",
    # Login
    "lock", "login", "error", "visibility", "visibility_off",
    # Ventana de envíos
    "check_circle", "inventory_2", "edit_document", "verified", "close",
    "send", "straighten", "scale", "category", "package_2", "assignment",
    "receipt_long", "alternate_email", "public", "tune",
    # Exportación
    "calendar_month", "schedule", "table_chart", "description", "filter_alt",
    # Varios
    "arrow_forward", "chevron_right", "expand_more", "warning", "task_alt",
    "cancel", "add", "open_in_full", "more_vert", "help",
    # Controles nativos que QSS dibuja con imagen (flechas, marca de selección)
    "expand_less", "check",
]


def _cache_dir() -> Path:
    path = Path(tempfile.gettempdir()) / "extractor_ocr_iconfont"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _download(url: str, target: Path) -> Path:
    if target.exists() and target.stat().st_size > 1024:
        print(f"caché: {target.name}")
        return target
    print(f"descargando {url}")
    urllib.request.urlretrieve(url, target)
    return target


def _load_codepoints(path: Path) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            mapping[parts[0]] = int(parts[1], 16)
    return mapping


def _write_codepoints_module(selected: dict[str, int]) -> None:
    lines = [
        '"""Codepoints de los iconos empaquetados (Material Symbols Outlined).',
        "",
        "Archivo generado por ``scripts/build_icon_font.py``. No editar a mano:",
        "los codepoints deben coincidir con los glifos incluidos en la fuente.",
        '"""',
        "",
        "ICON_CODEPOINTS = {",
    ]
    for name in sorted(selected):
        lines.append(f'    "{name}": "\\u{selected[name]:04x}",')
    lines.append("}")
    lines.append("")
    CODEPOINTS_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"escrito {CODEPOINTS_OUT.relative_to(REPO_ROOT)} ({len(selected)} iconos)")


def main() -> int:
    cache = _cache_dir()
    font_src = _download(FONT_URL, cache / "MaterialSymbolsOutlined-variable.ttf")
    codepoints_src = _download(CODEPOINTS_URL, cache / "MaterialSymbolsOutlined.codepoints")

    all_codepoints = _load_codepoints(codepoints_src)
    unknown = [name for name in ICON_NAMES if name not in all_codepoints]
    if unknown:
        print(f"ERROR: iconos inexistentes en Material Symbols: {unknown}", file=sys.stderr)
        return 1

    duplicates = {name for name in ICON_NAMES if ICON_NAMES.count(name) > 1}
    if duplicates:
        print(f"ERROR: nombres repetidos en ICON_NAMES: {sorted(duplicates)}", file=sys.stderr)
        return 1

    selected = {name: all_codepoints[name] for name in ICON_NAMES}

    font = TTFont(str(font_src))
    instantiateVariableFont(font, AXIS_VALUES, inplace=True, updateFontNames=False)

    options = Options()
    # Los iconos se dibujan por codepoint, no por ligadura de nombre.
    options.layout_features = []
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.name_legacy = True
    options.notdef_outline = True
    options.drop_tables += ["DSIG"]

    subsetter = Subsetter(options=options)
    subsetter.populate(unicodes=selected.values())
    subsetter.subset(font)

    FONT_OUT.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(FONT_OUT))
    font.close()

    size_kb = FONT_OUT.stat().st_size / 1024
    print(f"escrito {FONT_OUT.relative_to(REPO_ROOT)} ({size_kb:.1f} KB)")

    _write_codepoints_module(selected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
