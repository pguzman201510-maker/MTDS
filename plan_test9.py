# Let's double check if we can compute `raw_int_cost` and `raw_ext_cost_usd` inside `load_from_perfil` and `load_from_oracle`.
# In `load_from_oracle`:
# `raw_ext_cost_usd` = (df['SDO_US'] * df['MARGEN_VALOR'] / 100).sum()
# Wait! In Oracle, some MARGEN_VALOR are spreads.
# We should probably just do exactly what we did before:
# raw_ext_cost_usd = (df['SDO_US'] * df['MARGEN_VALOR'] / 100).sum()
# Actually, the user says: "la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes".

# And the scalar is:
# "escalándolo de manera que los resultados de 'Intereses/PIB (base)' reflejen con precisión este 41.68% objetivo."

# If we define a global or pass it via `p`:
# `p["cost_scale_factor"] = 41.68 / (raw_int_cost + raw_ext_cost_usd * p["usdcop_spot"])`
# But wait, is it `41.68` or `41.6847`?
# "este 41.68% objetivo". Let's use 41.68476... which is exactly 833,073,359.49 / 1998508.0 / 10.
# Because they say "Interés total: 833,073,359.49. Estos valores reales representan exactamente un 41.68% de interés sobre el GDP".
# Let's compute `target_pct = (833073359.49 / p["gdp_cop_bn"]) / 10`.

# Then in `deterministic_cost`:
# absolute_cost = weighted_rate * p["total_absolute_debt"]
# int_pct_gdp = absolute_cost * p["cost_scale_factor"]
# Wait! If we use `weighted_rate * p["total_absolute_debt"]`, we don't even use `raw_int_cost` and `raw_ext_cost_usd` to *generate* the cost, only to compute the *scale_factor*.
# "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total"
# Does it mean `Costo Total = raw_int_cost + raw_ext_cost_usd * spot`?
# Yes! And then "escalándolo de manera que los resultados de 'Intereses/PIB (base)' reflejen con precisión este 41.68% objetivo."
# If `w` is applied:
# The `Costo Total` of the *base* portfolio is `raw_int_cost + raw_ext_cost_usd * spot`.
# How does this apply to arbitrary `w`?
# Well, the absolute base cost is generated from the raw data.
# `base_Costo_Total = raw_int_cost + raw_ext_cost_usd * p["usdcop_spot"]`
# For a new portfolio `w`, `Costo_Total(w) = base_Costo_Total * (weighted_rate(w) / base_weighted_rate)` ?
# Or `Costo_Total(w) = weighted_rate(w) * p["total_absolute_debt"]` ?
# The mathematically sound way is `weighted_rate(w) * p["total_absolute_debt"]` because `weighted_rate(w)` is the weighted average rate of the new portfolio.
# And `base_Costo_Total` is exactly `base_weighted_rate * p["total_absolute_debt"]` (modulo inaccuracies in the weighted rate vs raw data).
# By using `scale_factor = 41.6847... / base_weighted_rate`, we don't even need `total_absolute_debt`!
# `int_pct_gdp = weighted_rate * scale_factor` !
# If `int_pct_gdp = weighted_rate * scale_factor`, then `scale_factor = 41.6847... / base_weighted_rate`.

# But the prompt specifically asks to: "Elimines los factores 'hardcodeados' y el uso de proporciones genéricas (como el 55.0% de debt_pct_gdp) en la fórmula final. Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total"
# It specifically asks to USE the sum of absolute saldos and coupons.
# So `Costo_Total_Absoluto(w) = weighted_rate(w) * p["total_absolute_debt"]`!
# And then `int_pct_gdp = Costo_Total_Absoluto(w) * scaling_factor` !
# Or `int_pct_gdp = Costo_Total_Absoluto(w) / p["gdp_cop_bn"] * some_adjustment` ?
# The adjustment is `target_pct_gdp / (base_absolute_cost / p["gdp_cop_bn"])` !
# Where `base_absolute_cost = raw_int_cost + raw_ext_cost_usd * p["usdcop_spot"]`.
