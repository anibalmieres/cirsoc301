# =============================================================================
# CIRSOC 301-2018 — Verificador de Secciones de Acero
# Módulo: doble_t.py — Verificación de secciones Doble T
# =============================================================================
# Copyright (c) 2026 Aníbal Mieres — anibalmieres@gmail.com
# Todos los derechos reservados.
#
# Este software no puede ser utilizado, copiado, modificado, distribuido
# ni incorporado en memorias de cálculo, proyectos o trabajos técnicos
# de terceros sin autorización escrita expresa del autor.
# Para consultas de licencia: anibalmieres@gmail.com
# =============================================================================
#
# Verificación de secciones Doble T simétricas según CIRSOC 301-2018.
# Cubre: Clasificación B.4-1 / E.3 / E.4 / F.2 / F.6 / G.2 / G.6 / D.2 /
#        J.4.3 / H.1-1a / H.1-1b / G.7
#
# CONVENCIÓN DE EJES (CIRSOC 301-2018 §H.1.1):
#   x-x = eje fuerte (Ix mayor) | y-y = eje débil (Iy menor)
#   Mdx (F.2), Vdy (G.2) → comparar con Mux, Vux
#   Mdy (F.6), Vdx (G.6) → comparar con Muy, Vuy
#
# Todas las funciones son puras (sin estado global, sin UI).
# Devuelven objetos BloqueResultado para trazabilidad completa.
#
# Bug documentado y corregido:
#   X2 en §F.2-4d usa Ix (eje fuerte), NO Iy — confirmado vs planilla de
#   referencia MC_em TIPICO CIRSOC_301_2018 18-10-2024.xlsx.
# =============================================================================
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional

from .perfiles     import PerfilDobleT
from .trazabilidad import BloqueResultado, ResultadoVerificacion

π  = math.pi
E  = 200_000.0   # MPa  módulo de Young (acero)
G  = 77_200.0    # MPa  módulo de corte  (acero)


def _sqrt(x: float) -> float:
    return math.sqrt(max(x, 0.0))


# ── Material ──────────────────────────────────────────────────────────────────

@dataclass
class Material:
    """Material de acero estructural según CIRSOC 301-2018 Tabla A-3.1."""
    nombre: str
    Fy:  float   # MPa  tensión de fluencia
    Fu:  float   # MPa  tensión de rotura
    Fr:  float = field(init=False)   # MPa  tensión residual (§F.2)

    _TABLA = {
        "F24": dict(Fy=235, Fu=370, Fr=48),
        "F36": dict(Fy=355, Fu=490, Fr=69),
    }

    def __post_init__(self):
        self.Fr = self._TABLA.get(self.nombre, {}).get("Fr", 69)

    @classmethod
    def desde_nombre(cls, nombre: str) -> "Material":
        t = cls._TABLA.get(nombre)
        if t is None:
            raise ValueError(
                f"Material '{nombre}' no reconocido. Opciones: {list(cls._TABLA)}")
        return cls(nombre=nombre, Fy=t["Fy"], Fu=t["Fu"])


# ── Inputs estructurales ──────────────────────────────────────────────────────

@dataclass
class InputsEstructurales:
    """Parámetros geométrico-estructurales del miembro (no del perfil)."""
    Lx:  float          # cm  longitud de pandeo eje fuerte
    kx:  float          # —   coeficiente eje fuerte
    Ly:  float          # cm  longitud de pandeo eje débil
    ky:  float          # —   coeficiente eje débil
    Lz:  float          # cm  longitud de pandeo torsional
    kz:  float          # —   coeficiente torsional
    Lb:  float          # cm  distancia entre puntos de arriostramiento lateral
    Cb:  float = 1.0    # —   factor de gradiente de momento (1.0 = conservador)
    carga_pos: str = "alma"   # "alma" | "ala_sup"


# ── Inputs de unión ───────────────────────────────────────────────────────────

@dataclass
class InputsUnion:
    """
    Descripción de la unión para cálculo de tracción (§D.2, D.3, J.4.3).

    Modo 1 — soldada total  : tipo="soldada_total"
    Modo 2 — An manual      : tipo="soldada_parcial"|"bulones", An_manual≠None
    Modo 3 — bulones auto   : tipo="bulones", completar db, n_bulones_linea, etc.
    """
    tipo: str = "soldada_total"

    # Modo 2: override manual
    An_manual: Optional[float] = None   # cm²
    U_manual:  Optional[float] = None   # factor de corte diferido D.3

    # Modo 3: disposición de bulones
    db:               float = 0.0    # cm  diámetro nominal del bulón
    n_bulones_linea:  int   = 0      # bulones en dirección de la carga
    n_lineas:         int   = 1      # líneas de bulones en paralelo
    elementos_conectados: str = "todos"   # "ala" | "alma" | "todos"
    t_elemento: Optional[float] = None    # cm  espesor elemento perforado

    # Bloque de corte J.4.3
    Agv: float = 0.0   # cm²  área bruta cortante (0 = no aplica)
    Agt: Optional[float] = None   # cm²  área bruta traccionada (None = Ag)


