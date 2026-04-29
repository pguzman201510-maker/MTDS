import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

# Wait, why was `int_pct_gdp` = 210526.709?
# Oh! `weighted_rate` is a sum of rates. Rates are numbers like 0.09.
# Let's verify what `p["raw_base_cost_cop"]` and `p["target_int_pct_gdp"]` are inside the script when it runs.

code = code.replace("""    print(f"\n[2/6]  Calculando escenarios de estrés BM-FMI …")
    stres_ref = stress_analysis(ref_w, p)""",
"""    print(f"\n[2/6]  Calculando escenarios de estrés BM-FMI …")
    print(f"DEBUG: raw_base_cost_cop={p['raw_base_cost_cop']}, total_absolute_debt={p['total_absolute_debt']}, target_int={p['target_int_pct_gdp']}")
    stres_ref = stress_analysis(ref_w, p)""")

with open("mtds_2026_v2 (1).py", "w") as f:
    f.write(code)
