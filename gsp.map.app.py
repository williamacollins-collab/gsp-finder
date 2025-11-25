
import streamlit as st
import pandas as pd
import numpy as np
import subprocess, json, os


def run_curl_and_get_datapackage():
    curl_cmd = [
        "curl",
        "-L",
        "-s",
        "https://connecteddata.nationalgrid.co.uk/dataset/network-opportunity-map-headroom/datapackage.json",
    ]
    try:
        out = subprocess.check_output(curl_cmd)
        return json.loads(out.decode("utf-8"))
    except Exception as e:
        st.warning(f"Could not fetch datapackage.json via curl: {e}")
        return None

def monte_carlo_curtailment(daily_peaks_mva, allowed_mva, export_mva_with_margin, sim_days, trials):
    daily_peaks = np.array(daily_peaks_mva)
    if len(daily_peaks) == 0:
        return 0.0
    idx = np.random.randint(0, len(daily_peaks), size=(trials, sim_days))
    sampled = daily_peaks[idx]
    overload = sampled + export_mva_with_margin > allowed_mva
    prob = overload.mean()
    return prob

def main():
    st.title("BESS Screening & Curtailment Tool")

    st.write("Upload daily peak MVA data and run Monte Carlo curtailment with simple NGED-style reinforcement logic.")

    if not os.path.exists(TEMPLATE_XLSX):
        st.error("Template Excel 'BESS_Screening_Model_final.xlsx' not found in working directory.")
        return

    wb = load_workbook(TEMPLATE_XLSX)
    cfg = wb["Config"]
    ass = wb["Assumptions"]
    data_sheet = wb["Daily_Peaks"]
    res_sheet = wb["Results"]

    sim_days = int(cfg["B2"].value)
    trials = int(cfg["B3"].value)
    energy_full = float(cfg["B5"].value)

    st.header("1. Upload daily peak data")
    uploaded = st.file_uploader("CSV with columns: BSP_Name, Date, Peak_MVA", type="csv")
    if uploaded is not None:
        df = pd.read_csv(uploaded)
        st.write(df.head())
        data_sheet.delete_rows(2, data_sheet.max_row)
        for i, row in df.iterrows():
            r = i + 2
            data_sheet[f"A{r}"] = str(row["BSP_Name"])
            data_sheet[f"B{r}"] = str(row["Date"])
            data_sheet[f"C{r}"] = float(row["Peak_MVA"])
        st.success("Loaded data into Excel Daily_Peaks sheet.")

    st.header("2. Run Monte Carlo simulation")
    if st.button("Run simulation"):
        rows = []
        for r in range(2, data_sheet.max_row+1):
            bsp = data_sheet[f"A{r}"].value
            date = data_sheet[f"B{r}"].value
            peak = data_sheet[f"C{r}"].value
            if bsp and peak is not None:
                rows.append((bsp, date, peak))
        if not rows:
            st.error("No data in Daily_Peaks. Upload CSV first.")
            return
        df_peaks = pd.DataFrame(rows, columns=["BSP_Name","Date","Peak_MVA"])

        size_rows = []
        for r in range(11, 11+20):
            size_mw = ass[f"A{r}"].value
            exp_mva_margin = ass[f"C{r}"].value
            if size_mw is None or exp_mva_margin is None:
                continue
            size_rows.append((size_mw, exp_mva_margin))
        size_df = pd.DataFrame(size_rows, columns=["Size_MW","Export_MVA_with_margin"])

        res_sheet.delete_rows(2, res_sheet.max_row)
        results = []

        for r in range(2, ass.max_row+1):
            bsp_name = ass[f"A{r}"].value
            if not bsp_name:
                continue
            allowed_mva = ass[f"F{r}"].value
            bsp_peaks = df_peaks.loc[df_peaks["BSP_Name"]==bsp_name,"Peak_MVA"].values
            if len(bsp_peaks)==0:
                continue
            for _, srow in size_df.iterrows():
                size_mw = srow["Size_MW"]
                exp_mva = float(srow["Export_MVA_with_margin"])
                prob = monte_carlo_curtailment(bsp_peaks, allowed_mva, exp_mva, sim_days, trials)
                curt_pct = prob*100
                eff_factor = 1-prob
                curtailed_mwh = prob*energy_full*365

                if curt_pct>10:
                    tier="HV_medium"; cost_low=600; cost_high=2000; rag="RED"
                elif curt_pct>2:
                    tier="LV_HV_small"; cost_low=200; cost_high=800; rag="AMBER"
                else:
                    tier="None"; cost_low=0; cost_high=200; rag="GREEN"

                rec = {
                    "BSP_Name":bsp_name,
                    "Size_MW":size_mw,
                    "Curtailment_%":curt_pct,
                    "Curtailment_MWh_per_yr":curtailed_mwh,
                    "Effective_Export_Factor":eff_factor,
                    "Reinforcement_Tier":tier,
                    "Reinforcement_Cost_low_£k":cost_low,
                    "Reinforcement_Cost_high_£k":cost_high,
                    "Overall_RAG":rag
                }
                results.append(rec)

        for i, rec in enumerate(results, start=2):
            res_sheet[f"A{i}"] = rec["BSP_Name"]
            res_sheet[f"B{i}"] = rec["Size_MW"]
            res_sheet[f"C{i}"] = rec["Curtailment_%"]
            res_sheet[f"D{i}"] = rec["Curtailment_MWh_per_yr"]
            res_sheet[f"E{i}"] = rec["Effective_Export_Factor"]
            res_sheet[f"F{i}"] = rec["Reinforcement_Tier"]
            res_sheet[f"G{i}"] = rec["Reinforcement_Cost_low_£k"]
            res_sheet[f"H{i}"] = rec["Reinforcement_Cost_high_£k"]
            res_sheet[f"I{i}"] = rec["Overall_RAG"]

        out_path = "BESS_Screening_Model_updated.xlsx"
        wb.save(out_path)
        st.success("Simulation complete. Results written to Excel.")
        st.dataframe(pd.DataFrame(results))

        with open(out_path,"rb") as f:
            st.download_button("Download updated Excel", f, file_name=out_path, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.header("3. Optional: Inspect NGED datapackage via curl")
    if st.button("Fetch datapackage.json"):
        dp = run_curl_and_get_datapackage()
        if dp is not None:
            st.json(dp.get("resources", [])[:5])

if __name__ == "__main__":
    main()