# ── Caso de carga ─────────────────────────────────────────────────────────────

@dataclass
class CasoCarga:
    """
    Solicitaciones de diseño para un caso de carga.
    Convención: Pu(+) = tracción, Pu(-) = compresión.
    Convención CIRSOC §H.1.1: x = eje fuerte, y = eje débil
    Eje fuerte = x-x → Mux, Vux (alma §G.2) | Eje débil = y-y → Muy, Vuy (alas §G.6)
    """
    label: str
    desc:  str
    Pu:    float = 0.0   # kN    axial
    Mux:   float = 0.0   # kNm   momento último eje fuerte (x-x) §H.1.1
    Muy:   float = 0.0   # kNm   momento último eje débil (y-y) §H.1.1
    Vux:   float = 0.0   # kN    cortante último paralelo al alma (Vdy §G.2)
    Vuy:   float = 0.0   # kN    cortante último paralelo a las alas (Vdx §G.6)
    Tu:    float = 0.0   # kNm   torsión (informativo)


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 0 — Clasificación de sección
# ══════════════════════════════════════════════════════════════════════════════

def clasificar_seccion(p: PerfilDobleT, mat: Material) -> BloqueResultado:
    """Clasifica alas y alma según Tabla B.4-1a (compresión) y B.4-1b (flexión)."""
    b      = BloqueResultado(titulo="Clasificación de sección",
                             referencia="CIRSOC 301-2018 Tabla B.4-1")
    sqEFy  = _sqrt(E / mat.Fy)
    bt     = p.b / p.tf
    htw    = p.hw / p.tw

    # Compresión (B.4-1a)
    lr_ala_c  = 0.56 * sqEFy
    lr_alma_c = 1.49 * sqEFy
    b.agregar("b/t alas [compresión]",
              f"(bf/2)/tf = ({p.bf:.3f}/2)/{p.tf:.3f}",
              bt, "", f"≤ λr = {lr_ala_c:.2f}  (Caso 1)",
              bt <= lr_ala_c, "B.4-1a")
    b.agregar("h/tw alma [compresión]",
              f"hw/tw = {p.hw:.3f}/{p.tw:.3f}",
              htw, "", f"≤ λr = {lr_alma_c:.2f}  (Caso 5)",
              htw <= lr_alma_c, "B.4-1a")

    # Flexión (B.4-1b)
    lp_ala_f  = 0.38 * sqEFy
    lr_ala_f  = 1.00 * sqEFy
    lp_alma_f = 3.76 * sqEFy
    lr_alma_f = 5.70 * sqEFy

    def clasif(val, lp, lr):
        if val <= lp: return "Compacta",    True
        if val <= lr: return "No compacta", None
        return "Esbelta", False

    cls_ala,  ok_ala  = clasif(bt,  lp_ala_f,  lr_ala_f)
    cls_alma, ok_alma = clasif(htw, lp_alma_f, lr_alma_f)

    b.agregar("b/t alas [flexión]",
              f"λp={lp_ala_f:.2f} / λr={lr_ala_f:.2f}",
              bt, "", f"→ {cls_ala}", ok_ala, "B.4-1b Caso 11")
    b.agregar("h/tw alma [flexión]",
              f"λp={lp_alma_f:.1f} / λr={lr_alma_f:.1f}",
              htw, "", f"→ {cls_alma}", ok_alma, "B.4-1b Caso 16")

    b._meta = dict(
        bt=bt, htw=htw,
        lr_ala_c=lr_ala_c, lr_alma_c=lr_alma_c,
        lp_ala_f=lp_ala_f, lr_ala_f=lr_ala_f,
        lp_alma_f=lp_alma_f, lr_alma_f=lr_alma_f,
        cls_ala_flex=cls_ala, cls_alma_flex=cls_alma,
        seccion_compacta=(cls_ala == "Compacta" and cls_alma == "Compacta"),
        Q=1.0,
    )
    b.verifica = (bt <= lr_ala_c) and (htw <= lr_alma_c)
    return b


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE E.3 — Compresión: pandeo flexional
# ══════════════════════════════════════════════════════════════════════════════

