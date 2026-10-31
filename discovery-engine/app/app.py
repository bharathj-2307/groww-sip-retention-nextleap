"""Groww SIP discovery engine: public feedback -> themes -> answers to the 9 research questions -> ranked opportunity areas.

Reads the stored results in ./data (built by build_app_data.py). The app does not call any AI at run time.
"""
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DROP = {"wavering", "paused_or_reduced", "stopped"}
THEMES = {
    "T1": "Why they started", "T2": "Expectation gap", "T3": "Confusing numbers", "T4": "Low or negative returns",
    "T5": "Missed or failed instalment", "T6": "Pause, reduce, stop or redeem", "T7": "Life event or cash crunch",
    "T8": "Checking too often", "T9": "Asking others", "T10": "App friction", "T11": "Trust and safety",
    "T12": "Feature request", "T13": "Support and charges", "T0": "Other",
}
SOURCES = {"play": "Play Store", "appstore": "App Store", "reddit": "Reddit", "tqna": "TradingQ&A", "youtube": "YouTube"}
STAGES = ["considering", "0-3 months", "3-12 months", "12+ months", "unknown"]
FIX_WEIGHT = {"in_app": 1.0, "partly": 0.6, "outside": 0.3}
FIX_LABEL = {"in_app": "Fixable in the app", "partly": "Partly fixable", "outside": "Mostly outside the app"}

st.set_page_config(page_title="Groww SIP discovery engine", layout="wide")


@st.cache_data
def load():
    df = pd.read_parquet(DATA / "posts.parquet")
    df["theme_list"] = df["themes"].fillna("").str.split(",").apply(lambda l: [t for t in l if t])
    df["source_name"] = df["source"].map(SOURCES)
    df["is_drop"] = df["status"].isin(DROP)
    opp = json.load(open(DATA / "opportunities.json")) if (DATA / "opportunities.json").exists() else None
    meta = json.load(open(DATA / "meta.json"))
    gold = json.load(open(DATA / "golden.json"))
    return df, opp, meta, gold


df_all, opp, meta, gold = load()


def clean_vals(s):
    return s.dropna().astype(str)


def dist(d, col, title, drop_vals=("unknown", "none", "not_applicable"), top=12):
    """Bar chart of a field among posts that say something about it, with the n and the 'not stated' share."""
    s = clean_vals(d[col])
    total = len(s)
    said = s[~s.isin(drop_vals)]
    if total == 0 or len(said) == 0:
        st.caption(f"{title}: no posts say this in the current filter.")
        return None
    vc = said.value_counts().head(top).rename_axis("value").reset_index(name="posts")
    vc["share"] = vc["posts"] / len(said)
    vc["value"] = vc["value"].str.replace("_", " ")
    st.markdown(f"**{title}**  \n<small>{len(said)} posts say this, {total - len(said)} do not (n = {total})</small>", unsafe_allow_html=True)
    ch = alt.Chart(vc).mark_bar().encode(
        y=alt.Y("value:N", sort="-x", title=None, axis=alt.Axis(labelLimit=280, labelOverlap=False)),
        x=alt.X("share:Q", axis=alt.Axis(format="%"), title="Share of posts that say it"),
        tooltip=["value", "posts", alt.Tooltip("share:Q", format=".0%")]).properties(height=28 * len(vc) + 30)
    st.altair_chart(ch, width="stretch")
    if len(said) < 30:
        st.warning(f"Only {len(said)} posts: treat as a pointer, not a number.")
    shares = (said.value_counts() / len(said)).to_dict()
    return {"n": len(said), "total": total, "shares": shares}


def pct(r, *labels):
    """Share (0-100) of the listed values in a dist() result."""
    return round(100 * sum(r["shares"].get(l, 0) for l in labels)) if r else 0


