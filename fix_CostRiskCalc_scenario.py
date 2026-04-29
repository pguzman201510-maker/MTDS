import re

with open("mtds_2026_v2 (1).py", "r") as f:
    code = f.read()

target = """                c = (
                    w[0]*rates[scen_i,t,0]/100 +
                    w[1]*(rates[scen_i,t,1]+p["uvr_real_rate"])/100*cum_uvr +
                    w[2]*rates[scen_i,t,2]/100*adj_usd +
                    w[3]*rates[scen_i,t,3]/100*adj_eur +
                    w[4]*(rates[scen_i,t,6]+p["eur_spread_eurib"])/100*adj_eur +
                    w[5]*(rates[scen_i,t,5]+p["usd_spread_sofr"])/100*adj_usd +
                    w[6]*rates[scen_i,t,4]/100*adj_chf +
                    w[7]*(rates[scen_i,t,7]+p["chf_spread_saron"])/100*adj_chf
                ) * p["debt_pct_gdp"]"""

replacement = """                c = (
                    w[0]*rates[scen_i,t,0]/100 +
                    w[1]*(rates[scen_i,t,1]+p["uvr_real_rate"])/100*cum_uvr +
                    w[2]*rates[scen_i,t,2]/100*adj_usd +
                    w[3]*rates[scen_i,t,3]/100*adj_eur +
                    w[4]*(rates[scen_i,t,6]+p["eur_spread_eurib"])/100*adj_eur +
                    w[5]*(rates[scen_i,t,5]+p["usd_spread_sofr"])/100*adj_usd +
                    w[6]*rates[scen_i,t,4]/100*adj_chf +
                    w[7]*(rates[scen_i,t,7]+p["chf_spread_saron"])/100*adj_chf
                )
                if "model_base_cost" in p and p["model_base_cost"] > 0:
                    c = (c * p["total_absolute_debt"]) * (p["target_int_pct_gdp"] / p["model_base_cost"])
                else:
                    c = c * p.get("debt_pct_gdp", 55.0)"""

if target in code:
    code = code.replace(target, replacement)

with open("mtds_2026_v2 (1).py", "w") as f:
    f.write(code)