def compresion_flexional(p: PerfilDobleT, mat: Material,
                         ie: InputsEstructurales, Q: float = 1.0) -> BloqueResultado:
    b = BloqueResultado(titulo="Compresión — pandeo flexional",
                        referencia="CIRSOC 301-2018 §E.3",
                        simbolo="Pd_flex", unidad="kN")

    kxLx_rx = ie.kx * ie.Lx / p.rx
    kyLy_ry = ie.ky * ie.Ly / p.ry
    kLr     = max(kxLx_rx, kyLy_ry)

    b.agregar("kx·Lx/rx", f"{ie.kx}·{ie.Lx}/{p.rx}",
              kxLx_rx, "", "≤ 200", kxLx_rx <= 200, "§E.3")
    b.agregar("ky·Ly/ry", f"{ie.ky}·{ie.Ly}/{p.ry}",
              kyLy_ry, "", "≤ 200", kyLy_ry <= 200, "§E.3")
    b.agregar("kL/r gobernante", "máx(kxLx/rx, kyLy/ry)", kLr, "")

    lc = (kLr / π) * _sqrt(mat.Fy / E)
    b.agregar("λc = (kL/r)/π · √(Fy/E)",
              f"({kLr:.3f}/π)·√({mat.Fy}/{E})", lc, "", None, None, "E.3-4")
    b.agregar("λc·√Q", f"{lc:.4f}·√{Q}", lc * _sqrt(Q), "")

    if lc * _sqrt(Q) <= 1.5:
        Fcr = Q * (0.658 ** (Q * lc**2)) * mat.Fy
        b.agregar("Fcr = Q·0.658^(Q·λc²)·Fy",
                  f"{Q}·0.658^({Q:.2f}·{lc**2:.4f})·{mat.Fy}",
                  Fcr, "MPa", "λc·√Q ≤ 1.5", None, "E.3-2")
    else:
        Fcr = (0.877 / lc**2) * mat.Fy
        b.agregar("Fcr = (0.877/λc²)·Fy",
                  f"0.877/{lc**2:.4f}·{mat.Fy}",
                  Fcr, "MPa", "λc·√Q > 1.5", None, "E.3-3")

    Pn = Fcr * p.Ag * 1e-1
    Pd = 0.85 * Pn
    b.agregar("Pn = Fcr·Ag·10⁻¹", f"{Fcr:.2f}·{p.Ag}·10⁻¹", Pn, "kN", None, None, "E.3-1")
    b.agregar("Pd = φc·Pn = 0.85·Pn", f"0.85·{Pn:.3f}", Pd, "kN")

    b.valor    = Pd
    b.verifica = (kxLx_rx <= 200) and (kyLy_ry <= 200)
    b._meta    = dict(Fcr=Fcr, Pn=Pn, Pd=Pd, lc=lc, kLr=kLr)
    return b


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE E.4 — Compresión: pandeo torsional
# ══════════════════════════════════════════════════════════════════════════════

def compresion_torsional(p: PerfilDobleT, mat: Material,
                         ie: InputsEstructurales) -> BloqueResultado:
    b = BloqueResultado(titulo="Compresión — pandeo torsional (doble simetría)",
                        referencia="CIRSOC 301-2018 §E.4",
                        simbolo="Pd_tor", unidad="kN")

    Fe = (π**2 * E * p.Cw / (ie.kz * ie.Lz)**2 + G * p.J) / (p.Ix + p.Iy)
    b.agregar("Fe = [π²·E·Cw/(kz·Lz)² + G·J] / (Ix+Iy)",
              f"[π²·{E}·{p.Cw:.0f}/({ie.kz}·{ie.Lz})²+{G}·{p.J}]"
              f"/({p.Ix:.0f}+{p.Iy:.0f})",
              Fe, "MPa", None, None, "E.4-4")

    le = _sqrt(mat.Fy / Fe)
    b.agregar("λe = √(Fy/Fe)", f"√({mat.Fy}/{Fe:.2f})", le, "")

    if le <= 1.5:
        Fcr = (0.658 ** (le**2)) * mat.Fy
        b.agregar("Fcr = 0.658^(λe²)·Fy",
                  f"0.658^({le**2:.4f})·{mat.Fy}",
                  Fcr, "MPa", "λe ≤ 1.5", None, "E.3-2")
    else:
        Fcr = (0.877 / le**2) * mat.Fy
        b.agregar("Fcr = (0.877/λe²)·Fy",
                  f"0.877/{le**2:.4f}·{mat.Fy}",
                  Fcr, "MPa", "λe > 1.5", None, "E.3-3")

    Pn = Fcr * p.Ag * 1e-1
    Pd = 0.85 * Pn
    b.agregar("Pn = Fcr·Ag·10⁻¹", f"{Fcr:.2f}·{p.Ag}·10⁻¹", Pn, "kN")
    b.agregar("Pd = 0.85·Pn",      f"0.85·{Pn:.3f}",          Pd, "kN")

    b.valor    = Pd
    b.verifica = True
    b._meta    = dict(Fe=Fe, Fcr=Fcr, Pn=Pn, Pd=Pd, le=le)
    return b


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE F.2 — Flexión eje fuerte
# ══════════════════════════════════════════════════════════════════════════════

