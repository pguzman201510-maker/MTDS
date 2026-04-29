# Let's write the exact steps for `deterministic_cost` and `CostRiskCalc`.

# In `main()`:
# Read Emisiones Vigentes to compute `raw_int_cost` and `total_emis_saldo`.
# Read Oracle to compute `raw_ext_cost_usd` and `total_oracle_saldo_usd`.
# `p["raw_int_cost"] = raw_int_cost`
# `p["raw_ext_cost_usd"] = raw_ext_cost_usd`
# `p["total_absolute_debt"] = total_emis_saldo + total_oracle_saldo_usd * p["usdcop_spot"]`

# But wait, in `deterministic_cost`, it uses `weighted_rate` and `w` array.
# The absolute cost of the NEW portfolio `w` under some shock is:
# cost_t = sum(w[i] * rates_i * Total_Debt)
# We want this to be scaled so that for the BASE portfolio without shock, the `int_pct_gdp` is exactly 41.6847 (or 41.68).
# Actually, the user says: "833073359.49. Estos valores reales representan exactamente un 41.68% de interés sobre el GDP"
# So `target_pct_gdp = 41.684764809` (or `833073359.49 / p["gdp_cop_bn"] / 10`).

# If we just calculate `base_weighted_rate` for the base portfolio and use it to find the scalar:
# In `main()`:
# N_INST = 8
# INSTRUMENTS = ...
# base_w = np.array([0.40, 0.20, 0.24, 0.06, 0.05, 0.05, 0.0, 0.0]) # Or whatever the actual base portfolio is! (which is calculated in `main` as `ref_w`)
# Calculate `base_weighted_rate` using `p` and `base_w` without shock.
# Calculate `raw_base_cost_cop = p["total_absolute_debt"] * base_weighted_rate`.
# Find `scale_factor = target_int_pct / raw_base_cost_cop`?
# NO, the instruction says: "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de "Intereses/PIB (base)" reflejen con precisión este 41.68% objetivo."
# This explicitly implies we should compute `raw_base_cost_cop` from Emisiones Vigentes and Oracle!
# `raw_base_cost_cop = raw_int_cost + raw_ext_cost_usd * fx_spot`!
# And then `scale_factor = 41.68 / raw_base_cost_cop`.
# Wait, if we use `scale_factor = 41.68 / raw_base_cost_cop`, then how do we apply it to different `w`?
# `int_pct_gdp = sum(w[i] * rates[i] * p["total_absolute_debt"]) * scale_factor`?
# Let's check: If `w` is the base portfolio, `sum(w[i] * rates[i] * Total_Debt)` should be approximately `raw_base_cost_cop`.
# Then `int_pct_gdp` will be `raw_base_cost_cop * (41.68 / raw_base_cost_cop) = 41.68`. It perfectly works!
