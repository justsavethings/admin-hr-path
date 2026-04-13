# HR Document Delivery

This project provides a simple Streamlit UI and a ChromaDB ingestion script to manage access to an employee handbook.

Files added:
- `requirements.txt` — dependencies
- `init_chromadb.py` — ingestion script that upserts leads into a ChromaDB collection `employee_db` using `email` as the unique id
- `app.py` — Streamlit app to check access and download `employee-handbook.pdf`

Quick run:
```powershell
pip install -r requirements.txt
python init_chromadb.py --csv "leads.csv" --chunksize 10000 --dbpath "./hr_chroma_db"
streamlit run app.py
```

Notes:
- Place `leads.csv` and `employee-handbook.pdf` in this folder, or adjust paths when running.
- The ingestion is idempotent and uses chunked CSV reads to handle large files.
