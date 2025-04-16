import requests
import pandas as pd
import matplotlib.pyplot as plt
import time
import streamlit as st
import os

# Binance API endpoint
BINANCE_API_URL = "https://api.binance.com/api/v1/klines"

def get_top_futures_symbols(limit=20):
    url = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
    response = requests.get(url)

    try:
        data = response.json()
        if not isinstance(data, list):
            st.error(f"Unexpected response format from Binance API: {data}")
            return []

        # Sort by quote volume descending
        sorted_data = sorted(data, key=lambda x: float(x['quoteVolume']), reverse=True)

        top_symbols = []
        for item in sorted_data:
            if item['symbol'].endswith('USDT') and 'PERP' not in item['symbol']:
                top_symbols.append(item['symbol'])
            if len(top_symbols) >= limit:
                break

        return top_symbols

    except Exception as e:
        st.error(f"Failed to fetch or parse Binance futures data: {e}")
        return []



# Example list of contracts (replace with live data if needed)
CONTRACTS = get_top_futures_symbols()

def fetch_ohlcv(symbol, data_folder="data"):
    file_path = os.path.join(data_folder, f"{symbol}.csv")
    if not os.path.exists(file_path):
        st.warning(f"No data found for {symbol}")
        return pd.DataFrame()

    df = pd.read_csv(file_path, parse_dates=["timestamp"])
    return df

def detect_volume_spikes(df, threshold_factor=2):
    df["volume_ma"] = df["volume"].rolling(window=7).mean()
    df["volume_std"] = df["volume"].rolling(window=7).std()
    df["spike"] = df["volume"] > (df["volume_ma"] + threshold_factor * df["volume_std"])
    spikes_df = df[df["spike"] & (df["quote_asset_volume"] >= 100_000_000)]
    return spikes_df

def plot_volume_spikes(df, spikes_df, selected_date=None):
    plt.figure(figsize=(10, 6))
    plt.plot(df["timestamp"], df["volume"], label="Volume", color='lightblue', alpha=0.7)
    plt.scatter(spikes_df["timestamp"], spikes_df["volume"], color='red', label="Volume Spike", zorder=5)
    plt.plot(df["timestamp"], df["volume_ma"], label="7-day MA", color='green', linestyle='--', alpha=0.7)

    if selected_date:
        selected_row = df[df["timestamp"] == pd.to_datetime(selected_date)]
        if not selected_row.empty:
            plt.scatter(selected_row["timestamp"], selected_row["volume"], color='orange', label='Selected Spike', s=120, zorder=10)

    plt.title("Trading Volume with Spikes")
    plt.xlabel("Date")
    plt.ylabel("Volume")
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    st.pyplot(plt)

# -----------------------------
# Streamlit App Starts Here
# -----------------------------
st.title("📊 Binance Volume Spike Analyzer")
st.caption("Detects large volume spikes over $100M across multiple contracts.")

# Step 1: Analyze all contracts for spikes
spike_summary = {}
all_spike_data = {}

with st.spinner("Analyzing contracts for volume spikes..."):
    for contract in CONTRACTS:
        df = fetch_ohlcv(contract)
        spikes_df = detect_volume_spikes(df, threshold_factor=2.2)

        if not spikes_df.empty:
            spikes_df["timestamp"] = spikes_df["timestamp"].dt.strftime('%Y-%m-%d')
            spike_summary[contract] = spikes_df[["timestamp", "quote_asset_volume"]]
            all_spike_data[contract] = (df, spikes_df)

# Step 2: Show list of contracts with spikes
if spike_summary:
    st.success(f"Found volume spikes in {len(spike_summary)} contract(s).")

    selected_contract = st.selectbox("🧠 Choose a contract to view spikes:", list(spike_summary.keys()))

    # Step 3: Show table of spikes for selected contract
    spikes_table = spike_summary[selected_contract]
    st.subheader(f"📌 Spikes for {selected_contract}")
    st.dataframe(spikes_table, use_container_width=True)

    selected_date = st.selectbox("📅 Choose a date to visualize spike:", spikes_table["timestamp"].tolist())

    # Step 4: Plot spike
    df_full, df_spikes = all_spike_data[selected_contract]
    plot_volume_spikes(df_full, df_spikes, selected_date)

else:
    st.warning("No volume spikes over 100M found for any contract.")