def flexion_eje_fuerte(p: PerfilDobleT, mat: Material,
                       ie: InputsEstructurales, cls_meta: dict) -> BloqueResultado:
    b = BloqueResultado(titulo="Flexión — eje fuerte (x-x)",
                        referencia="CIRSOC 301-2018 §F.2",
                        simbolo="Mdx", unidad="kNm")
    φb = 0.9
    FL = mat.Fy - mat.Fr

    # Plastificación
    Mp  = mat.Fy * p.Zx * 1e-3
    My  = mat.Fy * p.Sx * 1e-3
    Mn_plast = min(Mp, 1.5 * My)
    b.agregar("Mp = Fy·Zx·10⁻³",
              f"{mat.Fy}·{p.Zx}·10⁻³", Mp, "kNm", None, None, "F.2-1")
    b.agregar("1.5·My = 1.5·Fy·Sx·10⁻³",
              f"1.5·{mat.Fy}·{p.Sx}·10⁻³", 1.5*My, "kNm",
              f"Mp {'≤' if Mp <= 1.5*My else '>'} límite", Mp <= 1.5*My)

    # PLT — X1, X2
    # NOTA: X2 usa Ix (eje fuerte) — confirmado vs planilla de referencia
    X1 = (π / p.Sx) * _sqrt(E * G * p.J * p.Ag / 2)
    X2 = (4 * p.Cw / p.Ix) * (p.Sx / (G * p.J))**2

    if ie.carga_pos == "ala_sup":
        Lp    = 709  * p.ry / _sqrt(mat.Fy)
        Lr    = 1.28 * p.ry * X1 / FL
        Mcr   = 1e-3 * 1.28 * ie.Cb * p.Sx * X1 / (ie.Lb / p.ry)
        rLp, rLr = "F.2-5b", "F.2-6b"
    else:
        Lp    = 788  * p.ry / _sqrt(mat.Fy)
        dLr   = _sqrt(1 + _sqrt(1 + X2 * FL**2))
        Lr    = p.ry * X1 / FL * dLr if dLr else 0
        Mcr   = (1e-3 * ie.Cb * p.Sx * X1 * math.sqrt(2) / (ie.Lb / p.ry)
                 * _sqrt(1 + X1**2 * X2 / (2 * (ie.Lb / p.ry)**2)))
        rLp, rLr = "F.2-5a", "F.2-6a"

    Mr = FL * p.Sx * 1e-3

    b.agregar("X1 = (π/Sx)·√(E·G·J·Ag/2)",
              f"(π/{p.Sx:.0f})·√({E}·{G}·{p.J:.1f}·{p.Ag:.1f}/2)",
              X1, "MPa", None, None, "F.2-4c")
    b.agregar("Lp",  f"{'709' if ie.carga_pos=='ala_sup' else '788'}·ry/√Fy",
              Lp, "cm", None, None, rLp)
    b.agregar("Lr",  "ry·X1/FL·f(X1,X2)", Lr, "cm", None, None, rLr)
    b.agregar("Mr = FL·Sx·10⁻³",
              f"({mat.Fy}-{mat.Fr})·{p.Sx}·10⁻³", Mr, "kNm", None, None, "F.2-7a")
    b.agregar("Lb", "dist. entre arriostramientos", ie.Lb, "cm",
              f"{'Lb≤Lp' if ie.Lb<=Lp else ('Lp<Lb≤Lr' if ie.Lb<=Lr else 'Lb>Lr')}")

    if ie.Lb <= Lp:
        Mn_plt = Mp; zona = "Lb ≤ Lp → plastificación"
        b.agregar("Mn = Mp", f"{Mp:.3f}", Mn_plt, "kNm", None, None, "F.2-1")
    elif ie.Lb <= Lr:
        Mn_plt_raw = ie.Cb * (Mp - (Mp - Mr) * (ie.Lb - Lp) / (Lr - Lp))
        Mn_plt = min(Mn_plt_raw, Mp); zona = "Lp < Lb ≤ Lr → PLT inelástico"
        b.agregar("Mn = Cb·(Mp-(Mp-Mr)·(Lb-Lp)/(Lr-Lp))",
                  f"{ie.Cb}·({Mp:.2f}-({Mp:.2f}-{Mr:.2f})·"
                  f"({ie.Lb}-{Lp:.1f})/({Lr:.1f}-{Lp:.1f}))",
                  Mn_plt, "kNm", f"≤ Mp={Mp:.2f}", Mn_plt <= Mp, "F.2-2")
    else:
        Mn_plt = min(Mcr, Mp); zona = "Lb > Lr → PLT elástico"
        b.agregar("Mn = Mcr", f"Cb·Sx·X1·√(...)/{ie.Lb/p.ry:.2f}",
                  Mn_plt, "kNm", f"≤ Mp={Mp:.2f}", Mn_plt <= Mp, "F.2-3")

    b.nota = zona
    Mn  = min(Mn_plast, Mn_plt)
    Md  = φb * Mn
    b.agregar("Mn = mín(Mn_plast, Mn_PLT)", f"mín({Mn_plast:.3f},{Mn_plt:.3f})", Mn, "kNm")
    b.agregar("Md = φb·Mn = 0.9·Mn",        f"0.9·{Mn:.3f}", Md, "kNm")

    b.valor    = Md
    b.verifica = True
    b._meta    = dict(Mp=Mp, Mn=Mn, Md=Md, Lp=Lp, Lr=Lr, Mr=Mr, zona=zona)
    return b


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE F.6 — Flexión eje débil
# ══════════════════════════════════════════════════════════════════════════════

