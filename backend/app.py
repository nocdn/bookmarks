import io
import math
import os
import zipfile
from datetime import datetime, timezone   # <-- changed
from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    request,
    send_file,
    abort,
    g,
)
from flask_cors import CORS
from supabase import create_client, Client
from openai import OpenAI
import requests
import re
import tempfile
from urllib.parse import urlparse

try:
    from colorthief import ColorThief
    HAS_COLORTHIEF = True
except ImportError:
    HAS_COLORTHIEF = False

load_dotenv()

SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
SUPABASE_KEY: str | None = os.getenv("SUPABASE_KEY")
ALLOW_ORIGIN: str | None = os.getenv("ALLOW_ORIGIN", "*")
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
PORT: int = int(os.getenv("PORT", "4871"))

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY environment variables must be set."
    )

app = Flask(__name__)
CORS(
    app,
    resources={r"/api/*": {"origins": ALLOW_ORIGIN}},
    supports_credentials=False,
)

client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def get_supabase() -> Client:
    """
    Lazily attach one Supabase client per request context.
    """
    if "supabase" not in g:
        g.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return g.supabase


@app.teardown_appcontext
def close_supabase(_err):
    g.pop("supabase", None)


def paginate_meta(total: int, page: int, page_size: int) -> dict:
    """
    Build the pagination block that accompanies list responses.
    """
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if page_size else 1,
    }


def parse_pagination() -> tuple[int, int, int, int]:
    """
    Reads ?page and ?page_size query params (with sane defaults / limits)
    and converts them into Supabase start/end indices.
    """
    page = max(int(request.args.get("page", 1)), 1)
    raw_page_size = int(request.args.get("page_size", 50))
    page_size = min(max(raw_page_size, 1), 200)  # clamp [1, 200]

    start = (page - 1) * page_size
    end = start + page_size - 1
    return page, page_size, start, end


def handle_sb_error(resp):
    """
    Supabase-py 2.x doesn't expose .error on every response object
    (e.g. CSV responses).  Use getattr so we don't blow up when it is
    missing.  If your library version still has .error we behave the
    same as before.
    """
    err = getattr(resp, "error", None) or getattr(resp, "errors", None)
    if err:
        abort(500, err.message if hasattr(err, "message") else str(err))


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(422)
@app.errorhandler(500)
def json_errors(err):
    code = err.code if hasattr(err, "code") else 500
    msg = err.description if hasattr(err, "description") else str(err)
    return jsonify({"error": msg}), code


