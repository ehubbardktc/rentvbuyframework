import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.express as px

import plotly.io as pio

# Consistent, clean default theme for all charts
pio.templates.default = "plotly_white"
try:
    px.defaults.color_discrete_sequence = ["#4C78A8","#B279A2","#9C755F","#F2CF5B","#8E6C8A","#7F7F7F","#A0A0A0"]
except Exception:
    pass

import uuid

# ---- Sampling helpers for stochastic sections (used in Sections 4–5) ----
def sample_t_returns(n, mean_pct, std_pct, df, rng):
    """Sample Student-t annual returns scaled to target mean/std (percent inputs)."""
    mean = mean_pct / 100.0
    std = std_pct / 100.0
    # standard t has Var = df/(df-2) for df>2; scale to unit variance, then to target std.
    t = rng.standard_t(df, size=n)
    t_unit = t * ((df-2)/df) ** 0.5
    return mean + std * t_unit

def sample_lognormal_returns(n, mean_pct, std_pct, rng):
    """Sample lognormal annual returns, fitted from arithmetic mean/std (percent inputs)."""
    m = 1.0 + mean_pct/100.0
    s = std_pct/100.0
    sigma2 = np.log(1 + (s*s)/(m*m))
    sigma = sigma2 ** 0.5
    mu = np.log(m) - 0.5*sigma2
    gross = rng.lognormal(mean=mu, sigma=sigma, size=n)
    return gross - 1.0

# Global default values (no presets)
BASE_DEFAULTS = {
    "purchase_price": 500_000,
    "down_payment": 100_000,
    "closing_costs": 5000,
    "loan_years": 30,
    "mortgage_rate": 5.0,
    "pmi_rate": 0.20,
    "pmi_equity_threshold": 20,
    "property_taxes": 8000,
    "home_insurance": 1100,
    "maintenance": 6000,
    "hoa_fees": 1200,
    "cost_of_rent": 3000,
    "renters_insurance": 300,
    "security_deposit": 3000,
    "rental_utilities": 2400,
    "pet_fee": 500,
    "application_fee": 50,
    "lease_renewal_fee": 100,
    "parking_fee": 50,
    "vti_annual_return": 7.0,
    "annual_appreciation": 3.0,
    "annual_maintenance_increase": 3.0,
    "annual_insurance_increase": 3.0,
    "annual_hoa_increase": 3.0,
    "annual_rent_increase": 3.0,
}

# --- Load shareable scenario from URL query params (optional) ---
_qp = st.experimental_get_query_params()
def _qp_float(k, default=None):
    try:
        return float(_qp.get(k, [default])[0]) if _qp.get(k) else default
    except Exception:
        return default
def _qp_int(k, default=None):
    try:
        return int(float(_qp.get(k, [default])[0])) if _qp.get(k) else default
    except Exception:
        return default

# Supported keys: pp (price), dp (down), rate, term, rent, appr, invest, start, end
_qp_overrides = {
    "purchase_price": _qp_float("pp"),
    "down_payment": _qp_float("dp"),
    "mortgage_rate": _qp_float("rate"),
    "loan_years": _qp_int("term"),
    "cost_of_rent": _qp_float("rent"),
    "annual_appreciation": _qp_float("appr"),
    "vti_annual_return": _qp_float("invest"),
}
_eval_start_qp = _qp_int("start")
_eval_end_qp = _qp_int("end")

for _k, _v in _qp_overrides.items():
    if _v is not None:
        st.session_state[_k] = _v