def flexion_eje_debil(p: PerfilDobleT, mat: Material,
                      cls_meta: dict) -> BloqueResultado:
    b = BloqueResultado(titulo="Flexión — eje débil (y-y)",
                        referencia="CIRSOC 301-2018 §F.6",
                        simbolo="Mdy", unidad="kNm")
    φb  = 0.9
    Mp  = mat.Fy * p.Zy * 1e-3
    My  = mat.Fy * p.Sy * 1e-3
    Mn  = min(Mp, 1.5 * My)

    b.agregar("Mp = Fy·Zy·10⁻³",           f"{mat.Fy}·{p.Zy}·10⁻³",         Mp, "kNm", None, None, "F.6-1")
    b.agregar("1.5·My = 1.5·Fy·Sy·10⁻³",   f"1.5·{mat.Fy}·{p.Sy}·10⁻³",    1.5*My, "kNm",
              f"Mp {'≤' if Mp<=1.5*My else '>'} límite", Mp<=1.5*My)
    b.agregar("Mn = mín(Mp, 1.5·My)",        f"mín({Mp:.3f},{1.5*My:.3f})",   Mn, "kNm")

    if cls_meta.get("cls_ala_flex") == "Compacta":
        b.nota = "Ala compacta → no aplica pandeo local del ala (F.6-2)"

    Md = φb * Mn
    b.agregar("Md = 0.9·Mn", f"0.9·{Mn:.3f}", Md, "kNm")
    b.valor    = Md
    b.verifica = True
    b._meta    = dict(Mp=Mp, Mn=Mn, Md=Md)
    return b


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE G.2 — Corte eje fuerte (alma)
# ══════════════════════════════════════════════════════════════════════════════

def corte_eje_fuerte(p: PerfilDobleT, mat: Material) -> BloqueResultado:
    b = BloqueResultado(titulo="Corte por flexión alrededor del eje fuerte (§G.2)",
                        referencia="CIRSOC 301-2018 §G.2",
                        simbolo="Vdy", unidad="kN")  # Vdy — compara con Vuy
    φv  = 0.9
    Aw  = p.h * p.tw
    kv  = 5.0
    htw = p.hw / p.tw
    l1  = 492 * _sqrt(kv / mat.Fy)
    l2  = 613 * _sqrt(kv / mat.Fy)

    b.agregar("Aw = h·tw",  f"{p.h}·{p.tw}", Aw, "cm²", None, None, "G.2-2")
    b.agregar("kv = 5.0",   "alma sin rigidizadores", kv, "")
    b.agregar("h/tw",       f"{p.hw}/{p.tw}", htw, "",
              f"{'≤' if htw<=l1 else '>'} 492·√(kv/Fy)={l1:.2f}")

    if   htw <= l1: Cv = 1.0; ref_cv = "G.2-3"
    elif htw <= l2: Cv = 492 * _sqrt(kv/mat.Fy) / htw; ref_cv = "G.2-4"
    else:           Cv = 302_000 * kv / (htw**2 * mat.Fy); ref_cv = "G.2-5"

    b.agregar("Cv", f"(ver {ref_cv})", Cv, "", None, None, ref_cv)

    Vn = 0.6 * mat.Fy * Aw * Cv * 1e-1
    Vd = φv * Vn
    b.agregar("Vn = 0.6·Fy·Aw·Cv·10⁻¹", f"0.6·{mat.Fy}·{Aw:.3f}·{Cv:.3f}·10⁻¹", Vn, "kN", None, None, "G.2-1")
    b.agregar("Vdx = 0.9·Vn  (§G.6)",            f"0.9·{Vn:.3f}", Vd, "kN")

    b.valor    = Vd
    b.verifica = True
    b._meta    = dict(Aw=Aw, Cv=Cv, Vn=Vn, Vd=Vd)
    return b


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE G.6 — Corte eje débil (alas)
# ══════════════════════════════════════════════════════════════════════════════

