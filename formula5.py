# If the user complains that it's returning 3.841%, let's see why it's 3.841%.
# Because `weighted_rate` depends on `w`. In optimization, it found a specific `w` that yields 3.841%.
# But if we change the formula to directly scale to 41.68% *for the exact absolute values they provided*, we just redefine the denominator!

# What if `int_pct_gdp` is not `weighted_rate * p["debt_pct_gdp"]`?
# They want: "Asegures que las métricas finales que se imprimen en consola y se guardan en los reportes correspondan fielmente a la carga real del portafolio, respetando el PIB base de 1998508.0."
# "Utilices la suma de los saldos absolutos y los cupones extraídos directamente de Oracle y Emisiones Vigentes para generar el Costo Total, escalándolo de manera que los resultados de 'Intereses/PIB (base)' reflejen con precisión este 41.68% objetivo."

# This means:
# `Costo Total Absoluto = (w_internal * total_saldo_interno * tasa_interna) + (w_external * total_saldo_externo * tasa_externa * fx_spot)`
# But wait, weights are proportional. So if `w` is the percentage of the *total* absolute debt.
# Cost = SUM(w[i] * rates_i) * Total_Absolute_Debt
# Then `int_pct_gdp = Cost / PIB`.
# Wait, if we just set `p["debt_pct_gdp"]` dynamically to match the absolute data?
# Total_Absolute_Debt / PIB = 1236.79 !
# If we multiply 1236.79 * 0.03841 = 47.50, which doesn't match 41.68%.
# And they said "escalándolo de manera que los resultados... reflejen con precisión este 41.68% objetivo".

# Maybe we just overwrite `int_pct_gdp` computation!
# We know the absolute interest of the base portfolio is 833,073,359.49.
# We know the absolute debt of the base portfolio is `Total_Absolute_Debt`
# `base_weighted_rate = 833,073,359.49 / Total_Absolute_Debt`
# For ANY portfolio `w`, the new absolute interest is `(new_weighted_rate / base_weighted_rate) * 833,073,359.49`?
# Or simply:
# Absolute_Cost(w) = sum(w[i] * rates[i]) * Total_Absolute_Debt
# WAIT! The current `w` is percentage of TOTAL DEBT.
# So `w[i] * Total_Absolute_Debt` is the absolute debt in instrument i.
# So `sum(w[i] * rates[i] * Total_Absolute_Debt) = weighted_rate * Total_Absolute_Debt` is exactly the absolute cost!
# But the user says the absolute cost of the *actual* portfolio is 833,073,359.49.
# If we compute it our way, it's 187,863,665,219,357.22. That's way off!
# Because the "saldos" from the Excel files are not correctly scaled relative to 833,073,359.49.

# If the user says: "según los flujos proyectados y los saldos reales, el monto absoluto de los intereses es: Intereses internos: 694,651,132.90, Intereses externos: 138,422,226.58. Interés total: 833,073,359.49. Estos valores reales representan exactamente un 41.68% de interés sobre el GDP (Interés/GDP = 41.68%)... usa una fórmula genérica dependiente del parámetro p['debt_pct_gdp']."

# This means we should change the logic in `deterministic_cost` to scale to 41.68%.
# "escalándolo de manera que los resultados de 'Intereses/PIB (base)' reflejen con precisión este 41.68% objetivo."
