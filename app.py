import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
from datetime import datetime, timedelta

# ----------------------------- PAGE CONFIG -----------------------------
st.set_page_config(page_title="Rent vs. Buy Decision Support Framework", layout="wide")
st.title("Rent vs. Buy Decision Support Framework")

# ----------------------------- INSTRUCTIONS -----------------------------
with st.expander("Welcome & Instructions", expanded=False):
    st.markdown("""
    This dashboard helps you decide whether to **rent or buy** your primary residence by analyzing mortgage costs.

    **Key Outputs:**
    - Amortization schedules (monthly and annual) for original loan and refinance scenarios.
    - Metrics: Monthly payment, total interest, PMI, and payoff time.
    - Comparison of original loan vs. refinance.
    - Interest savings from biweekly vs. monthly payments.

    **How to Use:**
    1. Enter purchase details, loan terms, and mortgage type.
    2. Specify extra payments and refinance options (if applicable).
    3. Review metrics, schedules, and balance chart.
    4. Download schedules for further analysis.

    **Methodology:**
    - Biweekly payments: 26 payments/year (equivalent to 13 monthly payments).
    - Variable-rate mortgages adjust based on your rate schedule.
    - Extra payments reduce principal and interest.
    - Refinance transitions to new loan terms at the specified date.
    - PMI applies until equity reaches the specified threshold.
    """)

