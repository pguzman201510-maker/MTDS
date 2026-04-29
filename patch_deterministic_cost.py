import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

target = """    weighted_rate = sum(w[i] * rates[INSTRUMENTS[i][0]] for i in range(N_INST))
    int_pct_gdp   = weighted_rate * p["debt_pct_gdp"]
    int_pct_rev   = int_pct_gdp / p["revenues_pct_gdp"] * 100"""

replacement = """    weighted_rate = sum(w[i] * rates[INSTRUMENTS[i][0]] for i in range(N_INST))

    # Nuevo cálculo basado en valores absolutos y escalado a la meta exacta
    absolute_cost = weighted_rate * p["total_absolute_debt"]
    if p["raw_base_cost_cop"] > 0:
        int_pct_gdp = absolute_cost * (p["target_int_pct_gdp"] / p["raw_base_cost_cop"])
    else:
        int_pct_gdp = weighted_rate * p.get("debt_pct_gdp", 55.0)  # fallback

    int_pct_rev   = int_pct_gdp / p["revenues_pct_gdp"] * 100"""

if target in code:
    code = code.replace(target, replacement)
    with open("mtds_2026_v2 (1).py", "w") as f:
        f.write(code)
    print("Patched deterministic_cost")
else:
    print("Could not find deterministic_cost target")
