# 🧾 SplitSnap

**SplitSnap** is an AI-powered receipt parsing and bill-splitting web application built with Streamlit.

---

## 📁 Project Structure

```text
splitsnap/
├── app.py                          # Main Streamlit app
├── prompts.py                      # System prompt, welcome message, summary prompt
├── requirements.txt                # Dependencies
├── README.md                       # What the app does + how to run it
├── .gitignore                      # Keeps secrets and venv out of GitHub
└── .streamlit/
    ├── secrets.toml.example        # Secrets template (committed to GitHub)
    └── secrets.toml                # Real API keys & secrets (never committed)
```

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have Python 3.9+ installed on your system.

### 2. Set Up a Virtual Environment (Recommended)
```bash
# Create a virtual environment
python -m venv venv

# Activate on Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Activate on macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Secrets & API Keys
1. Create a `.streamlit` folder if it doesn't exist.
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
3. Open `.streamlit/secrets.toml` and add your Gemini API Key.

---

## 🏃 Run the Application

Start the Streamlit app with:
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## ✨ Features
- **📸 Receipt Parsing with AI**: Upload a receipt photo to automatically extract itemized prices.
- **👥 Group Item Splitting**: Easily assign items to one or multiple friends.
- **🧮 Proportional Tax & Tip Calculation**: Tax and tip are distributed dynamically based on individual orders.
- **📝 Easy Text Export**: Copy a clean text breakdown ready to share in group chats.
