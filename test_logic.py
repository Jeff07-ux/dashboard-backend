import pandas as pd
import io
import sys
import traceback
import re
import unicodedata
from core.config import settings


def normalize_header_value(value: str) -> str:
    if not isinstance(value, str):
        value = str(value)
    normalized = unicodedata.normalize('NFKD', value)
    normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = re.sub(r'[\(\)\[\]\{\}]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def match_column(actual: str, target: str) -> bool:
    actual_norm = normalize_header_value(actual)
    target_norm = normalize_header_value(target)
    return target_norm in actual_norm or actual_norm in target_norm


def map_dataframe_columns(df: pd.DataFrame, required_cols: list[str]) -> pd.DataFrame:
    mapping = {}
    for actual in df.columns:
        for target in required_cols:
            if match_column(actual, target):
                mapping[actual] = target
                break
    return df.rename(columns=mapping)


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
            settings.COL_TO,
            settings.COL_TA
        ]
        
        header_row_index = -1
        for i in range(min(50, len(raw_df))): 
            row_values = raw_df.iloc[i].astype(str).tolist()
            if all(any(match_column(cell, col) for cell in row_values) for col in required_cols):
                header_row_index = i
                break
                
        if header_row_index == -1:
            print("Headers not found")
            return
            
        contents_io = io.BytesIO(contents)
        df = pd.read_excel(contents_io, header=header_row_index)
        df = map_dataframe_columns(df, required_cols)
        missing_columns = [col for col in required_cols if col not in df.columns]
        if missing_columns:
            print(f"Headers not mapped: {', '.join(missing_columns)}")
            return
        
        df_grouped = df.groupby([settings.COL_CABLE_NAME, settings.COL_PHASE], as_index=False).agg({
            settings.COL_TS: "mean",
            settings.COL_TO: "mean",
            settings.COL_TA: "mean"
        })
        
        df_grouped["Taux d'adhérence (%)"] = (df_grouped[settings.COL_TO] / df_grouped[settings.COL_TS]) * 100
        df_grouped["Rendement (%)"] = (df_grouped[settings.COL_TA] / df_grouped[settings.COL_TS]) * 100
        
        df_total = df_grouped.groupby(settings.COL_CABLE_NAME, as_index=False).agg({
            settings.COL_TS: "sum",
            settings.COL_TO: "sum",
            settings.COL_TA: "sum"
        })
        df_total["Total_Performance (%)"] = (df_total[settings.COL_TO] / df_total[settings.COL_TS]) * 100
        df_total["Total_Rendement (%)"] = (df_total[settings.COL_TA] / df_total[settings.COL_TS]) * 100
        
        phase_performance = df_grouped.fillna("").to_dict(orient="records")
        total_performance = df_total.fillna("").to_dict(orient="records")
        
        raw_preview_df = df.head(100)
        raw_data = raw_preview_df.fillna("").to_dict(orient="records") 
        
        print("Success!")
        
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    test()