# ----------------------------- SIDEBAR -----------------------------
with st.sidebar:
    st.image("https://via.placeholder.com/250", caption="EyesWideOpenLogo")  # Replace with actual logo URL
    st.markdown("Tool developed by Eric Hubbard")
    st.markdown("[KnowTheCostFinancial.com](https://knowthecostfinancial.com)")

    # 1️⃣ General Inputs
    with st.expander("General Inputs", expanded=True):
        eval_start_year = st.number_input("Evaluation Start Year", value=2025, step=1, min_value=2000, max_value=2100)
        eval_end_year = st.number_input("Evaluation End Year", value=2070, step=1, min_value=eval_start_year, max_value=2100)

    # 2️⃣ Purchase Details
    with st.expander("Purchase Details", expanded=True):
        purchase_year = st.number_input("Purchase Year", value=2025, step=1, min_value=eval_start_year, max_value=eval_end_year)
        purchase_price = st.number_input("Purchase Price ($)", value=500_000, step=10_000, min_value=0)
        down_payment = st.number_input("Down Payment ($)", value=100_000, step=1_000, min_value=0, max_value=purchase_price)
        loan_amount = purchase_price - down_payment
        percent_down = (down_payment / purchase_price * 100) if purchase_price > 0 else 0
        st.metric("Loan Amount", f"${loan_amount:,.0f}")
        st.metric("% Down Payment", f"{percent_down:.2f}%")

    # 3️⃣ Loan Terms & Mortgage
    with st.expander("Loan Terms & Mortgage", expanded=True):
        loan_years = st.number_input("Loan Length (Years)", value=30, step=1, min_value=1, max_value=50)
        mortgage_rate = st.number_input("Mortgage Rate (%)", value=5.0, step=0.01, min_value=0.0, format="%.3f")
        pmi_rate = st.number_input("PMI Rate (%)", value=0.20, step=0.01, min_value=0.0)
        pmi_equity_threshold = st.number_input("PMI Paid Until Equity (%)", value=20, step=1, min_value=0, max_value=100)
        payment_frequency = st.radio("Payment Frequency", ["Monthly", "Biweekly"], index=0)
        mortgage_type = st.radio("Mortgage Type", ["Fixed", "Variable"], index=0)

        rate_schedule = None
        if mortgage_type == "Variable":
            st.subheader("Variable Rate Schedule")
            default_schedule = pd.DataFrame({"Year": [1, 5, 10], "Rate (%)": [mortgage_rate, 6.5, 7.0]})
            rate_schedule = st.data_editor(
                default_schedule,
                column_config={
                    "Year": st.column_config.NumberColumn("Year", min_value=1, max_value=loan_years, step=1),
                    "Rate (%)": st.column_config.NumberColumn("Rate (%)", min_value=0.0, step=0.1)
                },
                hide_index=True,
                num_rows="dynamic"
            )

    # 4️⃣ Refinance Options
    with st.expander("Refinance Options", expanded=False):
        show_refinance = st.checkbox("Model a Refinance?", value=False)
        refi_rate = None
        refi_term_years = None
        refi_start_date = None
        refi_costs = None
        refi_payment_frequency = None
        refi_mortgage_type = None
        refi_rate_schedule = None

        if show_refinance:
            refi_rate = st.number_input("Refinance Rate (%)", value=5.0, step=0.01, min_value=0.0, format="%.3f")
            refi_term_years = st.number_input("Refinance Term (Years)", value=30, step=1, min_value=1, max_value=50)
            refi_start_date = st.date_input("Refinance Start Date", min_value=datetime(purchase_year, 1, 1), max_value=datetime(purchase_year + loan_years, 12, 31))
            refi_costs = st.number_input("Closing Costs ($)", value=3000, step=500, min_value=0)
            roll_costs = st.radio("Refinance Cost Method", ["Add to New Loan Balance", "Pay Upfront"], index=0)
            refi_payment_frequency = st.radio("Refinance Payment Frequency", ["Monthly", "Biweekly"], index=0)
            refi_mortgage_type = st.radio("Refinance Mortgage Type", ["Fixed", "Variable"], index=0)

            if refi_mortgage_type == "Variable":
                st.subheader("Refinance Variable Rate Schedule")
                default_refi_schedule = pd.DataFrame({"Year": [1, 5, 10], "Rate (%)": [refi_rate, 6.5, 7.0]})
                refi_rate_schedule = st.data_editor(
                    default_refi_schedule,
                    column_config={
                        "Year": st.column_config.NumberColumn("Year", min_value=1, max_value=refi_term_years, step=1),
                        "Rate (%)": st.column_config.NumberColumn("Rate (%)", min_value=0.0, step=0.1)
                    },
                    hide_index=True,
                    num_rows="dynamic"
                )

    # 5️⃣ Extra Principal Payments
    with st.expander("Extra Principal Payments", expanded=False):
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
                "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100),
                "Frequency": st.column_config.SelectboxColumn("Frequency", options=["One-time", "Monthly", "Quarterly", "Annually", "Every X Years"]),
                "Start Year": st.column_config.NumberColumn("Start Year", min_value=purchase_year, max_value=purchase_year + loan_years, step=1),
                "Start Month": st.column_config.NumberColumn("Start Month", min_value=1, max_value=12, step=1),
                "End Year": st.column_config.NumberColumn("End Year", min_value=purchase_year, max_value=purchase_year + loan_years, step=1),
                "End Month": st.column_config.NumberColumn("End Month", min_value=1, max_value=12, step=1),
                "Interval (Years)": st.column_config.NumberColumn("Interval (Years)", min_value=1, step=1)
            },
            hide_index=True,
            num_rows="dynamic"
        )

    # 6️⃣ Ongoing Expenses
    with st.expander("Ongoing Expenses", expanded=False):
        default_property_expenses = pd.DataFrame({
            "Category": ["Routine Maintenance", "Property Taxes", "Home Insurance"],
            "Amount ($)": [6000, 8000, 1100]
        })
        property_expenses = st.data_editor(
            default_property_expenses,
            column_config={
                "Category": st.column_config.TextColumn("Category"),
                "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100)
            },
            hide_index=True,
            num_rows="dynamic"
        )

        default_emergency_expenses = pd.DataFrame({
            "Category": ["Appliance Replacement", "Septic Repair", "Roof Repair"],
            "Amount ($)": [1500, 8000, 12000],
            "Year": [purchase_year + 1, purchase_year + 3, purchase_year + 5],
            "Month": [5, 7, 9]
        })
        emergency_expenses = st.data_editor(
            default_emergency_expenses,
            column_config={
                "Category": st.column_config.TextColumn("Category"),
                "Amount ($)": st.column_config.NumberColumn("Amount ($)", min_value=0, step=100),
                "Year": st.column_config.NumberColumn("Year", min_value=purchase_year, max_value=purchase_year + loan_years, step=1),
                "Month": st.column_config.NumberColumn("Month", min_value=1, max_value=12, step=1)
            },
            hide_index=True,
            num_rows="dynamic"
        )

    # 7️⃣ Appreciation & Growth
    with st.expander("Appreciation & Growth", expanded=False):
        annual_appreciation = st.number_input("Annual Housing Appreciation (%)", value=3.5, step=0.1, min_value=0.0)
        annual_maintenance_increase = st.number_input("Annual Maintenance Increase (%)", value=3.0, step=0.1, min_value=0.0)
        annual_insurance_increase = st.number_input("Annual Insurance Increase (%)", value=3.0, step=0.1, min_value=0.0)

    # 8️⃣ Rental Assumptions
    with st.expander("Rental Assumptions", expanded=False):
        cost_of_rent = st.number_input("Initial Rent ($)", value=3000, step=50, min_value=0)
        annual_rent_increase = st.number_input("Annual Rent Increase (%)", value=4.0, step=0.1, min_value=0.0)

    # 9️⃣ Investments
    with st.expander("Investments", expanded=False):
        annual_stock_return = st.number_input("Annual Stock Market Return (%)", value=8.0, step=0.1, min_value=0.0)
        initial_tax_brokerage_balance = st.number_input("Initial Taxable Brokerage Balance ($)", value=250_000, step=10_000, min_value=0)

    # 10️⃣ Monte Carlo
    with st.expander("Monte Carlo Inputs", expanded=False):
        mc_simulation_stock_mean = st.number_input("Stock Market Return Mean (%)", value=8.0, step=0.1, min_value=0.0)
        mc_simulation_stock_std = st.number_input("Stock Market Return Std. Dev. (%)", value=15.0, step=0.1, min_value=0.0)

