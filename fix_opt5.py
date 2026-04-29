import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

target = """    p["target_int_pct_gdp"] = 833073359.49 / 1998508.0 / 10

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

replacement = """    p["target_int_pct_gdp"] = 833073359.49 / 1998508.0 / 10"""

code = code.replace(target, replacement)

# Now, find where `ref_w` is fully defined and insert it there.
target_insert = """        prev_m = inst[1]"""

# Actually, `ref_w` is fully defined right after `if oracle["ok"] and oracle["oracle_weights"]:` block ends and the print loop finishes.
target2 = """    for i, inst in enumerate(INSTRUMENTS):
        m_label = inst[1] if inst[1] != prev_m else ""
        print(f"         {m_label:<18} {inst[2]:<5} {inst[3]:<10} {ref_w[i]*100:>6.1f}%")
        prev_m = inst[1]"""

replacement2 = target2 + """

    # Calculate what the model evaluates the base cost as
    # So we can scale ANY scenario precisely relative to the model's own evaluation of the base
    w_base = ref_w
    rates_base = {
        "DI_COP_F": p["cop_fixed_rate"]/100,
        "DI_UVR_F": (p["uvr_real_rate"] + p.get("uvr_inflation", 4.5))/100,
        "DE_USD_F": p["usd_fixed_rate"]/100,
        "DE_EUR_F": p["eur_fixed_rate"]/100,
        "DE_EUR_V": (p.get("euribor_base",3.0) + p["eur_spread_eurib"])/100,
        "DE_USD_V": (p.get("sofr_base",4.5) + p["usd_spread_sofr"])/100,
        "DE_CHF_F": p["chf_fixed_rate"]/100,
        "DE_CHF_V": (p.get("saron_base",1.2) + p["chf_spread_saron"])/100,
    }
    weighted_rate_base = sum(w_base[i] * rates_base[INSTRUMENTS[i][0]] for i in range(N_INST))
    p["model_base_cost"] = weighted_rate_base * p["total_absolute_debt"]"""

code = code.replace(target2, replacement2)

with open("mtds_2026_v2 (1).py", "w") as f:
    f.write(code)
