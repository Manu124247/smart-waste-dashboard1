from flask import Flask, render_template, request, send_file
import pandas as pd

app = Flask(__name__)

# Helper to assign risk level
def get_risk_level(x):
    if x < 50:
        return "Low"
    elif x < 80:
        return "Medium"
    else:
        return "High"

@app.route("/")
def home():
    # Load data
    df = pd.read_csv("forecast_output.csv", parse_dates=["timestamp"])
    df["risk_level"] = df["forecast_fill"].apply(get_risk_level)

    # --- Dropdown options ---
    bin_options = sorted(df["bin_id"].unique().tolist())
    min_date = df["timestamp"].dt.date.min().strftime("%Y-%m-%d")
    max_date = df["timestamp"].dt.date.max().strftime("%Y-%m-%d")

    # --- Read filters from URL ---
    selected_bin = request.args.get("bin_id", "ALL")
    selected_risk = request.args.get("risk_level", "ALL")
    selected_start = request.args.get("start_date", min_date)
    selected_end = request.args.get("end_date", max_date)

    # --- Apply filters ---
    filtered = df.copy()

    # Bin filter
    if selected_bin != "ALL":
        filtered = filtered[filtered["bin_id"] == selected_bin]

    # Date filter
    filtered = filtered[
        (filtered["timestamp"].dt.date >= pd.to_datetime(selected_start).date()) &
        (filtered["timestamp"].dt.date <= pd.to_datetime(selected_end).date())
    ]

    # Risk filter
    if selected_risk != "ALL":
        filtered = filtered[filtered["risk_level"] == selected_risk]

    if filtered.empty:
        # Avoid errors if no rows after filter
        avg_forecast = 0
        high_risk_bins = 0
        next24h = 0
        table_html = "<p>No data for selected filters.</p>"
        trend_labels = []
        trend_values = []
        weekly_labels = []
        weekly_values = []
        risk_labels = ["Low", "Medium", "High"]
        risk_counts = [0, 0, 0]
        top_bins = []
        top_vals = []
    else:
        # --- KPIs ---
        avg_forecast = round(filtered["forecast_fill"].mean(), 2)
        high_risk_bins = filtered[filtered["risk_level"] == "High"]["bin_id"].nunique()
        next24h = round(filtered.tail(24)["forecast_fill"].mean(), 2)

        # --- Table ---
        table_html = filtered[["timestamp", "bin_id", "forecast_fill", "risk_level"]] \
            .head(100).to_html(classes="table table-striped", index=False)

        # --- Trend chart (all filtered rows) ---
        trend = filtered.sort_values("timestamp")
        trend_labels = trend["timestamp"].dt.strftime("%Y-%m-%d %H:%M").tolist()
        trend_values = trend["forecast_fill"].tolist()

        # --- Weekly / daily average chart ---
        daily = filtered.set_index("timestamp") \
                        .resample("D")["forecast_fill"].mean().dropna()
        weekly_labels = daily.index.strftime("%Y-%m-%d").tolist()
        weekly_values = daily.values.round(2).tolist()

        # --- Risk distribution (bar / pie) ---
        risk_counts_series = filtered["risk_level"].value_counts()
        risk_labels = ["Low", "Medium", "High"]
        risk_counts = [int(risk_counts_series.get(r, 0)) for r in risk_labels]

        # --- Top 5 high-risk bins ---
        top = filtered.groupby("bin_id")["forecast_fill"].mean().sort_values(ascending=False).head(5)
        top_bins = top.index.tolist()
        top_vals = top.values.round(2).tolist()

    return render_template(
        "index.html",
        avg_forecast=avg_forecast,
        high_risk=high_risk_bins,
        next24h=next24h,
        table=table_html,
        bin_options=bin_options,
        selected_bin=selected_bin,
        selected_risk=selected_risk,
        selected_start=selected_start,
        selected_end=selected_end,
        min_date=min_date,
        max_date=max_date,
        trend_labels=trend_labels,
        trend_values=trend_values,
        weekly_labels=weekly_labels,
        weekly_values=weekly_values,
        risk_labels=risk_labels,
        risk_counts=risk_counts,
        top_bins=top_bins,
        top_vals=top_vals
    )

@app.route("/download")
def download_csv():
    return send_file("forecast_output.csv", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