@app.route("/api/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


@app.route("/api/bookmarks", methods=["GET"])
def list_bookmarks():
    """
    GET /api/bookmarks
        ?folder_id=…
        ?search=foo
        ?sort=created_at | -created_at | title | -title (default -created_at)
        ?page=
        ?page_size=
    """
    page, page_size, start, end = parse_pagination()
    folder_id = request.args.get("folder_id")
    search = request.args.get("search")
    sort = request.args.get("sort", "-created_at")

    sb = get_supabase()
    query = sb.table("bookmarks").select("*", count="exact")

    if folder_id is not None:
        query = query.eq("folder_id", int(folder_id))

    if search:
        # ILIKE is case-insensitive LIKE in Postgres—Supabase exposes it.
        query = query.ilike("title", f"%{search}%")

    # Sorting
    descending = sort.startswith("-")
    sort_field = sort.lstrip("-")
    query = query.order(sort_field, desc=descending)

    query = query.range(start, end)
    resp = query.execute()
    handle_sb_error(resp)

    return (
        jsonify(
            {
                "data": resp.data,
                "pagination": paginate_meta(resp.count or 0, page, page_size),
            }
        ),
        200,
    )


@app.route("/api/bookmarks/<int:bookmark_id>", methods=["GET"])
def get_bookmark(bookmark_id: int):
    sb = get_supabase()
    resp = (
        sb.table("bookmarks")
        .select("*")
        .eq("id", bookmark_id)
        .single()
        .execute()
    )
    handle_sb_error(resp)
    if resp.data is None:
        abort(404, "Bookmark not found")
    return jsonify({"data": resp.data}), 200


@app.route("/api/bookmarks", methods=["POST"])
def create_bookmark():
    """
    Body JSON example:
    {
        "url": "https://example.com",
        "title": "Example",
        "comment": "",
        "folder_id": 42,
        "faviconColor": "rgb(0,0,0)"
    }
    """
    payload = request.get_json(force=True)
    if not payload or "url" not in payload:
        abort(400, "'url' is required")

    sb = get_supabase()
    resp = sb.table("bookmarks").insert(payload).select("*").single().execute()
    handle_sb_error(resp)
    return jsonify({"data": resp.data}), 201


@app.route("/api/bookmarks/<int:bookmark_id>", methods=["PUT", "PATCH"])
def update_bookmark(bookmark_id: int):
    payload = request.get_json(force=True)
    if not payload:
        abort(400, "Request body cannot be empty")

    sb = get_supabase()
    resp = (
        sb.table("bookmarks")
        .update(payload)
        .eq("id", bookmark_id)
        .select("*")
        .single()
        .execute()
    )
    handle_sb_error(resp)
    if resp.data is None:
        abort(404, "Bookmark not found")
    return jsonify({"data": resp.data}), 200


@app.route("/api/bookmarks/<int:bookmark_id>", methods=["DELETE"])
def delete_bookmark(bookmark_id: int):
    sb = get_supabase()
    resp = (
        sb.table("bookmarks")
        .delete()
        .eq("id", bookmark_id)
        .select("id")
        .single()
        .execute()
    )
    handle_sb_error(resp)
    if resp.data is None:
        abort(404, "Bookmark not found")
    return "", 204


@app.route("/api/folders", methods=["GET"])
def list_folders():
    """
    GET /api/folders
        ?parent_id=…      # optional: list only the children of X
    """
    parent_id = request.args.get("parent_id")
    sb = get_supabase()

    query = sb.table("folders").select("*")
    if parent_id is not None:
        query = query.eq("parent_id", int(parent_id))
    resp = query.order("name").execute()
    handle_sb_error(resp)
    return jsonify({"data": resp.data}), 200


@app.route("/api/folders/<int:folder_id>", methods=["GET"])
def get_folder(folder_id: int):
    sb = get_supabase()
    resp = (
        sb.table("folders")
        .select("*")
        .eq("id", folder_id)
        .single()
        .execute()
    )
    handle_sb_error(resp)
    if resp.data is None:
        abort(404, "Folder not found")
    return jsonify({"data": resp.data}), 200


@app.route("/api/folders", methods=["POST"])
def create_folder():
    payload = request.get_json(force=True)
    if not payload or "name" not in payload:
        abort(400, "'name' is required")

    sb = get_supabase()
    resp = sb.table("folders").insert(payload).select("*").single().execute()
    handle_sb_error(resp)
    return jsonify({"data": resp.data}), 201


@app.route("/api/folders/<int:folder_id>", methods=["PUT", "PATCH"])
def update_folder(folder_id: int):
    payload = request.get_json(force=True)
    if not payload:
        abort(400, "Request body cannot be empty")

    sb = get_supabase()
    resp = (
        sb.table("folders")
        .update(payload)
        .eq("id", folder_id)
        .select("*")
        .single()
        .execute()
    )
    handle_sb_error(resp)
    if resp.data is None:
        abort(404, "Folder not found")
    return jsonify({"data": resp.data}), 200


@app.route("/api/folders/<int:folder_id>", methods=["DELETE"])
def delete_folder(folder_id: int):
    sb = get_supabase()
    resp = (
        sb.table("folders")
        .delete()
        .eq("id", folder_id)
        .select("id")
        .single()
        .execute()
    )
    handle_sb_error(resp)
    if resp.data is None:
        abort(404, "Folder not found")
    return "", 204


@app.route("/api/folders/<int:folder_id>/bookmarks", methods=["GET"])
def bookmarks_in_folder(folder_id: int):
    """
    Shortcut that behaves exactly like /api/bookmarks?folder_id=X but
    keeps the folder id in the path.
    """
    request.args = request.args.copy()  # make the ImmutableMultiDict writable
    request.args["folder_id"] = str(folder_id)
    return list_bookmarks()

@app.route("/api/gemini/<url>", methods=["GET"])
def query_gemini(url: str):
    sb = get_supabase()
    folders = sb.table("folders").select("*").execute()
    response = client.chat.completions.create(
        model="gemini-2.5-flash-preview-04-17",
        messages=[
            {"role": "system", "content": "Here is a list of folders in a bookmark manager app. You will be provided with a URL, and you will need to determine which folder this URL should be added to. You can also put links into subfolders if you think it's appropiate. You must ONLY return the folder id as your response - NOT IN A CODE BLOCK, NOT IN QUOTES, NOT IN ANY OTHER FORMAT, JUST THE FOLDER ID IN PLAIN TEXT - THIS IS VERY IMPORTANT. Here is the list of folders: " + str(folders)},
            {
                "role": "user",
                "content": url
            }
        ]
    )
    return response.choices[0].message.content

@app.route("/api/export", methods=["GET"])
def export_zip():
    """
    GET /api/export
        Downloads a ZIP archive with bookmarks_YYYYMMDD-HHMM.csv
        and folders_YYYYMMDD-HHMM.csv
    """
    now = datetime.now(timezone.utc)  # <-- changed (no deprecation warning)
    ts = now.strftime("%Y%m%d-%H%M")

    sb = get_supabase()
    bm_resp = sb.table("bookmarks").select("*").csv().execute()
    fd_resp = sb.table("folders").select("*").csv().execute()
    handle_sb_error(bm_resp)
    handle_sb_error(fd_resp)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"bookmarks_{ts}.csv", bm_resp.data or "")
        zf.writestr(f"folders_{ts}.csv", fd_resp.data or "")
    zip_buf.seek(0)

    return send_file(
        zip_buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"bookmark_export_{ts}.zip",
    )


