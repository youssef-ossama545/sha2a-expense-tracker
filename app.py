import streamlit as st
import pandas as pd
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================
ROOMMATES = ["Safi", "Gandofly", "Lolo", "Jojo", "Body", "Paki"]
CURRENCY = "EGP" 

# ============================================================================
# CUSTOM CSS
# ============================================================================
def apply_custom_css():
    st.markdown("""
    <style>
        .stApp {
            background-color: #f5f7fa;
        }
        .main-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        .balance-positive { color: #28a745; font-weight: bold; }
        .balance-negative { color: #dc3545; font-weight: bold; }
        .balance-zero { color: #6c757d; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
def init_session_state():
    if "expenses" not in st.session_state:
        st.session_state.expenses = []
    if "payments" not in st.session_state:
        st.session_state.payments = []

# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================
def calculate_balances():
    """Calculate balances with selective sharing."""
    balances = {person: 0.0 for person in ROOMMATES}
    
    # Process expenses
    for expense in st.session_state.expenses:
        payer = expense["payer"]
        amount = expense["amount"]
        shared_with = expense["shared_with"]
        
        # Split amount among people who shared this expense
        split_amount = amount / len(shared_with)
        
        # Payer gets credited for full amount
        balances[payer] += amount
        
        # Everyone who shared pays their share
        for person in shared_with:
            balances[person] -= split_amount
    
    # Process payments
    for payment in st.session_state.payments:
        balances[payment["from"]] += payment["amount"]
        balances[payment["to"]] -= payment["amount"]
    
    return balances

def calculate_settlement():
    """Calculate who owes whom."""
    balances = calculate_balances()
    
    creditors = []
    debtors = []
    
    for person, balance in balances.items():
        if balance > 0.01:
            creditors.append({"name": person, "amount": balance})
        elif balance < -0.01:
            debtors.append({"name": person, "amount": -balance})
    
    creditors.sort(key=lambda x: x["amount"], reverse=True)
    debtors.sort(key=lambda x: x["amount"], reverse=True)
    
    settlements = []
    i, j = 0, 0
    
    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]
        
        transfer = min(debtor["amount"], creditor["amount"])
        
        if transfer > 0.01:
            settlements.append({
                "from": debtor["name"],
                "to": creditor["name"],
                "amount": round(transfer, 2)
            })
        
        debtor["amount"] -= transfer
        creditor["amount"] -= transfer
        
        if debtor["amount"] < 0.01:
            i += 1
        if creditor["amount"] < 0.01:
            j += 1
    
    return settlements

# ============================================================================
# MAIN APP
# ============================================================================
def main():
    st.set_page_config(
        page_title="Roommate Expense Tracker",
        page_icon="🏠",
        layout="wide"
    )
    
    apply_custom_css()
    init_session_state()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏠 Roommate Expense Tracker</h1>
        <p>Split expenses fairly among roommates</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard", 
        "➕ Add Expense", 
        "💸 Add Payment",
        "📜 History"
    ])
    
    # ========================================================================
    # TAB 1: DASHBOARD
    # ========================================================================
    with tab1:
        balances = calculate_balances()
        settlements = calculate_settlement()
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        total_expenses = sum(e["amount"] for e in st.session_state.expenses)
        total_payments = sum(p["amount"] for p in st.session_state.payments)
        
        with col1:
            st.metric("Total Expenses", f"{CURRENCY} {total_expenses:.2f}")
        with col2:
            st.metric("Total Payments", f"{CURRENCY} {total_payments:.2f}")
        with col3:
            st.metric("Transactions", len(st.session_state.expenses) + len(st.session_state.payments))
        
        st.markdown("---")
        
        # Balances
        st.subheader("💰 Current Balances")
        
        cols = st.columns(len(ROOMMATES))
        for i, person in enumerate(ROOMMATES):
            balance = balances[person]
            with cols[i]:
                if balance > 0.01:
                    st.markdown(f"**{person}**")
                    st.markdown(f'<p class="balance-positive">+{balance:.2f} {CURRENCY}</p>', unsafe_allow_html=True)
                    st.caption("Is owed")
                elif balance < -0.01:
                    st.markdown(f"**{person}**")
                    st.markdown(f'<p class="balance-negative">{balance:.2f} {CURRENCY}</p>', unsafe_allow_html=True)
                    st.caption("Owes")
                else:
                    st.markdown(f"**{person}**")
                    st.markdown(f'<p class="balance-zero">0.00 {CURRENCY}</p>', unsafe_allow_html=True)
                    st.caption("Settled")
        
        st.markdown("---")
        
        # Settlement plan
        st.subheader("🔄 Settlement Plan")
        
        if not settlements:
            st.success("🎉 Everyone is settled up!")
        else:
            for settlement in settlements:
                st.info(f"**{settlement['from']}** pays **{settlement['to']}**: {settlement['amount']:.2f} {CURRENCY}")
    
    # ========================================================================
    # TAB 2: ADD EXPENSE
    # ========================================================================
    with tab2:
        st.subheader("➕ Add New Expense")
        
        with st.form("expense_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                expense_date = st.date_input("Date", datetime.now())
                expense_description = st.text_input("Description", placeholder="e.g., Groceries, Utilities")
                expense_payer = st.selectbox("Who paid?", ROOMMATES)
            
            with col2:
                expense_amount = st.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=0.01)
                
                # ✨ KEY FEATURE: Select who shares this expense
                st.markdown("**Who shares this expense?**")
                shared_with = []
                for person in ROOMMATES:
                    if st.checkbox(person, value=True, key=f"share_{person}"):
                        shared_with.append(person)
            
            expense_notes = st.text_area("Notes (optional)")
            
            submit = st.form_submit_button("💾 Add Expense")
            
            if submit:
                if not expense_description:
                    st.error("Please enter a description")
                elif expense_amount <= 0:
                    st.error("Amount must be positive")
                elif len(shared_with) == 0:
                    st.error("Select at least one person to share this expense")
                else:
                    st.session_state.expenses.append({
                        "date": expense_date.strftime("%Y-%m-%d"),
                        "description": expense_description,
                        "payer": expense_payer,
                        "amount": expense_amount,
                        "shared_with": shared_with,
                        "notes": expense_notes
                    })
                    
                    split = expense_amount / len(shared_with)
                    st.success(f"✅ Expense added! {expense_payer} paid {expense_amount:.2f} {CURRENCY}, split {split:.2f} each among {', '.join(shared_with)}")
                    st.balloons()
                    st.rerun()
    
    # ========================================================================
    # TAB 3: ADD PAYMENT
    # ========================================================================
    with tab3:
        st.subheader("💸 Record Payment")
        
        with st.form("payment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                payment_date = st.date_input("Date", datetime.now())
                payment_from = st.selectbox("From", ROOMMATES)
            
            with col2:
                payment_to = st.selectbox("To", ROOMMATES)
                payment_amount = st.number_input(f"Amount ({CURRENCY})", min_value=0.0, step=0.01)
            
            payment_notes = st.text_area("Notes (optional)")
            
            submit = st.form_submit_button("💾 Record Payment")
            
            if submit:
                if payment_from == payment_to:
                    st.error("Payer and recipient must be different")
                elif payment_amount <= 0:
                    st.error("Amount must be positive")
                else:
                    st.session_state.payments.append({
                        "date": payment_date.strftime("%Y-%m-%d"),
                        "from": payment_from,
                        "to": payment_to,
                        "amount": payment_amount,
                        "notes": payment_notes
                    })
                    
                    st.success(f"✅ Payment recorded! {payment_from} paid {payment_amount:.2f} {CURRENCY} to {payment_to}")
                    st.rerun()
    
    # ========================================================================
    # TAB 4: HISTORY
    # ========================================================================
    with tab4:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📝 Expense History")
            if st.session_state.expenses:
                for i, exp in enumerate(reversed(st.session_state.expenses), 1):
                    with st.expander(f"{exp['date']} - {exp['description']} ({exp['amount']:.2f} {CURRENCY})"):
                        st.write(f"**Paid by:** {exp['payer']}")
                        st.write(f"**Shared by:** {', '.join(exp['shared_with'])}")
                        st.write(f"**Split:** {exp['amount']/len(exp['shared_with']):.2f} {CURRENCY} each")
                        if exp['notes']:
                            st.write(f"**Notes:** {exp['notes']}")
                        
                        if st.button("🗑️ Delete", key=f"del_exp_{i}"):
                            st.session_state.expenses.remove(exp)
                            st.rerun()
            else:
                st.info("No expenses yet")
        
        with col2:
            st.subheader("💸 Payment History")
            if st.session_state.payments:
                for i, pay in enumerate(reversed(st.session_state.payments), 1):
                    with st.expander(f"{pay['date']} - {pay['amount']:.2f} {CURRENCY}"):
                        st.write(f"**From:** {pay['from']}")
                        st.write(f"**To:** {pay['to']}")
                        if pay['notes']:
                            st.write(f"**Notes:** {pay['notes']}")
                        
                        if st.button("🗑️ Delete", key=f"del_pay_{i}"):
                            st.session_state.payments.remove(pay)
                            st.rerun()
            else:
                st.info("No payments yet")

if __name__ == "__main__":
    main()
