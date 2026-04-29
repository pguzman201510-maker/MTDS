import mtds_script as ms

# Let's inspect `weighted_rate` for the BASE portfolio.
import numpy as np

p = {
    "gdp_cop_bn": 1998508.0,
    "usdcop_spot": 4200.0,
    "cop_fixed_rate": 9.5,
    "uvr_real_rate": 4.5,
    "uvr_inflation": 4.5, # wait, what is uvr_inflation in template?
    "usd_fixed_rate": 6.0,
    "eur_fixed_rate": 4.0,
    "euribor_base": 3.0,
    "eur_spread_eurib": 0.9,
    "sofr_base": 4.5,
    "usd_spread_sofr": 1.2,
    "chf_fixed_rate": 2.0,
    "saron_base": 1.2,
    "chf_spread_saron": 0.6
}

w_base = np.array([0.40, 0.20, 0.24, 0.06, 0.05, 0.05, 0.0, 0.0])

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
print("weighted rate:", weighted_rate_base)
print("Base absolute model cost:", weighted_rate_base * 2471753084491324.0)

# What are the actual rates in Oracle?
import pandas as pd
df_oracle = pd.read_csv('Consulta Oracle 31-03-2026.xls', sep='\t', encoding='utf-8')
