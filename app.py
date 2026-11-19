from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine import (
    SimulationState,
    money_float,
    precalculus_foundation_metrics,
    run_monthly_step,
    to_money,
)

st.set_page_config(
    page_title="NUR-2 | Nurse-Led Health Education Simulation",
    layout="wide",
)

if "sim_state" not in st.session_state:
    st.session_state.sim_state = SimulationState()


def reset_state() -> None:
    st.session_state.sim_state = SimulationState()


state: SimulationState = st.session_state.sim_state

st.title("NUR-2: Nurse-Led Health Education Simulation")
st.caption(
    f"Course: {state.selected_course} | Pathway: {state.pathway_id} | "
    f"Approved Level: {state.selected_level} | Version: {state.state_version} | "
    f"Snapshot: {state.snapshot_id} | Fictional nonclinical educational simulation only"
)

if state.mode_used == "fixture":
    st.warning(
        "FIXTURE-TEST MODE ACTIVE: Capacity was overridden from monthly_fixture.csv to test ledger rules. "
        "Reset the simulation before running normal resource-derived rounds."
    )

# Persistent Math Skills & Challenge Level Panel (Overview requirement)
with st.expander(
    f"Math Skills & Challenge Level Panel — {state.selected_course} ({state.selected_level})",
    expanded=True,
):
    col_m1, col_m2 = st.columns([1.2, 1.8])
    with col_m1:
        selected_level = st.selectbox(
            "Challenge Level (Teacher-Approved)",
            ["Foundation", "Applied", "Advanced"],
            index=["Foundation", "Applied", "Advanced"].index(state.selected_level),
        )
        if selected_level != state.selected_level:
            state.selected_level = selected_level

        F_val = state.fixed_monthly_cost()
        v_val = state.variable_unit_cost()
        cap_val = state.derived_capacity()

        if state.selected_level == "Foundation":
            st.markdown("**Skill**: Rational Average Cost Function, Asymptotes, and Practical Domain")
            st.latex(
                rf"C(s) = {F_val:.0f} + {v_val:.0f}s, \qquad "
                rf"A(s) = \frac{{C(s)}}{{s}} = \frac{{{F_val:.0f}}}{{s}} + {v_val:.0f} \quad (0 < s \le {cap_val})"
            )
            st.markdown(
                f"- **Variables & Units**: $s$ = attended workshop seats/month; $C(s)$ = monthly total cost (USD); "
                f"$A(s)$ = average cost per attended seat (USD/seat).\n"
                f"- **Asymptotes**: Vertical asymptote at $s = 0$ ($A(0)$ is undefined); horizontal asymptote at $y = \${v_val:.2f}$/seat.\n"
                f"- **Practical Domain**: Integer seats $1 \le s \le {cap_val}$ under current educator hours and venue seats."
            )
            inspect_s = st.slider(
                "Inspect Seat Volume s (Predict A(s) before moving!)",
                min_value=0,
                max_value=max(80, cap_val + 20),
                value=cap_val,
            )
            metrics = precalculus_foundation_metrics(inspect_s, F_val, v_val, cap_val)
            a_disp = "Undefined" if metrics["average_cost"] is None else f"${metrics['average_cost']:.4f}/seat"
            st.info(
                f"**s = {inspect_s} seats** | Total Cost C({inspect_s}) = **${metrics['total_cost']:.2f}** | "
                f"Average Cost A({inspect_s}) = **{a_disp}** | Status: {metrics['domain_status']}"
            )
        elif state.selected_level == "Applied":
            st.markdown("**Skill (Preview)**: Function Composition $R(p) = p \cdot s(p)$ and $C(s(p))$")
            st.info(
                "Applied level unlocks piecewise demand composition q(p) = max(0, 2*D0 - (D0/p0)*p) capped at capacity. "
                "Requires teacher approval before switching from Foundation."
            )
        else:
            st.markdown("**Skill (Preview)**: Seasonal Trigonometric or Exponential Growth Extension")
            st.info(
                "Advanced level unlocks seasonal demand D(t) = D0*(1 + 0.20*sin(2*pi*(t-1)/12)) after trigonometry instruction. "
                "Requires teacher approval before switching from Foundation."
            )

    with col_m2:
        # Linked Average-Cost Graph & Table for Foundation
        s_grid = list(range(1, max(75, cap_val + 15) + 1))
        rows = []
        for s_pt in s_grid:
            m_pt = precalculus_foundation_metrics(s_pt, F_val, v_val, cap_val)
            rows.append(
                {
                    "Seats (s)": s_pt,
                    "Total Cost C(s) ($)": money_float(m_pt["total_cost"]),
                    "Average Cost A(s) ($/seat)": round(float(m_pt["average_cost"]), 4),
                    "Feasible": "Feasible (s <= cap)" if s_pt <= cap_val else "Infeasible (s > cap)",
                }
            )
        df_curve = pd.DataFrame(rows)

        fig = go.Figure()
        feasible_df = df_curve[df_curve["Seats (s)"] <= cap_val]
        infeasible_df = df_curve[df_curve["Seats (s)"] > cap_val]

        fig.add_trace(
            go.Scatter(
                x=feasible_df["Seats (s)"],
                y=feasible_df["Average Cost A(s) ($/seat)"],
                mode="lines+markers",
                name="A(s) Feasible Domain (0 < s <= cap)",
                line=dict(color="#1f77b4", width=3),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=infeasible_df["Seats (s)"],
                y=infeasible_df["Average Cost A(s) ($/seat)"],
                mode="lines",
                name="A(s) Above Capacity (Infeasible)",
                line=dict(color="#7f7f7f", width=2, dash="dash"),
            )
        )
        fig.add_hline(
            y=float(v_val),
            line_dash="dot",
            line_color="#2ca02c",
            annotation_text=f"Horizontal Asymptote y = ${v_val:.2f}/seat",
        )
        fig.add_vline(
            x=cap_val,
            line_dash="dash",
            line_color="#d62728",
            annotation_text=f"Capacity Cap s = {cap_val}",
        )
        fig.update_layout(
            title=f"NUR-2 Average Cost A(s) = {F_val:.0f}/s + {v_val:.0f} (Snapshot {state.snapshot_id}, {state.state_version})",
            xaxis_title="Attended Workshop Seats s (seats/month)",
            yaxis_title="Average Cost A(s) (USD/seat)",
            height=340,
            margin=dict(l=20, r=20, t=45, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

tab_overview, tab_inputs, tab_sim, tab_fixtures, tab_persistence = st.tabs(
    [
        "1. Overview & Balance Check",
        "2. Startup & Cost Inputs",
        "3. Run Monthly Step",
        "4. Fixture & Disruption Tests",
        "5. Save / Load & Exports",
    ]
)

with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spendable Cash", f"${state.current_cash:,.2f}")
    c2.metric("Derived Capacity", f"{state.derived_capacity()} seats/mo")
    c3.metric("Unit Variable Cost (v)", f"${state.variable_unit_cost():.2f}/seat")
    c4.metric("Monthly Fixed Cost (F)", f"${state.fixed_monthly_cost():.2f}/mo")

    st.subheader("Simplified Balance Sheet Check (Assets = Liabilities + Equity)")
    total_assets = state.current_cash + state.equipment_assets + state.opening_inventory
    total_liab_eq = state.debt_balance + state.owner_contribution + state.retained_earnings
    b1, b2, b3 = st.columns(3)
    b1.metric("Total Assets (Cash + Equipment)", f"${total_assets:,.2f}")
    b2.metric("Debt + Equity", f"${total_liab_eq:,.2f}")
    b3.metric("Reconciliation Diff", f"${(total_assets - total_liab_eq):,.2f}")

    st.subheader("Dated Event Ledger (Actual Simulated Transactions)")
    if state.ledger:
        st.dataframe(pd.DataFrame(state.ledger), use_container_width=True)
    else:
        st.info("No transactions recorded yet. Run a monthly step or replay monthly_fixture.csv.")

with tab_inputs:
    st.subheader("Editable Business Parameters & Cost Lines")
    with st.form("inputs_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            new_team_id = st.text_input("Team ID", value=state.team_id)
            new_price = st.number_input("Workshop Seat Price ($)", min_value=1.0, value=float(state.base_price), step=1.0)
            new_d0 = st.number_input("Baseline Monthly Demand D0 (seats)", min_value=0, value=int(state.d0), step=1)
            new_staff_hrs = st.number_input("Educator Staff Hours / Month", min_value=0.0, value=float(state.staff_hours), step=1.0)
            new_hrs_unit = st.number_input("Educator Hours / Seat", min_value=0.1, value=float(state.hours_per_unit), step=0.1)
            new_venue_seats = st.number_input("Venue Seats / Month", min_value=0, value=int(state.venue_seats), step=1)
            new_no_show = st.slider("No-Show Rate [0, 1]", min_value=0.0, max_value=1.0, value=float(state.no_show_rate), step=0.05)

        with col_b:
            v_edu = st.number_input("Variable: Educator Delivery ($/seat)", min_value=0.0, value=float(state.var_educator_delivery), step=0.5)
            v_mat = st.number_input("Variable: Materials ($/seat)", min_value=0.0, value=float(state.var_materials), step=0.5)
            v_cln = st.number_input("Variable: Cleaning Consumables ($/seat)", min_value=0.0, value=float(state.var_cleaning_consumables), step=0.5)
            f_ven = st.number_input("Fixed: Venue ($/mo)", min_value=0.0, value=float(state.fix_venue), step=10.0)
            f_sch = st.number_input("Fixed: Scheduling Software ($/mo)", min_value=0.0, value=float(state.fix_scheduling_software), step=10.0)
            f_acc = st.number_input("Fixed: Accessibility Support ($/mo)", min_value=0.0, value=float(state.fix_accessibility_support), step=10.0)
            f_adm = st.number_input("Fixed: Admin & Insurance ($/mo)", min_value=0.0, value=float(state.fix_admin_insurance), step=10.0)

        if st.form_submit_button("Save Input Parameters"):
            state.team_id = new_team_id.strip()
            state.base_price = to_money(new_price)
            state.d0 = int(new_d0)
            state.staff_hours = float(new_staff_hrs)
            state.hours_per_unit = float(new_hrs_unit)
            state.venue_seats = int(new_venue_seats)
            state.no_show_rate = float(new_no_show)
            state.var_educator_delivery = to_money(v_edu)
            state.var_materials = to_money(v_mat)
            state.var_cleaning_consumables = to_money(v_cln)
            state.fix_venue = to_money(f_ven)
            state.fix_scheduling_software = to_money(f_sch)
            state.fix_accessibility_support = to_money(f_acc)
            state.fix_admin_insurance = to_money(f_adm)
            state.validate()
            st.success(f"Parameters updated. Derived capacity = {state.derived_capacity()} seats/month.")
            st.rerun()

with tab_sim:
    st.subheader("Execute One Monthly Simulation Step (Normal Mode)")
    with st.form("run_step_form"):
        s1, s2, s3 = st.columns(3)
        with s1:
            run_id = st.text_input("Unique Run ID", value=f"RUN-{len(state.processed_run_ids)+1:03d}")
            period_date = st.text_input("Period End Date (YYYY-MM-DD)", value="2027-01-31")
            req_units = st.number_input("Requested Workshop Seats", min_value=0, value=state.d0, step=1)
        with s2:
            ad_spend = st.number_input("Approved Own-Business Marketing ($)", min_value=0.0, value=0.0, step=10.0)
            loan_in = st.number_input("New Simulated Loan Proceeds ($)", min_value=0.0, value=0.0, step=100.0)
            loan_prin = st.number_input("Loan Principal Repayment ($)", min_value=0.0, value=0.0, step=50.0)
        with s3:
            int_exp = st.number_input("Loan Interest Expense ($)", min_value=0.0, value=0.0, step=10.0)
            capex_out = st.number_input("Equipment CapEx Outflow ($)", min_value=0.0, value=0.0, step=50.0)
            refund_out = st.number_input("Customer Refunds ($)", min_value=0.0, value=0.0, step=25.0)

        if st.form_submit_button("Approve & Advance Simulation Once"):
            try:
                updated, rec, executed = run_monthly_step(
                    state,
                    run_id=run_id.strip(),
                    period_date=period_date.strip(),
                    requested=int(req_units),
                    ad_cost=to_money(ad_spend),
                    loan_cash=to_money(loan_in),
                    loan_principal=to_money(loan_prin),
                    interest=to_money(int_exp),
                    additional_capex=to_money(capex_out),
                    refund_amount=to_money(refund_out),
                )
                if not executed:
                    st.warning(f"Duplicate run_id '{run_id}' blocked. No new transaction created.")
                else:
                    st.session_state.sim_state = updated
                    st.success(
                        f"Step recorded ({rec['transaction_id']}): Sold {rec['sold']} seats, "
                        f"Revenue ${rec['revenue']}, Profit ${rec['net_profit']}, Closing Cash ${rec['closing_cash']}."
                    )
                    st.rerun()
            except ValueError as exc:
                st.error(str(exc))

with tab_fixtures:
    st.subheader("Handbook Acceptance & Fixture Verification")
    c_fix1, c_fix2 = st.columns(2)
    with c_fix1:
        st.markdown("**1. Replay `sample_data/monthly_fixture.csv`** (Resets to opening state first)")
        if st.button("Reset & Replay NUR-2 Monthly Fixture"):
            fixture_path = Path("sample_data/monthly_fixture.csv")
            if fixture_path.exists():
                df_fix = pd.read_csv(fixture_path)
            else:
                df_fix = pd.DataFrame(
                    [
                        {"month": "2027-01", "requested": 80, "capacity_override": 60, "ad_cost": 0},
                        {"month": "2027-02", "requested": 88, "capacity_override": 60, "ad_cost": 100},
                        {"month": "2027-03", "requested": 72, "capacity_override": 45, "ad_cost": 0},
                    ]
                )
            sim = SimulationState(team_id=state.team_id, selected_level=state.selected_level)
            for idx, row in df_fix.iterrows():
                sim, _, _ = run_monthly_step(
                    sim,
                    run_id=f"FIX-{row['month']}",
                    period_date=f"{row['month']}-28",
                    requested=int(row["requested"]),
                    capacity_override=int(row["capacity_override"]),
                    ad_cost=to_money(row["ad_cost"]),
                )
            st.session_state.sim_state = sim
            st.success("Replayed all 3 fixture rows from post-startup cash ($4,000).")
            st.rerun()

    with c_fix2:
        st.markdown("**2. Business-Specific Test (`no_show_rate = 0.20`)**")
        if st.button("Reset & Run No-Show Rate = 0.20 Test"):
            sim = SimulationState(
                team_id=state.team_id,
                selected_level=state.selected_level,
                no_show_rate=0.20,
            )
            sim, rec, _ = run_monthly_step(
                sim,
                run_id="TEST-NOSHOW-20",
                period_date="2027-01-31",
                requested=80,
            )
            st.session_state.sim_state = sim
            st.success(
                f"Booked={rec['booked']}, Attended={rec['attended']}, "
                f"Revenue=${rec['revenue']}, Variable=${rec['variable_expense']}, Profit=${rec['net_profit']}."
            )
            st.rerun()

    if st.button("Reset Simulation to Post-Startup Opening State ($4,000 Cash)"):
        reset_state()
        st.rerun()

with tab_persistence:
    st.subheader("Durable Save / Restore JSON & CSV Export")
    st.download_button(
        label="Download Snapshot JSON (Durable State)",
        data=state.to_json(),
        file_name=f"{state.team_id}_{state.pathway_id}_{state.state_version}_{state.snapshot_id}.json",
        mime="application/json",
    )
    if state.ledger:
        csv_data = pd.DataFrame(state.ledger).to_csv(index=False)
        st.download_button(
            label="Download Ledger CSV",
            data=csv_data,
            file_name=f"{state.team_id}_{state.pathway_id}_ledger.csv",
            mime="text/csv",
        )

    uploaded = st.file_uploader("Restore Saved Snapshot JSON", type=["json"])
    if uploaded is not None:
        try:
            restored = SimulationState.from_json(
                uploaded.read().decode("utf-8"),
                expected_team_id=state.team_id,
                expected_version=state.state_version,
            )
            st.session_state.sim_state = restored
            st.success(f"Snapshot {restored.snapshot_id} restored and validated.")
            st.rerun()
        except ValueError as exc:
            st.error(f"Import rejected: {exc}")
