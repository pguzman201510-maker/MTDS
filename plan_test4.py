# The user wants exactly THIS:
# "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de "Intereses/PIB (base)" reflejen con precisión este 41.68% objetivo."

# Let's say we literally calculate:
# `internal_cost` = sum(Emis_SALDO * Emis_TASA / 100)
# `external_cost_usd` = sum(Oracle_SDOUS * Oracle_MARGEN / 100)
# `total_cost_cop` = internal_cost + external_cost_usd * fx_spot
# Then `int_pct_gdp` = (total_cost_cop / scale_factor) / PIB * 100 ? No.

# If the target Intereses/PIB is exactly 41.68%, and this corresponds to a target interest of 833,073,359.49.
# Then the formula for `int_pct_gdp` is `Costo_Total_COP * scaling_factor`.
# `scaling_factor` = 41.684764809 / total_cost_cop ?

# Wait, the total cost depends on the weights!
# Costo Total changes with weights.
# The absolute cost of the ACTUAL portfolio is what we get from the files directly.
# And the user wants us to calculate `Costo Total` using the formula:
# Costo_Total_COP = Deuda_Interna_Absoluta * Tasa_Ponderada_Interna + Deuda_Externa_Absoluta * Tasa_Ponderada_Externa

# "Elimines los factores 'hardcodeados' y el uso de proporciones genéricas (como el 55.0% de debt_pct_gdp) en la fórmula final."
# Currently: `int_pct_gdp   = weighted_rate * p["debt_pct_gdp"]`
# And `ip[:, t] = cost_t * p["debt_pct_gdp"]`

# What if we replace `p["debt_pct_gdp"]` with `p["total_absolute_debt"] / p["gdp_cop_bn"]` scaled appropriately?
# "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total"
