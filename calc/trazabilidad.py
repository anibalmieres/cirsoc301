# =============================================================================
# CIRSOC 301-2018 — Verificador de Secciones de Acero
# Módulo: trazabilidad.py — Objetos de resultado y renderizado
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
from dataclasses import dataclass, field
from typing import Optional
import math

COPYRIGHT = "© 2026 Aníbal Mieres — anibalmieres@gmail.com"
VERSION   = "1.0.0"


# ── Objetos de resultado ──────────────────────────────────────────────────────

@dataclass
class Paso:
    desc:   str
    expr:   str
    valor:  Optional[float]
    unidad: str = ""
    limite: Optional[str] = None
    ok:     Optional[bool] = None
    ref:    str = ""


@dataclass
class BloqueResultado:
    titulo:     str
    referencia: str
    pasos:      list[Paso] = field(default_factory=list)
    simbolo:    str = ""
    valor:      Optional[float] = None
    unidad:     str = "kN"
    verifica:   Optional[bool] = None
    nota:       str = ""

    def agregar(self, desc, expr, valor, unidad="", limite=None, ok=None, ref=""):
        self.pasos.append(Paso(desc, expr, valor, unidad, limite, ok, ref))
        return valor

    def _fmt(self, v, d=4):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "—"
        if abs(v) >= 10000:
            return f"{v:,.1f}"
        if abs(v) >= 100:
            return f"{v:.2f}"
        return f"{v:.{d}f}"


@dataclass
class ResultadoVerificacion:
    perfil:   str
    material: str
    bloques:  list[BloqueResultado] = field(default_factory=list)
    casos:    list[dict]            = field(default_factory=list)

    def agregar_bloque(self, b: BloqueResultado):
        self.bloques.append(b)

    def resistencias(self) -> dict:
        return {b.simbolo: (b.valor, b.unidad)
                for b in self.bloques if b.simbolo}

    def todo_verifica(self) -> bool:
        ok_b = all(b.verifica is not False for b in self.bloques)
        ok_c = all(c.get("verifica", True) for c in self.casos)
        return ok_b and ok_c


# ── Renderizado Jupyter ───────────────────────────────────────────────────────

try:
    from IPython.display import display, HTML
    _IPYTHON = True
except ImportError:
    _IPYTHON = False


def _color_ok(ok):
    if ok is True:  return "#2d6a4f"
    if ok is False: return "#c1121f"
    return "#495057"

def _icono(ok):
    if ok is True:  return "✓"
    if ok is False: return "✗"
    return " "


