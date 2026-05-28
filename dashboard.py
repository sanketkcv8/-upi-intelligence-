# dashboard.py
# ------------
# Run with: streamlit run dashboard.py
#
# TABS:
#   1. Upload         — load PDF or sample data
#   2. Transactions   — searchable, filterable transaction table
#   3. Categories     — pie chart + bar chart spending breakdown
#   4. Insights       — Claude's personalised analysis
#   5. Month view     — month-on-month comparison

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import tempfile, os

from config      import CATEGORIES
from database    import init_db, save_statement, save_transactions, save_insights, \
                        get_transactions, get_all_statements, get_insights, delete_statement
from parser      import extract_transactions_with_claude, get_sample_statement
from categoriser import categorise_transactions
from insights    import generate_insights

st.set_page_config(page_title="UPI Spending Intelligence", page_icon="💳", layout="wide")
init_db()

# ── Sidebar — statement selector ──────────────────────────────────────────────
with st.sidebar:
    st.title("💳 UPI Intelligence")
    st.caption("Spending analysis for Indian bank statements")
    st.divider()

    statements = get_all_statements()
    if statements:
        options = {f"{s['bank']} — {s['period']} ({s['filename']})": s["id"]
                   for s in statements}
        selected_label = st.selectbox("Loaded statements", list(options.keys()))
        active_stmt_id = options[selected_label]

        if st.button("🗑️ Delete this statement", use_container_width=True):
            delete_statement(active_stmt_id)
            st.rerun()
    else:
        active_stmt_id = None
        st.info("No statements loaded yet. Upload one in the first tab.")

