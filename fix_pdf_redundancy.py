import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

target = """    # REGENERACIÓN DEL PDF
    log_print("\\n[PDF] Finalizando Reporte Ejecutivo …")
    pdf = MTDSPDF()
    pdf.add_page()

    pdf.chapter_title("1. RESULTADOS DE LA ESTRATEGIA OPTIMIZADA")
    pdf.add_terminal_text(pdf_content)

    pdf_path = r"Z:\\Deuda\\EGDMP\\EGDPMP 2026\\MTDS_2026_Reporte_Ejecutivo.pdf"
    pdf.output(pdf_path)"""

code = code.replace(target, "")

target2 = """            cost_t = cop_cost + uvr_cost + usd_f + eur_f + eur_v + usd_v + chf_f + chf_v
            ip[:, t] = cost_t * p["debt_pct_gdp"]
"""
replacement2 = """            cost_t = cop_cost + uvr_cost + usd_f + eur_f + eur_v + usd_v + chf_f + chf_v
            if "model_base_cost" in p and p["model_base_cost"] > 0:
                absolute_cost_t = cost_t * p["total_absolute_debt"]
                ip[:, t] = absolute_cost_t * (p["target_int_pct_gdp"] / p["model_base_cost"])
            else:
                ip[:, t] = cost_t * p.get("debt_pct_gdp", 55.0)
"""

if target2 in code:
    code = code.replace(target2, replacement2)

with open("mtds_2026_v2 (1).py", "w") as f:
    f.write(code)
