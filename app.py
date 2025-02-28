from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
import pandas as pd
from io import BytesIO
from joblib import Parallel, delayed
import numpy as np
import re
import uvicorn
from utils.description_processor import DescriptionProcessor

app = FastAPI()

UNITS = r'CM|MM|IN|FT|MR|ML|MG|GR|KG|LT|OZ|YARD|YD|GALLON|GAL|GL|OUNCE'
EXTRACT_PATTERN = re.compile(fr'(\d+(\.\d+)?({UNITS})\s*\(\d+(\.\d+)?({UNITS})\))')
OZ_PATTERN = re.compile(r'(\d+(\.\d+)?\s*OZ)', flags=re.IGNORECASE)

def process_chunk(chunk, processor):
    chunk = chunk.fillna("")
    return chunk.apply(lambda x: pd.Series(processor.process_description(x)))

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

    # Replace NaN with empty string to ensure consistent processing
    input_df['BC Item Description'] = input_df['BC Item Description'].fillna("")

    # Parallel processing
    n_cores = -1
    chunks = np.array_split(input_df['BC Item Description'], max(1, len(input_df) // 1000))
    results = Parallel(n_jobs=n_cores)(delayed(process_chunk)(chunk, processor) for chunk in chunks)
    processed_df = pd.concat(results, axis=0).reset_index(drop=True)
    input_df[['abbreviated_Descriptions', 'length_abbreviated', 'removed_words', 'characters_removed_length', 'un_abbriviated_words']] = processed_df

    input_df['above_40_words'] = (input_df['length_abbreviated'] > 40).astype(int)
    input_df['extracted_pattern'] = input_df['abbreviated_Descriptions'].apply(
        lambda x: EXTRACT_PATTERN.search(x).group(1) if EXTRACT_PATTERN.search(x) else None
    )
    input_df['oz_pattern'] = input_df['BC Item Description'].apply(
        lambda x: OZ_PATTERN.search(x).group(1) if OZ_PATTERN.search(x) else None
    )

    output = BytesIO()
    input_df.to_excel(output, index=False)
    output.seek(0)
    return output

@app.get("/", response_class=HTMLResponse)
async def get_home():
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.post("/process-file/")
async def process_file(file: UploadFile = File(...)):
    try:
        file_content = await file.read()
        processed_file = process_ai_training_data(file_content)
        return StreamingResponse(
            processed_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=Updated_File.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, port=8000)