def mostrar_bloque(bloque: BloqueResultado):
    if not _IPYTHON:
        _print_bloque_texto(bloque); return

    filas = ""
    for p in bloque.pasos:
        color = _color_ok(p.ok)
        icono = _icono(p.ok)
        val   = bloque._fmt(p.valor) if p.valor is not None else "—"
        lim   = p.limite or ""
        ref   = f'<span style="color:#6c757d;font-size:11px">{p.ref}</span>' if p.ref else ""
        filas += f"""
        <tr>
          <td style="padding:3px 8px;color:#495057">{p.desc}</td>
          <td style="padding:3px 8px;font-family:monospace;color:#212529">{p.expr}</td>
          <td style="padding:3px 8px;font-family:monospace;text-align:right;
                     font-weight:500;color:{color}">{val}</td>
          <td style="padding:3px 8px;color:#6c757d">{p.unidad}</td>
          <td style="padding:3px 8px;color:#6c757d;font-size:12px">{lim}</td>
          <td style="padding:3px 8px;text-align:center;color:{color};font-weight:600">{icono}</td>
          <td style="padding:3px 8px">{ref}</td>
        </tr>"""

    vc    = _color_ok(bloque.verifica)
    vi    = _icono(bloque.verifica)
    valf  = bloque._fmt(bloque.valor) if bloque.valor is not None else "—"
    fila_res = f"""
        <tr style="border-top:2px solid #dee2e6;background:#f8f9fa">
          <td colspan="2" style="padding:5px 8px;font-weight:600;color:#212529">
            {bloque.simbolo} = φ · Rn</td>
          <td style="padding:5px 8px;font-family:monospace;font-weight:700;
                     font-size:15px;text-align:right;color:{vc}">{valf}</td>
          <td style="padding:5px 8px;font-weight:600;color:#495057">{bloque.unidad}</td>
          <td colspan="2" style="padding:5px 8px;font-weight:700;
                                 font-size:15px;color:{vc}">{vi}</td>
          <td></td>
        </tr>"""

    nota_html = (f"<div style='padding:6px 12px;background:#fff3cd;font-size:12px'>"
                 f"⚠ {bloque.nota}</div>" if bloque.nota else "")

    html = f"""
    <div style="margin:12px 0;border:1px solid #dee2e6;border-radius:6px;overflow:hidden">
      <div style="background:#343a40;color:#f8f9fa;padding:8px 12px;
                  display:flex;justify-content:space-between;align-items:center">
        <span style="font-weight:600;font-size:14px">{bloque.titulo}</span>
        <span style="font-size:12px;color:#adb5bd">{bloque.referencia}</span>
      </div>
      {nota_html}
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead>
          <tr style="background:#f1f3f5;color:#6c757d;font-size:11px;
                     text-transform:uppercase;letter-spacing:0.05em">
            <th style="padding:4px 8px;text-align:left">Descripción</th>
            <th style="padding:4px 8px;text-align:left">Expresión</th>
            <th style="padding:4px 8px;text-align:right">Valor</th>
            <th style="padding:4px 8px">Unidad</th>
            <th style="padding:4px 8px">Límite</th>
            <th style="padding:4px 8px;text-align:center">OK</th>
            <th style="padding:4px 8px">Ref.</th>
          </tr>
        </thead>
        <tbody>{filas}{fila_res}</tbody>
      </table>
    </div>"""
    display(HTML(html))


def mostrar_resumen(resultado: ResultadoVerificacion):
    if not _IPYTHON:
        _print_resumen_texto(resultado); return

    filas_r = ""
    for b in resultado.bloques:
        if not b.simbolo: continue
        vc  = _color_ok(b.verifica)
        vi  = _icono(b.verifica)
        val = b._fmt(b.valor) if b.valor is not None else "—"
        filas_r += f"""
        <tr>
          <td style="padding:4px 10px;font-family:monospace;font-weight:500">{b.simbolo}</td>
          <td style="padding:4px 10px;color:#6c757d;font-size:12px">{b.titulo}</td>
          <td style="padding:4px 10px;font-family:monospace;font-weight:600;
                     text-align:right;color:{vc}">{val}</td>
          <td style="padding:4px 10px;color:#6c757d">{b.unidad}</td>
          <td style="padding:4px 10px;text-align:center;color:{vc};font-weight:700">{vi}</td>
        </tr>"""

    filas_c = ""
    for c in resultado.casos:
        ratio     = c.get("ratio", 0)
        ok        = c.get("verifica", True)
        color     = _color_ok(ok)
        icono     = _icono(ok)
        bar_w     = min(int(ratio * 100), 100)
        bar_color = "#2d6a4f" if ratio <= 0.8 else "#f4a261" if ratio <= 1.0 else "#c1121f"
        filas_c += f"""
        <tr>
          <td style="padding:4px 10px;font-weight:500">{c.get('label','')}</td>
          <td style="padding:4px 10px;color:#6c757d;font-size:12px">{c.get('desc','')}</td>
          <td style="padding:4px 10px;color:#6c757d;font-size:11px">{c.get('formula','')}</td>
          <td style="padding:4px 10px">
            <div style="background:#e9ecef;border-radius:3px;height:8px;width:120px">
              <div style="background:{bar_color};width:{bar_w}%;height:100%;border-radius:3px"></div>
            </div>
          </td>
          <td style="padding:4px 10px;font-family:monospace;font-weight:600;
                     text-align:right;color:{color}">{ratio:.3f}</td>
          <td style="padding:4px 10px;text-align:center;color:{color};font-weight:700">{icono}</td>
        </tr>"""

    todo_ok    = resultado.todo_verifica()
    est_color  = "#2d6a4f" if todo_ok else "#c1121f"
    est_txt    = "✓  TODOS VERIFICAN" if todo_ok else "✗  NO VERIFICA"

    html = f"""
    <div style="margin:16px 0">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
        <div>
          <span style="font-size:16px;font-weight:700">Verificación — {resultado.perfil}</span>
          <span style="font-size:12px;color:#6c757d;margin-left:10px">Material {resultado.material}</span>
        </div>
        <span style="padding:6px 16px;border-radius:20px;font-weight:700;font-size:13px;
                     background:{'#d8f3dc' if todo_ok else '#ffe0e0'};color:{est_color}">{est_txt}</span>
      </div>
      <div style="font-size:12px;font-weight:600;color:#6c757d;text-transform:uppercase;
                  letter-spacing:0.08em;margin-bottom:4px">Resistencias de diseño</div>
      <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:16px;
                    border:1px solid #dee2e6;border-radius:6px;overflow:hidden">
        <thead><tr style="background:#f1f3f5;color:#6c757d;font-size:11px;text-transform:uppercase">
          <th style="padding:5px 10px;text-align:left">Símbolo</th>
          <th style="padding:5px 10px;text-align:left">Verificación</th>
          <th style="padding:5px 10px;text-align:right">φRn</th>
          <th style="padding:5px 10px">Unidad</th>
          <th style="padding:5px 10px;text-align:center">OK</th>
        </tr></thead>
        <tbody>{filas_r}</tbody>
      </table>
      <div style="font-size:12px;font-weight:600;color:#6c757d;text-transform:uppercase;
                  letter-spacing:0.08em;margin-bottom:4px">Combinaciones por caso de carga</div>
      <table style="width:100%;border-collapse:collapse;font-size:13px;
                    border:1px solid #dee2e6;border-radius:6px;overflow:hidden">
        <thead><tr style="background:#f1f3f5;color:#6c757d;font-size:11px;text-transform:uppercase">
          <th style="padding:5px 10px;text-align:left">Caso</th>
          <th style="padding:5px 10px;text-align:left">Descripción</th>
          <th style="padding:5px 10px;text-align:left">Fórmula</th>
          <th style="padding:5px 10px">Aprovechamiento</th>
          <th style="padding:5px 10px;text-align:right">Ratio</th>
          <th style="padding:5px 10px;text-align:center">OK</th>
        </tr></thead>
        <tbody>{filas_c}</tbody>
      </table>
      <div style="margin-top:12px;text-align:right;font-size:11px;color:#adb5bd">
        {COPYRIGHT} — v{VERSION}
      </div>
    </div>"""
    display(HTML(html))