def corte_eje_debil(p: PerfilDobleT, mat: Material) -> BloqueResultado:
    b = BloqueResultado(titulo="Corte por flexión alrededor del eje débil (§G.6)",
                        referencia="CIRSOC 301-2018 §G.6",
                        simbolo="Vdx", unidad="kN")  # Vdx — compara con Vux
    φv  = 0.9
    Aw  = p.bf * p.tf
    kv  = 1.2
    btf = p.bf / p.tf
    l1  = 492 * _sqrt(kv / mat.Fy)
    l2  = 613 * _sqrt(kv / mat.Fy)

    b.agregar("Aw = bf·tf", f"{p.bf}·{p.tf}", Aw, "cm²", None, None, "G.2-2")
    b.agregar("kv = 1.2",   "alas", kv, "")
    b.agregar("b/tf",       f"{p.bf}/{p.tf}", btf, "",
              f"{'≤' if btf<=l1 else '>'} {l1:.2f}")

    if   btf <= l1: Cv = 1.0; ref_cv = "G.2-3"
    elif btf <= l2: Cv = 492 * _sqrt(kv/mat.Fy) / btf; ref_cv = "G.2-4"
    else:           Cv = 302_000 * kv / (btf**2 * mat.Fy); ref_cv = "G.2-5"

    b.agregar("Cv", f"(ver {ref_cv})", Cv, "", None, None, ref_cv)

    Vn = 0.6 * mat.Fy * Aw * Cv * 1e-1
    Vd = φv * Vn
    b.agregar("Vn = 0.6·Fy·Aw·Cv·10⁻¹", f"0.6·{mat.Fy}·{Aw:.3f}·{Cv:.3f}·10⁻¹", Vn, "kN", None, None, "G.2-1")
    b.agregar("Vdx = 0.9·Vn  (§G.6)",            f"0.9·{Vn:.3f}", Vd, "kN")

    b.valor    = Vd
    b.verifica = True
    b._meta    = dict(Aw=Aw, Cv=Cv, Vn=Vn, Vd=Vd)
    return b


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE D.2 — Tracción axial
# ══════════════════════════════════════════════════════════════════════════════

