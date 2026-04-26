import pandas as pd
import io
import sys
import traceback
from core.config import settings

def test():
    file_path = 'C:/Users/pc/Desktop/fichier.xlsx'
    try:
        with open(file_path, 'rb') as f:
            contents = f.read()

        raw_df = pd.read_excel(io.BytesIO(contents), header=None)
        
        required_cols = [
            settings.COL_CABLE_NAME,
            settings.COL_PHASE,
            settings.COL_TS,
            settings.COL_TO
        ]
        
        header_row_index = -1
        for i in range(min(50, len(raw_df))): 
            row_values = raw_df.iloc[i].astype(str).tolist()
            if all(col in row_values for col in required_cols):
                header_row_index = i
                break
                
        if header_row_index == -1:
            print("Headers not found")
            return
            
        contents_io = io.BytesIO(contents)
        df = pd.read_excel(contents_io, header=header_row_index)
        
        df_grouped = df.groupby([settings.COL_CABLE_NAME, settings.COL_PHASE], as_index=False).agg({
            settings.COL_TS: "mean",
            settings.COL_TO: "first"
        })
        
        df_grouped["Performance (%)"] = (df_grouped[settings.COL_TO] / df_grouped[settings.COL_TS]) * 100
        
        df_total = df_grouped.groupby(settings.COL_CABLE_NAME, as_index=False).agg({
            settings.COL_TS: "sum",
            settings.COL_TO: "sum"
        })
        df_total["Total_Performance (%)"] = (df_total[settings.COL_TO] / df_total[settings.COL_TS]) * 100
        
        phase_performance = df_grouped.fillna("").to_dict(orient="records")
        total_performance = df_total.fillna("").to_dict(orient="records")
        
        raw_preview_df = df.head(100)
        raw_data = raw_preview_df.fillna("").to_dict(orient="records") 
        
        print("Success!")
        
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    test()
