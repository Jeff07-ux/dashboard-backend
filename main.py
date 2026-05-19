from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import re
import unicodedata
from core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Cable Assembly API"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1].lower()
    if ext not in ["xlsx", "xls", "csv"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an Excel or CSV file.")
    
    contents = await file.read()
    try:
        contents_io = io.BytesIO(contents)
        if ext == "csv":
            # For CSV, we can try to find the header row similar to Excel
            # or just assume it's the first row. Let's try the same header search 
            # to be consistent with Excel handling.
            raw_df = pd.read_csv(contents_io, header=None)
        else:
            raw_df = pd.read_excel(contents_io, header=None)
        
        required_cols = [
            settings.COL_CABLE_NAME,
            settings.COL_PHASE,
            settings.COL_TS,
            settings.COL_TO,
            settings.COL_TA
        ]
        
        # Find the row that contains our required headers
        header_row_index = -1
        for i in range(min(50, len(raw_df))): # check first 50 rows
            row_values = raw_df.iloc[i].astype(str).tolist()
            if all(any(match_column(cell, col) for cell in row_values) for col in required_cols):
                header_row_index = i
                break
                
        if header_row_index == -1:
            raise HTTPException(
                status_code=400, 
                detail=f"Could not find required columns in the first 50 rows. Required: {', '.join(required_cols)}"
            )
            
        # Re-read the dataframe using the correct header row
        contents_io.seek(0)
        if ext == "csv":
            df = pd.read_csv(contents_io, header=header_row_index)
        else:
            df = pd.read_excel(contents_io, header=header_row_index)

        df = map_dataframe_columns(df, required_cols)
        missing_columns = [col for col in required_cols if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Could not map required columns after reading header row. Missing: {', '.join(missing_columns)}"
            )

        # Step 1: Aggregate times for repeated Cable + Phase
        df_grouped = df.groupby([settings.COL_CABLE_NAME, settings.COL_PHASE], as_index=False).agg({
            settings.COL_TS: "mean",
            settings.COL_TO: "mean",
            settings.COL_TA: "mean"
        })
        
        # Step 2: Phase KPI calculations
        df_grouped["Taux d'adhérence (%)"] = (df_grouped[settings.COL_TO] / df_grouped[settings.COL_TS]) * 100
        df_grouped["Rendement (%)"] = (df_grouped[settings.COL_TA] / df_grouped[settings.COL_TS]) * 100
        
        # Step 3: Total Performance per Cable
        df_total = df_grouped.groupby(settings.COL_CABLE_NAME, as_index=False).agg({
            settings.COL_TS: "sum",
            settings.COL_TO: "sum",
            settings.COL_TA: "sum"
        })
        df_total["Total_Performance (%)"] = (df_total[settings.COL_TO] / df_total[settings.COL_TS]) * 100
        df_total["Total_Rendement (%)"] = (df_total[settings.COL_TA] / df_total[settings.COL_TS]) * 100
        
        # Replacing NaNs with empty strings for safe JSON serialization
        phase_performance = df_grouped.fillna("").to_dict(orient="records")
        total_performance = df_total.fillna("").to_dict(orient="records")
        
        raw_preview_df = df.head(100)
        raw_data = raw_preview_df.fillna("").to_dict(orient="records") # Limit to 100 rows for preview

        # Step 4: Summary Metrics
        total_cables = int(df_total[settings.COL_CABLE_NAME].nunique())
        avg_performance = round(float(df_grouped["Taux d'adhérence (%)"].mean()), 2)
        underperforming = int((df_grouped["Taux d'adhérence (%)"] < 80).sum())
        top_cable_row = df_total.loc[df_total["Total_Performance (%)"].idxmax()]
        top_cable = str(top_cable_row[settings.COL_CABLE_NAME])
        top_cable_perf = round(float(top_cable_row["Total_Performance (%)"]), 2)
        
        summary_metrics = {
            "total_cables": total_cables,
            "avg_performance": avg_performance,
            "underperforming_phases": underperforming,
            "top_cable": top_cable,
            "top_cable_perf": top_cable_perf
        }

        return {
            "phase_performance": phase_performance,
            "total_performance": total_performance,
            "raw_preview": raw_data,
            "summary_metrics": summary_metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
