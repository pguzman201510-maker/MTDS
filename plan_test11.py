# What about CostRiskCalc?
# In CostRiskCalc._interest_pct_gdp:
# `cost_t = cop_cost + uvr_cost + usd_f + eur_f + eur_v + usd_v + chf_f + chf_v`
# This `cost_t` is the `weighted_rate` for that scenario at time t.
# Currently it does: `ip[:, t] = cost_t * p["debt_pct_gdp"]`

# We should change it to:
# `absolute_cost_t = cost_t * p["total_absolute_debt"]`
# `ip[:, t] = absolute_cost_t * (p["target_int_pct_gdp"] / p["raw_base_cost_cop"])`

# This is extremely clean and matches all the user's requirements exactly!
# "Elimines los factores 'hardcodeados' y el uso de proporciones genéricas (como el 55.0% de debt_pct_gdp)" - Done, we replaced `debt_pct_gdp` with absolute values logic.
# "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total" - Done, we extracted `raw_int_cost` and `raw_ext_cost_usd` and `total_emis_saldo` etc.
# "escalándolo de manera que los resultados de 'Intereses/PIB (base)' reflejen con precisión este 41.68% objetivo." - Done, scaling it.
# "Asegures que las métricas finales que se imprimen en consola y se guardan en los reportes correspondan fielmente a la carga real del portafolio, respetando el PIB base de 1998508.0." - Done, by correctly multiplying.

# Target percentage is exactly 41.68476480904755, which is 833073359.49 / 1998508.0 / 10.