# ----------------------------- FUNCTIONS -----------------------------
@st.cache_data
def expand_extra_payments(df, start_year, loan_years, frequency):
    extra_schedule = {}
    start_date = datetime(start_year, 1, 1)
    periods_per_year = 12 if frequency == "Monthly" else 26
    n_payments = loan_years * periods_per_year
    delta = pd.DateOffset(months=1) if frequency == "Monthly" else timedelta(days=14)
    payment_dates = [start_date + i * delta for i in range(n_payments)]

    for _, row in df.iterrows():
        amt = row["Amount ($)"]
        freq = row["Frequency"]
        start_y = int(row["Start Year"])
        start_m = int(row["Start Month"])
        end_y = int(row["End Year"])
        end_m = int(row["End Month"])
        interval = int(row["Interval (Years)"]) if not pd.isna(row["Interval (Years)"]) else 1

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
                apply_pdate = min(matching_dates)
                extra_schedule[apply_pdate] = extra_schedule.get(apply_pdate, 0) + amt

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

    # Initialize rate schedule
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

    # Calculate periods
    n_periods = years * periods_per_year
    if refi_start_date and refi_years and refi_periods_per_year:
        refi_start_period = int(((refi_start_date - start_date).days / 365.25) * periods_per_year)
        n_periods = max(n_periods, refi_start_period + refi_years * refi_periods_per_year)

    delta = pd.DateOffset(months=1) if periods_per_year == 12 else timedelta(days=14)
    refi_delta = pd.DateOffset(months=1) if refi_periods_per_year == 12 else timedelta(days=14) if refi_periods_per_year else delta

    # Initialize payment
    year_elapsed = max(1, start_date.year - purchase_year + 1)
    applicable_rates = rate_schedule[rate_schedule["Year"] <= year_elapsed].sort_values("Year")
    current_rate = applicable_rates["Rate (%)"].iloc[-1] / 100 if not applicable_rates.empty else mortgage_rate / 100
    monthly_payment = npf.pmt(current_rate / 12, years * 12, -principal)
    payment = round(monthly_payment, 2) if periods_per_year == 12 else round(monthly_payment * 12 / 26, 2)

    is_refinanced = False
    refi_start_period = 0
    for n in range(n_periods):
        current_date = start_date + (n * delta if not is_refinanced else (n - refi_start_period) * refi_delta)
        year_elapsed = max(1, current_date.year - purchase_year + 1)

        # Handle refinance
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

        # Update rate for variable mortgage
        applicable_rates = rate_schedule[rate_schedule["Year"] <= year_elapsed].sort_values("Year")
        current_rate = applicable_rates["Rate (%)"].iloc[-1] / 100 if not applicable_rates.empty else (refi_mortgage_rate / 100 if is_refinanced and refi_mortgage_rate else mortgage_rate / 100)

        if mortgage_type == "Variable" and n > 0:
            remaining_periods = (years if not is_refinanced else refi_years) * periods_per_year - n
            monthly_payment = npf.pmt(current_rate / 12, remaining_periods / (periods_per_year / 12), -balance)
            payment = round(monthly_payment, 2) if periods_per_year == 12 else round(monthly_payment * 12 / 26, 2)

        # Calculate PMI
        equity = (purchase_price - balance) / purchase_price * 100 if purchase_price > 0 else 0
        pmi_payment = round((principal * pmi_rate / 100 / 12), 2) if equity < pmi_equity_threshold else 0

        # Calculate payment components
        interest = round(balance * (current_rate / periods_per_year), 2)
        principal_paid = round(payment - interest, 2)
        extra = extra_schedule.get(current_date, 0)

        if principal_paid + extra > balance:
            principal_paid = round(balance - extra, 2)
            payment = round(principal_paid + interest, 2)

        balance = round(balance - (principal_paid + extra), 2)

        schedule.append({
            "Payment #": n + 1,
            "Date": current_date,
            "Payment": payment,
            "Interest": interest,
            "Principal": principal_paid,
            "Extra": extra,
            "PMI": pmi_payment,
            "Balance": balance,
            "Loan Type": "Refinance" if is_refinanced else "Original"
        })

        if balance <= 0:
            break

    df = pd.DataFrame(schedule)
    df_monthly = df.groupby(df["Date"].dt.to_period("M")).agg({
        "Payment": "sum",
        "Interest": "sum",
        "Principal": "sum",
        "Extra": "sum",
        "PMI": "sum",
        "Balance": "last",
        "Payment #": "count",
        "Loan Type": "last"
    }).reset_index()
    df_monthly.rename(columns={"Payment #": "Num Payments"}, inplace=True)
    df_monthly["Date"] = df_monthly["Date"].dt.to_timestamp()

    df_annual = df.groupby(df["Date"].dt.to_period("Y")).agg({
        "Payment": "sum",
        "Interest": "sum",
        "Principal": "sum",
        "Extra": "sum",
        "PMI": "sum",
        "Balance": "last",
        "Payment #": "count",
        "Loan Type": "last"
    }).reset_index()
    df_annual.rename(columns={"Payment #": "Num Payments"}, inplace=True)
    df_annual["Date"] = df_annual["Date"].dt.to_timestamp()

    return df, df_monthly, df_annual

