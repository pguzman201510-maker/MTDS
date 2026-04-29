import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

# Why is base 136% now instead of 41.68%?
# `raw_base_cost_cop` is the exact scalar base, but `weighted_rate` is based on `rates` which uses Oracle `tasa_wp` which might NOT reflect the pure absolute raw rate exactly.
# The user instruction:
# "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de "Intereses/PIB (base)" reflejen con precisión este 41.68% objetivo."

# If we force `int_pct_gdp` to be exactly `p["target_int_pct_gdp"]` when `w == ref_w` in base scenario, we can do:
# `p["model_base_cost"] = sum(ref_w[i] * base_rates[i]) * p["total_absolute_debt"]`
# And then scale by that!

target = """    p["target_int_pct_gdp"] = 833073359.49 / 1998508.0 / 10"""

replacement = """    p["target_int_pct_gdp"] = 833073359.49 / 1998508.0 / 10

    # Calculate what the model evaluates the base cost as
    # So we can scale ANY scenario precisely relative to the model's own evaluation of the base
    if oracle["ok"]:
        w_base = ref_w
        rates_base = {
            "DI_COP_F": p["cop_fixed_rate"]/100,
            "DI_UVR_F": (p["uvr_real_rate"] + p["uvr_inflation"])/100,
            "DE_USD_F": p["usd_fixed_rate"]/100,
            "DE_EUR_F": p["eur_fixed_rate"]/100,
            "DE_EUR_V": (p.get("euribor_base",3.0) + p["eur_spread_eurib"])/100,
            "DE_USD_V": (p.get("sofr_base",4.5) + p["usd_spread_sofr"])/100,
            "DE_CHF_F": p["chf_fixed_rate"]/100,
            "DE_CHF_V": (p.get("saron_base",1.2) + p["chf_spread_saron"])/100,
        }
        N_INST_TMP = 8
        INSTRUMENTS_TMP = [("DI_COP_F",), ("DI_UVR_F",), ("DE_USD_F",), ("DE_EUR_F",), ("DE_EUR_V",), ("DE_USD_V",), ("DE_CHF_F",), ("DE_CHF_V",)]
        weighted_rate_base = sum(w_base[i] * rates_base[INSTRUMENTS_TMP[i][0]] for i in range(N_INST_TMP))
        p["model_base_cost"] = weighted_rate_base * p["total_absolute_debt"]
    else:
        p["model_base_cost"] = p["raw_base_cost_cop"]"""

if target in code:
    code = code.replace(target, replacement)

target2 = """            if "raw_base_cost_cop" in p and p["raw_base_cost_cop"] > 0:
                absolute_cost_t = cost_t * p["total_absolute_debt"]
                ip[:, t] = absolute_cost_t * (p["target_int_pct_gdp"] / p["raw_base_cost_cop"])"""

replacement2 = """            if "model_base_cost" in p and p["model_base_cost"] > 0:
                absolute_cost_t = cost_t * p["total_absolute_debt"]
                ip[:, t] = absolute_cost_t * (p["target_int_pct_gdp"] / p["model_base_cost"])"""

code = code.replace(target2, replacement2)

target3 = """    absolute_cost = weighted_rate * p["total_absolute_debt"]
    if p["raw_base_cost_cop"] > 0:
        int_pct_gdp = absolute_cost * (p["target_int_pct_gdp"] / p["raw_base_cost_cop"])"""

replacement3 = """    absolute_cost = weighted_rate * p["total_absolute_debt"]
    if p.get("model_base_cost", 0) > 0:
        int_pct_gdp = absolute_cost * (p["target_int_pct_gdp"] / p["model_base_cost"])"""

code = code.replace(target3, replacement3)

with open("mtds_2026_v2 (1).py", "w") as f:
    f.write(code)