def traccion_axial(p: PerfilDobleT, mat: Material,
                   union: InputsUnion) -> BloqueResultado:
    b = BloqueResultado(titulo="Tracción axial",
                        referencia="CIRSOC 301-2018 §D.2 / D.3 / J.4.3",
                        simbolo="Pdt", unidad="kN")

    # EL1: fluencia sección bruta
    Pn_yield = p.Ag * mat.Fy * 1e-1
    Pd_yield = 0.9 * Pn_yield
    b.agregar("Pn = Ag·Fy·10⁻¹ [fluencia bruta]",
              f"{p.Ag}·{mat.Fy}·10⁻¹", Pn_yield, "kN", None, None, "D.2-1")
    b.agregar("Pd = 0.90·Pn", f"0.90·{Pn_yield:.3f}", Pd_yield, "kN")

    # Determinar An y U
    if union.tipo == "soldada_total":
        An, U = p.Ag, 1.0
        b.agregar("An = Ag [soldadura continua]", f"{p.Ag} cm²", An, "cm²", None, None, "D.3")
        b.agregar("U = 1.0 [todos los elementos conectados]", "", U, "", None, None, "D.3-(1)")
    elif union.An_manual is not None:
        An = union.An_manual
        U  = union.U_manual if union.U_manual is not None else 1.0
        b.agregar("An [ingresado manualmente]", f"{An} cm²", An, "cm²")
        b.agregar("U  [ingresado manualmente]", f"{U}", U, "")
    else:
        holgura = 0.32
        t_el    = union.t_elemento or p.tf
        d_aguj  = union.db + holgura
        An      = p.Ag - union.n_bulones_linea * union.n_lineas * d_aguj * t_el
        b.agregar("An = Ag - n·(db+0.32)·t",
                  f"{p.Ag} - {union.n_bulones_linea}·{union.n_lineas}·"
                  f"({union.db}+{holgura})·{t_el:.3f}",
                  An, "cm²", "An > 0", An > 0, "D.3")
        if union.U_manual is not None:
            U = union.U_manual
            b.agregar("U [manual]", f"{U}", U, "", None, None, "D.3")
        elif union.elementos_conectados == "todos":
            U = 1.0
            b.agregar("U = 1.0 [todos los elementos]", "", U, "", None, None, "D.3-(1)")
        elif union.elementos_conectados == "ala":
            U = 0.90 if union.n_bulones_linea >= 3 else 0.85
            b.agregar(f"U = {U} [alas, n={union.n_bulones_linea}]",
                      "Tabla D.3 Caso 2", U, "", None, None, "D.3")
        else:
            U = 0.70
            b.agregar("U = 0.70 [alma]", "Tabla D.3 Caso 2", U, "", None, None, "D.3")

    Ae = An * U
    b.agregar("Ae = An·U", f"{An:.3f}·{U}", Ae, "cm²", None, None, "D.3")

    # EL2: rotura sección neta
    Pn_rupt = Ae * mat.Fu * 1e-1
    Pd_rupt = 0.75 * Pn_rupt
    b.agregar("Pn = Ae·Fu·10⁻¹ [rotura neta]",
              f"{Ae:.3f}·{mat.Fu}·10⁻¹", Pn_rupt, "kN", None, None, "D.2-2")
    b.agregar("Pd = 0.75·Pn", f"0.75·{Pn_rupt:.3f}", Pd_rupt, "kN")

    # EL3: bloque de corte J.4.3
    Pd_bc = None
    if union.Agv > 0:
        Agt   = union.Agt if union.Agt is not None else p.Ag
        Anv   = union.Agv
        Ant   = Agt
        if mat.Fu * Ant >= 0.6 * mat.Fu * Anv:
            Pn_bc  = (0.6 * mat.Fy * union.Agv + mat.Fu * Ant) * 1e-1
            ref_bc = "J.4.3-1"
        else:
            Pn_bc  = (0.6 * mat.Fu * Anv + mat.Fy * Agt) * 1e-1
            ref_bc = "J.4.3-2"
        Pd_bc = 0.75 * Pn_bc
        b.agregar(f"Pn [bloque de corte] ({ref_bc})", "",  Pn_bc, "kN", None, None, "J.4.3")
        b.agregar("Pd = 0.75·Pn_bc", f"0.75·{Pn_bc:.3f}", Pd_bc, "kN")

    candidatos = [(Pd_yield, "fluencia §D.2-1"), (Pd_rupt, "rotura §D.2-2")]
    if Pd_bc is not None:
        candidatos.append((Pd_bc, "bloque de corte §J.4.3"))
    Pd, governa = min(candidatos, key=lambda x: x[0])
    b.agregar(f"Pdt = mín → {governa}",
              " / ".join(f"{v:.2f}" for v, _ in candidatos), Pd, "kN")

    b.valor    = Pd
    b.verifica = (An > 0) if (union.tipo == "bulones" and union.An_manual is None) else True
    b._meta    = dict(Pd_yield=Pd_yield, Pd_rupt=Pd_rupt, Pd_bc=Pd_bc,
                      An=An, Ae=Ae, U=U, governa=governa)
    return b


# ══════════════════════════════════════════════════════════════════════════════
# VERIFICACIÓN DE CASO: H.1 + G.7
# ══════════════════════════════════════════════════════════════════════════════