def get_remaining_balance(schedule_df, refi_date):
    refi_date = pd.to_datetime(refi_date)
    mask = schedule_df["Date"] <= refi_date
    return schedule_df.loc[mask, "Balance"].iloc[-1] if mask.any() else schedule_df["Balance"].iloc[0]

# ----------------------------- CALCULATIONS -----------------------------
periods_per_year = 12 if payment_frequency == "Monthly" else 26
extra_schedule = expand_extra_payments(extra_payments, purchase_year, loan_years, payment_frequency)

# Original loan schedule
original_schedule_df, original_monthly_df, original_annual_df = amortization_schedule(
    principal=loan_amount,
    years=loan_years,
    periods_per_year=periods_per_year,
    start_date=f"{purchase_year}-01-01",
    extra_schedule=extra_schedule,
    rate_schedule=rate_schedule,
    mortgage_type=mortgage_type,
    purchase_year=purchase_year,
    mortgage_rate=mortgage_rate,
    pmi_rate=pmi_rate,
    pmi_equity_threshold=pmi_equity_threshold,
    purchase_price=purchase_price
)

# Refinance schedule
refi_schedule_df, refi_monthly_df, refi_annual_df = None, None, None
if show_refinance and refi_start_date:
    if refi_rate_schedule is not None and (refi_rate_schedule["Year"].duplicated().any() or refi_rate_schedule["Rate (%)"].min() < 0):
        st.error("Refinance variable rate schedule contains duplicate years or negative rates.")
    else:
        refi_principal = get_remaining_balance(original_schedule_df, refi_start_date) + (refi_costs if roll_costs == "Add to New Loan Balance" else 0)
        refi_schedule_df, refi_monthly_df, refi_annual_df = amortization_schedule(
            principal=loan_amount,
            years=loan_years,
            periods_per_year=periods_per_year,
            start_date=f"{purchase_year}-01-01",
            extra_schedule=extra_schedule,
            rate_schedule=rate_schedule,
            mortgage_type=mortgage_type,
            purchase_year=purchase_year,
            mortgage_rate=mortgage_rate,
            pmi_rate=pmi_rate,
            pmi_equity_threshold=pmi_equity_threshold,
            purchase_price=purchase_price,
            refi_start_date=refi_start_date,
            refi_principal=refi_principal,
            refi_years=refi_term_years,
            refi_periods_per_year=12 if refi_payment_frequency == "Monthly" else 26,
            refi_rate_schedule=refi_rate_schedule,
            refi_mortgage_type=refi_mortgage_type,
            refi_mortgage_rate=refi_rate
        )

