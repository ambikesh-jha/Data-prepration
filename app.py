from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
import pandas as pd
from io import BytesIO
import numpy as np
import re
import os
import uvicorn
import time
from joblib import Parallel, delayed
from utils.description_processor import DescriptionProcessor

app = FastAPI()

UNITS = r'CM|MM|IN|FT|MR|ML|MG|GR|KG|LT|OZ|YARD|YD|GALLON|GAL|GL|OUNCE'
OZ_PATTERN = re.compile(r'(\d+(\.\d+)?\s*OZ)', flags=re.IGNORECASE)

OUTPUT_DIR = "output_csv"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def process_chunk(chunk, processor):
    chunk = chunk.fillna("")
    return chunk.apply(lambda x: pd.Series(processor.process_description(x)))

def extract_pattern(description):
    """
    Extract the parenthesized part of a description if it contains a unit.
    Units: CM, MM, IN, FT, MR, ML, MG, GR, KG, LT, OZ, YARD, YD, GALLON, GAL, GL, OUNCE
    """
    match = re.search(r'\(([^)]+)\)', description)
    if match:
        conv_part = match.group(1).strip()  # Text inside parentheses
        
        if re.search(rf'\b({UNITS})\b', conv_part, re.IGNORECASE):
            return f"({conv_part})"
    
    return None

def process_ai_training_data(file_content: bytes):
    file = BytesIO(file_content)
    excel_data = pd.ExcelFile(file)

    # Load abbreviations
    abbrev_df = excel_data.parse("Abbreviation List APR28 23").dropna(subset=['Word', 'Abbreviation'])
    food_abbrev_df = excel_data.parse("Food Item Abbreviation APR28 23").dropna(subset=['Word or Phrase (en)', 'Abbreviation-(en)'])
    for df, cols in [(abbrev_df, ['Word', 'Abbreviation']), (food_abbrev_df, ['Word or Phrase (en)', 'Abbreviation-(en)'])]:
        df[cols] = df[cols].apply(lambda x: x.str.strip().replace(r'^["\']|["\']$', '', regex=True)).astype('string')

    abbreviations = {
        **dict(zip(abbrev_df['Word'], abbrev_df['Abbreviation'])),
        **{k: v for k, v in zip(food_abbrev_df['Word or Phrase (en)'], food_abbrev_df['Abbreviation-(en)']) if k not in abbrev_df['Word']}
    }

    processor = DescriptionProcessor(abbreviations)
    input_df = excel_data.parse("AI Training Data").astype({'BC Item Description': 'string'})

    # Replace NaN with empty string and replace underscores with spaces
    input_df['BC Item Description'] = input_df['BC Item Description'].fillna("")
    input_df['BC Item Description'] = input_df['BC Item Description'].str.replace("_", " ")

    # Parallel processing
    n_cores = -1
    chunks = np.array_split(input_df['BC Item Description'], max(1, len(input_df) // 1000))
    results = Parallel(n_jobs=n_cores)(delayed(process_chunk)(chunk, processor) for chunk in chunks)
    processed_df = pd.concat(results, axis=0).reset_index(drop=True)
    input_df[['abbreviated_Descriptions', 'length_abbreviated', 'removed_words', 'characters_removed_length', 'un_abbriviated_words']] = processed_df

    input_df['above_40_words'] = (input_df['length_abbreviated'] > 40).astype(int)
    
    # Use parsing-based approach
    input_df['extracted_pattern'] = input_df['abbreviated_Descriptions'].apply(extract_pattern)
    
    input_df['oz_pattern'] = input_df['BC Item Description'].apply(
        lambda x: OZ_PATTERN.search(x).group(1) if OZ_PATTERN.search(x) else None
    )

    # Save to CSV in output_csv directory
    output_file = os.path.join(OUTPUT_DIR, f"processed_data_{int(time.time())}.csv")
    input_df.to_csv(output_file, index=False)
    
    # Prepare the CSV content for streaming response
    output = BytesIO()
    input_df.to_csv(output, index=False)
    output.seek(0)
    return output

@app.get("/", response_class=HTMLResponse)
async def get_home():
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)
    
@app.post("/process-file/")
async def process_file(file: UploadFile = File(...)):
    try:
        start_time = time.time()
        file_content = await file.read()
        result = process_ai_training_data(file_content)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Total execution time: {execution_time:.2f} seconds")
        return StreamingResponse(result, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=processed_data.csv"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
if __name__ == "__main__":
    uvicorn.run(app, port=8000)