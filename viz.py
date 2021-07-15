import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mc
import colorsys
import numpy as np
import re

fig, ax = plt.subplots(2, 2, figsize=(32,16))
# plt.subplots_adjust(hspace=0.3)
alpha = 0.7
county_bounds = [30, 75]
muni_bounds = [20, 350]

names = {
    "COUNTYFP": "COUNTY ONLY",
    "COUSUB_ID": "MUNI ONLY",
    "COUNTY_PREF":"COUNTY_PREF",
    "MUNI_PREF": "MUNI_PREF",
    "BOTH_EQUAL": "BOTH_EQUAL",
}

colors = {
    "COUNTY ONLY":"#1f77b4",
    "MUNI ONLY":"#ff7f0e",
    "COUNTY_PREF":'#9467bd',
    "MUNI_PREF":"#d62728",
    "BOTH_EQUAL":"#2ca02c",
    "NEUTRAL":"#8c564b",
}

def change_color(color, amount):
    c = colorsys.rgb_to_hls(*mc.to_rgb(color))
    return colorsys.hls_to_rgb(c[0], 1 - amount * (1-c[1]), c[2])

def annotate_plot(ax, title):
    ax[0][0].set_title("# Counties Split (Traceplot)", fontsize=24)
    ax[0][0].set_ylim(county_bounds)
    ax[0][1].set_title('# Counties Split (Histogram)', fontsize=24)
    ax[0][1].set_xlim(county_bounds)
    ax[1][0].set_title("# Munis Split (Traceplot)", fontsize=24)
    ax[1][0].set_ylim(muni_bounds)
    ax[1][1].set_title('# Munis Split (Histogram)', fontsize=24)
    ax[1][1].set_xlim(muni_bounds)
    ax[1][1].legend()
    plt.suptitle(title, fontsize=32)
    filename = re.sub(r'[^A-Za-z0-9 %]+', '', title)
    plt.savefig(f"plots_500k/{filename.replace(' ', '_')}.png", bbox_inches='tight')
    # plt.show()
    return

def plot_run(ax, epsilon, steps, division_aware, first_check_division, tuple_type):
    run = f"{division_aware}_{tuple_type}_{first_check_division}_{epsilon}_{steps}"
    if division_aware:
        label = names[tuple_type]
    else:
        label = "NEUTRAL"
    amount_to_darken = sum([division_aware, first_check_division, epsilon==0.05])
    run_color = change_color(colors[label], 1 + (amount_to_darken/10)) # figure out a way to not hard-code
    run_color = colors[label]
    df = pd.read_csv(f"outputs/{run}.csv", index_col=0)
    counties_data = df['split_counties']
    munis_data = df['split_munis']

    if first_check_division:
        label += ", first checking division"
    label += f", {100*epsilon}%"
    ax[0][0].plot(counties_data,
                    alpha=alpha,
                    # color=run_color,
                    label=label)
    ax[0][1].hist(counties_data,
                    bins=np.arange(county_bounds[0], county_bounds[1]+2, 1),
                    alpha=alpha,
                    # color=run_color,
                    label=label)

    ax[1][0].plot(munis_data,
                    alpha=alpha,
                    # color=run_color,
                    label=run)
    ax[1][1].hist(munis_data,
                    bins=np.arange(muni_bounds[0], muni_bounds[1]+5, 5),
                    alpha=alpha,
                    # color=run_color,
                    label=label)
    return

if __name__=="__main__":
    for epsilon in [0.05]:
        for steps in [500000]:
            for division_aware in [True, False]:
                if not division_aware:
                    plot_run(ax, epsilon, steps, division_aware, False, "BOTH_EQUAL")
                    continue
                for first_check_division in [False]:
                    for tuple_type in ["COUNTYFP", "COUSUB_ID", "COUNTY_PREF", "BOTH_EQUAL", "MUNI_PREF"]:
                    # for tuple_type in ["COUNTY_PREF", "BOTH_EQUAL", "MUNI_PREF"]:
                        plot_run(ax, epsilon, steps, division_aware, first_check_division, tuple_type)
                        
    annotate_plot(ax, "WI, 5% pop. dev., aware vs. neutral, first check division false")