def top_list(r, k=2, skip=()):
    """'long term wealth (76%) and specific goal (11%)' from a dist() result."""
    if not r:
        return "nothing stated"
    items = [(v, sh) for v, sh in sorted(r["shares"].items(), key=lambda x: -x[1]) if v not in skip][:k]
    parts = [f"{v.replace('_', ' ').replace('xirr', 'XIRR').replace('sip ', 'SIP ')} ({round(100 * sh)}%)" for v, sh in items]
    return " and ".join([", ".join(parts[:-1]), parts[-1]]) if len(parts) > 1 else (parts[0] if parts else "nothing else")


SLOT = {"box": None}  # set per question so the takeaway renders above its charts


def takeaway(text):
    """The plain-language reading of the charts, built from the numbers in view, shown above them."""
    with (SLOT["box"] or st).container(border=True):
        st.markdown(f"**What this tells us.** {text[:1].upper()}{text[1:]}")


def quotes(d, n=4, col="quote"):
    d = d[d[col].fillna("").str.len() > 25].sample(min(n, len(d)), random_state=3) if len(d) else d
    for _, r in d.iterrows():
        st.markdown(f"> {r[col]}  \n<small>{SOURCES.get(r['source'], r['source'])} · [open post]({r['url']})</small>", unsafe_allow_html=True)


# ---------------------------------------------------------------- sidebar filters
st.sidebar.header("Filter the evidence")
src_sel = st.sidebar.multiselect("Source", list(SOURCES.values()), default=list(SOURCES.values()))
stage_sel = st.sidebar.multiselect("Stage of SIP journey", STAGES, default=STAGES)
inc_sel = st.sidebar.multiselect("Income type (when stated)", ["salaried", "self_employed", "student", "unknown"],
                                 default=["salaried", "self_employed", "student", "unknown"])
age_sel = st.sidebar.multiselect("Age band (when stated)", ["under 25", "25-35", "36+", "unknown"],
                                 default=["under 25", "25-35", "36+", "unknown"])
df = df_all[df_all.source_name.isin(src_sel) & df_all.stage.isin(stage_sel) & df_all.income_type.isin(inc_sel)
            & df_all.age_band.isin(age_sel)]
st.sidebar.metric("Posts in view", f"{len(df):,}", help="Real SIP experiences matching the filters")
st.sidebar.caption(f"Second-pass detail exists for {int(df.second_pass.sum()):,} of them. "
                   "Questions 1, 3, 4, 5, 6 and 9 use the second pass.")

st.title("Groww SIP discovery engine")
st.caption("Public feedback about SIPs on Groww, tagged with AI, counted, and checked against a hand-labelled set. "
           "Built to find where first-time investors drop off, and which problems are worth solving first.")

tab_how, tab_q, tab_opp, tab_explore, tab_val = st.tabs(
    ["How it works", "The 9 questions", "Opportunity areas", "Explore posts", "Validation"])

# ---------------------------------------------------------------- how it works
with tab_how:
    st.subheader("From public posts to ranked opportunities")
    st.markdown("""
1. **Collect.** Play Store and App Store reviews, Reddit (r/IndiaInvestments, r/mutualfunds), TradingQ&A threads, YouTube comments on SIP videos. Only public text, no usernames kept.
2. **Filter and tag (AI, pass 1).** Keyword filter, then Gemini decides if the post is a real SIP experience and tags themes (13 codes), stage, status (continuing, wavering, paused, stopped) and any stated age, income type and money source. Only what the post says; unknown stays unknown.
3. **Extract detail (AI, pass 2).** For posts with a theme, Gemini pulls why they started, what they expected, why they dropped, what they check, what they do outside the app, which app area troubled them, and the unmet need, each with an exact quote.
4. **Count and compare.** Theme shares, drop-off links, stage splits and segment cuts. Every number carries its sample size.
5. **Rank opportunity areas.** reach × drop-off difference × how fixable it is in the app. Details in the Opportunity areas tab.
6. **Validate.** 20 posts labelled by hand, scored against the AI, with the corrections made along the way (Validation tab).
""")
    st.subheader("What was collected")
    rows = [{"Source": SOURCES[k], "Collected": v, "Real SIP experiences": meta["relevant"].get(k, 0)} for k, v in meta["collected"].items()]
    t = pd.DataFrame(rows)
    t.loc[len(t)] = ["Total", t["Collected"].sum(), t["Real SIP experiences"].sum()]
    st.dataframe(t, hide_index=True, width="stretch")
    st.subheader("Limits to keep in mind")
    st.markdown("""
- Reddit is a sample, Play Store reviews start from Feb 2026, App Store is thin (30 reviews).
- Few posts state age (about 18%) or income type (about 11%), so segment cuts are small. The strict segment (salaried, 25-35, first-time, 3-12 months in) cannot be proven from public posts; interviews have to confirm it.
- "Asking others" is high mainly because Reddit and TradingQ&A are places where people ask. Read it as a platform effect.
- Drop-off shares describe who posts about it, not the whole Groww user base.
""")

