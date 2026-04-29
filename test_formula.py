import numpy as np

def deterministic_cost(w, p, shock):
    rs = shock["rate_shock_bps"] / 10_000
    fx = shock["fx_shock_pct"]

    fx_mult = 1.0 / (1 + fx) if fx < 0 else 1.0

    rates = {
        "DI_COP_F": p["cop_fixed_rate"]/100 + rs,
        "DI_UVR_F": (p["uvr_real_rate"] + p["uvr_inflation"])/100 + rs,
        "DE_USD_F": (p["usd_fixed_rate"]/100 + rs) * fx_mult,
        "DE_EUR_F": (p["eur_fixed_rate"]/100 + rs) * fx_mult,
        "DE_EUR_V": ((p["euribor_base"] + p["eur_spread_eurib"])/100 + rs) * fx_mult,
        "DE_USD_V": ((p["sofr_base"] + p["usd_spread_sofr"])/100 + rs) * fx_mult,
        "DE_CHF_F": (p["chf_fixed_rate"]/100 + rs) * fx_mult,
        "DE_CHF_V": ((p["saron_base"] + p["chf_spread_saron"])/100 + rs) * fx_mult,
    }

    N_INST = 8
    INSTRUMENTS = [
        ("DI_COP_F",), ("DI_UVR_F",), ("DE_USD_F",), ("DE_EUR_F",),
        ("DE_EUR_V",), ("DE_USD_V",), ("DE_CHF_F",), ("DE_CHF_V",)
    ]

    weighted_rate = sum(w[i] * rates[INSTRUMENTS[i][0]] for i in range(N_INST))

    # NEW FORMULA
    # We want base total interest to be 833,073,359.49
    # If the w parameter is the base weights, the weighted_rate is base_rate.
    # To scale the cost properly across any weights:
    # cost = total_absolute_debt * weighted_rate * calibration_factor
    # Where calibration_factor = 833,073,359.49 / (total_absolute_debt * base_rate)

    # Or, we just calculate absolute total interest directly from weights and saldos!
    # "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de "Intereses/PIB (base)" reflejen con precisión este 41.68% objetivo."
    pass
