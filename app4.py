import io
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Análisis de Cerchas 2D",
    page_icon="📐",
    layout="wide",
)

# --- Fondo SVG de cercha + estilos visuales ---
st.markdown(
    """
    <style>
        /* Fondo sutil con patrón geométrico de cercha (SVG codificado) */
        .stApp {
            background-color: #f4f6f9;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='80' viewBox='0 0 160 80'%3E%3Cg fill='none' stroke='%2394a3b8' stroke-opacity='0.18' stroke-width='1.2'%3E%3Cline x1='0' y1='70' x2='160' y2='70'/%3E%3Cline x1='0' y1='70' x2='40' y2='20'/%3E%3Cline x1='40' y1='20' x2='80' y2='70'/%3E%3Cline x1='80' y1='70' x2='120' y2='20'/%3E%3Cline x1='120' y1='20' x2='160' y2='70'/%3E%3Cline x1='40' y1='20' x2='120' y2='20'/%3E%3Cline x1='40' y1='20' x2='40' y2='70'/%3E%3Cline x1='80' y1='70' x2='80' y2='20'/%3E%3Cline x1='120' y1='20' x2='120' y2='70'/%3E%3C/g%3E%3C/svg%3E");
            background-repeat: repeat;
        }

        /* Banner superior */
        .hero-box {
            background: linear-gradient(120deg, #0f172a 0%, #1e3a5f 100%);
            color: #ffffff;
            padding: 1.5rem 1.8rem;
            border-radius: 14px;
            margin-bottom: 1.2rem;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
            border-left: 6px solid #38bdf8;
        }
        .hero-box h1 {
            margin: 0 0 0.35rem 0;
            font-size: 1.85rem;
            color: #ffffff;
        }
        .hero-box p {
            margin: 0;
            color: #cbd5e1;
            font-size: 0.98rem;
        }

        /* Tarjetas para secciones */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 0.4rem 0.6rem;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
        }

        /* Botón principal */
        .stDownloadButton > button {
            background-color: #0f172a;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 0.55rem 1.1rem;
            font-weight: 600;
        }
        .stDownloadButton > button:hover {
            background-color: #1e3a5f;
            color: #ffffff;
        }
    </style>

    <div class="hero-box">
        <h1>📐 Análisis de Cerchas 2D — Método de los Nudos</h1>
        <p>Calcula reacciones en apoyos, fuerzas internas y visualiza el diagrama de la cercha a partir de tu archivo Excel.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def resolver_cercha(archivo_o_buffer):
    try:
        df_nudos = pd.read_excel(archivo_o_buffer, sheet_name="Nudos")
        df_elementos = pd.read_excel(archivo_o_buffer, sheet_name="Elementos")
        df_apoyos = pd.read_excel(archivo_o_buffer, sheet_name="Apoyos")
        df_cargas = pd.read_excel(archivo_o_buffer, sheet_name="Cargas")
    except Exception as e:
        return None, f"No se pudieron leer las hojas requeridas (`Nudos`, `Elementos`, `Apoyos`, `Cargas`). Detalles: {e}"

    nudos = {}
    for _, row in df_nudos.iterrows():
        nudo_id = int(row["nudo"])
        nudos[nudo_id] = (float(row["x"]), float(row["y"]))
    num_nudos = len(nudos)

    elementos = []
    for _, row in df_elementos.iterrows():
        n1 = int(row["nudo_inicial"])
        n2 = int(row["nudo_final"])
        elementos.append((n1, n2))
    num_elementos = len(elementos)

    reacciones = []
    for _, row in df_apoyos.iterrows():
        nudo_apoyo = int(row["nudo"])
        tipo = int(row["tipo"])
        if tipo == 1:
            reacciones.append((nudo_apoyo, "x"))
            reacciones.append((nudo_apoyo, "y"))
        elif tipo == 2:
            reacciones.append((nudo_apoyo, "y"))
        elif tipo == 3:
            reacciones.append((nudo_apoyo, "x"))

    cargas_x = {i: 0.0 for i in range(1, num_nudos + 1)}
    cargas_y = {i: 0.0 for i in range(1, num_nudos + 1)}

    for _, row in df_cargas.iterrows():
        nudo_carga = int(row["nudo"])
        cargas_x[nudo_carga] += float(row["fx"])
        cargas_y[nudo_carga] += float(row["fy"])

    num_incognitas = num_elementos + len(reacciones)
    num_ecuaciones = 2 * num_nudos
    advertencia = None

    if num_incognitas != num_ecuaciones:
        advertencia = (
            f"El sistema tiene {num_ecuaciones} ecuaciones y {num_incognitas} incógnitas. "
            "La cercha podría ser inestable o hiperestática."
        )

    A = np.zeros((num_ecuaciones, num_incognitas))
    B = np.zeros(num_ecuaciones)

    for nudo in range(1, num_nudos + 1):
        B[2 * (nudo - 1)] = -cargas_x[nudo]
        B[2 * (nudo - 1) + 1] = -cargas_y[nudo]

    longitudes = []
    for idx_elem, (n1, n2) in enumerate(elementos):
        x1, y1 = nudos[n1]
        x2, y2 = nudos[n2]
        L = np.hypot(x2 - x1, y2 - y1)
        if L == 0:
            return None, f"El elemento {idx_elem + 1} (Nudos {n1}-{n2}) tiene longitud cero."
        longitudes.append(L)

        cos_theta = (x2 - x1) / L
        sin_theta = (y2 - y1) / L

        A[2 * (n1 - 1), idx_elem] = cos_theta
        A[2 * (n1 - 1) + 1, idx_elem] = sin_theta

        A[2 * (n2 - 1), idx_elem] = -cos_theta
        A[2 * (n2 - 1) + 1, idx_elem] = -sin_theta

    for idx_reac, (nudo_apoyo, direccion) in enumerate(reacciones):
        col = num_elementos + idx_reac
        if direccion == "x":
            A[2 * (nudo_apoyo - 1), col] = 1.0
        elif direccion == "y":
            A[2 * (nudo_apoyo - 1) + 1, col] = 1.0

    try:
        solucion = np.linalg.solve(A, B)
    except np.linalg.LinAlgError:
        return None, "La matriz es singular. Revisa la geometría, la numeración de nudos o las condiciones de apoyo."

    filas_reacciones = []
    for idx_reac, (nudo_apoyo, direccion) in enumerate(reacciones):
        val = float(solucion[num_elementos + idx_reac])
        filas_reacciones.append({
            "Nudo": nudo_apoyo,
            "Dirección": f"R{direccion.upper()}",
            "Valor": round(val, 4),
        })

    filas_elementos = []
    fuerzas_elem = []
    for idx_elem, (n1, n2) in enumerate(elementos):
        fuerza = float(solucion[idx_elem])
        if abs(fuerza) < 1e-6:
            estado = "ELEMENTO CERO (0)"
            fuerza = 0.0
        elif fuerza > 0:
            estado = "TENSIÓN (T)"
        else:
            estado = "COMPRESIÓN (C)"

        fuerzas_elem.append(fuerza)
        filas_elementos.append({
            "Elemento": idx_elem + 1,
            "Nudo Inicial": n1,
            "Nudo Final": n2,
            "Longitud": round(longitudes[idx_elem], 4),
            "Magnitud": round(abs(fuerza), 4),
            "Fuerza con signo": round(fuerza, 4),
            "Estado": estado,
        })

    return {
        "nudos": nudos,
        "elementos": elementos,
        "fuerzas": fuerzas_elem,
        "reacciones": pd.DataFrame(filas_reacciones),
        "elementos_df": pd.DataFrame(filas_elementos),
        "advertencia": advertencia,
    }, None


def dibujar_cercha(nudos, elementos, fuerzas, mostrar_etiquetas=True):
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8fafc")

    for idx, (n1, n2) in enumerate(elementos):
        x1, y1 = nudos[n1]
        x2, y2 = nudos[n2]
        f = fuerzas[idx]

        if abs(f) < 1e-6:
            color = "#64748b"
            estilo = "--"
        elif f > 0:
            color = "#0284c7"
            estilo = "-"
        else:
            color = "#dc2626"
            estilo = "-"

        ax.plot([x1, x2], [y1, y2], color=color, linestyle=estilo, linewidth=2.6, zorder=2)

        if mostrar_etiquetas:
            xm, ym = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(
                xm,
                ym,
                f"E{idx+1}: {abs(f):.1f}",
                fontsize=8,
                ha="center",
                va="bottom",
                bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="#e2e8f0", alpha=0.9),
                zorder=4,
            )

    for nudo_id, (x, y) in nudos.items():
        ax.scatter(x, y, color="#0f172a", s=65, zorder=3)
        ax.text(x, y, f"  {nudo_id}", fontsize=9, fontweight="bold", color="#0f172a", ha="left", va="top", zorder=5)

    ax.plot([], [], color="#0284c7", lw=2.6, label="Tensión (T)")
    ax.plot([], [], color="#dc2626", lw=2.6, label="Compresión (C)")
    ax.plot([], [], color="#64748b", ls="--", lw=2.6, label="Elemento Cero (0)")
    ax.legend(loc="best", frameon=True, facecolor="white", edgecolor="#cbd5e1")

    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel("Coordenada X")
    ax.set_ylabel("Coordenada Y")
    ax.set_title("Diagrama de Fuerzas Internas de la Cercha")
    ax.grid(True, linestyle=":", color="#cbd5e1", alpha=0.8)
    plt.tight_layout()
    return fig


# --- Barra lateral ---
with st.sidebar:
    st.header("Guía de entrada")
    st.markdown("Tu archivo `.xlsx` debe incluir estas 4 hojas:")
    st.markdown(
        """
        * **Nudos:** `nudo`, `x`, `y`
        * **Elementos:** `nudo_inicial`, `nudo_final`
        * **Apoyos:** `nudo`, `tipo` (`1` fijo X/Y, `2` rodillo Y, `3` rodillo X)
        * **Cargas:** `nudo`, `fx`, `fy`
        """
    )
    st.divider()
    mostrar_etiquetas = st.checkbox("Mostrar etiquetas de fuerza en el gráfico", value=True)
    st.caption("Convención de signos: **+** Tensión, **−** Compresión.")

# --- Carga de archivo ---
with st.container(border=True):
    st.subheader("1. Cargar archivo de datos")
    archivo_subido = st.file_uploader(
        "Selecciona tu archivo Excel (.xlsx)",
        type=["xlsx"],
        help="Debe contener las hojas Nudos, Elementos, Apoyos y Cargas.",
    )

if archivo_subido is not None:
    resultado, error = resolver_cercha(archivo_subido)

    if error:
        st.error(error)
    else:
        if resultado["advertencia"]:
            st.warning(resultado["advertencia"])

        df_elem = resultado["elementos_df"]
        df_reac = resultado["reacciones"]

        total_elem = len(df_elem)
        n_tension = int((df_elem["Estado"] == "TENSIÓN (T)").sum())
        n_compresion = int((df_elem["Estado"] == "COMPRESIÓN (C)").sum())
        n_cero = int((df_elem["Estado"] == "ELEMENTO CERO (0)").sum())

        # --- Tarjetas de métricas ---
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            with st.container(border=True):
                st.metric("Elementos analizados", total_elem)
        with m2:
            with st.container(border=True):
                st.metric("En tensión (T)", n_tension)
        with m3:
            with st.container(border=True):
                st.metric("En compresión (C)", n_compresion)
        with m4:
            with st.container(border=True):
                st.metric("Elementos cero", n_cero)

        st.write("")

        # --- Gráfica + Tablas ---
        col_izq, col_der = st.columns([1.15, 1])

        with col_izq:
            with st.container(border=True):
                st.subheader("2. Gráfico de la Cercha")
                fig = dibujar_cercha(
                    resultado["nudos"],
                    resultado["elementos"],
                    resultado["fuerzas"],
                    mostrar_etiquetas=mostrar_etiquetas,
                )
                st.pyplot(fig, use_container_width=True)

        with col_der:
            with st.container(border=True):
                st.subheader("3. Reacciones en los Apoyos")
                st.dataframe(df_reac, use_container_width=True, hide_index=True)

            st.write("")

            with st.container(border=True):
                st.subheader("4. Fuerzas Internas")
                st.dataframe(df_elem, use_container_width=True, hide_index=True)

                csv_buffer = io.StringIO()
                df_elem.to_csv(csv_buffer, index=False)
                st.download_button(
                    label="⬇ Descargar resultados (CSV)",
                    data=csv_buffer.getvalue(),
                    file_name="resultados_cercha.csv",
                    mime="text/csv",
                )
else:
    with st.container(border=True):
        st.info("Sube un archivo `.xlsx` en el panel superior para comenzar el análisis y ver el gráfico.")