# ---------------------------------------------------------------- 9 questions
QUESTIONS = {
    "1. Why do people start an SIP and what do they expect?": "q1",
    "2. What changes in behaviour in the months after starting?": "q2",
    "3. What leads them to pause, reduce or stop?": "q3",
    "4. What do they check in the app, and how often?": "q4",
    "5. What confuses or worries them in the app?": "q5",
    "6. What do they do outside the app when unsure?": "q6",
    "7. What separates continuers from quiet drop-offs?": "q7",
    "8. How do patterns differ across segments?": "q8",
    "9. What unmet needs keep coming up?": "q9",
}
with tab_q:
    q = QUESTIONS[st.selectbox("Pick a question", list(QUESTIONS))]
    SLOT["box"] = st.container()
    sp = df[df.second_pass]
    if q != "q2" and q != "q7" and q != "q8" and len(sp) < len(df):
        st.info(f"This answer uses the second AI pass, which covers {len(sp):,} of the {len(df):,} posts in view "
                f"({100 * len(sp) / max(1, len(df)):.0f}%). Posts with only a one-line theme are not extracted.")

    if q == "q1":
        c1, c2 = st.columns(2)
        with c1:
            r_start = dist(sp, "start_reason", "Why they started")
            r_inf = dist(sp, "influence_source", "Who or what got them started")
        with c2:
            r_exp = dist(sp, "expectation", "What they expected")
        if r_start and r_exp:
            takeaway(f"Most people start for {top_list(r_start)} and expect {top_list(r_exp, 1)}; only "
                     f"{pct(r_exp, 'quick_gains')}% say they wanted quick gains. {pct(r_inf, 'self')}% say they started on their "
                     "own, so a first-time investor who hits a bad month usually has no advisor to lean on.")
        quotes(sp[sp.start_reason.notna() & ~sp.start_reason.isin(["unknown"])])

    elif q == "q2":
        known = df[df.stage.isin(STAGES[:4])]
        rows = []
        for stg in STAGES[:4]:
            a = known[known.stage == stg]
            k = a[a.status != "unknown"]
            rows.append({"Stage": stg, "Posts": len(a), "Status stated": len(k),
                         "Drop-off share": (k.is_drop.mean() if len(k) else None)})
        st.markdown("**Drop-off share by stage** (among posts that state both stage and what they did with the SIP)")
        t = pd.DataFrame(rows)
        st.altair_chart(alt.Chart(t.dropna()).mark_bar().encode(
            x=alt.X("Stage:N", sort=STAGES[:4]), y=alt.Y("Drop-off share:Q", axis=alt.Axis(format="%")),
            tooltip=["Stage", "Posts", "Status stated", alt.Tooltip("Drop-off share:Q", format=".0%")]), width="stretch")
        st.dataframe(t, hide_index=True, width="stretch")
        ds = {r["Stage"]: r["Drop-off share"] for r in rows if r["Status stated"] >= 10}
        if {"0-3 months", "3-12 months"} <= ds.keys():
            later = f", and {round(100 * ds['12+ months'])}% after a year" if "12+ months" in ds else ""
            takeaway(f"Drop-off grows with time: {round(100 * ds['0-3 months'])}% of posts in the first 3 months show "
                     f"pausing, reducing, stopping or wavering, against {round(100 * ds['3-12 months'])}% in months 3-12{later}. "
                     "The first year is where wobbles start, which is the window the 12-month continuation metric measures.")
        th = []
        for stg in STAGES[:4]:
            a = known[known.stage == stg]
            for code, name in THEMES.items():
                if code in ("T0",):
                    continue
                th.append({"Stage": stg, "Theme": name, "Share": a.theme_list.apply(lambda l: code in l).mean() if len(a) else 0})
        st.markdown("**Which themes show up at each stage**")
        st.altair_chart(alt.Chart(pd.DataFrame(th)).mark_rect().encode(
            x=alt.X("Stage:N", sort=STAGES[:4]), y=alt.Y("Theme:N", sort=None),
            color=alt.Color("Share:Q", scale=alt.Scale(scheme="blues")),
            tooltip=["Stage", "Theme", alt.Tooltip("Share:Q", format=".0%")]).properties(height=380), width="stretch")

    elif q == "q3":
        dd = sp[sp.is_drop | sp.drop_reason.notna() & ~sp.drop_reason.isin(["not_applicable", "unknown"])]
        r = dist(dd, "drop_reason", "Reason given for pausing, reducing, stopping or thinking of it")
        if r:
            takeaway(f"{top_list(r)} lead. Market-driven reasons (low returns and market fall) make up "
                     f"{pct(r, 'low_returns', 'market_fall')}% and money needs (cash crunch, needing money) "
                     f"{pct(r, 'cash_crunch_or_life_event', 'needs_money')}%. Reasons Groww controls directly (failed instalment, "
                     f"app or support issue, lost trust) are {pct(r, 'failed_instalment_or_mandate', 'app_or_support_issue', 'lost_trust')}%. "
                     "Groww cannot stop markets falling, but it can shape what people do when they waver.")
        quotes(dd[dd.drop_reason.notna() & ~dd.drop_reason.isin(["not_applicable", "unknown"])])

    elif q == "q4":
        c1, c2 = st.columns(2)
        with c1:
            r_what = dist(sp, "what_checked", "What they look at")
        with c2:
            r_freq = dist(sp, "check_frequency", "How often")
        if r_what:
            freq = (f"Only {r_freq['n']} posts say how often they check, so frequency is a pointer at best."
                    if r_freq else "Almost no posts say how often they check.")
            takeaway(f"People mostly look at {top_list(r_what)}: numbers that move with the market, so a falling "
                     f"market is the first thing they see when they open the app. {freq}")
        chk = df[df.theme_list.apply(lambda l: "T8" in l)]
        st.caption(f"{len(chk)} posts mention checking too often or anxiety from daily movement (theme T8).")
        quotes(chk)

    elif q == "q5":
        r = dist(sp, "app_issue_area", "Area of the app or service people struggle with")
        if r:
            takeaway(f"The most common trouble spots are {top_list(r, 3, skip=('other',))}. Unlike market moves, these "
                     "happen inside the app, so they are the problems Groww can fix directly.")
        c = st.columns(3)
        for col, code in zip(c, ("T3", "T4", "T11")):
            a = df[df.theme_list.apply(lambda l: code in l)]
            col.metric(THEMES[code], f"{len(a)} posts", f"{100 * len(a) / max(1, len(df)):.0f}% of view", delta_color="off")
        quotes(sp[sp.app_issue_area.notna() & ~sp.app_issue_area.isin(["none", "other"])])

    elif q == "q6":
        r = dist(sp, "outside_action", "What they do outside the app when unsure")
        if r:
            takeaway(f"{pct(r, 'ask_online_community')}% ask an online community, which mostly reflects that Reddit is "
                     f"a place for asking. Beyond that, people turn to {top_list(r, 3, skip=('ask_online_community',))}. "
                     "The survey suggests friends and influencers matter more than these posts can show.")
        st.caption("Reddit and TradingQ&A are places where people ask others, so this is inflated by where the posts come from.")
        quotes(sp[sp.outside_action.notna() & ~sp.outside_action.isin(["none", "unknown"])])

    elif q == "q7":
        k = df[df.status != "unknown"].copy()
        k["group"] = k.status.map(lambda s: "Dropping (paused, reduced, stopped, wavering)" if s in DROP else "Continuing")
        n_d, n_c = int((k.group != "Continuing").sum()), int((k.group == "Continuing").sum())
        st.markdown(f"Posts that say what they did with their SIP: **{len(k)}** ({n_c} continuing, {n_d} dropping).")
        rows = []
        for code, name in THEMES.items():
            if code in ("T0", "T6"):
                continue
            for g, a in k.groupby("group"):
                rows.append({"Theme": name, "Group": g, "Share of group": a.theme_list.apply(lambda l: code in l).mean()})
        st.altair_chart(alt.Chart(pd.DataFrame(rows)).mark_bar().encode(
            y=alt.Y("Theme:N", sort=None), x=alt.X("Share of group:Q", axis=alt.Axis(format="%")),
            color="Group:N", yOffset="Group:N", tooltip=["Theme", "Group", alt.Tooltip("Share of group:Q", format=".0%")]).properties(height=420),
            width="stretch")
        g = pd.DataFrame(rows).pivot(index="Theme", columns="Group", values="Share of group")
        if g.shape[1] == 2:
            g["gap"] = 100 * (g.iloc[:, 1] - g.iloc[:, 0]) if g.columns[1] == "Dropping (paused, reduced, stopped, wavering)" else 100 * (g.iloc[:, 0] - g.iloc[:, 1])
            up = g.sort_values("gap", ascending=False).head(3)
            down = g.sort_values("gap").head(1)
            takeaway("Compared with people who keep going, people who drop off talk far more about "
                     + ", ".join(f"{t.lower()} (+{round(v)} pts)" for t, v in list(up["gap"].items())[:-1])
                     + f" and {up.index[-1].lower()} (+{round(up['gap'].iloc[-1])} pts)"
                     + f". Continuers talk more about {down.index[0].lower()}. The gaps point at where the wobble begins.")
        st.caption("T6 (pause, reduce, stop) is left out because it is the outcome itself. Quiet drop-offs rarely post, so the dropping group is under-represented; read gaps as direction, not size.")
        dist(sp[sp.status != "unknown"].assign(g=lambda x: x.is_drop.map({True: "dropping", False: "continuing"})), "g", "Split in the second-pass sample")

    elif q == "q8":
        st.markdown("Compare groups using what posts state about themselves. Most posts state none of it, so the groups are small.")
        by = st.radio("Split by", ["income_type", "age_band", "money_source", "first_time_investor", "influenced_by_others"], horizontal=True)
        a = df[df[by] != "unknown"]
        if len(a) == 0:
            st.write("No posts state this in the current filter.")
        else:
            rows = []
            for val, g in a.groupby(by):
                gk = g[g.status != "unknown"]
                rows.append({"Group": val, "Posts": len(g), "Status stated": len(gk),
                             "Drop-off share": gk.is_drop.mean() if len(gk) else None,
                             "Top themes": ", ".join(THEMES[t] for t, _ in pd.Series([t for l in g.theme_list for t in l if t not in ("T0", "T6")]).value_counts().head(3).items())})
            t = pd.DataFrame(rows)
            st.dataframe(t.style.format({"Drop-off share": "{:.0%}"}, na_rep="n/a"), hide_index=True, width="stretch")
            big = t[t["Status stated"] >= 30].dropna(subset=["Drop-off share"])
            if len(big) >= 2:
                hi, lo = big.loc[big["Drop-off share"].idxmax()], big.loc[big["Drop-off share"].idxmin()]
                takeaway(f"Among groups with at least 30 posts that say what they did with their SIP, {hi['Group']} shows the "
                         f"most drop-off ({hi['Drop-off share']:.0%}) and {lo['Group']} the least ({lo['Drop-off share']:.0%}). "
                         "Few posts state these details, so use this to choose who to interview, not as a final answer.")
            else:
                takeaway("Too few posts state this detail to compare groups. The interviews and survey have to answer this one.")
            small = t[t["Posts"] < 30]["Group"].tolist()
            if small:
                st.warning(f"Small groups (under 30 posts): {', '.join(small)}. Treat as a pointer only.")

    elif q == "q9":
        r = dist(sp, "need_category", "Kind of unmet need")
        if r:
            takeaway(f"{pct(r, 'fund_guidance')}% of stated needs are fund guidance, mostly people asking Reddit to review "
                     "their portfolio, which says more about the platform than about Groww. The needs that point at the app are "
                     f"{top_list(r, 3, skip=('fund_guidance', 'learning_education', 'other', 'tax_help'))}.")
        needs = sp[sp.unmet_need.fillna("").str.len() > 3]
        st.markdown(f"**In their own words** ({len(needs)} posts state a need)")
        vc = needs["unmet_need"].str.lower().str.strip(" .").value_counts().head(12)
        st.dataframe(vc.rename_axis("Need").reset_index(name="Posts"), hide_index=True, width="stretch")
        quotes(needs)

