import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

target = """            cost_t = cop_cost + uvr_cost + usd_f + eur_f + eur_v + usd_v + chf_f + chf_v
            ip[:, t] = cost_t * p["debt_pct_gdp"]"""

replacement = """            cost_t = cop_cost + uvr_cost + usd_f + eur_f + eur_v + usd_v + chf_f + chf_v

            if "raw_base_cost_cop" in p and p["raw_base_cost_cop"] > 0:
                absolute_cost_t = cost_t * p["total_absolute_debt"]
                ip[:, t] = absolute_cost_t * (p["target_int_pct_gdp"] / p["raw_base_cost_cop"])
            else:
                ip[:, t] = cost_t * p.get("debt_pct_gdp", 55.0)"""

if target in code:
    code = code.replace(target, replacement)
    with open("mtds_2026_v2 (1).py", "w") as f:
        f.write(code)
    print("Patched CostRiskCalc._interest_pct_gdp")
else:
    print("Could not find CostRiskCalc target")