# Custom CSS for styling
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        font-size: 14px !important;
    }
    .dataframe td, .dataframe th {
        font-size: 12px !important;
    }
    .st-container {
        padding: 10px;
        border-radius: 5px;
    }
    .stSlider > div > div > div > div {
        background-color: #e6f3ff;
        border-radius: 5px;
        padding: 10px;
    }
    .st-expander {
        background-color: #f5f5f5;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .highlight-box {
        background-color: #e6f3ff;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #d3e3ff;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
  :root {
    --bg: #ffffff;
    --panel: #f8fafc;
    --accent: #2563eb;
    --muted: #94a3b8;
    --ring: #dbeafe;
    --radius: 12px;
  }
  .stApp {
    background: var(--bg);
  }
  section.main > div {padding-top: 8px;}
  div[data-testid="stMetricValue"] { font-weight: 400; }
  div[data-testid="metric-container"] {
    padding: 8px 10px;
    border: 1px solid #e2e8f0;
    border-radius: var(--radius);
    background: var(--panel);
  }
  .dataframe td, .dataframe th { font-size: 12.5px !important; }
  .stTabs [data-baseweb="tab"] { font-weight: 600; }
  .highlight-box {
    background: #f1f5ff;
    border: 1px solid var(--ring);
    border-radius: var(--radius);
  }
  .st-expander {
    border: 1px solid #e5e7eb;
    border-radius: var(--radius);
    background: #fbfbfd;
  }
</style>
""", unsafe_allow_html=True)

def section_header(title: str, subtitle: str | None = None):
    st.markdown(f"<div style='display:flex;align-items:baseline;gap:.5rem'><h2 style='margin:0'>{title}</h2>" +
                (f"<span style='color:#64748b'>{subtitle}</span>" if subtitle else "") +
                "</div>", unsafe_allow_html=True)

def thick_divider():
    st.markdown(
        """<hr style="height:4px;border:none;color:#333;background-color:#333;" />""",
        unsafe_allow_html=True
    )

# Page Config
st.set_page_config(page_title="Rent vs. Buy Decision Support Framework", layout="wide")
st.title("Rent vs. Buy Decision Support Framework")

# Instructions
with st.expander("Welcome & Instructions", expanded=True):
    st.markdown("""
    ### BLUF — Bottom Line Up Front
    This Rent vs Buy Decision Support Framework helps you compare long-term financial outcomes
    from buying a home versus continuing to rent. It produces deterministic metrics (Sections 1–3)
    and probabilistic analysis that accounts for uncertainty (Sections 4–5).
    The core calculation framework is consistent across both views — the difference is whether selected variables
    are modeled as fixed values (deterministic) or as distributions (probabilistic).

    ### What you’ll learn / do (BLUF)
    - Compare one-time and ongoing costs for buying vs renting and see year-by-year breakdowns.
    - Explore mortgage amortization, extra payments, and refinance impacts on interest and payoff timelines.
    - Project asset and net asset evolution under different assumptions.
    - Run Monte Carlo simulations (Section 5) to quantify the impact of uncertain variables on outcomes.

    ### Section breakdown
    - **Section 1 — Inputs (Deterministic):** Enter purchase, loan, refinance, homeownership and rental parameters. These feed the deterministic calculations.
    - **Section 2 — Mortgage Metrics (Deterministic):** Payment schedule, PMI, total interest, payoff dates and refinance comparisons.
    - **Section 3 — Cost & Asset Results (Deterministic):** Year-by-year cost breakdowns, net asset calculation and core visualizations.
    - **Section 4 — Distributions (Probabilistic):** Inspect distributions for selected uncertain variables and quick histograms/percentiles.
    - **Section 5 — Monte Carlo Simulation (Probabilistic):** Run many trials (default 500) to see ranges, confidence intervals and breakeven likelihoods.

    ### Variables that commonly include uncertainty (examples)
    - Housing appreciation (`annual_appreciation`)
    - Rent growth (`annual_rent_increase`)
    - Investment returns (`vti_annual_return`)
    - Maintenance, insurance and HOA inflation (`annual_maintenance_increase`, `annual_insurance_increase`, `annual_hoa_increase`)
    - Future mortgage/refinance rates for variable-rate or future refis (`mortgage_rate`, `refi_rate`)

    **Important:** Sections 1–3 use the same calculation framework as Sections 4–5. The probabilistic sections draw scenarios by varying the variables above while keeping formulas identical.

    ### Quick tips
    - Use the **Run Monte Carlo with updated parameters** button in Section 5 to re-run simulations after changing inputs (prevents constant auto-runs).
    - The **Evaluation Period** controls the horizon for all charts and projections — it affects payoff timelines, cumulative costs and net asset charts.
    - Colors and layout follow a consistent style (no red/green semantics). Look for the standardized color palette across charts.
    """)

# Inputs
st.header("1. Inputs")
st.markdown("Configure the parameters below to compare renting vs. buying. All fields are required unless marked optional. Adjust parameters below to compare renting vs. buying.")
# Ensure property tax growth default
if 'annual_property_tax_increase' not in st.session_state:
    st.session_state['annual_property_tax_increase'] = 3.0
# Initialize session state for inputs
for key, value in BASE_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Buying Parameters
st.subheader("Buying Parameters")
with st.container(border=True):
    st.markdown("### Purchase and Loan Details")
    col1, col2 = st.columns(2)
    with col1:
        purchase_year = st.number_input("Purchase Year", value=2025, step=1, min_value=2000, max_value=2100, help="Year you plan to purchase the home.")
        purchase_price = st.number_input("Purchase Price ($)", value=float(st.session_state["purchase_price"]), step=10_000.0, min_value=0.0, help="Total cost of the home.")
        down_payment = st.number_input("Down Payment ($)", value=float(st.session_state["down_payment"]), step=1_000.0, min_value=0.0, max_value=purchase_price, help="Initial payment toward purchase price.")
        if down_payment > purchase_price:
            st.warning("Down payment cannot exceed purchase price.")
        percent_down = (down_payment / purchase_price * 100) if purchase_price > 0 else 0
        st.metric("Down Payment Percentage", f"{percent_down:.2f}%")
        closing_costs = st.number_input("Closing Costs ($)", value=float(st.session_state["closing_costs"]), step=500.0, min_value=0.0, help="One-time costs at purchase (e.g., fees, title).")
        closing_costs_method = st.selectbox("Closing Costs Method", ["Add to Loan Balance", "Pay Upfront"], index=0, help="Finance closing costs or pay upfront.")
        loan_amount = purchase_price - down_payment + (closing_costs if closing_costs_method == "Add to Loan Balance" else 0)

    with col2:
        loan_years = st.number_input("Loan Length (Years)", value=st.session_state["loan_years"], step=1, min_value=1, max_value=50, help="Duration of the mortgage.")
        mortgage_rate = st.number_input("Mortgage Rate (%)", value=st.session_state["mortgage_rate"], step=0.01, min_value=0.0, format="%.3f", help="Annual interest rate for the mortgage.")
        pmi_rate = st.number_input("PMI Rate (%)", value=st.session_state["pmi_rate"], step=0.01, min_value=0.0, help="Private Mortgage Insurance rate, applied if equity < threshold.")
        pmi_equity_threshold = st.number_input("PMI Paid Until Equity (%)", value=st.session_state["pmi_equity_threshold"], step=1, min_value=0, max_value=100, help="Equity percentage at which PMI stops.")
        payment_frequency = st.selectbox("Payment Frequency", ["Monthly", "Biweekly"], index=0, help="Monthly (12/year) or biweekly (26/year) payments.")
        mortgage_type = st.selectbox("Mortgage Type", ["Fixed", "Variable"], index=0, help="Fixed or variable rate mortgage.")

        buy_points = st.checkbox("Buy Points to Reduce Rate?", value=False, help="Pay points to lower mortgage rate.")
        points = 0
        discount_per_point = 0.25
        points_cost_method = "Add to Loan Balance"
        points_cost = 0
        effective_rate = mortgage_rate
        if buy_points:
            points = st.number_input("Number of Points", value=1.0, step=0.25, min_value=0.0, help="Points purchased (1 point = 1% of loan amount).")
            discount_per_point = st.number_input("Rate Discount per Point (%)", value=0.25, step=0.01, min_value=0.0, help="Rate reduction per point purchased.")
            points_cost_method = st.selectbox("Points Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0, help="Finance or pay points upfront.")
            effective_rate = mortgage_rate - (discount_per_point * points)
            points_cost = points * (purchase_price - down_payment) * 0.01
            st.metric("Effective Rate After Points", f"{effective_rate:.3f}%")
            st.metric("Points Cost", f"${points_cost:,.0f}")

    # Now calculate loan amount display (after points vars exist)
    display_loan_amount = loan_amount + (points_cost if (buy_points and points_cost_method == "Add to Loan Balance") else 0)
    st.metric("Calculated Loan Amount", f"${display_loan_amount:,.0f}", help="Includes financed closing costs and financed points when applicable.")

    if mortgage_type == "Variable":
        st.markdown("### Variable Rate Schedule")
        default_schedule = pd.DataFrame({"Year": [1, 5, 10], "Rate (%)": [mortgage_rate, mortgage_rate + 1.5, mortgage_rate + 2.0]})
        rate_schedule = st.data_editor(
            default_schedule,
            column_config={
                "Year": st.column_config.NumberColumn("Year", min_value=1, max_value=loan_years, step=1, help="Year the rate applies."),
                "Rate (%)": st.column_config.NumberColumn("Rate (%)", min_value=0.0, step=0.1, help="Mortgage rate for the specified year.")
            },
            hide_index=True,
            num_rows="dynamic"
        )
    else:
        rate_schedule = pd.DataFrame({"Year": [1], "Rate (%)": [mortgage_rate]})

    # Inside the "Advanced Options" section, replace the Extra Principal Payments part
    st.markdown("### Extra Principal Payments")
    st.markdown("Add extra payments to reduce your mortgage principal faster. Ensure all required fields are filled to avoid errors.")
    default_payments = pd.DataFrame({
        "Amount ($)": [200, 10000],
        "Frequency": ["Monthly", "One-time"],
        "Start Year": [purchase_year, purchase_year + 5],
        "Start Month": [1, 6],
        "End Year": [purchase_year + 5, purchase_year + 5],
        "End Month": [12, 6],
        "Interval (Years)": [None, None]
    })
    extra_payments = st.data_editor(
        default_payments,
        column_config={
            "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100, help="Amount of extra payment.", required=True),
            "Frequency": st.column_config.SelectboxColumn("Frequency", options=["One-time", "Monthly", "Quarterly", "Annually", "Every X Years"], help="How often the payment is made.", required=True),
            "Start Year": st.column_config.NumberColumn("Start Year", min_value=purchase_year, max_value=purchase_year + loan_years, step=1, help="Year payments start.", required=True),
            "Start Month": st.column_config.NumberColumn("Start Month", min_value=1, max_value=12, step=1, help="Month payments start.", required=True),
            "End Year": st.column_config.NumberColumn("End Year", min_value=purchase_year, max_value=purchase_year + loan_years, step=1, help="Year payments end.", required=True),
            "End Month": st.column_config.NumberColumn("End Month", min_value=1, max_value=12, step=1, help="Month payments end.", required=True),
            "Interval (Years)": st.column_config.NumberColumn("Interval (Years)", min_value=1, step=1, help="Interval for 'Every X Years' payments (optional).")
        },
        hide_index=True,
        num_rows="dynamic"
    )

# Validate extra_payments DataFrame
required_columns = ["Amount ($)", "Frequency", "Start Year", "Start Month", "End Year", "End Month"]
invalid_rows = extra_payments[required_columns].isna().any(axis=1)
if invalid_rows.any():
    st.warning("Some extra payment rows have missing values in required fields (Amount, Frequency, Start/End Year/Month). These rows will be ignored.")
    extra_payments = extra_payments[~invalid_rows].copy()

# Additional validation for Interval (Years)
if "Interval (Years)" in extra_payments.columns:
    extra_payments.loc[
        (extra_payments["Frequency"] != "Every X Years") | extra_payments["Interval (Years)"].isna(),
        "Interval (Years)"
    ] = None


# Advanced Homeownership Options
st.subheader("Advanced Homeownership Options")
with st.expander("Refinance", expanded=False):
    st.markdown("### Refinance Options")
    show_refinance = st.checkbox("Model a Refinance?", value=False, help="Include a refinance scenario in calculations.")
    refi_rate = None
    refi_term_years = None
    refi_start_date = None
    refi_costs = None
    roll_costs = None
    refi_payment_frequency = None
    refi_mortgage_type = None
    refi_rate_schedule = None
    refi_periods_per_year = None
    refi_buy_points = False
    refi_points = 0
    refi_discount_per_point = 0.25
    refi_points_cost_method = "Add to Loan Balance"
    refi_points_cost = 0
    refi_effective_rate = None

    if show_refinance:
        col1, col2 = st.columns(2)
        with col1:
            refi_rate = st.number_input("Refinance Rate (%)", value=4.0, step=0.01, min_value=0.0, format="%.3f", help="Interest rate for refinanced loan.")
            refi_term_years = st.number_input("Refinance Term (Years)", value=20, step=1, min_value=1, max_value=50, help="Duration of refinanced loan.")
            refi_start_date = st.date_input("Refinance Start Date", min_value=datetime(purchase_year, 1, 1), max_value=datetime(purchase_year + loan_years, 12, 31), help="Date refinance begins.")
        with col2:
            refi_costs = st.number_input("Refinance Closing Costs ($)", value=3000.0, step=500.0, min_value=0.0, help="One-time costs for refinancing.")
            roll_costs = st.selectbox("Refinance Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0, help="Finance or pay refinance costs upfront.")
            refi_payment_frequency = st.selectbox("Refinance Payment Frequency", ["Monthly", "Biweekly"], index=0, help="Payment frequency for refinanced loan.")
            refi_mortgage_type = st.selectbox("Refinance Mortgage Type", ["Fixed", "Variable"], index=0, help="Fixed or variable rate for refinanced loan.")
            refi_periods_per_year = 12 if refi_payment_frequency == "Monthly" else 26
            refi_effective_rate = refi_rate

        refi_buy_points = st.checkbox("Buy Points for Refinance?", value=False, help="Pay points to lower refinance rate.")
        if refi_buy_points:
            col1, col2 = st.columns(2)
            with col1:
                refi_points = st.number_input("Refinance Points", value=1.0, step=0.25, min_value=0.0, help="Points purchased for refinance.")
                refi_discount_per_point = st.number_input("Refinance Rate Discount per Point (%)", value=0.25, step=0.01, min_value=0.0, help="Rate reduction per refinance point.")
            with col2:
                refi_points_cost_method = st.selectbox("Refinance Points Cost Method", ["Add to Loan Balance", "Pay Upfront"], index=0, help="Finance or pay refinance points upfront.")
                refi_effective_rate = refi_rate - (refi_discount_per_point * refi_points)
                refi_points_cost = refi_points * (purchase_price - down_payment) * 0.01
                st.metric("Refinance Effective Rate", f"{refi_effective_rate:.3f}%")
                st.metric("Refinance Points Cost", f"${refi_points_cost:,.0f}")

        if refi_mortgage_type == "Variable":
            st.markdown("### Refinance Variable Rate Schedule")
            default_refi_schedule = pd.DataFrame({"Year": [1, 5, 10], "Rate (%)": [refi_effective_rate, refi_effective_rate + 1.5, refi_effective_rate + 2.0]})
            refi_rate_schedule = st.data_editor(
                default_refi_schedule,
                column_config={
                    "Year": st.column_config.NumberColumn("Year", min_value=1.0, max_value=refi_term_years, step=1.0, help="Year the refinance rate applies."),
                    "Rate (%)": st.column_config.NumberColumn("Rate (%)", min_value=0.0, step=0.1, help="Refinance rate for the specified year.")
                },
                hide_index=True,
                num_rows="dynamic"
            )
        else:
            refi_rate_schedule = pd.DataFrame({"Year": [1], "Rate (%)": [refi_effective_rate]})

# Expense Info Label
st.subheader("Homeownership Costs")
st.markdown('<div class="highlight-box">Recurring Costs: Property taxes, insurance, maintenance, HOA. These grow annually based on your inputs.</div>', unsafe_allow_html=True)
st.markdown("")
st.markdown('<div class="highlight-box">One-Time Costs: Closing costs, points (if paid upfront), emergency repairs in the specified year.</div>', unsafe_allow_html=True)

# Ongoing Expenses
st.subheader("Homeownership Expenses")
with st.expander("Homeownership Expenses (click to expand)", expanded=False):
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Recurring Expenses**")
            st.markdown("Enter annual recurring expenses for homeownership.")
            default_property_expenses = pd.DataFrame({
                "Category": ["Property Taxes", "Home Insurance", "Routine Maintenance", "HOA Fees"],
                "Amount ($)": [st.session_state["property_taxes"], st.session_state["home_insurance"], st.session_state["maintenance"], st.session_state["hoa_fees"]]
            })
            edited_property_expenses = st.data_editor(
                default_property_expenses,
                column_config={
                    "Category": st.column_config.TextColumn("Category", help="Type of recurring expense."),
                    "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100, help="Annual cost in dollars.")
                },
                hide_index=True,
                num_rows="dynamic"
            )

        with col2:
            st.markdown("**One-Time Expenses**")
            st.markdown("Enter one-time emergency repair costs.")
            default_emergency_expenses = pd.DataFrame({
                "Category": ["Appliance Replacement", "Septic Repair", "Roof Repair"],
                "Amount ($)": [1500, 8000, 12000],
                "Year": [purchase_year + 1, purchase_year + 5, purchase_year + 10],
                "Month": [5, 7, 9]
            })
            edited_emergency_expenses = st.data_editor(
                default_emergency_expenses,
                column_config={
                    "Category": st.column_config.TextColumn("Category", help="Type of emergency repair."),
                    "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100, help="Cost of the repair."),
                    "Year": st.column_config.NumberColumn("Year", min_value=purchase_year, max_value=purchase_year + loan_years, step=1, help="Year of the repair."),
                    "Month": st.column_config.NumberColumn("Month", min_value=1, max_value=12, step=1, help="Month of the repair.")
                },
                hide_index=True,
                num_rows="dynamic"
            )

st.markdown("### Appreciation and Growth Rates")
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        annual_appreciation = st.number_input("Annual Housing Appreciation (%)", value=st.session_state["annual_appreciation"], step=0.1, min_value=0.0, help="Expected annual increase in home value.")
        annual_maintenance_increase = st.number_input("Annual Maintenance Increase (%)", value=st.session_state["annual_maintenance_increase"], step=0.1, min_value=0.0, help="Annual increase in maintenance costs.")
        annual_property_tax_increase = st.number_input("Annual Property Tax Increase (%)",value=3.0, step=0.1, min_value=0.0,help="Annual increase in property tax costs.")
    with col2:
        annual_insurance_increase = st.number_input("Annual Insurance Increase (%)", value=st.session_state["annual_insurance_increase"], step=0.1, min_value=0.0, help="Annual increase in home insurance costs.")
        annual_hoa_increase = st.number_input("Annual HOA Increase (%)", value=st.session_state["annual_hoa_increase"], step=0.1, min_value=0.0, help="Annual increase in HOA fees.")

# Rental Parameters
st.subheader("Rental Parameters")
st.markdown("**Clear separation from Buying parameters** — inputs below apply to renting only.")
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Recurring (Monthly/Annual)")
        cost_of_rent = st.number_input(f"Initial Monthly Rent ({purchase_year}) ($)", value=float(st.session_state["cost_of_rent"]), step=50.0, min_value=0.0, help="Monthly rent excluding utilities and fees.")
        annual_rent_increase = st.number_input("Annual Rent Increase (%)", value=st.session_state["annual_rent_increase"], step=0.1, min_value=0.0, help="Expected annual increase in rent.")
        renters_insurance = st.number_input("Annual Renters' Insurance ($)", value=float(st.session_state["renters_insurance"]), step=50.0, min_value=0.0, help="Yearly cost of renters' insurance.")
        security_deposit = st.number_input("Security Deposit ($)", value=float(st.session_state["security_deposit"]), step=100.0, min_value=0.0, help="One-time deposit, invested as opportunity cost.")
    with col2:
        st.markdown("#### One-time / Per-lease")
        rental_utilities = st.number_input("Annual Rental Utilities ($)", value=float(st.session_state["rental_utilities"]), step=100.0, min_value=0.0, help="Yearly utility costs for renting.")
        pet_fee = st.number_input("Pet Fee/Deposit ($)", value=float(st.session_state["pet_fee"]), step=50.0, min_value=0.0, help="One-time or annual pet fee, depending on frequency.")
        pet_fee_frequency = st.selectbox("Pet Fee Frequency", ["One-time", "Annual"], index=0, help="Whether pet fee is one-time or annual.")
        application_fee = st.number_input("Application Fee ($)", value=float(st.session_state["application_fee"]), step=10.0, min_value=0.0, help="One-time fee per lease application.")
        lease_renewal_fee = st.number_input("Annual Lease Renewal Fee ($)", value=float(st.session_state["lease_renewal_fee"]), step=50.0, min_value=0.0, help="Annual fee for renewing lease.")
        parking_fee = st.number_input("Monthly Parking Fee ($)", value=float(st.session_state["parking_fee"]), step=10.0, min_value=0.0, help="Monthly parking cost.")

# Investment and Evaluation Period
st.subheader("Investment and Analysis Period")
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Investment Returns")
        vti_annual_return = st.number_input("Annual Personal Brokerage Account Return (%)", value=st.session_state["vti_annual_return"], step=0.1, min_value=0.0, help="Expected annual return on investments (e.g., Personal Brokerage Account).")
    with col2:
        st.markdown("### Evaluation Period")
        st.caption("This sets the analysis horizon used across all tables and charts, including amortization, costs, assets, and net assets.")
        eval_start_year = st.number_input("Evaluation Start Year", value=2025, step=1, min_value=2000, max_value=2100, help="Start year for analysis.")
        eval_end_year = st.number_input("Evaluation End Year", value=2070, step=1, min_value=eval_start_year, max_value=2100, help="End year for analysis.")
        if eval_end_year < eval_start_year:
            st.warning("End year must be greater than or equal to start year.")


# --- Share scenario (build URL query string for current key inputs) ---
with st.container(border=True):
    st.markdown("#### Share this Scenario")
    _q = {
        "pp": purchase_price,
        "dp": down_payment,
        "rate": mortgage_rate,
        "term": loan_years,
        "rent": cost_of_rent,
        "appr": annual_appreciation,
        "invest": vti_annual_return,
        "start": eval_start_year,
        "end": eval_end_year,
    }
    _qs = "&".join([f"{k}={v}" for k,v in _q.items()])
    st.code(f"?{_qs}", language="text")
    if st.button("Copy params to URL (set query params)"):
        st.experimental_set_query_params(**{k:[str(v)] for k,v in _q.items()})
        st.success("Query params set. Use your browser URL bar to copy the link.")

# Functions
@st.cache_data
def expand_extra_payments(df, start_year, loan_years, frequency):
    extra_schedule = {}
    start_date = datetime(start_year, 1, 1)
    periods_per_year = 12 if frequency == "Monthly" else 26
    n_payments = loan_years * periods_per_year
    delta = pd.DateOffset(months=1) if frequency == "Monthly" else timedelta(days=14)
    payment_dates = [start_date + i * delta for i in range(n_payments)]

    # Filter out rows with any NaN in required columns
    required_columns = ["Amount ($)", "Frequency", "Start Year", "Start Month", "End Year", "End Month"]
    df = df.dropna(subset=required_columns, how="any").copy()

    for _, row in df.iterrows():
        try:
            amt = float(row["Amount ($)"])
            freq = row["Frequency"]
            start_y = int(row["Start Year"])
            start_m = int(row["Start Month"])
            end_y = int(row["End Year"])
            end_m = int(row["End Month"])
            interval = int(row["Interval (Years)"]) if not pd.isna(row["Interval (Years)"]) and freq == "Every X Years" else 1

            # Validate inputs
            if amt <= 0 or start_y < start_year or start_y > start_year + loan_years or start_m < 1 or start_m > 12 or end_y < start_y or end_y > start_year + loan_years or end_m < 1 or end_m > 12:
                continue  # Skip invalid rows

            extra_dates = []
            if freq == "One-time":
                extra_dates.append(datetime(start_y, start_m, 1))
            else:
                current = datetime(start_y, start_m, 1)
                end = datetime(end_y, end_m, 28)
                while current <= end:
                    extra_dates.append(current)
                    if freq == "Monthly":
                        current += pd.DateOffset(months=1)
                    elif freq == "Quarterly":
                        current += pd.DateOffset(months=3)
                    elif freq == "Annually":
                        current += pd.DateOffset(years=1)
                    elif freq == "Every X Years":
                        current += pd.DateOffset(years=interval)

            for apply_date in extra_dates:
                matching_dates = [pdate for pdate in payment_dates if pdate.year == apply_date.year and pdate.month == apply_date.month]
                if matching_dates:
                    if freq == "Monthly" and frequency == "Biweekly" and len(matching_dates) > 1:
                        split_amt = amt / len(matching_dates)
                        for pdate in matching_dates:
                            extra_schedule[pdate] = extra_schedule.get(pdate, 0) + split_amt
                    else:
                        apply_pdate = min(matching_dates, key=lambda x: abs((x - apply_date).days))
                        extra_schedule[apply_pdate] = extra_schedule.get(apply_pdate, 0) + amt
        except (ValueError, TypeError):
            continue  # Skip rows with invalid data (e.g., non-numeric values)

    return extra_schedule

@st.cache_data
def amortization_schedule(
    principal,
    years,
    periods_per_year=12,
    start_date="2025-01-01",
    extra_schedule=None,
    rate_schedule=None,
    mortgage_type="Fixed",
    purchase_year=2025,
    mortgage_rate=5.0,
    pmi_rate=0.0,
    pmi_equity_threshold=20.0,
    purchase_price=500_000,
    refi_start_date=None,
    refi_principal=None,
    refi_years=None,
    refi_periods_per_year=None,
    refi_rate_schedule=None,
    refi_mortgage_type="Fixed",
    refi_mortgage_rate=None
):
    balance = principal
    start_date = pd.to_datetime(start_date)
    refi_start_date = pd.to_datetime(refi_start_date) if refi_start_date else None
    extra_schedule = extra_schedule or {}
    schedule = []

    if mortgage_type == "Fixed":
        rate_schedule = pd.DataFrame({"Year": [1], "Rate (%)": [mortgage_rate]})
    elif rate_schedule is None or rate_schedule.empty:
        rate_schedule = pd.DataFrame({"Year": [1], "Rate (%)": [mortgage_rate]})
    else:
        if not any(rate_schedule["Year"] == 1):
            rate_schedule = pd.concat([
                pd.DataFrame({"Year": [1], "Rate (%)": [mortgage_rate]}),
                rate_schedule
            ]).sort_values("Year").reset_index(drop=True)

    if refi_mortgage_type == "Fixed" and refi_mortgage_rate is not None:
        refi_rate_schedule = pd.DataFrame({"Year": [1], "Rate (%)": [refi_mortgage_rate]})
    elif refi_rate_schedule is None or refi_rate_schedule.empty:
        refi_rate_schedule = pd.DataFrame({"Year": [1], "Rate (%)": [refi_mortgage_rate]}) if refi_mortgage_rate else rate_schedule
    else:
        if not any(refi_rate_schedule["Year"] == 1):
            refi_rate_schedule = pd.concat([
                pd.DataFrame({"Year": [1], "Rate (%)": [refi_mortgage_rate if refi_mortgage_rate else mortgage_rate]}),
                refi_rate_schedule
            ]).sort_values("Year").reset_index(drop=True)

    n_periods = years * periods_per_year
    if refi_start_date and refi_years and refi_periods_per_year:
        refi_start_period = int(((refi_start_date - start_date).days / 365.25) * periods_per_year)
        n_periods = max(n_periods, refi_start_period + refi_years * refi_periods_per_year)

    delta = pd.DateOffset(months=1) if periods_per_year == 12 else timedelta(days=14)
    refi_delta = pd.DateOffset(months=1) if refi_periods_per_year == 12 else timedelta(days=14) if refi_periods_per_year else delta

    year_elapsed = max(1, start_date.year - purchase_year + 1)
    applicable_rates = rate_schedule[rate_schedule["Year"] <= year_elapsed].sort_values("Year")
    current_rate = applicable_rates["Rate (%)"].iloc[-1] / 100 if not applicable_rates.empty else mortgage_rate / 100
    monthly_payment = npf.pmt(current_rate / 12, years * 12, -principal)
    payment = round(monthly_payment, 2) if periods_per_year == 12 else round(monthly_payment * 12 / 26, 2)

    is_refinanced = False
    refi_start_period = 0
    for n in range(n_periods):
        current_date = start_date + (n * delta) if not is_refinanced else refi_start_date + (n - refi_start_period) * refi_delta
        year_elapsed = max(1, current_date.year - purchase_year + 1)

        if refi_start_date and current_date >= refi_start_date and not is_refinanced:
            is_refinanced = True
            balance = refi_principal
            periods_per_year = refi_periods_per_year
            rate_schedule = refi_rate_schedule
            mortgage_type = refi_mortgage_type
            purchase_year = refi_start_date.year
            refi_start_period = n
            year_elapsed = 1
            applicable_rates = rate_schedule[rate_schedule["Year"] <= year_elapsed].sort_values("Year")
            current_rate = applicable_rates["Rate (%)"].iloc[-1] / 100 if not applicable_rates.empty else refi_mortgage_rate / 100 if refi_mortgage_rate else mortgage_rate / 100
            monthly_payment = npf.pmt(current_rate / 12, refi_years * 12, -refi_principal)
            payment = round(monthly_payment, 2) if periods_per_year == 12 else round(monthly_payment * 12 / 26, 2)

        applicable_rates = rate_schedule[rate_schedule["Year"] <= year_elapsed].sort_values("Year")
        current_rate = applicable_rates["Rate (%)"].iloc[-1] / 100 if not applicable_rates.empty else (refi_mortgage_rate / 100 if is_refinanced and refi_mortgage_rate else mortgage_rate / 100)

        if mortgage_type == "Variable" and n > 0:
            remaining_periods = (years if not is_refinanced else refi_years) * periods_per_year - n
            monthly_payment = npf.pmt(current_rate / 12, remaining_periods / (periods_per_year / 12), -balance)
            payment = round(monthly_payment, 2) if periods_per_year == 12 else round(monthly_payment * 12 / 26, 2)

        equity = (purchase_price - balance) / purchase_price * 100 if purchase_price > 0 else 0
        pmi_payment = round((principal * pmi_rate / 100 / 12), 2) if equity < pmi_equity_threshold else 0

        extra = 0
        if extra_schedule:
            closest_date = min(extra_schedule.keys(), key=lambda x: abs((x - current_date).days), default=None)
            if closest_date and abs((closest_date - current_date).days) <= (30 if periods_per_year == 12 else 14):
                extra = extra_schedule.get(closest_date, 0)

        interest = round(balance * (current_rate / periods_per_year), 2)
        principal_paid = round(payment - interest, 2)

        if principal_paid + extra > balance:
            principal_paid = round(balance - extra, 2)
            payment = round(principal_paid + interest, 2)

        balance = round(balance - (principal_paid + extra), 2)

        schedule.append({
            "Date": current_date,
            "Payment": payment,
            "Interest": interest,
            "Principal": principal_paid,
            "Extra Principal Payments": extra,
            "PMI": pmi_payment,
            "Balance": balance,
            "Loan Type": "Refinance" if is_refinanced else "Original",
            "Effective Rate (%)": round(current_rate * 100, 2)
        })

        if balance <= 0:
            break

    df = pd.DataFrame(schedule)
    df_monthly = df.groupby(df["Date"].dt.to_period("M")).agg({
        "Payment": "sum",
        "Interest": "sum",
        "Principal": "sum",
        "Extra Principal Payments": "sum",
        "PMI": "sum",
        "Balance": "last",
        "Loan Type": "last",
        "Effective Rate (%)": "last"
    }).reset_index()
    df_monthly["Date"] = df_monthly["Date"].dt.to_timestamp()

    df_annual = df.groupby(df["Date"].dt.to_period("Y")).agg({
        "Payment": "sum",
        "Interest": "sum",
        "Principal": "sum",
        "Extra Principal Payments": "sum",
        "PMI": "sum",
        "Balance": "last",
        "Loan Type": "last",
        "Effective Rate (%)": "last"
    }).reset_index()
    df_annual["Date"] = df_annual["Date"].dt.to_timestamp()

    return df, df_monthly, df_annual

@st.cache_data
def calculate_cost_comparison(
    annual_df,
    edited_property_expenses,
    edited_emergency_expenses,
    purchase_year,
    eval_start_year,
    eval_end_year,
    annual_appreciation,
    annual_insurance_increase,
    annual_maintenance_increase,
    annual_hoa_increase,
    annual_property_tax_increase,
    cost_of_rent,
    annual_rent_increase,
    renters_insurance,
    security_deposit,
    points_cost,
    points_cost_method,
    closing_costs,
    closing_costs_method,
    refi_costs,
    roll_costs,
    refi_points_cost,
    refi_points_cost_method,
    rental_utilities,
    pet_fee,
    pet_fee_frequency,
    application_fee,
    lease_renewal_fee,
    parking_fee,
    purchase_price,
    vti_annual_return=7.0,
    down_payment=0
):
    years = range(eval_start_year, eval_end_year + 1)
    comparison_data = []
    cumulative_buy = 0
    cumulative_rent = 0
    taxes = edited_property_expenses[edited_property_expenses["Category"] == "Property Taxes"]["Amount ($)"].iloc[0] if "Property Taxes" in edited_property_expenses["Category"].values else 0
    insurance = edited_property_expenses[edited_property_expenses["Category"] == "Home Insurance"]["Amount ($)"].iloc[0] if "Home Insurance" in edited_property_expenses["Category"].values else 0
    maintenance = edited_property_expenses[edited_property_expenses["Category"] == "Routine Maintenance"]["Amount ($)"].iloc[0] if "Routine Maintenance" in edited_property_expenses["Category"].values else 0
    hoa = edited_property_expenses[edited_property_expenses["Category"] == "HOA Fees"]["Amount ($)"].iloc[0] if "HOA Fees" in edited_property_expenses["Category"].values else 0
    current_rent = cost_of_rent
    current_renters_insurance = renters_insurance
    current_deposit = security_deposit
    current_utilities = rental_utilities
    current_pet_fee = pet_fee
    current_parking = parking_fee
    home_value = purchase_price
    base_home_value = purchase_price
    buy_investment = 0
    rent_investment = down_payment + security_deposit

    for year in years:
        year_idx = year - purchase_year
        if year <= purchase_year + loan_years and year in annual_df["Date"].dt.year.values:
            p_and_i = annual_df[annual_df["Date"].dt.year == year]["Payment"].sum() + annual_df[annual_df["Date"].dt.year == year]["Extra Principal Payments"].sum()
            pmi = annual_df[annual_df["Date"].dt.year == year]["PMI"].sum()
            year_balance = annual_df[annual_df["Date"].dt.year == year]["Balance"].iloc[-1]
        else:
            p_and_i = 0
            pmi = 0
            year_balance = 0

        year_taxes = taxes * (1 + annual_property_tax_increase / 100) ** year_idx
        year_insurance = insurance * (1 + annual_insurance_increase / 100) ** year_idx
        year_maintenance = maintenance * (1 + annual_maintenance_increase / 100) ** year_idx
        year_hoa = hoa * (1 + annual_hoa_increase / 100) ** year_idx
        year_emergency = edited_emergency_expenses[edited_emergency_expenses["Year"] == year]["Amount ($)"].sum() if not edited_emergency_expenses.empty else 0
        year_closing = (closing_costs if year == purchase_year and closing_costs_method == "Pay Upfront" else 0) + (refi_costs if show_refinance and refi_start_date and refi_start_date.year == year and roll_costs == "Pay Upfront" else 0)
        year_points = (points_cost if year == purchase_year and points_cost_method == "Pay Upfront" else 0) + (refi_points_cost if show_refinance and refi_start_date and refi_start_date.year == year and refi_points_cost_method == "Pay Upfront" else 0)
        financing_method = (
            f"{'Closing: Upfront' if year == purchase_year and closing_costs_method == 'Pay Upfront' else 'Closing: Financed' if year == purchase_year else ''}"
            f"{'; ' if year == purchase_year and points_cost_method == 'Pay Upfront' else ''}{'Points: Upfront' if year == purchase_year and points_cost_method == 'Pay Upfront' else 'Points: Financed' if year == purchase_year else ''}"
            f"{'; ' if show_refinance and refi_start_date and refi_start_date.year == year else ''}{'Refi Closing: Upfront' if show_refinance and refi_start_date and refi_start_date.year == year and roll_costs == 'Pay Upfront' else 'Refi Closing: Financed' if show_refinance and refi_start_date and refi_start_date.year == year else ''}"
            f"{'; ' if show_refinance and refi_start_date and refi_start_date.year == year and refi_points_cost_method == 'Pay Upfront' else ''}{'Refi Points: Upfront' if show_refinance and refi_start_date and refi_start_date.year == year and refi_points_cost_method == 'Pay Upfront' else 'Refi Points: Financed' if show_refinance and refi_start_date and refi_start_date.year == year else ''}"
        ).strip("; ")
        indirect_costs = pmi + year_taxes + year_insurance + year_maintenance + year_hoa + year_emergency + year_closing + year_points
        buy_cost = p_and_i + indirect_costs

        year_rent = current_rent * 12
        year_renters_insurance = current_renters_insurance
        year_deposit = current_deposit if year == purchase_year else 0
        year_utilities = current_utilities
        year_pet_fee = current_pet_fee if pet_fee_frequency == "Annual" or (pet_fee_frequency == "One-time" and year == purchase_year) else 0
        year_application_fee = application_fee if year == purchase_year else 0
        year_renewal_fee = lease_renewal_fee if year > purchase_year else 0
        year_parking = current_parking * 12
        rent_cost = year_rent + year_renters_insurance + year_deposit + year_utilities + year_pet_fee + year_application_fee + year_renewal_fee + year_parking

        cumulative_buy += buy_cost
        cumulative_rent += rent_cost
        home_value = home_value * (1 + annual_appreciation / 100)
        appreciation = home_value - base_home_value
        equity = home_value - year_balance if year_balance > 0 else home_value

        cost_difference = buy_cost - rent_cost
        if cost_difference > 0:
            rent_investment = rent_investment * (1 + vti_annual_return / 100) + cost_difference
            buy_investment = buy_investment * (1 + vti_annual_return / 100)
        else:
            buy_investment = buy_investment * (1 + vti_annual_return / 100) + abs(cost_difference)
            rent_investment = rent_investment * (1 + vti_annual_return / 100)

        buy_total_assets = equity + buy_investment
        rent_total_assets = rent_investment

        comparison_data.append({
            "Year": year,
            "Direct Costs (P&I)": p_and_i,
            "Indirect Costs": indirect_costs,
            "PMI": pmi,
            "Property Taxes": year_taxes,
            "Home Insurance": year_insurance,
            "Maintenance": year_maintenance,
            "Emergency": year_emergency,
            "HOA Fees": year_hoa,
            "Closing Costs": year_closing,
            "Points Costs": year_points,
            "Financing Method": financing_method if financing_method else "None",
            "Total Buying Cost": buy_cost,
            "Total Renting Cost": rent_cost,
            "Cumulative Buying Cost": cumulative_buy,
            "Cumulative Renting Cost": cumulative_rent,
            "Cost Difference (Buy - Rent)": cumulative_buy - cumulative_rent,
            "Equity Gain": equity,
            "Appreciation": appreciation,
            "Buying Investment": buy_investment,
            "Renting Investment": rent_investment,
            "Buying Total Assets": buy_total_assets,
            "Renting Total Assets": rent_total_assets,
            "Asset Difference (Buy - Rent)": buy_total_assets - rent_total_assets,
            "Rent": year_rent,
            "Renters Insurance": year_renters_insurance,
            "Security Deposit": year_deposit,
            "Utilities": year_utilities,
            "Pet Fees": year_pet_fee,
            "Application Fee": year_application_fee,
            "Lease Renewal Fee": year_renewal_fee,
            "Parking Fee": year_parking
        })

        current_rent *= (1 + annual_rent_increase / 100)
        current_renters_insurance *= (1 + annual_rent_increase / 100)
        current_utilities *= (1 + annual_rent_increase / 100)
        current_pet_fee *= (1 + annual_rent_increase / 100) if pet_fee_frequency == "Annual" else 1
        current_parking *= (1 + annual_rent_increase / 100)

    return pd.DataFrame(comparison_data)

@st.cache_data
def calculate_breakeven(no_refi_monthly_df, monthly_with_extra_df, refi_costs, refi_points_cost, roll_costs, refi_points_cost_method):
    """Breakeven when total refi costs == cumulative (Interest + PMI) savings."""
    total_costs = float(refi_costs or 0) + float(refi_points_cost or 0)
    if total_costs <= 0:
        return None, None
    no_refi_cum_interest = no_refi_monthly_df['Interest'].cumsum()
    no_refi_cum_pmi = no_refi_monthly_df['PMI'].cumsum() if 'PMI' in no_refi_monthly_df.columns else 0.0
    refi_cum_interest = monthly_with_extra_df['Interest'].cumsum()
    refi_cum_pmi = monthly_with_extra_df['PMI'].cumsum() if 'PMI' in monthly_with_extra_df.columns else 0.0
    savings = (no_refi_cum_interest + no_refi_cum_pmi) - (refi_cum_interest + refi_cum_pmi)
    breakeven_idx = savings[savings >= total_costs].index
    if len(breakeven_idx) > 0:
        breakeven_month = int(breakeven_idx[0]) + 1
        breakeven_years = breakeven_month / 12
        return breakeven_years, breakeven_month
    return None, None


@st.cache_data
def get_remaining_balance(schedule_df, refi_date):
    refi_date = pd.to_datetime(refi_date)
    mask = schedule_df["Date"] <= refi_date
    return schedule_df.loc[mask, "Balance"].iloc[-1] if mask.any() else schedule_df["Balance"].iloc[0]

# Calculations
effective_principal = loan_amount + (points_cost if points_cost_method == "Add to Loan Balance" else 0)
effective_mortgage_rate = effective_rate

extra_schedule = expand_extra_payments(extra_payments, purchase_year, loan_years, payment_frequency)
extra_schedule_monthly = expand_extra_payments(extra_payments, purchase_year, loan_years, "Monthly")

no_refi_schedule_df, no_refi_monthly_df, no_refi_annual_df = amortization_schedule(
    principal=effective_principal,
    years=loan_years,
    periods_per_year=12,
    start_date=f"{purchase_year}-01-01",
    extra_schedule=extra_schedule_monthly,
    rate_schedule=rate_schedule,
    mortgage_type=mortgage_type,
    purchase_year=purchase_year,
    mortgage_rate=effective_mortgage_rate,
    pmi_rate=pmi_rate,
    pmi_equity_threshold=pmi_equity_threshold,
    purchase_price=purchase_price
)

refi_effective_principal = None
if show_refinance:
    refi_effective_principal = get_remaining_balance(no_refi_schedule_df, refi_start_date) + (refi_costs if roll_costs == "Add to Loan Balance" else 0) + (refi_points_cost if refi_points_cost_method == "Add to Loan Balance" else 0)

main_periods_per_year = 12 if payment_frequency == "Monthly" else 26
schedule_with_extra_df, monthly_with_extra_df, annual_with_extra_df = amortization_schedule(
    principal=effective_principal,
    years=loan_years,
    periods_per_year=main_periods_per_year,
    start_date=f"{purchase_year}-01-01",
    extra_schedule=extra_schedule,
    rate_schedule=rate_schedule,
    mortgage_type=mortgage_type,
    purchase_year=purchase_year,
    mortgage_rate=effective_mortgage_rate,
    pmi_rate=pmi_rate,
    pmi_equity_threshold=pmi_equity_threshold,
    purchase_price=purchase_price,
    refi_start_date=refi_start_date if show_refinance else None,
    refi_principal=refi_effective_principal,
    refi_years=refi_term_years,
    refi_periods_per_year=refi_periods_per_year if show_refinance else None,
    refi_rate_schedule=refi_rate_schedule,
    refi_mortgage_type=refi_mortgage_type,
    refi_mortgage_rate=refi_effective_rate
)

schedule_without_extra_df, monthly_without_extra_df, annual_without_extra_df = amortization_schedule(
    principal=effective_principal,
    years=loan_years,
    periods_per_year=main_periods_per_year,
    start_date=f"{purchase_year}-01-01",
    extra_schedule={},
    rate_schedule=rate_schedule,
    mortgage_type=mortgage_type,
    purchase_year=purchase_year,
    mortgage_rate=effective_mortgage_rate,
    pmi_rate=pmi_rate,
    pmi_equity_threshold=pmi_equity_threshold,
    purchase_price=purchase_price,
    refi_start_date=refi_start_date if show_refinance else None,
    refi_principal=refi_effective_principal,
    refi_years=refi_term_years,
    refi_periods_per_year=refi_periods_per_year if show_refinance else None,
    refi_rate_schedule=refi_rate_schedule,
    refi_mortgage_type=refi_mortgage_type,
    refi_mortgage_rate=refi_effective_rate
)

monthly_payment = schedule_with_extra_df['Payment'].iloc[0] if main_periods_per_year == 12 else schedule_with_extra_df['Payment'].iloc[0] * 26 / 12
payment_per_period = schedule_with_extra_df['Payment'].iloc[0]
total_interest = schedule_with_extra_df['Interest'].sum()
total_pmi = schedule_with_extra_df['PMI'].sum()
payoff_years = len(schedule_with_extra_df) / main_periods_per_year
payoff_date = schedule_with_extra_df[schedule_with_extra_df['Balance'] <= 0]['Date'].min() if (schedule_with_extra_df['Balance'] <= 0).any() else schedule_with_extra_df['Date'].max()
payoff_year = payoff_date.year
payoff_month = payoff_date.month

interest_saved_refi = 0
pmi_saved_refi = 0
payoff_difference_refi = 0
breakeven_years = None
breakeven_months = None
if show_refinance and refi_start_date:
    interest_saved_refi = no_refi_schedule_df['Interest'].sum() - total_interest
    pmi_saved_refi = no_refi_schedule_df['PMI'].sum() - total_pmi
    payoff_difference_refi = len(no_refi_schedule_df) / 12 - payoff_years
    breakeven_years, breakeven_months = calculate_breakeven(no_refi_monthly_df, monthly_with_extra_df, refi_costs, refi_points_cost, roll_costs, refi_points_cost_method)

interest_saved_biweekly = 0
payoff_difference_biweekly = 0
if payment_frequency == "Biweekly":
    monthly_comparison_df, monthly_comparison_monthly_df, monthly_comparison_annual_df = amortization_schedule(
        principal=effective_principal,
        years=loan_years,
        periods_per_year=12,
        start_date=f"{purchase_year}-01-01",
        extra_schedule=extra_schedule_monthly,
        rate_schedule=rate_schedule,
        mortgage_type=mortgage_type,
        purchase_year=purchase_year,
        mortgage_rate=effective_mortgage_rate,
        pmi_rate=pmi_rate,
        pmi_equity_threshold=pmi_equity_threshold,
        purchase_price=purchase_price,
        refi_start_date=refi_start_date if show_refinance else None,
        refi_principal=refi_effective_principal,
        refi_years=refi_term_years,
        refi_periods_per_year=refi_periods_per_year if show_refinance else None,
        refi_rate_schedule=refi_rate_schedule,
        refi_mortgage_type=refi_mortgage_type,
        refi_mortgage_rate=refi_effective_rate
    )
    interest_saved_biweekly = monthly_comparison_df['Interest'].sum() - total_interest
    payoff_difference_biweekly = len(monthly_comparison_df) / 12 - payoff_years

cost_comparison_df = calculate_cost_comparison(
    annual_with_extra_df,
    edited_property_expenses,
    edited_emergency_expenses,
    purchase_year,
    eval_start_year,
    eval_end_year,
    annual_appreciation,
    annual_insurance_increase,
    annual_maintenance_increase,
    annual_hoa_increase,
    annual_property_tax_increase,
    cost_of_rent,
    annual_rent_increase,
    renters_insurance,
    security_deposit,
    points_cost,
    points_cost_method,
    closing_costs,
    closing_costs_method,
    refi_costs,
    roll_costs,
    refi_points_cost,
    refi_points_cost_method,
    rental_utilities,
    pet_fee,
    pet_fee_frequency,
    application_fee,
    lease_renewal_fee,
    parking_fee,
    purchase_price,
    vti_annual_return,
    down_payment
)

cost_comparison_df['Buying Down Payment'] = down_payment
cost_comparison_df['Buying Earned Equity'] = cost_comparison_df['Equity Gain'] - down_payment
cost_comparison_df['Asset % Difference (Buy vs Rent)'] = np.where(
    cost_comparison_df['Renting Total Assets'] > 0,
    (cost_comparison_df['Buying Total Assets'] - cost_comparison_df['Renting Total Assets']) / cost_comparison_df['Renting Total Assets'] * 100,
    0
)

# Display
thick_divider()
st.header("Mortgage Metrics")
with st.container(border=True):
    left, right = st.columns(2)
    with left:
        st.subheader("Original Mortgage")
        st.metric("Loan Amount", f"${display_loan_amount:,.0f}")
        st.metric("Rate", f"{effective_mortgage_rate:.3f}%")
        st.metric("Term (Years)", f"{loan_years}")
        st.metric("Monthly Payment", f"${monthly_payment:,.2f}")
        st.metric("Payment per Period", f"${payment_per_period:,.2f}")
        st.metric("Total Interest", f"${total_interest:,.2f}")
        st.metric("Total PMI", f"${total_pmi:,.2f}")
        st.metric("Payoff", f"{payoff_year}-{payoff_month:02d}")
    with right:
        st.subheader("Refinance")
        if show_refinance and refi_start_date and refi_effective_principal is not None:
            st.metric("New Principal (at Refi)", f"${refi_effective_principal:,.0f}")
            st.metric("Refi Rate", f"{refi_effective_rate:.3f}%")
            st.metric("Refi Term (Years)", f"{refi_term_years}")
            breakeven_years, breakeven_months = calculate_breakeven(no_refi_monthly_df, monthly_with_extra_df, refi_costs, refi_points_cost, "Pay Upfront", "Pay Upfront")
            st.caption("Breakeven = when cumulative Interest+PMI savings exceed total refi costs (incl. points). " + (f"~{breakeven_years:.1f} years ({breakeven_months:.0f} months)" if breakeven_years else "Not reached in horizon."))
        else:
            st.caption("Refinance disabled or not configured.")


# --- Deterministic KPI strip ---
with st.container(border=True):
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Monthly Payment", f"${monthly_payment:,.2f}")
    k2.metric("Total Interest (All-in)", f"${total_interest:,.0f}")
    k3.metric("Payoff Date", f"{payoff_year}-{payoff_month:02d}")
    if show_refinance and breakeven_years:
        k4.metric("Refi Breakeven", f"{breakeven_years:.1f} yrs")
    else:
        k4.metric("Refi Breakeven", "—")

st.header("Amortization Schedule")
st.markdown("**Note**: 'Loan Type' indicates 'Original' (white) or 'Refinance' (blue). 'Effective Rate (%)' shows the applied interest rate.")
tab1, tab2 = st.tabs(["Annual", "Monthly"])
with tab1:
    st.dataframe(
        annual_with_extra_df.style.format({
            "Date": "{:%Y}",
            "Payment": "${:,.2f}",
            "Interest": "${:,.2f}",
            "Principal": "${:,.2f}",
            "Extra Principal Payments": "${:,.2f}",
            "PMI": "${:,.2f}",
            "Balance": "${:,.2f}",
            "Effective Rate (%)": "{:.2f}%"
        }).apply(lambda row: ["background-color: #e6f3ff" if row["Loan Type"] == "Refinance" else ""] * len(row), axis=1),
        hide_index=True
    )
with tab2:
    st.dataframe(
        monthly_with_extra_df.style.format({
            "Date": "{:%Y-%m}",
            "Payment": "${:,.2f}",
            "Interest": "${:,.2f}",
            "Principal": "${:,.2f}",
            "Extra Principal Payments": "${:,.2f}",
            "PMI": "${:,.2f}",
            "Balance": "${:,.2f}",
            "Effective Rate (%)": "{:.2f}%"
        }).apply(lambda row: ["background-color: #e6f3ff" if row["Loan Type"] == "Refinance" else ""] * len(row), axis=1),
        hide_index=True
    )

st.header("Amortization Breakdown")
show_baseline = st.checkbox("Show baseline without extra principal (dashed)", value=True)
schedule_with_extra_df['Year'] = schedule_with_extra_df['Date'].dt.year
annual_with_extra = annual_with_extra_df.copy()
annual_with_extra['Year'] = annual_with_extra['Date'].dt.year
annual_with_extra['Cum Principal'] = annual_with_extra['Principal'].cumsum()
annual_with_extra['Cum Interest'] = annual_with_extra['Interest'].cumsum()
annual_with_extra['Cum PMI'] = annual_with_extra['PMI'].cumsum() if 'PMI' in annual_with_extra.columns else 0.0

tab1, tab2, tab3 = st.tabs(["By Payment", "By Year", "Cumulative Payoff"])
with tab1:
    fig_amort_payment = go.Figure()
    fig_amort_payment.add_trace(go.Scatter(x=schedule_with_extra_df['Date'], y=schedule_with_extra_df['Principal'], mode='lines', name='Principal (With Extra)', line=dict(dash='solid', color='rgba(33, 150, 243, 1)')))
    fig_amort_payment.add_trace(go.Scatter(x=schedule_with_extra_df['Date'], y=schedule_with_extra_df['Interest'], mode='lines', name='Interest (With Extra)', line=dict(dash='solid')))
    fig_amort_payment.add_trace(go.Bar(x=schedule_with_extra_df['Date'], y=schedule_with_extra_df['PMI'], name='PMI', yaxis='y2', opacity=0.4))
    if show_baseline:
        fig_amort_payment.add_trace(go.Scatter(x=schedule_without_extra_df['Date'], y=schedule_without_extra_df['Principal'], mode='lines', name='Principal (No Extra)', line=dict(dash='dash')))
        fig_amort_payment.add_trace(go.Scatter(x=schedule_without_extra_df['Date'], y=schedule_without_extra_df['Interest'], mode='lines', name='Interest (No Extra)', line=dict(dash='dash')))
    fig_amort_payment.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Date', yaxis_title='Amount ($)', yaxis2=dict(overlaying='y', side='right', title='PMI ($)'),
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    if show_refinance and refi_start_date:
        refi_timestamp = pd.Timestamp(refi_start_date).timestamp() * 1000
        fig_amort_payment.add_vline(x=refi_timestamp, line_dash="dash", line_color="orange", annotation_text="Refinance")
    if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
        payoff_timestamp = pd.Timestamp(f"{payoff_year}-01-01").timestamp() * 1000
        fig_amort_payment.add_vline(x=payoff_timestamp, line_dash="dash", line_color="purple", annotation_text="Payoff")
    st.plotly_chart(fig_amort_payment, use_container_width=True)

with tab2:
    fig_amort_year = go.Figure()
    fig_amort_year.add_trace(go.Scatter(x=annual_with_extra['Year'], y=annual_with_extra['Principal'], mode='lines', name='Principal (With Extra)', line=dict(dash='solid', color='rgba(33, 150, 243, 1)')))
    fig_amort_year.add_trace(go.Scatter(x=annual_with_extra['Year'], y=annual_with_extra['Interest'], mode='lines', name='Interest (With Extra)', line=dict(dash='solid')))
    fig_amort_year.add_trace(go.Bar(x=annual_with_extra['Year'], y=annual_with_extra['PMI'], name='PMI', yaxis='y2', opacity=0.4))
    if show_baseline:
        annual_without_extra_local = annual_without_extra_df.copy()
        annual_without_extra_local['Year'] = annual_without_extra_local['Date'].dt.year
        fig_amort_year.add_trace(go.Scatter(x=annual_without_extra_local['Year'], y=annual_without_extra_local['Principal'], mode='lines', name='Principal (No Extra)', line=dict(dash='dash')))
        fig_amort_year.add_trace(go.Scatter(x=annual_without_extra_local['Year'], y=annual_without_extra_local['Interest'], mode='lines', name='Interest (No Extra)', line=dict(dash='dash')))
    fig_amort_year.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Amount ($)', yaxis2=dict(overlaying='y', side='right', title='PMI ($)'),
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    if show_refinance and refi_start_date:
        fig_amort_year.add_vline(x=refi_start_date.year, line_dash="dash", line_color="orange", annotation_text="Refinance")
    if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
        fig_amort_year.add_vline(x=payoff_year, line_dash="dash", line_color="purple", annotation_text="Payoff")
    st.plotly_chart(fig_amort_year, use_container_width=True)

with tab3:
    fig_amort_cum = go.Figure()
    fig_amort_cum.add_trace(go.Scatter(x=annual_with_extra['Year'], y=annual_with_extra['Cum Principal'], mode='lines', name='Principal (With Extra)', line=dict(dash='solid', color='rgba(33, 150, 243, 1)')))
    fig_amort_cum.add_trace(go.Scatter(x=annual_with_extra['Year'], y=annual_with_extra['Cum Interest'], mode='lines', name='Interest (With Extra)', line=dict(dash='solid')))
    fig_amort_cum.add_trace(go.Bar(x=annual_with_extra['Year'], y=annual_with_extra['Cum PMI'], name='PMI', yaxis='y2', opacity=0.4))
    if show_baseline:
        annual_without_extra_local = annual_without_extra_df.copy()
        annual_without_extra_local['Year'] = annual_without_extra_local['Date'].dt.year
        annual_without_extra_local['Cum Principal'] = annual_without_extra_local['Principal'].cumsum()
        annual_without_extra_local['Cum Interest'] = annual_without_extra_local['Interest'].cumsum()
        fig_amort_cum.add_trace(go.Scatter(x=annual_without_extra_local['Year'], y=annual_without_extra_local['Cum Principal'], mode='lines', name='Cum Principal (No Extra)', line=dict(dash='dash')))
        fig_amort_cum.add_trace(go.Scatter(x=annual_without_extra_local['Year'], y=annual_without_extra_local['Cum Interest'], mode='lines', name='Cum Interest (No Extra)', line=dict(dash='dash')))
    fig_amort_cum.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Cumulative Amount ($)', yaxis2=dict(overlaying='y', side='right', title='PMI ($)'),
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    if show_refinance and refi_start_date:
        fig_amort_cum.add_vline(x=refi_start_date.year, line_dash="dash", line_color="orange", annotation_text="Refinance")
    if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
        fig_amort_cum.add_vline(x=payoff_year, line_dash="dash", line_color="purple", annotation_text="Payoff")
    st.plotly_chart(fig_amort_cum, use_container_width=True)

st.divider()  # divider between Mortgage Metrics and Savings Comparison
# Prepare baseline (without extra payments) for savings comparison
annual_without_extra = annual_without_extra_df.copy()
annual_without_extra['Year'] = annual_without_extra['Date'].dt.year
annual_without_extra['Cum Principal'] = annual_without_extra['Principal'].cumsum()
annual_without_extra['Cum Interest'] = annual_without_extra['Interest'].cumsum()
annual_without_extra['Cum PMI'] = annual_without_extra['PMI'].cumsum() if 'PMI' in annual_without_extra.columns else 0.0

st.header("Savings from Extra Payments")
annual_with_extra['Interest Saved (Cum)'] = (annual_without_extra['Cum Interest'] - annual_with_extra['Cum Interest']).fillna(0)
annual_with_extra['PMI Saved (Cum)'] = (annual_without_extra['Cum PMI'] - annual_with_extra['Cum PMI']).fillna(0)
annual_with_extra['Interest Saved (Year)'] = annual_with_extra['Interest Saved (Cum)'].diff().fillna(annual_with_extra['Interest Saved (Cum)'])
annual_with_extra['PMI Saved (Year)'] = annual_with_extra['PMI Saved (Cum)'].diff().fillna(annual_with_extra['PMI Saved (Cum)'])

tab_y, tab_c = st.tabs(["By Year", "Cumulative"])
with tab_y:
    fig_sy = go.Figure()
    fig_sy.add_trace(go.Scatter(x=annual_with_extra['Year'], y=annual_with_extra['Interest Saved (Year)'], mode='lines+markers', name='Interest Saved (Year)'))
    fig_sy.add_trace(go.Scatter(x=annual_with_extra['Year'], y=annual_with_extra['PMI Saved (Year)'], mode='lines+markers', name='PMI Saved (Year)', yaxis='y2'))
    fig_sy.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Interest Saved ($)', yaxis2=dict(overlaying='y', side='right', title='PMI Saved ($)'),
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    st.plotly_chart(fig_sy, use_container_width=True)

with tab_c:
    fig_sc = go.Figure()
    fig_sc.add_trace(go.Scatter(x=annual_with_extra['Year'], y=annual_with_extra['Interest Saved (Cum)'], mode='lines+markers', name='Interest Saved (Cum)'))
    fig_sc.add_trace(go.Scatter(x=annual_with_extra['Year'], y=annual_with_extra['PMI Saved (Cum)'], mode='lines+markers', name='PMI Saved (Cum)', yaxis='y2'))
    fig_sc.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Interest Saved ($)', yaxis2=dict(overlaying='y', side='right', title='PMI Saved ($)'),
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    st.plotly_chart(fig_sc, use_container_width=True)


# Savings from Buying Points
if buy_points and points > 0:
    st.header("Savings from Buying Points")
    # Compare payment/interest with and without the points discount, holding term constant.
    # Build a no-points schedule for comparison.
    no_points_rate_schedule = rate_schedule.copy()
    if mortgage_type == "Fixed":
        no_points_rate_schedule["Rate (%)"] = mortgage_rate
    else:
        no_points_rate_schedule["Rate (%)"] = no_points_rate_schedule["Rate (%)"] + (discount_per_point * points)
    no_points_df, no_points_monthly, no_points_annual = amortization_schedule(
        principal=loan_amount + (closing_costs if closing_costs_method == "Add to Loan Balance" else 0) + (0 if points_cost_method == "Pay Upfront" else points_cost),
        years=loan_years,
        periods_per_year=12,
        start_date=f"{purchase_year}-01-01",
        extra_schedule=extra_schedule_monthly,
        rate_schedule=no_points_rate_schedule,
        mortgage_type=mortgage_type,
        purchase_year=purchase_year,
        mortgage_rate=mortgage_rate,
        pmi_rate=pmi_rate,
        pmi_equity_threshold=pmi_equity_threshold,
        purchase_price=purchase_price
    )
    pts_annual = annual_with_extra_df.copy()
    pts_annual['Year'] = pts_annual['Date'].dt.year
    no_pts_annual = no_points_annual.copy()
    no_pts_annual['Year'] = no_pts_annual['Date'].dt.year
    pts_annual['Cum Interest'] = pts_annual['Interest'].cumsum()
    no_pts_annual['Cum Interest'] = no_pts_annual['Interest'].cumsum()
    interest_saved_points = no_pts_annual['Cum Interest'] - pts_annual['Cum Interest']
    cum_points_cost = np.cumsum([points_cost if points_cost_method == "Pay Upfront" and y == purchase_year else 0 for y in pts_annual['Year']])
    fig_pts = go.Figure()
    fig_pts.add_trace(go.Scatter(x=pts_annual['Year'], y=interest_saved_points, mode='lines+markers', name='Interest Saved from Points'))
    fig_pts.add_trace(go.Scatter(x=pts_annual['Year'], y=cum_points_cost, mode='lines+markers', name='Cumulative Points Cost', yaxis='y2'))
    fig_pts.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Interest Saved ($)', yaxis2=dict(overlaying='y', side='right', title='Cumulative Cost ($)'),
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    fig_pts.add_hline(y=0, line_dash="dash", line_color="black")
    st.plotly_chart(fig_pts, use_container_width=True)

if payment_frequency == "Biweekly":
    st.header("Savings from Biweekly Payments")
    monthly_comp_annual = monthly_comparison_annual_df.copy()
    monthly_comp_annual['Year'] = monthly_comp_annual['Date'].dt.year
    monthly_comp_annual['Cum Interest'] = monthly_comp_annual['Interest'].cumsum()
    monthly_comp_annual['Cum PMI'] = monthly_comp_annual['PMI'].cumsum()
    annual_with_extra['Cum Interest'] = annual_with_extra['Interest'].cumsum()
    annual_with_extra['Cum PMI'] = annual_with_extra['PMI'].cumsum()
    annual_with_extra['Interest Saved'] = monthly_comp_annual['Cum Interest'] - annual_with_extra['Cum Interest']
    annual_with_extra['PMI Saved'] = monthly_comp_annual['Cum PMI'] - annual_with_extra['Cum PMI']
    fig_saved_bi = go.Figure()
    fig_saved_bi.add_trace(go.Scatter(x=annual_with_extra['Year'], y=annual_with_extra['Interest Saved'], mode='lines+markers', name='Interest Saved'))
    fig_saved_bi.add_trace(go.Scatter(x=annual_with_extra['Year'], y=annual_with_extra['PMI Saved'], mode='lines+markers', name='PMI Saved', yaxis='y2'))
    fig_saved_bi.update_layout(
        plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
        xaxis_title='Year', yaxis_title='Interest Saved ($)', yaxis2=dict(overlaying='y', side='right', title='PMI Saved ($)'),
        legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
    )
    if show_refinance and refi_start_date:
        fig_saved_bi.add_vline(x=refi_start_date.year, line_dash="dash", line_color="orange", annotation_text="Refinance")
    if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
        fig_saved_bi.add_vline(x=payoff_year, line_dash="dash", line_color="purple", annotation_text="Payoff")
    fig_saved_bi.add_hline(y=0, line_dash='dash', line_color='black')
    st.plotly_chart(fig_saved_bi, use_container_width=True)


thick_divider()

st.header("Evaluation Year Selection")
st.markdown('<div class="highlight-box">Select a year to analyze asset and cost metrics. This selection will carry through the 2.) Assets and 3.) Costs sections.</div>', unsafe_allow_html=True)
st.markdown(" ")
selected_year = st.selectbox(
    "Select Evaluation Year",
    options=list(range(eval_start_year, eval_end_year + 1)),
    index=0,
    help="Choose a year to view detailed asset and cost breakdowns."
)

thick_divider()

st.header("2. Asset Metrics")
st.markdown('<div class="highlight-box">Buying assets include home equity, appreciation, and Personal Brokerage Account investments. Renting assets include Personal Brokerage Account investments from cost savings and down payment.</div>', unsafe_allow_html=True)
final_data = cost_comparison_df[cost_comparison_df["Year"] == selected_year]
if not final_data.empty:
    final_balance = annual_with_extra_df[annual_with_extra_df["Date"].dt.year == selected_year]["Balance"].iloc[-1] if selected_year in annual_with_extra_df["Date"].dt.year.values else 0
    final_home_value = purchase_price * (1 + annual_appreciation / 100) ** (selected_year - purchase_year)
    equity_gain = final_data["Equity Gain"].iloc[0]
    appreciation = final_data["Appreciation"].iloc[0]
    buying_investment = final_data["Buying Investment"].iloc[0]
    renting_investment = final_data["Renting Investment"].iloc[0]
    buying_assets = final_data["Buying Total Assets"].iloc[0]
    renting_assets = final_data["Renting Total Assets"].iloc[0]
    asset_difference = buying_assets - renting_assets
else:
    year_idx = selected_year - purchase_year
    final_balance = 0
    final_home_value = purchase_price * (1 + annual_appreciation / 100) ** year_idx
    equity_gain = final_home_value
    appreciation = final_home_value - purchase_price
    last_year_data = cost_comparison_df[cost_comparison_df["Year"] == cost_comparison_df["Year"].max()]
    if not last_year_data.empty:
        last_year_idx = cost_comparison_df["Year"].max() - purchase_year
        years_diff = year_idx - last_year_idx
        buying_investment = last_year_data["Buying Investment"].iloc[0] * (1 + vti_annual_return / 100) ** years_diff
        renting_investment = last_year_data["Renting Investment"].iloc[0] * (1 + vti_annual_return / 100) ** years_diff
    else:
        buying_investment = 0
        renting_investment = 0
    buying_assets = equity_gain + buying_investment
    renting_assets = renting_investment
    asset_difference = buying_assets - renting_assets

buy_col, rent_col = st.columns(2)
with buy_col:
    st.markdown(f"### Buying Assets ({selected_year})")
    buy_asset_df = pd.DataFrame({
        "Item": ["Equity Gain", "Appreciation", "Investment"],
        "Value": [equity_gain, appreciation, buying_investment]
    })
    buy_asset_df = buy_asset_df[buy_asset_df["Value"] > 0]
    total_buy = buy_asset_df["Value"].sum()
    buy_asset_df["% of Total"] = (buy_asset_df["Value"] / total_buy) * 100 if total_buy > 0 else 0
    total_buy_row = pd.DataFrame({"Item": ["Total"], "Value": [total_buy], "% of Total": [100.0]})
    buy_asset_df = pd.concat([buy_asset_df, total_buy_row], ignore_index=True)
    st.dataframe(
        buy_asset_df.style.format({"Value": "${:,.2f}", "% of Total": "{:.2f}%"})
        .apply(lambda row: ["background-color: #e6f3ff" if row["Item"] == "Total" else ""] * len(row), axis=1),
        hide_index=True
    )
with rent_col:
    st.markdown(f"### Renting Assets ({selected_year})")
    rent_asset_df = pd.DataFrame({
        "Item": ["Investment"],
        "Value": [renting_investment]
    })
    rent_asset_df = rent_asset_df[rent_asset_df["Value"] > 0]
    total_rent = rent_asset_df["Value"].sum()
    rent_asset_df["% of Total"] = (rent_asset_df["Value"] / total_rent) * 100 if total_rent > 0 else 0
    total_rent_row = pd.DataFrame({"Item": ["Total"], "Value": [total_rent], "% of Total": [100.0]})
    rent_asset_df = pd.concat([rent_asset_df, total_rent_row], ignore_index=True)
    st.dataframe(
        rent_asset_df.style.format({"Value": "${:,.2f}", "% of Total": "{:.2f}%"})
        .apply(lambda row: ["background-color: #e6f3ff" if row["Item"] == "Total" else ""] * len(row), axis=1),
        hide_index=True
    )

buy_asset_data = cost_comparison_df[cost_comparison_df['Year'] == selected_year][['Equity Gain', 'Appreciation', 'Buying Investment']].melt(
    var_name='Category', value_name='Value'
)
buy_asset_data = buy_asset_data[buy_asset_data['Value'] > 0]
rent_asset_data = cost_comparison_df[cost_comparison_df['Year'] == selected_year][['Renting Investment']].melt(
    var_name='Category', value_name='Value'
)
rent_asset_data = rent_asset_data[rent_asset_data['Value'] > 0]

st.divider()

# Projected Assets Section
st.header("Projected Assets")
st.markdown("Visualize the growth of total assets over time. Buying assets include home equity, appreciation, and Personal Brokerage Account investments. Renting assets include Personal Brokerage Account investments from cost savings and down payment.")
with st.container(border=True):
    tab_period, tab_cumulative, tab_pct_diff = st.tabs(["Annual Assets", "Cumulative Assets", "Asset % Difference"])
    with tab_period:
        st.markdown("**Annual Assets**: Compare yearly total assets for buying vs. renting.")
        asset_data = pd.concat([
            pd.DataFrame({"Year": cost_comparison_df["Year"], "Assets": cost_comparison_df["Buying Total Assets"], "Type": "Buying"}),
            pd.DataFrame({"Year": cost_comparison_df["Year"], "Assets": cost_comparison_df["Renting Total Assets"], "Type": "Renting"})
        ], ignore_index=True)
        fig_assets = px.line(asset_data, x='Year', y='Assets', color='Type', markers=True)
        fig_assets.update_layout(
            plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
            xaxis_title='Year', yaxis_title='Annual Assets ($)',
            legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
        )
        if show_refinance and refi_start_date:
            fig_assets.add_vline(x=refi_start_date.year, line_dash="dash", line_color="orange", annotation_text="Refinance")
        if purchase_year and eval_start_year <= purchase_year <= eval_end_year:
            fig_assets.add_vline(x=purchase_year, line_dash="dash", line_color="blue", annotation_text="Purchase")
        if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
            fig_assets.add_vline(x=payoff_year, line_dash="dash", line_color="purple", annotation_text="Payoff")
        st.plotly_chart(fig_assets, use_container_width=True)

    with tab_cumulative:
        st.markdown("**Cumulative Assets**: Compare the cumulative total assets for buying vs. renting over time.")
        cum_asset_data = pd.concat([
            pd.DataFrame({"Year": cost_comparison_df["Year"], "Assets": cost_comparison_df["Buying Total Assets"].cumsum(), "Type": "Buying"}),
            pd.DataFrame({"Year": cost_comparison_df["Year"], "Assets": cost_comparison_df["Renting Total Assets"].cumsum(), "Type": "Renting"})
        ], ignore_index=True)
        fig_cum_assets = px.line(cum_asset_data, x='Year', y='Assets', color='Type', markers=True)
        fig_cum_assets.update_layout(
            plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
            xaxis_title='Year', yaxis_title='Cumulative Assets ($)',
            legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
        )
        if show_refinance and refi_start_date:
            fig_cum_assets.add_vline(x=refi_start_date.year, line_dash="dash", line_color="orange", annotation_text="Refinance")
        if purchase_year and eval_start_year <= purchase_year <= eval_end_year:
            fig_cum_assets.add_vline(x=purchase_year, line_dash="dash", line_color="blue", annotation_text="Purchase")
        if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
            fig_cum_assets.add_vline(x=payoff_year, line_dash="dash", line_color="purple", annotation_text="Payoff")
        st.plotly_chart(fig_cum_assets, use_container_width=True)

    with tab_pct_diff:
        st.markdown("**Asset % Difference**: Percentage difference between buying and renting assets, calculated as ((Buying Assets - Renting Assets) / Renting Assets) * 100.")
        asset_pct_diff = pd.DataFrame({
            "Year": cost_comparison_df["Year"],
            "Asset % Difference": ((cost_comparison_df["Buying Total Assets"] - cost_comparison_df["Renting Total Assets"]) / cost_comparison_df["Renting Total Assets"].replace(0, np.nan)) * 100
        })
        asset_pct_diff["Asset % Difference"] = asset_pct_diff["Asset % Difference"].fillna(0)  # Handle division by zero
        fig_asset_pct_diff = px.line(asset_pct_diff, x='Year', y='Asset % Difference', markers=True)
        fig_asset_pct_diff.update_layout(
            plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
            xaxis_title='Year', yaxis_title='Asset % Difference (Buy - Rent) / Rent (%)',
            showlegend=False
        )
        if show_refinance and refi_start_date:
            fig_asset_pct_diff.add_vline(x=refi_start_date.year, line_dash="dash", line_color="orange", annotation_text="Refinance")
        if purchase_year and eval_start_year <= purchase_year <= eval_end_year:
            fig_asset_pct_diff.add_vline(x=purchase_year, line_dash="dash", line_color="blue", annotation_text="Purchase")
        if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
            fig_asset_pct_diff.add_vline(x=payoff_year, line_dash="dash", line_color="purple", annotation_text="Payoff")
        fig_asset_pct_diff.add_hline(y=0, line_dash='dot', opacity=0.5)
        st.plotly_chart(fig_asset_pct_diff, use_container_width=True)
        st.markdown("**Note**: Zero values indicate no renting assets for that year, preventing division by zero.")

thick_divider()

# Cost Metrics Section
st.header("3. Cost Metrics")
st.markdown(f"Breakdown of costs for the selected year ({selected_year}). Buying costs include P&I, PMI, taxes, insurance, maintenance, and more. Renting costs include rent, fees, and utilities.")
with st.container(border=True):
    buy_cost_cols = ['Direct Costs (P&I)', 'PMI', 'Property Taxes', 'Home Insurance', 'Maintenance', 'Emergency', 'HOA Fees', 'Closing Costs', 'Points Costs']
    rent_cost_cols = ['Rent', 'Renters Insurance', 'Security Deposit', 'Utilities', 'Pet Fees', 'Application Fee', 'Lease Renewal Fee', 'Parking Fee']
    
    buy_cost_df = cost_comparison_df[cost_comparison_df['Year'] == selected_year][buy_cost_cols].melt(var_name='Item', value_name='Value')
    buy_cost_df = buy_cost_df[buy_cost_df['Value'] > 0]
    total_buy_cost = buy_cost_df['Value'].sum()
    buy_cost_df['% of Total'] = (buy_cost_df['Value'] / total_buy_cost * 100) if total_buy_cost > 0 else 0
    total_buy_cost_row = pd.DataFrame({"Item": ["Total"], "Value": [total_buy_cost], "% of Total": [100.0]})
    buy_cost_df = pd.concat([buy_cost_df, total_buy_cost_row], ignore_index=True)

    rent_cost_df = cost_comparison_df[cost_comparison_df['Year'] == selected_year][rent_cost_cols].melt(var_name='Item', value_name='Value')
    rent_cost_df = rent_cost_df[rent_cost_df['Value'] > 0]
    total_rent_cost = rent_cost_df['Value'].sum()
    rent_cost_df['% of Total'] = (rent_cost_df['Value'] / total_rent_cost * 100) if total_rent_cost > 0 else 0
    total_rent_cost_row = pd.DataFrame({"Item": ["Total"], "Value": [total_rent_cost], "% of Total": [100.0]})
    rent_cost_df = pd.concat([rent_cost_df, total_rent_cost_row], ignore_index=True)

    buy_col, rent_col = st.columns(2)
    with buy_col:
        st.markdown(f"### Buying Costs ({selected_year})")
        st.dataframe(
            buy_cost_df.style.format({"Value": "${:,.2f}", "% of Total": "{:.2f}%"})
            .apply(lambda row: ["background-color: #e6f3ff" if row["Item"] == "Total" else ""] * len(row), axis=1),
            hide_index=True
        )
    with rent_col:
        st.markdown(f"### Renting Costs ({selected_year})")
        st.dataframe(
            rent_cost_df.style.format({"Value": "${:,.2f}", "% of Total": "{:.2f}%"})
            .apply(lambda row: ["background-color: #e6f3ff" if row["Item"] == "Total" else ""] * len(row), axis=1),
            hide_index=True
        )

# Costs Section
st.header("Projected Costs")
st.markdown("Track total costs over time for buying (P&I, PMI, taxes, insurance, etc.) and renting (rent, fees, utilities).")
with st.container(border=True):
    tab_non_cum, tab_cum, tab_pct_diff = st.tabs(["Annual Costs", "Cumulative Costs", "Cost % Difference"])
    with tab_non_cum:
        st.markdown("**Annual Costs**: Compare yearly total costs for buying vs. renting.")
        cost_data = pd.concat([
            pd.DataFrame({"Year": cost_comparison_df["Year"], "Cost": cost_comparison_df["Total Buying Cost"], "Type": "Buying"}),
            pd.DataFrame({"Year": cost_comparison_df["Year"], "Cost": cost_comparison_df["Total Renting Cost"], "Type": "Renting"})
        ], ignore_index=True)
        fig_costs = px.line(cost_data, x='Year', y='Cost', color='Type', markers=True)
        fig_costs.update_layout(
            plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
            xaxis_title='Year', yaxis_title='Annual Cost ($)',
            legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
        )
        if show_refinance and refi_start_date:
            fig_costs.add_vline(x=refi_start_date.year, line_dash="dash", line_color="orange", annotation_text="Refinance")
        if purchase_year and eval_start_year <= purchase_year <= eval_end_year:
            fig_costs.add_vline(x=purchase_year, line_dash="dash", line_color="blue", annotation_text="Purchase")
        if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
            fig_costs.add_vline(x=payoff_year, line_dash="dash", line_color="purple", annotation_text="Payoff")
        st.plotly_chart(fig_costs, use_container_width=True)

    with tab_cum:
        st.markdown("**Cumulative Costs**: Compare the cumulative total costs for buying vs. renting over time.")
        cum_cost_data = pd.concat([
            pd.DataFrame({"Year": cost_comparison_df["Year"], "Cost": cost_comparison_df["Cumulative Buying Cost"], "Type": "Buying"}),
            pd.DataFrame({"Year": cost_comparison_df["Year"], "Cost": cost_comparison_df["Cumulative Renting Cost"], "Type": "Renting"})
        ], ignore_index=True)
        fig_cum_costs = px.line(cum_cost_data, x='Year', y='Cost', color='Type', markers=True)
        fig_cum_costs.update_layout(
            plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
            xaxis_title='Year', yaxis_title='Cumulative Cost ($)',
            legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
        )
        if show_refinance and refi_start_date:
            fig_cum_costs.add_vline(x=refi_start_date.year, line_dash="dash", line_color="orange", annotation_text="Refinance")
        if purchase_year and eval_start_year <= purchase_year <= eval_end_year:
            fig_cum_costs.add_vline(x=purchase_year, line_dash="dash", line_color="blue", annotation_text="Purchase")
        if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
            fig_cum_costs.add_vline(x=payoff_year, line_dash="dash", line_color="purple", annotation_text="Payoff")
        st.plotly_chart(fig_cum_costs, use_container_width=True)

    with tab_pct_diff:
        st.markdown("**Cost % Difference**: Percentage difference between buying and renting costs, calculated as ((Buying Cost - Renting Cost) / Renting Cost) * 100.")
        cost_pct_diff = pd.DataFrame({
            "Year": cost_comparison_df["Year"],
            "Cost % Difference": ((cost_comparison_df["Total Buying Cost"] - cost_comparison_df["Total Renting Cost"]) / cost_comparison_df["Total Renting Cost"].replace(0, np.nan)) * 100
        })
        cost_pct_diff["Cost % Difference"] = cost_pct_diff["Cost % Difference"].fillna(0)  # Handle division by zero
        fig_cost_pct_diff = px.line(cost_pct_diff, x='Year', y='Cost % Difference', markers=True)
        fig_cost_pct_diff.update_layout(
            plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
            xaxis_title='Year', yaxis_title='Cost % Difference (Buy - Rent) / Rent (%)',
            showlegend=False
        )
        if show_refinance and refi_start_date:
            fig_cost_pct_diff.add_vline(x=refi_start_date.year, line_dash="dash", line_color="orange", annotation_text="Refinance")
        if purchase_year and eval_start_year <= purchase_year <= eval_end_year:
            fig_cost_pct_diff.add_vline(x=purchase_year, line_dash="dash", line_color="blue", annotation_text="Purchase")
        if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
            fig_cost_pct_diff.add_vline(x=payoff_year, line_dash="dash", line_color="purple", annotation_text="Payoff")
        fig_cost_pct_diff.add_hline(y=0, line_dash='dot', opacity=0.5)
        st.plotly_chart(fig_cost_pct_diff, use_container_width=True)
        st.markdown("**Note**: Zero values indicate no renting costs for that year, preventing division by zero.")

# One-time vs. Repeating Costs Section
st.header("One-time vs. Repeating Costs")
st.markdown("Compare one-time (e.g., closing costs, security deposit) and repeating (e.g., P&I, rent) costs over time.")
with st.container(border=True):
    buy_cost_types = pd.DataFrame({
        'Year': cost_comparison_df['Year'],
        'One-time': cost_comparison_df['Closing Costs'] + cost_comparison_df['Points Costs'] + cost_comparison_df['Emergency'],
        'Repeating': cost_comparison_df['Direct Costs (P&I)'] + cost_comparison_df['PMI'] + cost_comparison_df['Property Taxes'] + cost_comparison_df['Home Insurance'] + cost_comparison_df['Maintenance'] + cost_comparison_df['HOA Fees']
    })
    rent_cost_types = pd.DataFrame({
        'Year': cost_comparison_df['Year'],
        'One-time': cost_comparison_df['Security Deposit'] + cost_comparison_df['Application Fee'] + (cost_comparison_df['Pet Fees'] if pet_fee_frequency == "One-time" else 0),
        'Repeating': cost_comparison_df['Rent'] + cost_comparison_df['Renters Insurance'] + cost_comparison_df['Utilities'] + cost_comparison_df['Lease Renewal Fee'] + cost_comparison_df['Parking Fee'] + (cost_comparison_df['Pet Fees'] if pet_fee_frequency == "Annual" else 0)
    })

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Buying Costs")
        fig_buy_cost_types = go.Figure()
        fig_buy_cost_types.add_trace(go.Bar(x=buy_cost_types['Year'], y=buy_cost_types['One-time'], name='One-time'))
        fig_buy_cost_types.add_trace(go.Bar(x=buy_cost_types['Year'], y=buy_cost_types['Repeating'], name='Repeating'))
        fig_buy_cost_types.update_layout(
            barmode='stack',
            plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
            xaxis_title='Year', yaxis_title='Cost ($)',
            legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
        )
        if show_refinance and refi_start_date:
            fig_buy_cost_types.add_vline(x=refi_start_date.year, line_dash="dash", line_color="orange", annotation_text="Refinance")
        if purchase_year and eval_start_year <= purchase_year <= eval_end_year:
            fig_buy_cost_types.add_vline(x=purchase_year, line_dash="dash", line_color="blue", annotation_text="Purchase")
        if payoff_year and eval_start_year <= payoff_year <= eval_end_year:
            fig_buy_cost_types.add_vline(x=payoff_year, line_dash="dash", line_color="purple", annotation_text="Payoff")
        st.plotly_chart(fig_buy_cost_types, use_container_width=True)

    with col2:
        st.markdown("### Renting Costs")
        fig_rent_cost_types = go.Figure()
        fig_rent_cost_types.add_trace(go.Bar(x=rent_cost_types['Year'], y=rent_cost_types['One-time'], name='One-time'))
        fig_rent_cost_types.add_trace(go.Bar(x=rent_cost_types['Year'], y=rent_cost_types['Repeating'], name='Repeating'))
        fig_rent_cost_types.update_layout(
            barmode='stack',
            plot_bgcolor="rgb(245, 245, 245)", paper_bgcolor="rgb(245, 245, 245)",
            xaxis_title='Year', yaxis_title='Cost ($)',
            legend=dict(yanchor="top", y=1.1, xanchor="left", x=0)
        )
        st.plotly_chart(fig_rent_cost_types, use_container_width=True)

    
with st.expander("Detailed Costs Breakdown by Year (Rent & Buy)", expanded=False):
    cost_breakout = cost_comparison_df[['Year', 'Direct Costs (P&I)', 'PMI', 'Property Taxes', 'Home Insurance', 'Maintenance', 'Emergency', 'HOA Fees', 'Closing Costs', 'Points Costs', 'Total Buying Cost', 'Rent', 'Renters Insurance', 'Security Deposit', 'Utilities', 'Pet Fees', 'Application Fee', 'Lease Renewal Fee', 'Parking Fee', 'Total Renting Cost', 'Cost Difference (Buy - Rent)']]
    cost_breakout['Year'] = cost_breakout['Year'].astype(str)
    buy_cols = ['Direct Costs (P&I)', 'PMI', 'Property Taxes', 'Home Insurance', 'Maintenance', 'Emergency', 'HOA Fees', 'Closing Costs', 'Points Costs', 'Total Buying Cost']
    rent_cols = ['Rent', 'Renters Insurance', 'Security Deposit', 'Utilities', 'Pet Fees', 'Application Fee', 'Lease Renewal Fee', 'Parking Fee', 'Total Renting Cost']
    st.dataframe(
        cost_breakout.style
            .format({col: "${:,.2f}" for col in cost_breakout.columns if col != 'Year'})
            .set_properties(subset=buy_cols, **{'background-color': '#eef2ff'})
            .set_properties(subset=rent_cols, **{'background-color': '#f5f5f5'}),
        hide_index=True
    )


# --- Export: Download all CSVs as a single ZIP ---
with st.expander("Download All Data (ZIP)", expanded=False):
    import io, zipfile
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
        try:
            zf.writestr("amortization_annual.csv", annual_with_extra_df.to_csv(index=False))
            zf.writestr("amortization_monthly.csv", monthly_with_extra_df.to_csv(index=False))
        except Exception:
            pass
        try:
            sy_year_df = annual_with_extra[['Year','Interest Saved (Year)','PMI Saved (Year)']].copy()
            sy_cum_df  = annual_with_extra[['Year','Interest Saved (Cum)','PMI Saved (Cum)']].copy()
            zf.writestr("savings_by_year.csv", sy_year_df.to_csv(index=False))
            zf.writestr("savings_cumulative.csv", sy_cum_df.to_csv(index=False))
        except Exception:
            pass
        try:
            zf.writestr("cost_comparison_full.csv", cost_comparison_df.to_csv(index=False))
        except Exception:
            pass
    st.download_button("Download ZIP", data=zbuf.getvalue(), file_name="rent_vs_buy_export.zip", mime="application/zip")

thick_divider()

# Net Asset Value (Assets - Costs) Over Time Section

st.header("Net Asset Value (Assets - Costs) Over Time")
st.info("**Net Assets = Total Assets − Cumulative Costs.** A negative value means cumulative costs so far exceed assets accumulated to date; a positive value means assets exceed costs.")
with st.container(border=True):
    options = {
        "Buy — Total Assets": ("Buying Total Assets", "Assets", "Buy"),
        "Rent — Total Assets": ("Renting Total Assets", "Assets", "Rent"),
        "Buy — Cumulative Costs": ("Cumulative Buying Cost", "Costs", "Buy"),
        "Rent — Cumulative Costs": ("Cumulative Renting Cost", "Costs", "Rent"),
        "Buy — Net Assets": ("Buying Total Assets", "Net", "Buy"),
        "Rent — Net Assets": ("Renting Total Assets", "Net", "Rent"),
    }
    selected = st.multiselect("Select lines to display", list(options.keys()), ["Buy — Net Assets"])
    long_df = []
    for key in selected:
        col_name, kind, side = options[key]
        if kind == "Net":
            vals = (cost_comparison_df["Buying Total Assets"] - cost_comparison_df["Cumulative Buying Cost"]) if side == "Buy" else (cost_comparison_df["Renting Total Assets"] - cost_comparison_df["Cumulative Renting Cost"])
            label = f"{side} — Net Assets"
        else:
            vals = cost_comparison_df[col_name]
            label = f"{side} — {kind}"
        long_df.append(pd.DataFrame({"Year": cost_comparison_df["Year"], "Value": vals, "Series": label}))
    nav_long = pd.concat(long_df, ignore_index=True) if long_df else pd.DataFrame(columns=["Year","Value","Series"])
    fig_nav = px.line(nav_long, x="Year", y="Value", color="Series", markers=True)
    fig_nav.update_layout(plot_bgcolor="rgb(245,245,245)", paper_bgcolor="rgb(245,245,245)")
    st.plotly_chart(fig_nav, use_container_width=True)


# =====================================================
# 4) Investment Simulation — Stochastic (t for brokerage, lognormal for housing)
#    NOTE: Sections 1–3 are deterministic (fixed assumptions) to set a baseline.
#          Sections 4–5 introduce statistical modeling to capture uncertainty.
# =====================================================

section_header("4) Investment Simulation — Stochastic", "Deterministic baseline above; uncertainty introduced here")

# -----------------------------------------------------
# Explanatory container and parameter inputs
# -----------------------------------------------------

with st.container(border=True):
    st.markdown("**Sections 1–3 are deterministic.** They use fixed returns for clarity and baseline understanding. "
                "**Sections 4–5** introduce uncertainty using statistical distributions.")
    colA, colB, colC = st.columns([1,1,1])
    with colA:
        t_mean = st.number_input("Brokerage annual mean (%)", value=st.session_state.get("brokerage_mean_pct", 7.0), step=0.1, key="t_mean_pct")
        t_std  = st.number_input("Brokerage annual std. dev. (%)", value=st.session_state.get("brokerage_std_pct", 15.0), step=0.5, key="t_std_pct")
    with colB:
        t_df   = st.number_input("Brokerage t-dist degrees of freedom (ν>2)", value=st.session_state.get("brokerage_df", 7), min_value=3, max_value=1000, step=1, key="t_df")
        rng_seed_one = st.text_input("Optional seed (single-path)", value=st.session_state.get("seed_one", ""), help="Set a number for reproducible single-path simulation.")
    with colC:
        ln_mean = st.number_input("Housing annual mean (%)", value=st.session_state.get("housing_mean_pct", 3.0), step=0.1, key="ln_mean_pct")
        ln_std  = st.number_input("Housing annual std. dev. (%)", value=st.session_state.get("housing_std_pct", 8.0), step=0.5, key="ln_std_pct")

    st.subheader("Distributions (based on your parameters)")
    rng_vis = np.random.default_rng(seed_val if "seed_val" in globals() and seed_val is not None else None)
    vis_bro = sample_t_returns(10000, t_mean, t_std, t_df, rng_vis)
    vis_home = sample_lognormal_returns(10000, ln_mean, ln_std, rng_vis)
    fig_d1 = px.histogram(x=vis_bro*100, nbins=60, title="Brokerage: t-distribution (annual %)", labels={'x':'% return'})
    fig_d2 = px.histogram(x=vis_home*100, nbins=60, title="Housing: lognormal (annual %)", labels={'x':'% return'})
    st.plotly_chart(fig_d1, use_container_width=True)
    st.plotly_chart(fig_d2, use_container_width=True)
    st.caption("t-distribution is scaled to your mean & stdev; housing uses a lognormal on gross (1+r) with parameters fitted from your mean & stdev.")

    # Advanced parameters (to retain prior visuals and controls)
    
    # Years horizon follows the cost comparison if available
    try:
        years_list = cost_comparison_df["Year"].tolist()
    except Exception:
        try:
            years_list = list(range(purchase_year, purchase_year + loan_years + 1))
        except Exception:
            years_list = list(range(1, int(n_years_sim)+1))
    n_years = len(years_list)

    # Helpers to align with requested parameterization
    def sample_t_returns(n, mean_pct, std_pct, df, rng):
        mean = mean_pct/100.0
        std  = std_pct/100.0
        # standard Student t: var = df/(df-2). Scale to unit variance then to target std.
        t = rng.standard_t(df, size=n)
        t_unit = t * np.sqrt((df-2)/df)
        return mean + std * t_unit

    def sample_lognormal_returns(n, mean_pct, std_pct, rng):
        # Fit lognormal for gross 1+r given arithmetic mean/stdev of r
        m = 1.0 + mean_pct/100.0
        s = std_pct/100.0
        sigma2 = np.log(1 + (s**2)/(m**2))
        sigma = np.sqrt(sigma2)
        mu = np.log(m) - 0.5*sigma2
        gross = rng.lognormal(mean=mu, sigma=sigma, size=n)
        return gross - 1.0

    # Single-path RNG
    if rng_seed_one.strip():
        try:
            seed_val = int(rng_seed_one.strip())
        except:
            seed_val = None
    else:
    # if empty string, we keep None for non-deterministic run
        seed_val = None
    rng = np.random.default_rng(seed_val)

    bro_ret = sample_t_returns(n_years, t_mean, t_std, t_df, rng)
    home_ret = sample_lognormal_returns(n_years, ln_mean, ln_std, rng)

    # Pull baseline inputs (with safe fallbacks)
    try:
        current_rent = cost_of_rent
        current_renters_insurance = renters_insurance
        current_deposit = security_deposit
        current_utilities = rental_utilities
        current_pet_fee = pet_fee
        current_parking = parking_fee
    except Exception:
        current_rent = 2000.0
        current_renters_insurance = 300.0
        current_deposit = 2000.0
        current_utilities = 2000.0
        current_pet_fee = 0.0
        current_parking = 0.0

    # Annual amortization basis (ensure annual_df exists)
    if 'annual_df' not in globals():
        try:
            annual_df = annual_with_extra_df.copy()
        except Exception:
            if 'cost_comparison_df' in locals():
                annual_df = cost_comparison_df.copy()
            else:
                annual_df = pd.DataFrame()
            annual_df = pd.DataFrame()
    # Ensure Date column exists if we depend on .dt
    if 'Date' not in annual_df.columns:
        if isinstance(annual_df.index, pd.DatetimeIndex):
            annual_df = annual_df.reset_index().rename(columns={"index": "Date"})
        else:
            # fabricate a yearly Date for safety (won't affect sums if unused)
            start_date = datetime.today()
            if len(annual_df) == 0:
                annual_df = pd.DataFrame({"Date": pd.date_range(start=start_date, periods=n_years, freq="Y")})
            else:
                annual_df["Date"] = pd.date_range(start=start_date, periods=len(annual_df), freq="Y")

    home_value = float(purchase_price) if 'purchase_price' in globals() else 0.0
    base_home_value = float(purchase_price) if 'purchase_price' in globals() else 0.0
    buy_investment = 0.0    # brokerage associated to Buy scenario (from cost differences)
    rent_investment = float(down_payment if 'down_payment' in globals() else 0.0) + float(security_deposit if 'security_deposit' in globals() else 0.0)

    buy_nw_path = []
    rent_nw_path = []
    comp_down = []
    comp_amort = []
    comp_extra = []
    comp_apprec = []
    comp_broker = []

    # ---------- Single-path engine (stochastic) ----------

    for i, year in enumerate(years_list):
        # Mortgage-linked items for this calendar year
        if 'Date' in annual_df.columns and not annual_df.empty and year in annual_df["Date"].dt.year.values:
            mask = (annual_df["Date"].dt.year == year)
            p_and_i = annual_df.loc[mask, "P&I"].sum() if "P&I" in annual_df.columns else 0.0
            pmi = annual_df.loc[mask, "PMI"].sum() if "PMI" in annual_df.columns else 0.0
            year_balance = annual_df.loc[mask, "Balance"].iloc[-1] if "Balance" in annual_df.columns else 0.0
            extra_prin = annual_df.loc[mask, "Extra Principal Payments"].sum() if "Extra Principal Payments" in annual_df.columns else 0.0
            sched_prin = annual_df.loc[mask, "Principal"].sum() if "Principal" in annual_df.columns else 0.0
        else:
            p_and_i = 0.0; pmi = 0.0; year_balance = 0.0; extra_prin = 0.0; sched_prin = 0.0

        # Indirect/recurring housing costs (deterministic inflation, baseline)
        def _infl(base, pct, yrs):
            try:
                return float(base) * ((1 + float(pct)/100.0) ** float(yrs))
            except Exception:
                return 0.0

        yr_idx = i if 'purchase_year' not in globals() else (year - purchase_year)
        year_taxes = _infl(taxes if 'taxes' in globals() else 0.0, annual_property_tax_increase if 'annual_property_tax_increase' in globals() else 0.0, yr_idx)
        year_insurance = _infl(insurance if 'insurance' in globals() else 0.0, annual_insurance_increase if 'annual_insurance_increase' in globals() else 0.0, yr_idx)
        year_maintenance = _infl(maintenance if 'maintenance' in globals() else 0.0, annual_maintenance_increase if 'annual_maintenance_increase' in globals() else 0.0, yr_idx)
        year_hoa = _infl(hoa if 'hoa' in globals() else 0.0, annual_hoa_increase if 'annual_hoa_increase' in globals() else 0.0, yr_idx)

        # One-time costs treated as homeowner costs regardless of financing (opportunity cost)
        add_purchase_closing = float(closing_costs if 'closing_costs' in globals() else 0.0) if (('purchase_year' in globals()) and (year == purchase_year)) else 0.0
        add_purchase_points  = float(points_cost if 'points_cost' in globals() else 0.0) if (('purchase_year' in globals()) and (year == purchase_year)) else 0.0
        add_refi_points = 0.0
        try:
            if 'show_refinance' in globals() and show_refinance and 'refi_start_date' in globals() and refi_start_date and refi_start_date.year == year:
                add_refi_points = float(refi_points_cost) if 'refi_points_cost' in globals() else float(refi_costs) if 'refi_costs' in globals() else 0.0
        except Exception:
            pass

        indirect_costs = pmi + year_taxes + year_insurance + year_maintenance + year_hoa + add_purchase_closing + add_purchase_points + add_refi_points
        buy_cost = p_and_i + indirect_costs

        # Renting costs
        year_rent = float(current_rent) * 12.0
        year_renters_insurance = float(current_renters_insurance)
        year_deposit = float(current_deposit) if year == years_list[0] else 0.0
        year_utilities = float(current_utilities)
        year_pet_fee = float(current_pet_fee) if (('pet_fee_frequency' in globals() and pet_fee_frequency=='Annual') or (year==years_list[0])) else 0.0
        year_application_fee = float(application_fee) if 'application_fee' in globals() and year == years_list[0] else 0.0
        year_renewal_fee = float(lease_renewal_fee) if 'lease_renewal_fee' in globals() and year > years_list[0] else 0.0
        year_parking = float(current_parking)

        rent_cost = year_rent + year_renters_insurance + year_deposit + year_utilities + year_pet_fee + year_application_fee + year_renewal_fee + year_parking

        # Update home value stochastically
        home_value *= (1 + home_ret[i])

        # Equity composition
        equity_principal = float(purchase_price if 'purchase_price' in globals() else 0.0) - float(year_balance)
        appreciation = home_value - base_home_value
        equity_total = equity_principal + max(0.0, appreciation)

        # Invest cost differences using SAME brokerage draw (apples-to-apples)
        r_b = bro_ret[i]
        if buy_cost > rent_cost:
            rent_investment = rent_investment * (1 + r_b) + (buy_cost - rent_cost)
            buy_investment = buy_investment * (1 + r_b)
        else:
            buy_investment = buy_investment * (1 + r_b) + (rent_cost - buy_cost)
            rent_investment = rent_investment * (1 + r_b)

        buy_total_assets = equity_total + buy_investment
        rent_total_assets = rent_investment

        buy_nw_path.append(buy_total_assets)
        rent_nw_path.append(rent_total_assets)

        comp_down.append(float(down_payment) if 'down_payment' in globals() else 0.0 if i>0 else float(down_payment) if 'down_payment' in globals() else 0.0)
        comp_amort.append(max(0.0, equity_principal))
        comp_extra.append(float(extra_prin))
        comp_apprec.append(max(0.0, appreciation))
        comp_broker.append(max(0.0, buy_investment))

        # Inflate renter side items for next year
        infl = (1 + float(annual_rent_increase if 'annual_rent_increase' in globals() else 0.0) / 100.0)
        current_rent *= infl
        current_renters_insurance *= infl
        current_utilities *= infl
        current_parking *= infl
        if 'pet_fee_frequency' in globals() and pet_fee_frequency == "Annual":
            current_pet_fee *= infl

    # ---------------- Visuals: Single-path ----------------
    x = years_list
    fig_one = go.Figure()
    fig_one.add_trace(go.Scatter(x=x, y=buy_nw_path, mode="lines", name="Buy — Net Worth (stochastic)"))
    fig_one.add_trace(go.Scatter(x=x, y=rent_nw_path, mode="lines", name="Rent — Net Worth (stochastic)"))
    if 'refi_start_date' in globals() and refi_start_date:
        fig_one.add_vline(x=refi_start_date.year, line_dash="dash", line_color="orange")
    if 'purchase_year' in globals():
        fig_one.add_vline(x=purchase_year, line_dash="dash", line_color="blue")
    st.plotly_chart(fig_one, use_container_width=True)

    st.caption("Monthly payment logic (from Sections 1–3) reflects points buy-downs and any refinance you specified. "
               "In Sections 4–5, **points and refinance costs are counted as homeowner costs** regardless of whether they were financed or paid upfront (opportunity cost). "
               "Vertical dashed lines mark **purchase** (blue) and **refinance** (orange) years.")

# ---------------- Visuals: Distributions ----------------

thick_divider()

# =====================================================
# 5) Monte Carlo — Probabilistic Outcomes
# =====================================================

section_header("5) Monte Carlo — Probabilistic Outcomes", "")
run_mc = st.button("Run Monte Carlo with updated parameters")

with st.container(border=True):
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        n_trials = st.number_input("Number of trials", value=500, min_value=100, max_value=20000, step=100,
                                   help="More trials improves stability but takes longer.")
    with col2:
        seed_text = st.text_input("Optional seed (Monte Carlo)", value="", help="Set a number for reproducible runs.")
    with col3:
        st.info("Primary chart shows **Buy probability** each year. Rent probability = 1 − Buy.")
    if n_trials > 10000:
        st.warning("High trial count may be slow. Consider using a seed for reproducibility.")
    if not run_mc:
        st.caption("Parameters changed or no run yet. Click **Run Monte Carlo with updated parameters** to refresh results.")
        st.stop()
    try:
        seed_mc = int(seed_text.strip()) if seed_text.strip() else None
    except:
        seed_mc = None
    rng_mc = np.random.default_rng(seed_mc)

    years = years_list if 'years_list' in globals() else list(range(1, n_years+1))
    T = len(years)

    buy_gt_rent_counts = np.zeros(T, dtype=int)
    buy_paths = np.zeros((n_trials, T))
    rent_paths = np.zeros((n_trials, T))

    progress = st.progress(0.0)

    for t in range(n_trials):
        bro = sample_t_returns(T, t_mean, t_std, t_df, rng_mc)
        hom = sample_lognormal_returns(T, ln_mean, ln_std, rng_mc)

        # Re-run the single-path engine fast for each trial
        try:
            current_rent = cost_of_rent
            current_renters_insurance = renters_insurance
            current_deposit = security_deposit
            current_utilities = rental_utilities
            current_pet_fee = pet_fee
            current_parking = parking_fee
        except Exception:
            current_rent = 2000.0
            current_renters_insurance = 300.0
            current_deposit = 2000.0
            current_utilities = 2000.0
            current_pet_fee = 0.0
            current_parking = 0.0

        home_value = float(purchase_price) if 'purchase_price' in globals() else 0.0
        base_home_value = home_value
        buy_investment = 0.0
        rent_investment = float(down_payment if 'down_payment' in globals() else 0.0) + float(security_deposit if 'security_deposit' in globals() else 0.0)

        for i, year in enumerate(years):
            if 'Date' in annual_df.columns and not annual_df.empty and year in annual_df["Date"].dt.year.values:
                mask = (annual_df["Date"].dt.year == year)
                p_and_i = annual_df.loc[mask, "P&I"].sum() if "P&I" in annual_df.columns else 0.0
                pmi = annual_df.loc[mask, "PMI"].sum() if "PMI" in annual_df.columns else 0.0
                year_balance = annual_df.loc[mask, "Balance"].iloc[-1] if "Balance" in annual_df.columns else 0.0
            else:
                p_and_i = 0.0; pmi = 0.0; year_balance = 0.0

            def _infl(base, pct, yrs):
                try:
                    return float(base) * ((1 + float(pct)/100.0) ** float(yrs))
                except Exception:
                    return 0.0
            yr_idx = i if 'purchase_year' not in globals() else (year - purchase_year)
            year_taxes = _infl(taxes if 'taxes' in globals() else 0.0, annual_property_tax_increase if 'annual_property_tax_increase' in globals() else 0.0, yr_idx)
            year_insurance = _infl(insurance if 'insurance' in globals() else 0.0, annual_insurance_increase if 'annual_insurance_increase' in globals() else 0.0, yr_idx)
            year_maintenance = _infl(maintenance if 'maintenance' in globals() else 0.0, annual_maintenance_increase if 'annual_maintenance_increase' in globals() else 0.0, yr_idx)
            year_hoa = _infl(hoa if 'hoa' in globals() else 0.0, annual_hoa_increase if 'annual_hoa_increase' in globals() else 0.0, yr_idx)

            add_purchase_closing = float(closing_costs if 'closing_costs' in globals() else 0.0) if (('purchase_year' in globals()) and (year == purchase_year)) else 0.0
            add_purchase_points  = float(points_cost if 'points_cost' in globals() else 0.0) if (('purchase_year' in globals()) and (year == purchase_year)) else 0.0
            add_refi_points = 0.0
            try:
                if 'show_refinance' in globals() and show_refinance and 'refi_start_date' in globals() and refi_start_date and refi_start_date.year == year:
                    add_refi_points = float(refi_points_cost) if 'refi_points_cost' in globals() else float(refi_costs) if 'refi_costs' in globals() else 0.0
            except Exception:
                pass

            indirect_costs = pmi + year_taxes + year_insurance + year_maintenance + year_hoa + add_purchase_closing + add_purchase_points + add_refi_points
            buy_cost = p_and_i + indirect_costs

            year_rent = float(current_rent) * 12.0
            year_renters_insurance = float(current_renters_insurance)
            year_deposit = float(current_deposit) if year == years[0] else 0.0
            year_utilities = float(current_utilities)
            year_pet_fee = float(current_pet_fee) if (('pet_fee_frequency' in globals() and pet_fee_frequency=='Annual') or (year==years[0])) else 0.0
            year_application_fee = float(application_fee) if 'application_fee' in globals() and year == years[0] else 0.0
            year_renewal_fee = float(lease_renewal_fee) if 'lease_renewal_fee' in globals() and year > years[0] else 0.0
            year_parking = float(current_parking)

            rent_cost = year_rent + year_renters_insurance + year_deposit + year_utilities + year_pet_fee + year_application_fee + year_renewal_fee + year_parking

            home_value *= (1 + hom[i])
            equity_principal = float(purchase_price if 'purchase_price' in globals() else 0.0) - float(year_balance)
            appreciation = home_value - base_home_value
            equity_total = equity_principal + max(0.0, appreciation)

            r_b = bro[i]
            if buy_cost > rent_cost:
                rent_investment = rent_investment * (1 + r_b) + (buy_cost - rent_cost)
                buy_investment = buy_investment * (1 + r_b)
            else:
                buy_investment = buy_investment * (1 + r_b) + (rent_cost - buy_cost)
                rent_investment = rent_investment * (1 + r_b)

            buy_total_assets = equity_total + buy_investment
            rent_total_assets = rent_investment

            buy_paths[t, i] = buy_total_assets
            rent_paths[t, i] = rent_total_assets

            infl = (1 + float(annual_rent_increase if 'annual_rent_increase' in globals() else 0.0) / 100.0)
            current_rent *= infl
            current_renters_insurance *= infl
            current_utilities *= infl
            current_parking *= infl
            if 'pet_fee_frequency' in globals() and pet_fee_frequency == "Annual":
                current_pet_fee *= infl

        buy_gt_rent_counts += (buy_paths[t] > rent_paths[t])

        if (t+1) % max(1, n_trials//50) == 0:
            progress.progress((t+1)/n_trials)

    # Probability that Buy > Rent each year (NEW)
    buy_prob = buy_gt_rent_counts / n_trials
    fig_prob = go.Figure()
    fig_prob.add_trace(go.Scatter(x=years, y=buy_prob, mode="lines", name="P(Buy beats Rent)"))
    fig_prob.add_hline(y=0.5, line_dash='dot', opacity=0.5)
    fig_prob.update_yaxes(title='Probability (0–1)', range=[0,1])
    if 'refi_start_date' in globals() and refi_start_date:
        fig_prob.add_vline(x=refi_start_date.year, line_dash="dash", line_color="orange")
    if 'purchase_year' in globals():
        fig_prob.add_vline(x=purchase_year, line_dash="dash", line_color="blue")
    st.plotly_chart(fig_prob, use_container_width=True)
    st.caption("We plot **Buy** probability for clarity. **Rent** probability is `1 − Buy`.")

    # VISUAL from earlier version: two-line % wins per year
    df_wins = pd.DataFrame({
        "Year": years,
        "% Buy Wins": (buy_paths > rent_paths).mean(axis=0) * 100.0,
        "% Rent Wins": (rent_paths > buy_paths).mean(axis=0) * 100.0
    })
    fig_wins = px.line(df_wins.melt(id_vars=["Year"], var_name="Scenario", value_name="Percent"), x="Year", y="Percent", color="Scenario", markers=True, title="% of Trials Each Scenario Wins (per year)")
    st.plotly_chart(fig_wins, use_container_width=True)

    # Box & whisker plots of final-year net worth (from earlier version)
    fig_box = go.Figure()
    fig_box.add_trace(go.Box(y=buy_paths[:, -1], name="Buy — Net Worth (Final Year)"))
    fig_box.add_trace(go.Box(y=rent_paths[:, -1], name="Rent — Net Worth (Final Year)"))
    st.plotly_chart(fig_box, use_container_width=True)

    