# ---------------------------------------------------------------- opportunities
with tab_opp:
    if not opp:
        st.write("Ranking not built yet.")
    else:
        st.subheader("Where is the biggest chance to keep first-time investors investing?")
        st.markdown("""
**Score = reach × drop-off difference × fixability.**
*Reach*: share of real SIP experiences that touch the area. *Drop-off difference*: how much more often people in that area say they paused, reduced, stopped or are wavering than people outside it (percentage points, with a 95% interval). *Fixability*: how much Groww can change it inside the app.
An area is marked **firm** only when at least 30 posts state their status and the interval stays above zero; otherwise **thin**.
""")
        st.markdown("Change how fixable you think each type is:")
        c = st.columns(3)
        w = {k: c[i].slider(FIX_LABEL[k], 0.0, 1.0, FIX_WEIGHT[k], 0.1) for i, k in enumerate(FIX_WEIGHT)}
        rows = []
        for a in opp["areas"]:
            diff = a["drop_diff_pp"] or 0
            lo = a["drop_diff_ci_pp"][0] if a["drop_diff_ci_pp"] else None
            hi = a["drop_diff_ci_pp"][1] if a["drop_diff_ci_pp"] else None
            rows.append({
                "Area": a["area"], "Score": round(a["reach_pct"] * max(0, diff) * w[a["fixable"]] / 100, 2),
                "Posts": a["posts"], "Reach %": a["reach_pct"], "Drop-off in area %": a["drop_rate_in_pct"],
                "Drop-off elsewhere %": a["drop_rate_out_pct"], "Difference (pp)": a["drop_diff_pp"],
                "95% interval": f"{lo} to {hi}" if lo is not None else "n/a", "Status stated": a["status_known_in"],
                "Early life %": a["early_life_pct"], "Fixable": FIX_LABEL[a["fixable"]], "Metric lever": a["metric_lever"],
                "Evidence": a["evidence"], "Detail coverage %": a["second_pass_coverage_pct"]})
        t = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)
        t.index += 1
        st.dataframe(t, width="stretch")
        st.altair_chart(alt.Chart(t).mark_bar().encode(
            y=alt.Y("Area:N", sort="-x"), x="Score:Q", color=alt.Color("Evidence:N", scale=alt.Scale(domain=["firm", "thin"], range=["#1f77b4", "#c7c7c7"])),
            tooltip=["Area", "Score", "Posts", "Evidence"]), width="stretch")
        st.caption(f"Based on {opp['relevant_posts']:,} real SIP experiences, of which {opp['status_known']:,} state what they did with their SIP. "
                   "Drop-off shares describe people who post, not all users. The ranking is a place to look, not proof; interviews and the survey test it.")
        pick = st.selectbox("Open an area", t["Area"])
        a = next(x for x in opp["areas"] if x["area"] == pick)
        c1, c2 = st.columns(2)
        c1.markdown(f"**Metric lever:** {a['metric_lever']}  \n**Fixability:** {FIX_LABEL[a['fixable']]}  \n**Sources:** "
                    + ", ".join(f"{SOURCES.get(k, k)} {v}" for k, v in a["sources"].items()))
        c2.markdown(f"**Who:** salaried share {a['salaried_share_pct']}% (all posts {a['salaried_share_all_pct']}%, n={a['income_known_in']}) · "
                    f"aged 25-35 {a['age_25_35_share_pct']}% (all posts {a['age_25_35_share_all_pct']}%, n={a['age_known_in']})  \n"
                    f"**Early life (first 12 months):** {a['early_life_pct']}% vs {round(a['early_life_pct'] - a['early_life_vs_all_pp'], 1) if a['early_life_pct'] is not None else 'n/a'}% overall")
        for qq in a["quotes"]:
            st.markdown(f"> {qq['quote']}  \n<small>{SOURCES.get(qq['source'], qq['source'])} · [open post]({qq['url']})</small>", unsafe_allow_html=True)

