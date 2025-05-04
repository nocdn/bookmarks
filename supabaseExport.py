import io
import zipfile
from datetime import datetime
from flask import Flask, send_file
from flask_cors import CORS
from supabase import create_client

app = Flask(__name__)
CORS(app)

# Supabase credentials
SUPABASE_URL = "https://zglidwrsngurwotngzct.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpnbGlkd3Jzbmd1cndvdG5nemN0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxMTAzNTksImV4cCI6MjA1OTY4NjM1OX0.uLVaw_K83mybR3kuhSfJxM4EidTcXgdWYD6UbIoq6H0"

@app.route("/export", methods=["GET"])
def export_data():
    # 1) Build timestamp and filenames
    now = datetime.now()
    ts = now.strftime("%d-%m-%Y_%H-%M")
    bookmarks_fname = f"bookmarks_{ts}.csv"
    folders_fname   = f"folders_{ts}.csv"
    zip_fname       = f"bookmarks_export_full_{ts}.zip"

    # 2) Fetch CSV data strings from Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    resp_bm = supabase.table("bookmarks").select("*").csv().execute()
    resp_fd = supabase.table("folders")  .select("*").csv().execute()

    # 3) Create in-memory ZIP
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(bookmarks_fname, resp_bm.data or "")
        zf.writestr(folders_fname,   resp_fd.data or "")
    memory_file.seek(0)

    # 4) Return the ZIP as a downloadable file
    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name=zip_fname   # for Flask>=2.0; use attachment_filename=zip_fname on older versions
    )

if __name__ == "__main__":
    app.run(debug=True, port=4871)