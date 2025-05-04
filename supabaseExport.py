from supabase import create_client
from datetime import datetime
import zipfile
import os

now = datetime.now()
formatted_date = now.strftime("%d-%m-%Y-%M-%H")

url = "https://zglidwrsngurwotngzct.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpnbGlkd3Jzbmd1cndvdG5nemN0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxMTAzNTksImV4cCI6MjA1OTY4NjM1OX0.uLVaw_K83mybR3kuhSfJxM4EidTcXgdWYD6UbIoq6H0"
supabase = create_client(url, key)

response_bookmarks = supabase.table("bookmarks").select("*").csv().execute()
bookmarks_filename = f"bookmarks_{formatted_date}.csv"

response_folders = supabase.table("folders").select("*").csv().execute()
folders_filename = f"folders_{formatted_date}.csv"

with open(bookmarks_filename, "w") as f:
    f.write(response_bookmarks.data)

with open(folders_filename, "w") as f:
    f.write(response_folders.data)

files_to_zip = [bookmarks_filename, folders_filename]
zip_filename = f"bookmarks_export_full_{formatted_date}.zip"

try:
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file_path in files_to_zip:
            if os.path.exists(file_path):
                zipf.write(file_path, os.path.basename(file_path))
                print(f"Added {file_path} to {zip_filename}")
            else:
                print(f"Warning: File '{file_path}' not found, skipping.")

    print(f"\nSuccessfully created {zip_filename} containing {len(files_to_zip)} files.")
    # delete the original files after zipping
    for file_path in files_to_zip:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted original file: {file_path}")
        else:
            print(f"Warning: File '{file_path}' not found for deletion.")

except Exception as e:
    print(f"An error occurred when zipping: {e}")
