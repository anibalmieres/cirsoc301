# CIRSOC 301-2018 — Verificador de Secciones de Acero

**Autor:** Aníbal Mieres — anibalmieres@gmail.com  
**Versión:** 1.0.0  
© 2026 Aníbal Mieres. Todos los derechos reservados.

> **Aviso de uso:** Este software no puede ser utilizado, copiado ni distribuido
> en memorias de cálculo, proyectos o trabajos técnicos de terceros sin
> autorización escrita expresa del autor. Ver `LICENSE` para más detalle.

---

## Descripción

Herramienta de verificación estructural de secciones de acero según **CIRSOC 301-2018**
(basado en AISC 360-05). Disponible como:

- **Web app** — interfaz para ingenieros, sin instalación
- **Notebooks Jupyter** — memoria de cálculo auditable, trazabilidad completa
- **Módulos Python** — núcleo de cálculo reutilizable, testeable

## Estructura del repositorio

```
cirsoc301/
├── calc/                        ← núcleo de cálculo (Python puro)
│   ├── __init__.py
│   ├── perfiles.py              ← carga y validación de CSVs
│   ├── doble_t.py               ← verificación Doble T ✓
│   └── trazabilidad.py          ← objetos de resultado y renderizado Jupyter
│
├── data/                        ← base de datos de perfiles (EDITABLE)
│   ├── perfiles_doblet.csv      ← 367 perfiles: W, HEA, HEB, IPE, IPN, HP, S, M
│   ├── perfiles_upn.csv         ← 12 perfiles UPN
│   └── perfiles_simplel.csv     ← 28 ángulos simples L
│
├── notebooks/
│   └── 01_doble_t.ipynb         ← verificación Doble T con trazabilidad completa ✓
│
├── web/
│   ├── index.html               ← página de inicio — selector de tipologías ✓
│   └── doble_t.html             ← verificación Doble T interactiva ✓
│
├── .gitignore
├── LICENSE                      ← licencia propietaria
├── README.md
├── requirements.txt
└── vercel.json                  ← configuración de deploy automático
```

## Tipologías

| # | Tipología | Módulo | Notebook | Web | Estado |
|---|-----------|--------|----------|-----|--------|
| 1 | Doble T (W, HEA, HEB, IPE...) | `calc/doble_t.py` | `01_doble_t.ipynb` | `doble_t.html` | ✅ completo |
| 2 | UPN simple | — | — | — | 🔜 próximo |
| 3 | 2UPN Grupo II | — | — | — | 🔜 |
| 4 | 2UPN Grupo V | — | — | — | 🔜 |
| 5 | Ángulo simple L | — | — | — | 🔜 |
| 6 | 2L Grupo II | — | — | — | 🔜 |
| 7 | 2L en Cruz X | — | — | — | 🔜 |
| 8 | Tensores | — | — | — | 🔜 |

## Verificaciones implementadas (Doble T)

| Cláusula | Descripción |
|----------|-------------|
| B.4-1 | Clasificación: compacta / no compacta / esbelta |
| E.3 | Compresión — pandeo flexional |
| E.4 | Compresión — pandeo torsional |
| F.2 | Flexión eje fuerte — plastificación + PLT (3 zonas) |
| F.6 | Flexión eje débil |
| G.2 | Corte eje fuerte (alma) |
| G.6 | Corte eje débil (alas) |
| D.2 / D.3 | Tracción — fluencia, rotura, factor U |
| J.4.3 | Bloque de corte (uniones bulonadas) |
| H.1-1a/b + G.7 | Combinaciones por caso de carga |

## Uso del notebook

### Opción A — VS Code
```bash
git clone https://github.com/anibalmieres/cirsoc301
cd cirsoc301
pip install jupyter ipython
code .
# Abrir notebooks/01_doble_t.ipynb
```

### Opción B — Google Colab (sin instalación)
```python
# Primera celda en Colab:
!git clone https://github.com/anibalmieres/cirsoc301
import sys; sys.path.insert(0, '/content/cirsoc301')
```

## Editar la base de datos de perfiles

Los archivos `data/perfiles_*.csv` son texto plano editables con Excel.

**Para agregar un perfil nuevo:**
1. Abrir el CSV correspondiente
2. Agregar una fila con los datos, respetando el orden de columnas
3. Completar la columna `fuente` con la norma de referencia
4. Guardar — los cambios se aplican en el próximo `Run All` del notebook

**Para corregir un valor:** editar directamente la celda en el CSV.

## Validación

El módulo `doble_t.py` fue validado contra la planilla de referencia:
`MC_em - TIPICO - verificaciones_CIRSOC_301_2018 - 18-10-2024.xlsx`

- 6/6 resistencias de diseño coinciden con diferencia < 0.05%
- 4/4 casos de carga sin discrepancias
- Bug documentado: X2 en §F.2-4d usa Ix (eje fuerte), no Iy

## Stack tecnológico

- Python 3.x — cálculos y notebooks
- HTML/CSS/JS — web app estática (sin servidor)
- CSV — base de datos editable
- GitHub — control de versiones
- Vercel — deploy automático (gratuito)

---

© 2026 Aníbal Mieres — anibalmieres@gmail.com
