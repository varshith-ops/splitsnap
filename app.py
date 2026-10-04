import html
import streamlit as st
import os
import re
from PIL import Image
from services import parse_receipt, calculate_split, send_email
from settle import settle_up
from upi import is_valid_upi_id, build_upi_link, make_qr_png

# Page Configuration
st.set_page_config(
    page_title="SplitSnap - AI Bill Splitter",
    page_icon="🧾",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Helper functions & email/model config
SECRETS_ERROR = None

def secret(name, default=""):
    global SECRETS_ERROR
    try:
        val = st.secrets[name]
        if isinstance(val, str):
            return val.strip()
        return val
    except Exception as e:
        SECRETS_ERROR = f"{type(e).__name__}: {e}"
        return default

GMAIL_ADDRESS = secret("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = secret("GMAIL_APP_PASSWORD")
MODEL_NAME = secret("GEMINI_MODEL", "gemini-3.5-flash")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def reset_assignments():
    for k in [k for k in st.session_state if k.startswith("item_assign_")]:
        del st.session_state[k]

# --- MODERN CUSTOM STYLING (EMERALD & NAVY THEME) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        body, p, h1, h2, h3, h4, h5, h6, label, input, textarea, button, [data-testid="stMarkdownContainer"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        [data-testid="stIconMaterial"],
        .material-icons,
        .material-symbols-rounded,
        span[class*="material"] {
            font-family: "Material Symbols Rounded", "Material Icons" !important;
        }

        /* Hide Streamlit footer and main menu */
        #MainMenu, footer {
            visibility: hidden;
        }

        /* Container & Padding */
        .block-container {
            padding-top: 3.5rem;
            padding-bottom: 3rem;
            max-width: 780px;
        }

        /* Keyframe Fade-In Animation */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .animate-fade-in {
            animation: fadeIn 0.35s ease-out forwards;
        }

        /* Hero Section Card */
        .hero-card {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(6, 182, 212, 0.08) 100%);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 16px;
            padding: 22px;
            text-align: center;
            margin-bottom: 18px;
            animation: fadeIn 0.4s ease-out forwards;
        }

        .hero-title {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #10B981 0%, #06B6D4 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 4px;
        }

        .hero-tagline {
            color: #94A3B8;
            font-size: 1rem;
            font-weight: 500;
        }

        /* 3-Step Cards */
        .step-card {
            background-color: #131C2E;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 14px;
            text-align: center;
            transition: all 0.2s ease-in-out;
            margin-bottom: 10px;
        }

        .step-card:hover {
            transform: translateY(-3px);
            border-color: rgba(16, 185, 129, 0.4);
            box-shadow: 0 8px 20px rgba(16, 185, 129, 0.15);
        }

        .step-icon {
            font-size: 1.4rem;
            margin-bottom: 4px;
        }

        .step-title {
            font-size: 0.9rem;
            font-weight: 700;
            color: #E6EDF7;
        }

        .step-desc {
            font-size: 0.78rem;
            color: #94A3B8;
        }

        /* Person Breakdown Card */
        .person-card {
            background-color: #131C2E;
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: 14px;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            transition: all 0.2s ease;
            animation: fadeIn 0.3s ease-out forwards;
        }

        .person-card:hover {
            transform: translateY(-2px);
            border-color: #10B981;
            box-shadow: 0 6px 16px rgba(16, 185, 129, 0.18);
        }

        .person-info {
            display: flex;
            align-items: center;
        }

        .avatar-circle {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: linear-gradient(135deg, #10B981, #06B6D4);
            color: #0B1220;
            font-weight: 800;
            font-size: 1.15rem;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 14px;
            text-transform: uppercase;
        }

        .person-name {
            font-size: 1.1rem;
            font-weight: 700;
            color: #E6EDF7;
        }

        .amount-badge {
            background-color: rgba(16, 185, 129, 0.15);
            color: #10B981;
            font-weight: 700;
            font-size: 1.1rem;
            padding: 6px 14px;
            border-radius: 20px;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        /* Buttons & Controls */
        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 14px rgba(16, 185, 129, 0.25);
        }

        /* Tabs styling */
        .stTabs [aria-selected="true"] {
            background-color: rgba(16, 185, 129, 0.15) !important;
            color: #10B981 !important;
            border-bottom: 3px solid #10B981 !important;
        }

        /* Metrics Styling */
        .stMetric {
            background-color: #131C2E;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 12px 16px;
        }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR SETUP & SETTINGS ---
st.sidebar.title("🧾 SplitSnap Settings")

# API Key handling via secrets or manual input
gemini_api_key = secret("GEMINI_API_KEY")
if not gemini_api_key:
    gemini_api_key = st.sidebar.text_input("Gemini API Key (Optional)", type="password", help="Enter key for AI receipt scanner")

st.sidebar.divider()
currency_symbol = st.sidebar.selectbox("Currency", ["₹", "$", "€", "£"], index=0)

# Session State Initialization (starts empty)
if "bill_items" not in st.session_state:
    st.session_state["bill_items"] = []
if "friends" not in st.session_state:
    st.session_state.friends = []
if "tax" not in st.session_state:
    st.session_state.tax = 0.0
if "tip" not in st.session_state:
    st.session_state.tip = 0.0

# Tax & Tip inside st.expander in sidebar
with st.sidebar.expander("⚙️ Optional Bill Details (Tax & Tip)", expanded=True):
    st.session_state.tax = st.number_input(f"Tax Amount ({currency_symbol})", min_value=0.0, value=float(st.session_state.tax), step=0.50)
    st.session_state.tip = st.number_input(f"Tip Amount ({currency_symbol})", min_value=0.0, value=float(st.session_state.tip), step=0.50)

# Diagnostics expander at bottom of sidebar
with st.sidebar.expander("🔧 Diagnostics", expanded=False):
    cwd = os.getcwd()
    secrets_file = os.path.join(".streamlit", "secrets.toml")
    file_exists = os.path.exists(secrets_file)
    st.write(f"**CWD:** `{cwd}`")
    st.write(f"**secrets.toml exists:** `{file_exists}`")
    
    secrets_keys = []
    secrets_exception = SECRETS_ERROR
    try:
        secrets_keys = list(st.secrets.keys())
    except Exception as e:
        secrets_exception = f"{type(e).__name__}: {e}"
    
    if secrets_exception:
        st.write(f"**st.secrets error:** `{secrets_exception}`")
    else:
        st.write(f"**st.secrets keys:** `{secrets_keys}`")
    
    st.write(f"**GEMINI_API_KEY:** {'set' if secret('GEMINI_API_KEY') else 'missing'}")
    st.write(f"**GMAIL_ADDRESS:** {'set' if GMAIL_ADDRESS else 'missing'}")
    st.write(f"**GMAIL_APP_PASSWORD:** {'set' if GMAIL_APP_PASSWORD else 'missing'}")

# --- HERO SECTION & STEP CARDS ---
st.markdown("""
    <div class="hero-card">
        <div class="hero-title">🧾 SplitSnap</div>
        <div class="hero-tagline">Effortless AI-Powered Bill & Expense Splitting</div>
    </div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
        <div class="step-card">
            <div class="step-icon">📸</div>
            <div class="step-title">1. Upload</div>
            <div class="step-desc">Scan receipt or enter items</div>
        </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("""
        <div class="step-card">
            <div class="step-icon">👥</div>
            <div class="step-title">2. Assign</div>
            <div class="step-desc">Tag friends to items</div>
        </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown("""
        <div class="step-card">
            <div class="step-icon">📊</div>
            <div class="step-title">3. Summary</div>
            <div class="step-desc">Get per-person totals</div>
        </div>
    """, unsafe_allow_html=True)

# Step Progress Bar
progress_val = 0.33
if st.session_state["bill_items"]:
    progress_val = 0.66
if st.session_state["bill_items"] and st.session_state.friends:
    progress_val = 1.0

st.progress(progress_val, text=f"Step Progress: {int(progress_val * 100)}% Complete")
st.divider()

# Tabs
tab1, tab2, tab3 = st.tabs(["📸 1. Receipt & Items", "👥 2. Split & Assign", "📊 3. Final Summary"])

# --- TAB 1: RECEIPT & ITEMS ---
with tab1:
    st.subheader("Step 1: Add Bill Items")
    
    col_upload, col_manual = st.columns([1, 1])
    
    with col_upload:
        st.markdown("##### 📸 Upload Receipt Image")
        uploaded_file = st.file_uploader("Upload a receipt photo", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Receipt", use_container_width=True)
            
            if st.button("🤖 Parse Receipt with AI", use_container_width=True, type="primary"):
                if not gemini_api_key:
                    st.warning("Please configure your GEMINI_API_KEY in `.streamlit/secrets.toml` or the sidebar to use AI parsing.")
                else:
                    with st.spinner("Analyzing receipt photo with AI..."):
                        try:
                            result = parse_receipt(gemini_api_key, MODEL_NAME,
                                                   uploaded_file.getvalue(), uploaded_file.type)
                        except Exception as e:
                            result = None
                            st.error(f"Couldn't read that receipt: {e}")
                    if result is not None:
                        if not result["is_receipt"]:
                            st.warning("That doesn't look like a readable receipt. Try a clearer photo.")
                        else:
                            parsed_items = []
                            for i in result["items"]:
                                cleaned_name = str(i.get("item", "")).replace("*", "").strip()
                                if cleaned_name:
                                    parsed_items.append({**i, "item": cleaned_name, "assigned_to": []})
                            st.session_state["bill_items"] = parsed_items
                            st.session_state.tax = result["tax"]
                            st.session_state.tip = result["tip"]
                            reset_assignments()
                            st.toast("Receipt parsed successfully!", icon="🧾")
                            st.rerun()

    with col_manual:
        st.markdown("##### ✍️ Add Item Manually")
        with st.form("add_item_form", clear_on_submit=True):
            item_name = st.text_input("Item Name", placeholder="e.g. Margherita Pizza")
            item_price = st.number_input(f"Price ({currency_symbol})", min_value=0.0, step=0.50, format="%.2f", value=0.0)
            submitted = st.form_submit_button("➕ Add Item", use_container_width=True)
            if submitted:
                cleaned_name = item_name.replace("*", "").strip()
                if cleaned_name:
                    st.session_state["bill_items"].append({"item": cleaned_name, "price": item_price, "assigned_to": []})
                    st.toast(f"Added '{cleaned_name}' ({currency_symbol}{item_price:.2f})", icon="✅")
                    st.rerun()
                else:
                    st.error("Please enter an item name.")

    st.divider()
    
    # Running Subtotal Metric & Items Header
    col_hdr, col_subt = st.columns([2, 1])
    with col_hdr:
        st.subheader("📋 Current Item List")
    with col_subt:
        running_subtotal = sum(i["price"] for i in st.session_state["bill_items"])
        st.metric("Subtotal", f"{currency_symbol}{running_subtotal:.2f}")

    if not st.session_state["bill_items"]:
        st.info("💡 No items yet. Upload a receipt or add one manually.")
    else:
        # Display items with individual delete options
        for idx, item_data in enumerate(st.session_state["bill_items"]):
            c_name, c_price, c_del = st.columns([3, 2, 1])
            c_name.write(f"**{item_data['item']}**")
            c_price.write(f"{currency_symbol}{item_data['price']:.2f}")
            if c_del.button("🗑️", key=f"del_item_{idx}"):
                removed_item = st.session_state["bill_items"].pop(idx)
                reset_assignments()
                st.toast(f"Removed '{removed_item['item']}'", icon="🗑️")
                st.rerun()

        st.markdown("")
        if st.button("🗑️ Clear All Items", type="secondary"):
            st.session_state["bill_items"] = []
            reset_assignments()
            st.toast("Cleared all items", icon="🧹")
            st.rerun()

# --- TAB 2: SPLIT & ASSIGN ---
with tab2:
    st.subheader("Step 2: Assign Items to Friends")
    
    st.markdown("##### 👥 Manage Group")
    
    with st.form("add_person_form", clear_on_submit=True):
        c_in, c_btn = st.columns([3, 1])
        new_friend = c_in.text_input("Person Name", placeholder="e.g. Alex", label_visibility="collapsed")
        submitted_person = c_btn.form_submit_button("➕ Add Person", use_container_width=True)
        if submitted_person:
            if new_friend and new_friend not in st.session_state.friends:
                st.session_state.friends.append(new_friend)
                st.toast(f"Added {new_friend} to group!", icon="👥")
                st.rerun()
            elif not new_friend:
                st.error("Please enter a person's name.")

    # List of Friends with Remove option
    if st.session_state.friends:
        st.markdown("**Group Members:**")
        cols = st.columns(min(len(st.session_state.friends), 4))
        for idx, friend in enumerate(st.session_state.friends):
            col_idx = idx % 4
            with cols[col_idx]:
                c_f, c_rem = st.columns([3, 1])
                c_f.write(f"👤 {friend}")
                if c_rem.button("❌", key=f"del_friend_{friend}"):
                    st.session_state.friends.remove(friend)
                    st.toast(f"Removed {friend}", icon="👤")
                    st.rerun()
    else:
        st.info("No people added yet. Add people to start splitting!")

    st.divider()

    # Guard check for items & friends
    if not st.session_state["bill_items"] and not st.session_state.friends:
        st.warning("⚠️ Please add at least one item (Step 1) and one person above to assign items.")
    elif not st.session_state["bill_items"]:
        st.warning("⚠️ Please add at least one item in Step 1 before assigning.")
    elif not st.session_state.friends:
        st.warning("⚠️ Please add at least one person above before assigning.")
    else:
        st.markdown("##### 🍕 Item Assignments")
        for idx, item_data in enumerate(st.session_state["bill_items"]):
            st.markdown(f"**{item_data['item']}** — `{currency_symbol}{item_data['price']:.2f}`")
            selected = st.multiselect(
                f"Who ordered {item_data['item']}?",
                options=st.session_state.friends,
                default=item_data["assigned_to"],
                key=f"item_assign_{idx}"
            )
            st.session_state["bill_items"][idx]["assigned_to"] = selected
            st.divider()

# --- TAB 3: FINAL SUMMARY ---
with tab3:
    st.subheader("Step 3: Final Breakdown & Settlement")
    
    if not st.session_state["bill_items"] or not st.session_state.friends:
        st.info("💡 Please add items in Step 1 and friends in Step 2 to view the summary.")
    else:
        # Calculate totals
        subtotal = sum(i["price"] for i in st.session_state["bill_items"])
        tax = st.session_state.tax
        tip = st.session_state.tip
        grand_total = subtotal + tax + tip
        
        totals = calculate_split(st.session_state["bill_items"],
            st.session_state.friends, tax, tip)

        # Overview Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Subtotal", f"{currency_symbol}{subtotal:.2f}")
        m2.metric("Tax", f"{currency_symbol}{tax:.2f}")
        m3.metric("Tip", f"{currency_symbol}{tip:.2f}")
        m4.metric("Grand Total", f"{currency_symbol}{grand_total:.2f}")
        
        st.divider()
        st.markdown("### 💰 Per-Person Breakdown Cards")
        
        # Person Cards with Avatar Circles
        for person, amount in totals.items():
            initial = person[0].upper() if person else "?"
            st.markdown(f"""
                <div class="person-card">
                    <div class="person-info">
                        <div class="avatar-circle">{initial}</div>
                        <div class="person-name">{person}</div>
                    </div>
                    <div class="amount-badge">{currency_symbol}{amount:.2f}</div>
                </div>
            """, unsafe_allow_html=True)
                    
        st.divider()
        st.markdown("### 🤝 Who Paid & Who Owes Whom")

        if "payer" in st.session_state and st.session_state.payer not in st.session_state.friends:
            st.session_state.payer = st.session_state.friends[0]

        payer = st.selectbox("Who paid the bill?", options=st.session_state.friends, key="payer")
        payments = settle_up(totals, payer)

        if not payments:
            st.success("Nobody owes anything.")
        else:
            for debtor, creditor, amount in payments:
                safe_debtor = html.escape(str(debtor))
                safe_creditor = html.escape(str(creditor))
                st.markdown(f"""
                    <div class="person-card">
                        <div class="person-info">
                            <div class="person-name">{safe_debtor} owes {safe_creditor}</div>
                        </div>
                        <div class="amount-badge">{currency_symbol}{amount:.2f}</div>
                    </div>
                """, unsafe_allow_html=True)

        payer_upi_input = ""
        valid_upi = False
        if currency_symbol == "₹" and payments:
            st.divider()
            st.markdown("### 📲 Pay via UPI")
            payer_upi_input = st.text_input(
                "Payer's UPI ID",
                placeholder="e.g. name@okhdfcbank",
                key="payer_upi"
            )
            st.caption("Used only to build payment links. It is not stored.")

            upi_id_clean = payer_upi_input.strip()
            if not upi_id_clean:
                st.info(f"Enter {payer}'s UPI ID to generate payment QR codes.")
            elif not is_valid_upi_id(upi_id_clean):
                st.warning("That UPI ID doesn't look right.")
            else:
                valid_upi = True
                with st.expander("Show payment QR codes", expanded=False):
                    for debtor, creditor, amount in payments:
                        safe_d = html.escape(str(debtor))
                        safe_c = html.escape(str(creditor))
                        st.markdown(f"#### {safe_d} pays {safe_c} {currency_symbol}{amount:.2f}")
                        upi_link = build_upi_link(upi_id_clean, payer, amount, "SplitSnap bill")
                        qr_bytes = make_qr_png(upi_link)
                        if qr_bytes is not None:
                            st.image(qr_bytes, width=180)
                        else:
                            st.warning("QR code package not installed.")
                        st.code(upi_link, language="markdown")

        st.divider()

        # Copyable Text Summary (Plain text title)
        st.markdown("### 📝 Shareable Text Summary")
        summary_text = f"🧾 SplitSnap Summary\n"
        summary_text += f"Total Bill: {currency_symbol}{grand_total:.2f}\n"
        summary_text += "-------------------------\n"
        for person, amount in totals.items():
            summary_text += f"• {person}: {currency_symbol}{amount:.2f}\n"
        
        if payments:
            summary_text += f"\nSettle up (paid by {payer}):\n"
            for debtor, creditor, amount in payments:
                summary_text += f"• {debtor} -> {creditor}: {currency_symbol}{amount:.2f}\n"

        if valid_upi and upi_id_clean:
            summary_text += f"\nPay {payer} via UPI: {upi_id_clean}\n"

        summary_text += "\nThank you for using SplitSnap!"

        st.code(summary_text, language="markdown")

        st.divider()
        st.markdown("### 📧 Send Summary via Email")
        recipient_email = st.text_input("Recipient Email Address", placeholder="friend@example.com")
        if st.button("🚀 Send to Email", type="primary", use_container_width=True):
            if not EMAIL_RE.match(recipient_email.strip()):
                st.error("Please enter a valid email address.")
            elif not (GMAIL_ADDRESS and GMAIL_APP_PASSWORD):
                missing_keys = []
                if not GMAIL_ADDRESS:
                    missing_keys.append("GMAIL_ADDRESS")
                if not GMAIL_APP_PASSWORD:
                    missing_keys.append("GMAIL_APP_PASSWORD")
                st.error(f"Email is not configured: {' and '.join(missing_keys)} {'are' if len(missing_keys) > 1 else 'is'} missing.")
            else:
                with st.spinner("Sending..."):
                    ok, info = send_email(GMAIL_ADDRESS, GMAIL_APP_PASSWORD,
                        recipient_email.strip(), "Your SplitSnap bill breakdown 🧾",
                        summary_text)
                if ok:
                    st.toast(f"Summary sent to {recipient_email.strip()}!", icon="📧")
                    st.balloons()
                    st.success(f"✅ Summary successfully sent to {recipient_email.strip()}!")
                else:
                    st.error(f"Couldn't send: {info}")