def verificar_caso(caso: CasoCarga,
                   Pd_comp: float, Pd_tract: float,
                   Mdx: float, Mdy: float,
                   Vdy: float, Vdx: float) -> dict:
    """Verifica H.1-1 y G.7-1 para un caso de carga. Devuelve dict con trazabilidad."""
    Pu        = caso.Pu
    fPn       = Pd_comp if Pu <= 0 else Pd_tract
    tipo_ax   = "compresión" if Pu <= 0 else "tracción"
    ratio_ax  = abs(Pu) / fPn if fPn > 0 else 0

    # G.7 interacción momento-corte
    # G.7: Vux (alma) vs Vdy, Vuy (alas) vs Vdx
    actG7x = (abs(caso.Vux) >= 0.6*Vdy) and (abs(caso.Mux) >= 0.75*Mdx)
    ratG7x = (abs(caso.Mux)/Mdx + 0.625*abs(caso.Vux)/Vdy) if actG7x else None
    actG7y = (abs(caso.Vuy) >= 0.6*Vdx) and (abs(caso.Muy) >= 0.75*Mdy)
    ratG7y = (abs(caso.Muy)/Mdy + 0.625*abs(caso.Vuy)/Vdx) if actG7y else None

    # H.1
    rMx = abs(caso.Mux) / Mdx if Mdx > 0 else 0   # eje fuerte
    rMy = abs(caso.Muy) / Mdy if Mdy > 0 else 0   # eje débil

    if ratio_ax >= 0.2:
        ratio_H1 = ratio_ax + (8/9) * (rMx + rMy);  formula = "H.1-1a"
    else:
        ratio_H1 = ratio_ax / 2 + (rMx + rMy);       formula = "H.1-1b"

    verifica = (ratio_H1 <= 1.0
                and (ratG7x is None or ratG7x <= 1.375)
                and (ratG7y is None or ratG7y <= 1.375))

    return dict(label=caso.label, desc=caso.desc,
                Pu=Pu, Mux=caso.Mux, Muy=caso.Muy,
                Vux=caso.Vux, Vuy=caso.Vuy,
                tipo_axial=tipo_ax, fPn=fPn,
                ratio_ax=ratio_ax, rMx=rMx, rMy=rMy,
                ratio_H1=ratio_H1, formula=formula,
                activa_G7x=actG7x, ratio_G7x=ratG7x,
                activa_G7y=actG7y, ratio_G7y=ratG7y,
                ratio=ratio_H1, verifica=verifica)


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def verificar_doblet(perfil:   PerfilDobleT,
                     material: Material,
                     ie:       InputsEstructurales,
                     union:    InputsUnion,
                     casos:    list[CasoCarga]) -> ResultadoVerificacion:
    """
    Verificación completa de una sección Doble T según CIRSOC 301-2018.
    Devuelve ResultadoVerificacion con todos los bloques y casos de carga.
    """
    res = ResultadoVerificacion(
        perfil   = perfil.nombre,
        material = f"{material.nombre} (Fy={material.Fy} MPa, Fu={material.Fu} MPa)",
    )

    blq_cls = clasificar_seccion(perfil, material)
    res.agregar_bloque(blq_cls)
    cls_meta = blq_cls._meta

    blq_ef = compresion_flexional(perfil, material, ie, Q=cls_meta["Q"])
    blq_et = compresion_torsional(perfil, material, ie)
    res.agregar_bloque(blq_ef)
    res.agregar_bloque(blq_et)

    Pd_comp = min(blq_ef.valor, blq_et.valor)
    gov_txt = "pandeo flexional (E.3)" if blq_ef.valor <= blq_et.valor else "pandeo torsional (E.4)"
    blq_cg  = BloqueResultado(titulo="Compresión — resistencia gobernante",
                              referencia="CIRSOC 301-2018 §E",
                              simbolo="Pd_comp", unidad="kN",
                              valor=Pd_comp, verifica=True)
    blq_cg.agregar(f"Pd = mín(E.3, E.4) → {gov_txt}",
                   f"mín({blq_ef.valor:.2f},{blq_et.valor:.2f})", Pd_comp, "kN")
    res.agregar_bloque(blq_cg)

    blq_fx = flexion_eje_fuerte(perfil, material, ie, cls_meta)
    blq_fy = flexion_eje_debil(perfil, material, cls_meta)
    res.agregar_bloque(blq_fx)
    res.agregar_bloque(blq_fy)

    blq_vz = corte_eje_fuerte(perfil, material)
    blq_vy = corte_eje_debil(perfil, material)
    res.agregar_bloque(blq_vz)
    res.agregar_bloque(blq_vy)

    blq_tr = traccion_axial(perfil, material, union)
    res.agregar_bloque(blq_tr)

    for caso in casos:
        res.casos.append(verificar_caso(
            caso,
            Pd_comp  = Pd_comp,
            Pd_tract = blq_tr.valor,
            Mdx      = blq_fx.valor,
            Mdy      = blq_fy.valor,
            Vdy      = blq_vz.valor,   # G.2 alma → resiste Vux
            Vdx      = blq_vy.valor,   # G.6 alas → resiste Vuy
        ))

    return res