# ── Load active transactions ───────────────────────────────────────────────────
txns = get_transactions(active_stmt_id) if active_stmt_id else []
df   = pd.DataFrame(txns) if txns else pd.DataFrame()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📁 Upload", "📋 Transactions", "🍩 Categories", "🤖 Insights", "📅 Monthly"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Load your bank statement")
    st.write("Upload a PDF from any Indian bank — HDFC, SBI, ICICI, Axis, Kotak, and more. Claude reads any format.")

    mode = st.radio(
        "Choose:", ["📄 Upload real PDF", "🧪 Use sample data (Priya's 3-month statement)"],
        horizontal=True
    )

    if mode == "📄 Upload real PDF":
        st.info("**How to get your statement:** Login to your bank's netbanking → Statements → Download PDF (last 3–6 months recommended)")
        pdf_file = st.file_uploader("Upload bank statement PDF", type=["pdf"])

        if pdf_file and st.button("🚀 Analyse Statement", type="primary", use_container_width=True):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_file.read())
                tmp_path = tmp.name

            try:
                with st.status("Step 1 of 3 — Reading PDF with Claude...", expanded=True) as status:
                    with open(tmp_path, "rb") as f:
                        from parser import extract_pdf_text
                        text, pages = extract_pdf_text(tmp_path)
                    st.write(f"Extracted text from {pages} pages")
                    data = extract_transactions_with_claude(text)
                    st.write(f"Found **{len(data['transactions'])}** transactions from {data.get('bank','your bank')}")
                    status.update(label="✅ Transactions extracted", state="complete")

                with st.status("Step 2 of 3 — Categorising transactions...", expanded=True) as status:
                    labelled = categorise_transactions(data["transactions"])
                    status.update(label=f"✅ All {len(labelled)} transactions categorised", state="complete")

                with st.status("Step 3 of 3 — Generating insights...", expanded=True) as status:
                    stmt_id = save_statement(pdf_file.name, data.get("bank","Unknown"), data.get("period",""))
                    save_transactions(stmt_id, labelled)
                    insight_text = generate_insights(labelled, data)
                    save_insights(stmt_id, insight_text)
                    status.update(label="✅ Insights ready", state="complete")

                st.success(f"Done! Go to the **Categories** or **Insights** tab to explore your spending.")
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                os.unlink(tmp_path)

    else:
        st.info("Using a realistic 3-month sample statement for Priya Kulkarni (Pune, ₹65K/month salary, Jan–Mar 2024).")
        if st.button("🚀 Load Sample & Analyse", type="primary", use_container_width=True):
            with st.status("Step 1 of 3 — Loading sample data...", expanded=True) as status:
                data = get_sample_statement()
                st.write(f"Loaded {len(data['transactions'])} sample transactions")
                status.update(label="✅ Sample data loaded", state="complete")

            with st.status("Step 2 of 3 — Categorising transactions...", expanded=True) as status:
                labelled = categorise_transactions(data["transactions"])
                status.update(label=f"✅ All {len(labelled)} transactions categorised", state="complete")

            with st.status("Step 3 of 3 — Generating insights...", expanded=True) as status:
                stmt_id = save_statement("sample_statement.pdf", data["bank"], data["period"])
                save_transactions(stmt_id, labelled)
                insight_text = generate_insights(labelled, data)
                save_insights(stmt_id, insight_text)
                status.update(label="✅ Insights ready", state="complete")

            st.success("Done! Explore your spending in the other tabs.")
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TRANSACTIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    if df.empty:
        st.info("Load a statement first.")
    else:
        st.subheader(f"All transactions ({len(df)})")

        col1, col2, col3 = st.columns(3)
        cat_filter  = col1.multiselect("Filter by category", sorted(df["category"].unique()))
        type_filter = col2.multiselect("Filter by type", ["debit","credit"])
        search      = col3.text_input("Search description", placeholder="e.g. Swiggy")

        filtered = df.copy()
        if cat_filter:  filtered = filtered[filtered["category"].isin(cat_filter)]
        if type_filter: filtered = filtered[filtered["type"].isin(type_filter)]
        if search:      filtered = filtered[filtered["description"].str.contains(search, case=False, na=False)]

        # Colour code debit/credit
        def style_type(val):
            return "color: #D85A30; font-weight:500" if val == "debit" else "color: #1D9E75; font-weight:500"

        display_cols = ["date","merchant","description","category","amount","type","balance"]
        available    = [c for c in display_cols if c in filtered.columns]
        styled = filtered[available].style.applymap(style_type, subset=["type"])

        st.dataframe(styled, use_container_width=True, hide_index=True)

        col_a, col_b, col_c = st.columns(3)
        debits = filtered[filtered["type"]=="debit"]
        col_a.metric("Total spent", f"₹{debits['amount'].sum():,.0f}")
        col_b.metric("Transactions", len(filtered))
        col_c.metric("Avg transaction", f"₹{debits['amount'].mean():,.0f}" if not debits.empty else "—")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CATEGORIES
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    if df.empty:
        st.info("Load a statement first.")
    else:
        debits = df[df["type"] == "debit"]
        cat_summary = debits.groupby("category")["amount"].sum().reset_index()
        cat_summary  = cat_summary.sort_values("amount", ascending=False)

        # Map colours from config
        cat_summary["color"] = cat_summary["category"].map(
            {k: v["color"] for k, v in CATEGORIES.items()}
        ).fillna("#9E9E9E")

        col_pie, col_bar = st.columns([1, 1.4])

        with col_pie:
            fig_pie = px.pie(
                cat_summary, names="category", values="amount",
                color="category",
                color_discrete_map={k: v["color"] for k, v in CATEGORIES.items()},
                title="Spending by category",
                hole=0.45,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(showlegend=False, height=380,
                                  margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_bar:
            fig_bar = px.bar(
                cat_summary, x="amount", y="category",
                orientation="h",
                color="category",
                color_discrete_map={k: v["color"] for k, v in CATEGORIES.items()},
                title="₹ Spent per category",
                text_auto=".2s",
            )
            fig_bar.update_layout(showlegend=False, height=380,
                                  yaxis=dict(autorange="reversed"),
                                  margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_bar, use_container_width=True)

        # Category cards
        st.divider()
        st.subheader("Category breakdown")
        cols = st.columns(3)
        for i, row in cat_summary.iterrows():
            cat  = row["category"]
            icon = CATEGORIES.get(cat, {}).get("icon", "📦")
            col  = cols[list(cat_summary.index).index(i) % 3]
            count = len(debits[debits["category"] == cat])
            col.metric(f"{icon} {cat}", f"₹{row['amount']:,.0f}", f"{count} transactions")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    if df.empty:
        st.info("Load a statement first.")
    elif active_stmt_id:
        st.subheader("🤖 Claude's Spending Analysis")

        insight_text = get_insights(active_stmt_id)

        if insight_text:
            # Metrics row
            debits = df[df["type"]=="debit"]
            credits = df[df["type"]=="credit"]
            income = credits[credits["description"].str.contains(
                "salary|neft cr|credit", case=False, na=False)]["amount"].sum()
            spent  = debits["amount"].sum()
            saved  = income - spent

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total income",  f"₹{income:,.0f}")
            c2.metric("Total spent",   f"₹{spent:,.0f}")
            c3.metric("Net savings",   f"₹{saved:,.0f}",
                      delta=f"{saved/income*100:.1f}% savings rate" if income > 0 else None)
            c4.metric("Transactions",  len(debits))

            st.divider()
            st.markdown(
                f"<div style='background:var(--secondary-background-color);"
                f"border-radius:12px;padding:1.5rem 2rem;line-height:1.9;font-size:14px'>"
                f"{insight_text.replace(chr(10),'<br>')}</div>",
                unsafe_allow_html=True
            )

            st.download_button(
                "📥 Download insights report",
                data=insight_text,
                file_name="spending_insights.txt",
                mime="text/plain",
            )

        else:
            st.warning("No insights found. Try re-uploading the statement.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — MONTHLY VIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    if df.empty:
        st.info("Load a statement first.")
    else:
        debits = df[df["type"] == "debit"].copy()
        debits["month"] = pd.to_datetime(debits["date"], errors="coerce").dt.to_period("M").astype(str)

        monthly = debits.groupby(["month","category"])["amount"].sum().reset_index()

        if not monthly.empty:
            fig = px.bar(
                monthly, x="month", y="amount", color="category",
                color_discrete_map={k: v["color"] for k, v in CATEGORIES.items()},
                title="Monthly spending by category",
                labels={"amount":"Amount (₹)", "month":"Month"},
                text_auto=False,
            )
            fig.update_layout(
                barmode="stack", height=420,
                legend=dict(orientation="h", y=-0.2),
                margin=dict(l=10,r=10,t=40,b=10)
            )
            st.plotly_chart(fig, use_container_width=True)

            # Month-over-month total
            monthly_total = debits.groupby("month")["amount"].sum().reset_index()
            st.subheader("Month-over-month total")
            for _, row in monthly_total.iterrows():
                st.metric(row["month"], f"₹{row['amount']:,.0f}")