def mostrar_memoria(resultado: ResultadoVerificacion):
    """Memoria completa: todos los bloques + resumen ejecutivo."""
    for bloque in resultado.bloques:
        mostrar_bloque(bloque)
    mostrar_resumen(resultado)


# ── Fallback texto ────────────────────────────────────────────────────────────

def _print_bloque_texto(b: BloqueResultado):
    print(f"\n{'━'*70}\n  {b.titulo}   [{b.referencia}]\n{'━'*70}")
    for p in b.pasos:
        ok_str = f"  {_icono(p.ok)}" if p.ok is not None else ""
        lim    = f"  ({p.limite})" if p.limite else ""
        val    = f"{p.valor:.4g}" if p.valor is not None else "—"
        print(f"  {p.desc:<30}  {p.expr:<45}  {val:>10} {p.unidad:<4}{lim}{ok_str}")
    valf = f"{b.valor:.4g}" if b.valor is not None else "—"
    print(f"{'─'*70}\n  {b.simbolo} = {valf} {b.unidad}  {_icono(b.verifica)}")


def _print_resumen_texto(r: ResultadoVerificacion):
    print(f"\n{'═'*70}\n  RESUMEN — {r.perfil}  [{r.material}]\n{'═'*70}")
    for b in r.bloques:
        if not b.simbolo: continue
        val = f"{b.valor:.2f}" if b.valor is not None else "—"
        print(f"  {b.simbolo:<10}  {val:>10} {b.unidad:<5}  {_icono(b.verifica)}")
    print()
    for c in r.casos:
        print(f"  {c.get('label',''):<10}  ratio={c.get('ratio',0):.3f}  "
              f"{c.get('formula','')}  {_icono(c.get('verifica'))}")
    print(f"\n  {COPYRIGHT}")
