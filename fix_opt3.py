import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

target = """    print("\\n[2/6]  Calculando escenarios de estrés BM-FMI …")
    stres_ref = stress_analysis(ref_w, p)"""
replacement = """    print("\\n[2/6]  Calculando escenarios de estrés BM-FMI …")
    print(f"DEBUG: raw_base_cost_cop={p['raw_base_cost_cop']}, total_absolute_debt={p['total_absolute_debt']}, target_int={p['target_int_pct_gdp']}")
    stres_ref = stress_analysis(ref_w, p)"""

if target in code:
    code = code.replace(target, replacement)
else:
    print("Not found")

with open("mtds_2026_v2 (1).py", "w") as f:
    f.write(code)