@app.route("/api/title", methods=["GET"])
def fetch_title():
    """
    GET /api/title?url=...
    Fetches the title of a webpage and extracts the dominant color from its favicon.
    Returns: {"title": "...", "faviconColor": [r, g, b] or null}
    """
    url = request.args.get("url")
    if not url:
        abort(400, "url parameter is required")
    
    # Add https:// if no protocol specified
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"
    
    # Define user agent
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; BookmarkAppBot/1.0)"
    }
    
    try:
        # Fetch the webpage
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        # Extract title using regex
        title_match = re.search(r'<title[^>]*>(.*?)</title>', response.text, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        
        # Initialize favicon color
        favicon_color = None
        
        # Try to fetch favicon and extract color
        if HAS_COLORTHIEF:
            try:
                parsed_url = urlparse(url)
                favicon_url = f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico"
                
                favicon_response = requests.get(favicon_url, headers=headers, timeout=5)
                if favicon_response.status_code == 200:
                    # Use a temporary file for ColorThief
                    with tempfile.NamedTemporaryFile(suffix=".ico", delete=False) as tmp_file:
                        tmp_file.write(favicon_response.content)
                        tmp_file_path = tmp_file.name
                    
                    try:
                        ct = ColorThief(tmp_file_path)
                        dominant_color = ct.get_color(quality=1)
                        favicon_color = list(dominant_color)  # Convert tuple to list
                    finally:
                        # Clean up temp file
                        os.unlink(tmp_file_path)
                        
            except Exception as e:
                # Silently ignore favicon/color extraction errors
                pass
        
        return jsonify({
            "title": title,
            "faviconColor": favicon_color
        }), 200
        
    except requests.RequestException as e:
        error_type = type(e).__name__
        if isinstance(e, requests.HTTPError):
            abort(500, f"Failed to fetch URL: received status {e.response.status_code}")
        else:
            abort(500, f"Failed to fetch URL: network error - {error_type}")
    except Exception as e:
        abort(500, f"An internal server error occurred: {type(e).__name__}")


if __name__ == "__main__":
    app.run(debug=True, port=PORT)