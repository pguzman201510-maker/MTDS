# If we extract absolute internal and absolute external from Emisiones Vigentes and Oracle in `main()`, we can store them in `p`:
# `p["abs_int_cost"] = raw_int_cost`
# `p["abs_ext_cost_usd"] = raw_ext_cost_usd`

# Then in `deterministic_cost` we want to compute `int_pct_gdp`!
# `base_total_cost = p["abs_int_cost"] + p["abs_ext_cost_usd"] * p["usdcop_spot"]`
# But wait, `deterministic_cost` receives `w` (the weights of the portfolio).
# We can calculate the absolute cost for the NEW portfolio `w`.
# `total_debt = p["total_absolute_debt"]`
# `new_total_cost = total_debt * weighted_rate`
# `scale_factor = 41.68 / base_total_cost` -> NO, `scale_factor` should scale the *cost* to match the 41.68% target when `w == w_base`.
# Actually: "Intereses internos: 694,651,132.90. Intereses externos: 138,422,226.58. Interés total: 833,073,359.49. Estos valores reales representan exactamente un 41.68% de interés sobre el GDP"
# `833073359.49 / 1998508.0 = 416.84`.
# Wait, `833073359.49 / 1998508.0 / 10` = 41.684.
# So `41.68` is exactly `833073359.49 / p["gdp_cop_bn"] / 10`.

# If we compute the relative new cost:
# `new_total_cost = (weighted_rate / base_weighted_rate) * 833,073,359.49`
# Then `int_pct_gdp = new_total_cost / p["gdp_cop_bn"] / 10`
# Does this satisfy: "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo..."
# Yes! `base_total_cost = raw_int_cost + raw_ext_cost_usd * usdcop_spot`
# Then we find a `scale_factor` = 833,073,359.49 / base_total_cost.
# `Costo_Total = Total_Debt * weighted_rate * scale_factor`
# Wait! If `Total_Debt * weighted_rate` is the absolute cost computed from the rates.
# The issue explicitly mentions: "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de 'Intereses/PIB (base)' reflejen con precisión este 41.68% objetivo."

# This means:
# `raw_base_cost_cop = sum(saldos * cupones)`
# We have a `target_pct_gdp = 41.68`
# We want `int_pct_gdp = (Total_Cost * Scale) / GDP`?
# "escalándolo de manera que los resultados de 'Intereses/PIB (base)' reflejen con precisión este 41.68% objetivo."
# Let `Scale = 41.68 / raw_base_cost_cop`
# `int_pct_gdp = (w_internal * raw_int_cost_total + w_external * raw_ext_cost_total) * Scale`? No, `w` are the proportions of the *debt*.
