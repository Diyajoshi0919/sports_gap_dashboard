"""
Sports Gap Dashboard — Streamlit version
What India watches vs. what it funds vs. what it wins

Run:
    pip install -r requirements.txt
    streamlit run app.py
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Sports Gap Dashboard",
    page_icon="🏏",
    layout="wide",
)

DEFAULT_DATA_DIR = os.environ.get(
    "SPORTS_DATA_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),
)

FILES = {
    "core5":          "sports_master_core5.csv",
    "master_all":     "sports_master_all.csv",
    "trends_yearly":  "trends_yearly_clean.csv",
    "trends_state":   "trends_state_clean.csv",
    "trends_summary": "trends_state_summary.csv",
    "nsf_long":       "nsf_funding_long.csv",
    "nsf_by_sport":   "nsf_funding_by_sport.csv",
    "olympics":       "olympic_medals_events.csv",
    "asian_games":    "asian_games_sport_year.csv",
    "budget_change":  "budget_change_2026_27.csv",
    "budget_long":    "budget_long.csv",
    "ki_infra":       "khelo_india_infrastructure.csv",
    "ki_enrol":       "khelo_india_enrolment.csv",
    "sapa":           "sapa_clean.csv",
}

SECTIONS = [
    "1. Overview",
    "2. Public interest",
    "3. Funding & efficiency",
    "4. Medal performance",
    "5. Budget 2026-27",
    "6. Grassroots",
]

# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
st.sidebar.title("🏏 Sports Gap Dashboard")
st.sidebar.caption("What India watches vs. what it funds vs. what it wins")

data_dir = st.sidebar.text_input("Data folder", DEFAULT_DATA_DIR)
section = st.sidebar.radio("Section", SECTIONS)
st.sidebar.divider()


@st.cache_data
def _read(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def load(key: str) -> pd.DataFrame | None:
    path = os.path.join(data_dir, FILES[key])
    if not os.path.exists(path):
        st.warning(f"Missing file: `{FILES[key]}` in `{data_dir}`")
        return None
    return _read(path).copy()


def as_bool(s: pd.Series) -> pd.Series:
    """CSV booleans can arrive as bool, 'True'/'False', or 1/0."""
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y"])


def show(fig, height=None):
    if height:
        fig.update_layout(height=height)
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig, width="stretch")


def raw_data(df: pd.DataFrame, label: str, fname: str):
    with st.expander(f"View data — {label}"):
        st.dataframe(df, width="stretch", hide_index=True)
        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name=fname,
            mime="text/csv",
            key=f"dl_{fname}_{label}",
        )


st.title("Sports Gap Dashboard")
st.caption("What India watches vs. what it funds vs. what it wins")

# ----------------------------------------------------------------------------
# 1. Overview
# ----------------------------------------------------------------------------
if section == SECTIONS[0]:
    st.header("1. Overview")
    nsf, oly, tsum = load("nsf_by_sport"), load("olympics"), load("trends_summary")

    if nsf is not None and oly is not None and tsum is not None:
        cricket_top = int((tsum["dominant_sport"] == "Cricket").sum())
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("NSF funding 2022-25", f"₹{nsf['total_2022_25_rs_cr'].sum():,.2f} cr")
        c2.metric("Olympic medals (all time)", len(oly))
        c3.metric("States where cricket is #1", f"{cricket_top} of {len(tsum)}")
        c4.metric("Sports funded via NSF", nsf["sport_std"].nunique())

    core5 = load("core5")
    if core5 is not None:
        chart_data = core5[[
            "sport_std",
            "avg_search_interest_2004_2026_norm",
            "total_2022_25_rs_cr_norm",
            "olympic_total_norm",
            "asian_total_norm",
            "cwg_total_norm",
        ]].copy()
        chart_data.columns = ["Sport", "Search interest", "Govt funding",
                              "Olympic medals", "Asian Games medals", "CWG medals"]
        metrics = chart_data.columns[1:].tolist()

        picked = st.multiselect("Metrics to compare", metrics, default=metrics)
        if picked:
            col_a, col_b = st.columns([3, 2])
            with col_a:
                fig = px.bar(chart_data, x="Sport", y=picked, barmode="group",
                             title="Interest vs Funding vs Medals (normalised 0-1)",
                             labels={"value": "Normalised score", "variable": "Metric"})
                show(fig, 480)
            with col_b:
                fig = px.imshow(chart_data.set_index("Sport")[picked], text_auto=".2f",
                                color_continuous_scale="Blues", aspect="auto",
                                title="Core-5 heatmap (0-1)")
                show(fig, 480)
        raw_data(chart_data, "Core-5 normalised", "core5_normalised.csv")

# ----------------------------------------------------------------------------
# 2. Public interest
# ----------------------------------------------------------------------------
elif section == SECTIONS[1]:
    st.header("2. Public interest")

    ty = load("trends_yearly")
    if ty is not None:
        sports = sorted(ty["sport"].unique())
        yr_min, yr_max = int(ty["year"].min()), int(ty["year"].max())
        st.sidebar.subheader("Filters")
        sel_sports = st.sidebar.multiselect("Sports", sports, default=sports)
        yr = st.sidebar.slider("Years", yr_min, yr_max, (yr_min, yr_max))

        d = ty[ty["sport"].isin(sel_sports) & ty["year"].between(*yr)]
        fig = px.line(d, x="year", y="search_interest_index", color="sport", markers=True,
                      title=f"Search Interest in India, {yr[0]}-{yr[1]}",
                      labels={"search_interest_index": "Search interest index"})
        show(fig, 450)

    tab1, tab2 = st.tabs(["State heatmap", "Cricket's share by state"])

    with tab1:
        ts = load("trends_state")
        if ts is not None:
            pivot = ts.pivot_table(index="state", columns="sport", values="interest_share_pct")
            states = st.multiselect("Limit to states (blank = all)", sorted(pivot.index))
            if states:
                pivot = pivot.loc[states]
            fig = px.imshow(pivot, text_auto=True, aspect="auto",
                            color_continuous_scale="Blues",
                            title="Share of Search Interest by State (%)")
            show(fig, max(400, 26 * len(pivot)))
            raw_data(ts, "state trends", "trends_state_clean.csv")

    with tab2:
        tsum = load("trends_summary")
        if tsum is not None:
            tsum = tsum.sort_values("cricket_share_pct")
            fig = px.bar(tsum, x="cricket_share_pct", y="state", orientation="h",
                         color="dominant_sport",
                         title="Cricket's Share of Search Interest by State",
                         labels={"cricket_share_pct": "Cricket share (%)", "state": ""})
            show(fig, 850)

# ----------------------------------------------------------------------------
# 3. Funding & efficiency
# ----------------------------------------------------------------------------
elif section == SECTIONS[2]:
    st.header("3. Funding & efficiency")

    nsf = load("nsf_by_sport")
    nl = load("nsf_long")
    ma = load("master_all")

    st.sidebar.subheader("Filters")
    top_n = st.sidebar.slider("Show top N sports by funding", 5, 40, 20)

    tab1, tab2, tab3 = st.tabs(["Allocation", "Funding vs medals", "Cost per medal"])

    with tab1:
        if nsf is not None:
            nsf = nsf.sort_values("total_2022_25_rs_cr", ascending=False)
            top_sports = nsf["sport_std"].head(top_n).tolist()

            fig = px.bar(nsf.head(top_n), x="sport_std", y="total_2022_25_rs_cr",
                         color="high_priority",
                         title=f"Total NSF Funding 2022-25 — top {top_n} (Rs crore)",
                         labels={"sport_std": "", "total_2022_25_rs_cr": "Rs crore",
                                 "high_priority": "High priority"})
            fig.update_layout(xaxis_tickangle=-45)
            show(fig, 480)

            if nl is not None:
                d = nl[nl["sport_std"].isin(top_sports)]
                fig = px.bar(d, x="allocation_rs_cr", y="sport_std", color="fiscal_year",
                             orientation="h",
                             title="NSF Allocation by Sport and Year (Rs crore)",
                             labels={"allocation_rs_cr": "Rs crore", "sport_std": "",
                                     "fiscal_year": "Fiscal year"})
                fig.update_yaxes(categoryorder="total ascending")
                show(fig, max(400, 28 * len(top_sports)))
            raw_data(nsf, "NSF by sport", "nsf_funding_by_sport.csv")

    with tab2:
        if ma is not None:
            ma2 = ma.dropna(subset=["total_2022_25_rs_cr", "medals_2022_24"]).copy()
            label_all = st.checkbox("Label every sport", value=False)
            if label_all:
                ma2["label"] = ma2["sport_std"]
            else:
                ma2["label"] = ma2["sport_std"].where(
                    (ma2["total_2022_25_rs_cr"] > 25) | (ma2["medals_2022_24"] >= 5), "")

            corr = ma2["total_2022_25_rs_cr"].corr(ma2["medals_2022_24"])
            st.metric("Correlation: funding vs medals", f"{corr:.2f}")

            fig = px.scatter(
                ma2, x="total_2022_25_rs_cr", y="medals_2022_24", text="label",
                hover_name="sport_std",
                title="Does Funding Buy Medals? (Funding 2022-25 vs Medals 2022-24)",
                labels={"total_2022_25_rs_cr": "Funding 2022-25 (Rs crore)",
                        "medals_2022_24": "Medals (Asian Games 2022 + Paris 2024)"},
            )
            fig.update_traces(
                textposition=["bottom center" if s == "Badminton" else "top center"
                              for s in ma2["label"]],
                marker=dict(size=10),
            )
            show(fig, 600)

    with tab3:
        if ma is not None:
            cpm = ma.dropna(subset=["rs_cr_per_medal_2022_24"]).sort_values(
                "rs_cr_per_medal_2022_24")
            fig = px.bar(cpm, x="rs_cr_per_medal_2022_24", y="sport_std", orientation="h",
                         text_auto=".2f",
                         title="Cost per Medal (Rs crore) — lower is more efficient",
                         labels={"rs_cr_per_medal_2022_24": "Rs crore per medal",
                                 "sport_std": ""})
            show(fig, max(400, 32 * len(cpm)))
            raw_data(cpm[["sport_std", "total_2022_25_rs_cr", "medals_2022_24",
                          "rs_cr_per_medal_2022_24"]],
                     "cost per medal", "cost_per_medal.csv")

# ----------------------------------------------------------------------------
# 4. Medal performance
# ----------------------------------------------------------------------------
elif section == SECTIONS[3]:
    st.header("4. Medal performance")

    oly = load("olympics")
    ag = load("asian_games")
    ma = load("master_all")

    tab1, tab2, tab3 = st.tabs(["Olympics", "Asian Games", "All competitions"])

    with tab1:
        if oly is not None:
            medals = sorted(oly["medal"].unique())
            sel = st.multiselect("Medal types", medals, default=medals)
            d = oly[oly["medal"].isin(sel)]

            c1, c2 = st.columns(2)
            with c1:
                fig = px.histogram(d, x="year", color="medal",
                                   title="India's Olympic Medals by Year "
                                         "(1900 medals are disputed)")
                fig.update_xaxes(type="category")
                show(fig, 450)
            with c2:
                fig = px.histogram(d, y="sport_std", color="medal",
                                   title="Olympic Medals by Sport (All Time)",
                                   labels={"sport_std": ""})
                fig.update_yaxes(categoryorder="total ascending")
                show(fig, 450)
            raw_data(d, "Olympic medal events", "olympic_medals_events.csv")

    with tab2:
        if ag is not None:
            n = st.slider("Number of top sports", 3, 15, 8)
            top = ag.groupby("sport_std")["total"].sum().nlargest(n).index
            fig = px.line(ag[ag["sport_std"].isin(top)], x="year", y="total",
                          color="sport_std", markers=True,
                          title=f"Asian Games Medals by Sport (Top {n} Sports)",
                          labels={"total": "Medals", "sport_std": "Sport"})
            show(fig, 500)

    with tab3:
        if ma is not None:
            ma = ma.rename(columns={"olympic_total": "Olympics",
                                    "asian_total": "Asian Games", "cwg_total": "CWG"})
            comps = ["Olympics", "Asian Games", "CWG"]
            sel = st.multiselect("Competitions", comps, default=comps)
            n = st.slider("Top N sports", 5, 30, 15, key="top_all")
            if sel:
                ma["all_medals"] = ma[sel].sum(axis=1)
                top = ma.sort_values("all_medals").tail(n)
                fig = px.bar(top, x=sel, y="sport_std", orientation="h",
                             title=f"All-Time Medals by Competition (Top {n} Sports)",
                             labels={"sport_std": "", "value": "Medals",
                                     "variable": "Competition"})
                show(fig, max(400, 32 * n))

# ----------------------------------------------------------------------------
# 5. Budget 2026-27
# ----------------------------------------------------------------------------
elif section == SECTIONS[4]:
    st.header("5. Budget 2026-27")

    bc = load("budget_change")
    if bc is not None:
        d = bc[as_bool(bc["sport_relevant"])].sort_values("change_rs_cr").copy()
        inc, dec = d[d["change_rs_cr"] > 0], d[d["change_rs_cr"] < 0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Net change", f"₹{d['change_rs_cr'].sum():,.2f} cr")
        c2.metric("Schemes increased", len(inc))
        c3.metric("Schemes cut", len(dec))

        d["Direction"] = d["change_rs_cr"].apply(lambda v: "Increase" if v > 0 else "Decrease")
        fig = px.bar(d, x="change_rs_cr", y="scheme", orientation="h", color="Direction",
                     color_discrete_map={"Increase": "#2a9d8f", "Decrease": "#e76f51"},
                     title="Change in Sports Budget: RE 2025-26 to BE 2026-27 (Rs crore)",
                     labels={"change_rs_cr": "Change (Rs crore)", "scheme": ""})
        show(fig, 650)
        raw_data(d, "budget change", "budget_change_2026_27.csv")

    bl = load("budget_long")
    if bl is not None:
        d = bl[as_bool(bl["sport_relevant"])].copy()
        d["period"] = d["fiscal_year"].astype(str) + " " + d["estimate_type"].astype(str)
        d = d.sort_values("period")
        mode = st.radio("View", ["Stacked", "Grouped"], horizontal=True)
        fig = px.bar(d, x="period", y="total_rs_cr", color="category",
                     barmode="stack" if mode == "Stacked" else "group",
                     title="Sports Budget by Category (Rs crore)",
                     labels={"total_rs_cr": "Rs crore", "period": "", "category": "Category"})
        show(fig, 500)

# ----------------------------------------------------------------------------
# 6. Grassroots
# ----------------------------------------------------------------------------
elif section == SECTIONS[5]:
    st.header("6. Grassroots")

    tab1, tab2, tab3 = st.tabs(["Khelo India infrastructure",
                                "Khelo India enrolment", "SAPA survey"])

    with tab1:
        ki = load("ki_infra")
        if ki is not None:
            facilities = ["multipurpose_hall", "athletic_track", "football_field",
                          "hockey_field", "swimming_pool", "others"]
            facilities = [f for f in facilities if f in ki.columns]
            sel = st.multiselect("Facility types", facilities, default=facilities,
                                 format_func=lambda s: s.replace("_", " ").title())
            if sel:
                ki["total"] = ki[sel].sum(axis=1)
                st.metric("Total facilities (selected types)", int(ki["total"].sum()))
                fig = px.bar(ki, y="state", x=sel, orientation="h",
                             title="Khelo India Infrastructure by State",
                             labels={"state": "", "value": "Facilities",
                                     "variable": "Facility"})
                fig.update_yaxes(categoryorder="total ascending")
                show(fig, 800)
            raw_data(ki, "Khelo India infrastructure", "khelo_india_infrastructure.csv")

    with tab2:
        ke = load("ki_enrol")
        if ke is not None:
            c1, c2, c3 = st.columns(3)
            m, f = ke["male_trainees"].sum(), ke["female_trainees"].sum()
            c1.metric("Male trainees", f"{int(m):,}")
            c2.metric("Female trainees", f"{int(f):,}")
            c3.metric("Females per 100 males (overall)", f"{100 * f / m:.1f}" if m else "—")

            view = st.radio("View", ["Trainees by gender", "Gender ratio"], horizontal=True)
            if view == "Trainees by gender":
                fig = px.bar(ke, y="state", x=["male_trainees", "female_trainees"],
                             orientation="h", barmode="group",
                             title="Khelo India Trainees by Gender",
                             labels={"state": "", "value": "Trainees", "variable": "Gender"})
                show(fig, 750)
            else:
                d = ke.sort_values("female_per_100_male")
                fig = px.bar(d, x="female_per_100_male", y="state", orientation="h",
                             title="Female Trainees per 100 Male Trainees (100 = equal)",
                             labels={"female_per_100_male": "Females per 100 males",
                                     "state": ""})
                fig.add_vline(x=100, line_dash="dash")
                show(fig, 700)

    with tab3:
        sapa = load("sapa")
        if sapa is not None:
            pct = sapa[sapa["unit"] == "%"].sort_values("value_num")
            factors = sorted(pct["factor"].dropna().unique())
            sel = st.multiselect("Factors", factors, default=factors)
            d = pct[pct["factor"].isin(sel)]
            fig = px.bar(d, x="value_num", y="metric", color="factor", orientation="h",
                         title="SAPA Survey Findings (%)",
                         labels={"value_num": "%", "metric": "", "factor": "Factor"})
            show(fig, max(400, 28 * len(d)))

            inactivity = sapa[sapa["metric"].str.contains("inactivity rate", na=False)]
            if not inactivity.empty:
                fig = px.bar(inactivity, x="segment", y="value_num", text_auto=True,
                             title="Physical Inactivity: Urban vs Rural (%)",
                             labels={"value_num": "%", "segment": ""})
                show(fig, 400)
            raw_data(sapa, "SAPA survey", "sapa_clean.csv")