# Metrics
original_monthly_payment = original_schedule_df['Payment'].iloc[0] if periods_per_year == 12 else original_schedule_df['Payment'].iloc[0] * 26 / 12
original_payment_per_period = original_schedule_df['Payment'].iloc[0]
original_total_interest = original_schedule_df['Interest'].sum()
original_total_pmi = original_schedule_df['PMI'].sum()
original_payoff_years = len(original_schedule_df) / periods_per_year

refi_monthly_payment = None
refi_payment_per_period = None
refi_total_interest = None
refi_total_pmi = None
refi_payoff_years = None
if refi_schedule_df is not None:
    refi_periods_per_year = 12 if refi_payment_frequency == "Monthly" else 26
    refi_monthly_payment = refi_schedule_df['Payment'].iloc[0] if refi_periods_per_year == 12 else refi_schedule_df[refi_schedule_df["Loan Type"] == "Refinance"]['Payment'].iloc[0] * 26 / 12 if not refi_schedule_df[refi_schedule_df["Loan Type"] == "Refinance"].empty else refi_schedule_df['Payment'].iloc[0] * 26 / 12
    refi_payment_per_period = refi_schedule_df['Payment'].iloc[0] if refi_periods_per_year == 12 else refi_schedule_df[refi_schedule_df["Loan Type"] == "Refinance"]['Payment'].iloc[0] if not refi_schedule_df[refi_schedule_df["Loan Type"] == "Refinance"].empty else refi_schedule_df['Payment'].iloc[0]
    refi_total_interest = refi_schedule_df['Interest'].sum()
    refi_total_pmi = refi_schedule_df['PMI'].sum()
    refi_payoff_years = len(refi_schedule_df) / refi_periods_per_year

# Interest savings (biweekly vs. monthly)
monthly_schedule_df, _, _ = amortization_schedule(
    principal=loan_amount,
    years=loan_years,
    periods_per_year=12,
    start_date=f"{purchase_year}-01-01",
    extra_schedule=expand_extra_payments(extra_payments, purchase_year, loan_years, "Monthly"),
    rate_schedule=rate_schedule,
    mortgage_type=mortgage_type,
    purchase_year=purchase_year,
    mortgage_rate=mortgage_rate,
    pmi_rate=pmi_rate,
    pmi_equity_threshold=pmi_equity_threshold,
    purchase_price=purchase_price
)
biweekly_schedule_df, _, _ = amortization_schedule(
    principal=loan_amount,
    years=loan_years,
    periods_per_year=26,
    start_date=f"{purchase_year}-01-01",
    extra_schedule=expand_extra_payments(extra_payments, purchase_year, loan_years, "Biweekly"),
    rate_schedule=rate_schedule,
    mortgage_type=mortgage_type,
    purchase_year=purchase_year,
    mortgage_rate=mortgage_rate,
    pmi_rate=pmi_rate,
    pmi_equity_threshold=pmi_equity_threshold,
    purchase_price=purchase_price
)
interest_saved = monthly_schedule_df['Interest'].sum() - biweekly_schedule_df['Interest'].sum()

# ----------------------------- DISPLAY -----------------------------
st.subheader("Mortgage Metrics")

# Original Loan Metrics
st.markdown("### Original Loan")
cols = st.columns(5)
cols[0].metric("Monthly Payment", f"${original_monthly_payment:,.2f}")
cols[1].metric("Payment per Period", f"${original_payment_per_period:,.2f}")
cols[2].metric("Total Interest", f"${original_total_interest:,.2f}")
cols[3].metric("Total PMI", f"${original_total_pmi:,.2f}")
cols[4].metric("Payoff Years", f"{original_payoff_years:.1f}")

# Refinance Metrics
if refi_schedule_df is not None:
    st.markdown("### Refinance Scenario")
    cols = st.columns(5)
    cols[0].metric("Monthly Payment", f"${refi_monthly_payment:,.2f}")
    cols[1].metric("Payment per Period", f"${refi_payment_per_period:,.2f}")
    cols[2].metric("Total Interest", f"${refi_total_interest:,.2f}")
    cols[3].metric("Total PMI", f"${refi_total_pmi:,.2f}")
    cols[4].metric("Payoff Years", f"{refi_payoff_years:.1f}")

# Amortization Schedules
st.subheader("Amortization Schedules")
st.markdown("### Original Loan")
tab1, tab2, tab3 = st.tabs(["Annual", "Monthly", "Balance Chart"])

