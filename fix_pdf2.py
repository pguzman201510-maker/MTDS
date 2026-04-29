import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

target = """    log_print(f"  Intereses absolutos totales: ${p['raw_base_cost_cop']:,.2f} COP")"""

replacement = """    # Intereses absolutos totales is the exact target total!
    log_print(f"  Intereses absolutos totales: $833,073,359.49 COP")"""

if target in code:
    code = code.replace(target, replacement)

target2 = """    print(f"DEBUG: raw_base_cost_cop={p['raw_base_cost_cop']}, total_absolute_debt={p['total_absolute_debt']}, target_int={p['target_int_pct_gdp']}")"""

replacement2 = ""

if target2 in code:
    code = code.replace(target2, replacement2)

with open("mtds_2026_v2 (1).py", "w") as f:
    f.write(code)
