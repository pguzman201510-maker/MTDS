# The user wants:
# "Elimines los factores 'hardcodeados' y el uso de proporciones genéricas (como el 55.0% de debt_pct_gdp) en la fórmula final. Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de "Intereses/PIB (base)" reflejen con precisión este 41.68% objetivo. Asegures que las métricas finales que se imprimen en consola y se guardan en los reportes correspondan fielmente a la carga real del portafolio, respetando el PIB base de 1998508.0."

# Right now `int_pct_gdp` is calculated as:
# `int_pct_gdp = weighted_rate * p["debt_pct_gdp"]`
# And in CostRiskCalc:
# `ip[:, t] = cost_t * p["debt_pct_gdp"]`

# We need to change this to:
# total_absolute_cost = absolute_cost_int + absolute_cost_ext
# (we compute this once based on the actual sum from Emisiones Vigentes and Oracle)
# BUT wait! `deterministic_cost` depends on the weights `w`.
# If `w` changes, does the total interest change?
# YES, because we are optimizing the weights `w`!
# BUT the user says: "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de "Intereses/PIB (base)" reflejen con precisión este 41.68% objetivo."

# A 41.68% GDP corresponds to an absolute interest of 833,073,359.49, assuming GDP base = 1998508.0.
# The calculation in `int_pct_gdp` in % is `int_pct_gdp = total_interest / (pib_base * 10) * 100` -> `total_interest / (pib_base / 10)`?
# Let's say: `int_pct_gdp` = `total_interest / 1998508.0 * X`
# If total_interest = 833,073,359.49 and `int_pct_gdp` is expected to be 41.68 (or 416.84? The prompt says `41.68%`). So `41.68`.

# So the formula for the "base" portfolio using actual weights should give `41.68%`?
# Wait! In `deterministic_cost`, `weighted_rate` is the effective rate of the portfolio.
# If we calculate the total interest:
# `total_interest_amount = weighted_rate * total_absolute_debt`
# `int_pct_gdp = total_interest_amount / (p["gdp_cop_bn"] * scale_factor)`
# So we need `total_absolute_debt`.
# Where do we get `total_absolute_debt`?
# "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes"
# Total Debt = sum(Emisiones Vigentes saldos) + sum(Oracle SDO_US * USDCOP) ?