# ---------------------------------------------------------------- explore
with tab_explore:
    st.subheader("Browse the evidence behind the numbers")
    th_sel = st.multiselect("Theme", [f"{k} {v}" for k, v in THEMES.items()])
    codes = [t.split()[0] for t in th_sel]
    ex = df
    if codes:
        ex = ex[ex.theme_list.apply(lambda l: all(c in l for c in codes))]
    status_sel = st.multiselect("Status", ["continuing", "wavering", "paused_or_reduced", "stopped", "unknown"])
    if status_sel:
        ex = ex[ex.status.isin(status_sel)]
    text = st.text_input("Search in quotes")
    if text:
        ex = ex[ex.quote.fillna("").str.contains(text, case=False, regex=False)]
    st.caption(f"{len(ex):,} posts")
    show = ex[["source_name", "date", "stage", "status", "themes", "quote", "url"]].rename(columns={"source_name": "source"})
    st.dataframe(show.head(500), hide_index=True, width="stretch",
                 column_config={"url": st.column_config.LinkColumn("post", display_text="open")})
    st.download_button("Download these rows (CSV)", show.to_csv(index=False), "posts.csv", "text/csv")

# ---------------------------------------------------------------- validation
with tab_val:
    st.subheader("How we know the tagging can be trusted")
    st.markdown("""
20 posts were labelled by hand (before seeing the AI's answers), then compared with the AI.
Scores count only posts both sides agree are real SIP experiences. Corrections were made after the first round,
so the final numbers are optimistic: they were tuned on the same 20 posts. A fresh holdout set is the honest check.
""")
    names = {"relevance": "Real SIP experience?", "themes_exact": "Themes (exact match)", "themes_overlap": "Themes (at least one shared)",
             "stage": "Stage", "status": "Status"}
    rounds = {"first_round_first_labels": "Round 1, my first labels", "first_round_reviewed_labels": "Round 1, after I re-reviewed labels",
              "final": "After 3 corrections"}
    rows = []
    for k, n in names.items():
        r = {"Check": n}
        for rk, rn in rounds.items():
            if rk in gold and k in gold[rk]:
                g = gold[rk][k]
                r[rn] = f"{g['pct']:.0f}% ({g['agree']}/{g['of']})"
        rows.append(r)
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.markdown("""
**Corrections made to the AI instructions**
1. *Stage:* count from the person's first SIP ("just started" = 0-3 months, "after 4 months" = 3-12), not from the post date.
2. *Status:* unknown unless the post says what they did with their SIP. A complaint alone is not "wavering".
3. *Relevance:* praise or complaints about the app count as real experiences; posts asking for advice count as "asking others".
4. *Batch size:* 3 posts per request matched 1 per request; 8 per request dropped and mislabelled posts.
""")
