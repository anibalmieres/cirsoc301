# =============================================================================
# CIRSOC 301-2018 — Verificador de Secciones de Acero
# Módulo: perfiles.py — Carga y validación de base de datos de perfiles
# =============================================================================
# Copyright (c) 2026 Aníbal Mieres — anibalmieres@gmail.com
# Todos los derechos reservados.
#
# Este software no puede ser utilizado, copiado, modificado, distribuido
# ni incorporado en memorias de cálculo, proyectos o trabajos técnicos
# de terceros sin autorización escrita expresa del autor.
# Para consultas de licencia: anibalmieres@gmail.com
# =============================================================================
from __future__ import annotations
import csv
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Optional

_DATA_DIR = Path(__file__).parent.parent / "data"


# ── Dataclasses por familia ───────────────────────────────────────────────────

@dataclass
class PerfilDobleT:
    """Propiedades de una sección Doble T (W, HEA, HEB, IPE, IPN, HP, S, M)."""
    familia:  str
    nombre:   str
    Ag:  float          # cm²   área bruta
    bf:  float          # cm    ancho de ala
    tf:  float          # cm    espesor de ala
    h:   float          # cm    altura total
    hw:  float          # cm    altura del alma
    tw:  float          # cm    espesor del alma
    Ix:  float          # cm⁴   momento de inercia eje fuerte
    Sx:  float          # cm³   módulo elástico eje fuerte
    rx:  float          # cm    radio de giro eje fuerte
    Zx:  float          # cm³   módulo plástico eje fuerte
    Iy:  float          # cm⁴   momento de inercia eje débil
    Sy:  float          # cm³   módulo elástico eje débil
    ry:  float          # cm    radio de giro eje débil
    Zy:  float          # cm³   módulo plástico eje débil
    J:   float          # cm⁴   constante de torsión de St-Venant
    Cw:  float          # cm⁶   constante de alabeo
    g:   float          # kg/m  peso lineal
    fuente: str = "desconocida"
    b: float = field(init=False)   # cm  proyección del ala = bf/2

    def __post_init__(self):
        self.b = self.bf / 2


@dataclass
class PerfilUPN:
    """Propiedades de un perfil canal UPN."""
    familia:  str
    nombre:   str
    Ag:  float
    bf:  float
    tf:  float
    h:   float
    hw:  float
    tw:  float
    Ix:  float
    Sx:  float
    rx:  float
    Zx:  float
    Iy:  float
    Sy:  float
    ry:  float
    Zy:  float
    J:   float
    Cw:  float
    ey:  float          # cm  excentricidad del centroide (eje material)
    ec:  float          # cm  excentricidad del centro de corte
    g:   float
    fuente: str = "desconocida"


@dataclass
class PerfilSimpleL:
    """Propiedades de un ángulo simple L."""
    familia:  str
    nombre:   str
    Ag:   float
    b:    float
    t:    float
    exy:  float
    Iv:   float
    rv:   float
    Iz:   float
    rz:   float
    Ixy:  float
    rxy:  float
    J:    float
    Cw:   float
    g:    float
    gramil: float
    fuente: str = "desconocida"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _cast(row: dict, key: str) -> float:
    try:
        return float(row[key])
    except (ValueError, KeyError):
        raise ValueError(
            f"Perfil '{row.get('nombre','?')}': campo '{key}' inválido → '{row.get(key)}'"
        )


# ── Loaders ───────────────────────────────────────────────────────────────────

def cargar_doblet(csv_path: Optional[Path] = None) -> dict[str, PerfilDobleT]:
    """Carga perfiles_doblet.csv. Devuelve dict {nombre: PerfilDobleT}."""
    path   = csv_path or _DATA_DIR / "perfiles_doblet.csv"
    rows   = _load_csv(path)
    result: dict[str, PerfilDobleT] = {}
    errores: list[str] = []
    campos = ["Ag","bf","tf","h","hw","tw","Ix","Sx","rx","Zx","Iy","Sy","ry","Zy","J","Cw","g"]
    for row in rows:
        nombre = row.get("nombre", "?")
        try:
            vals = {c: _cast(row, c) for c in campos}
            result[nombre] = PerfilDobleT(
                familia=row["familia"], nombre=nombre,
                fuente=row.get("fuente","desconocida"), **vals)
        except ValueError as e:
            errores.append(str(e))
    if errores:
        raise ValueError(f"Errores en {path.name}:\n" + "\n".join(errores))
    return result


def cargar_upn(csv_path: Optional[Path] = None) -> dict[str, PerfilUPN]:
    path   = csv_path or _DATA_DIR / "perfiles_upn.csv"
    rows   = _load_csv(path)
    result: dict[str, PerfilUPN] = {}
    campos = ["Ag","bf","tf","h","hw","tw","Ix","Sx","rx","Zx","Iy","Sy","ry","Zy","J","Cw","ey","ec","g"]
    for row in rows:
        nombre = row.get("nombre","?")
        vals   = {c: _cast(row, c) for c in campos}
        result[nombre] = PerfilUPN(
            familia=row["familia"], nombre=nombre,
            fuente=row.get("fuente","desconocida"), **vals)
    return result


def cargar_simplel(csv_path: Optional[Path] = None) -> dict[str, PerfilSimpleL]:
    path   = csv_path or _DATA_DIR / "perfiles_simplel.csv"
    rows   = _load_csv(path)
    result: dict[str, PerfilSimpleL] = {}
    campos = ["Ag","b","t","exy","Iv","rv","Iz","rz","Ixy","rxy","J","Cw","g","gramil"]
    for row in rows:
        nombre = row.get("nombre","?")
        vals   = {c: _cast(row, c) for c in campos}
        result[nombre] = PerfilSimpleL(
            familia=row["familia"], nombre=nombre,
            fuente=row.get("fuente","desconocida"), **vals)
    return result


# ── Utilidades ────────────────────────────────────────────────────────────────

def listar_familias(perfiles: dict) -> list[str]:
    return sorted(set(p.familia for p in perfiles.values()))


def filtrar_familia(perfiles: dict, familia: str) -> dict:
    return {k: v for k, v in perfiles.items() if v.familia == familia}