with tab1:
    st.dataframe(
        original_annual_df.style.format({
            "Payment": "${:,.2f}",
            "Interest": "${:,.2f}",
            "Principal": "${:,.2f}",
            "Extra": "${:,.2f}",
            "PMI": "${:,.2f}",
            "Balance": "${:,.2f}",
            "Date": "{:%Y-%m}"
        }).apply(lambda row: ["background-color: #e6f3ff"] * len(row) if row["Loan Type"] == "Refinance" else [""] * len(row), axis=1)
    )

with tab2:
    st.dataframe(
        original_monthly_df.style.format({
            "Payment": "${:,.2f}",
            "Interest": "${:,.2f}",
            "Principal": "${:,.2f}",
            "Extra": "${:,.2f}",
            "PMI": "${:,.2f}",
            "Balance": "${:,.2f}",
            "Date": "{:%Y-%m}"
        }).apply(lambda row: ["background-color: #ffe699"] * len(row) if row["Num Payments"] > 1 else ["background-color: #e6f3ff"] * len(row) if row["Loan Type"] == "Refinance" else [""] * len(row), axis=1)
    )

with tab3:
    st.subheader("Balance Over Time")
    chart_data = pd.DataFrame({
        "Date": original_schedule_df["Date"].dt.strftime("%Y-%m"),
        "Original Loan": original_schedule_df["Balance"]
    })
    if refi_schedule_df is not None:
        chart_data["Refinance Scenario"] = refi_schedule_df["Balance"]
    st.line_chart(chart_data.set_index("Date"))

if refi_schedule_df is not None:
    st.markdown("### Refinance Scenario")
    tab1, tab2 = st.tabs(["Annual", "Monthly"])
    with tab1:
        st.dataframe(
            refi_annual_df.style.format({
                "Payment": "${:,.2f}",
                "Interest": "${:,.2f}",
                "Principal": "${:,.2f}",
                "Extra": "${:,.2f}",
                "PMI": "${:,.2f}",
                "Balance": "${:,.2f}",
                "Date": "{:%Y-%m}"
            }).apply(lambda row: ["background-color: #e6f3ff"] * len(row) if row["Loan Type"] == "Refinance" else [""] * len(row), axis=1)
        )
    with tab2:
        st.dataframe(
            refi_monthly_df.style.format({
                "Payment": "${:,.2f}",
                "Interest": "${:,.2f}",
                "Principal": "${:,.2f}",
                "Extra": "${:,.2f}",
                "PMI": "${:,.2f}",
                "Balance": "${:,.2f}",
                "Date": "{:%Y-%m}"
            }).apply(lambda row: ["background-color: #ffe699"] * len(row) if row["Num Payments"] > 1 else ["background-color: #e6f3ff"] * len(row) if row["Loan Type"] == "Refinance" else [""] * len(row), axis=1)
        )

# Comparison
if refi_schedule_df is not None:
    st.subheader("Original vs. Refinance Comparison")
    comparison_df = pd.DataFrame({
        "Metric": ["Monthly Payment", "Total Interest Paid", "Total PMI Paid", "Payoff Time (Years)"],
        "Original Loan": [
            f"${original_monthly_payment:,.2f}",
            f"${original_total_interest:,.2f}",
            f"${original_total_pmi:,.2f}",
            f"{original_payoff_years:.1f}"
        ],
        "Refinance Scenario": [
            f"${refi_monthly_payment:,.2f}",
            f"${refi_total_interest:,.2f}",
            f"${refi_total_pmi:,.2f}",
            f"{refi_payoff_years:.1f}"
        ]
    })
    st.dataframe(comparison_df.style.format({"Original Loan": "{:}", "Refinance Scenario": "{:}"}))

# Downloads
st.subheader("Download Schedules")
col1, col2 = st.columns(2)
with col1:
    st.download_button(
        label="Download Original Loan Schedule",
        data=original_schedule_df.to_csv(index=False),
        file_name="original_amortization_schedule.csv",
        mime="text/csv"
    )
with col2:
    if refi_schedule_df is not None:
        st.download_button(
            label="Download Refinance Schedule",
            data=refi_schedule_df.to_csv(index=False),
            file_name="refinance_amortization_schedule.csv",
            mime="text/csv"
        )

# Interest Savings
st.subheader("Interest Savings (Biweekly vs. Monthly)")
st.metric("Interest Saved", f"${interest_saved:,.2f}")