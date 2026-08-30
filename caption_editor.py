"""A small, LAN-accessible web UI for reviewing image caption files."""

from __future__ import annotations

import argparse
import errno
import hmac
import ipaddress
import json
import mimetypes
import os
from pathlib import Path
import secrets
import socket
import tempfile
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".avif"}
MAX_CAPTION_BYTES = 1024 * 1024
DEFAULT_KEYS_FILE = Path(__file__).with_name("access_keys.txt")


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#15171a">
  <title>Caption Editor</title>
  <style>
    :root { color-scheme: dark; --bg:#0d0f11; --panel:#171a1e; --panel2:#20242a; --line:#31363e; --text:#f2f4f7; --muted:#9ca5b0; --accent:#ffb45b; --danger:#ff7a78; }
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body { margin:0; background:radial-gradient(circle at 20% 0%,#1a2025 0,var(--bg) 42%); color:var(--text); font:15px/1.45 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; overflow:hidden; }
    button,input,textarea { font:inherit; }
    button { min-height:38px; padding:7px 13px; border:1px solid var(--line); border-radius:9px; background:var(--panel2); color:var(--text); cursor:pointer; touch-action:manipulation; }
    button:hover { border-color:#555d69; }
    button:active { transform:translateY(1px); }
    button:disabled { opacity:.42; cursor:default; transform:none; }
    input,textarea { color:var(--text); background:#101317; border:1px solid var(--line); border-radius:9px; outline:none; }
    input:focus,textarea:focus { border-color:var(--accent); box-shadow:0 0 0 3px #ffb45b22; }
    .primary { background:var(--accent); border-color:var(--accent); color:#21170b; font-weight:700; }
    .app { height:100%; display:grid; grid-template-rows:auto 1fr auto; }
    header { min-height:58px; padding:10px clamp(12px,2vw,24px); border-bottom:1px solid var(--line); background:#14171be6; backdrop-filter:blur(12px); display:flex; align-items:center; gap:14px; }
    .brand { font-weight:760; letter-spacing:-.02em; white-space:nowrap; }
    .folder-form { display:flex; gap:8px; flex:1; min-width:0; }
    #folderInput { width:100%; min-width:0; padding:8px 10px; }
    main { min-height:0; display:grid; grid-template-columns:minmax(0,1fr) minmax(300px,390px); }
    .viewer { min-width:0; min-height:0; position:relative; display:grid; place-items:center; padding:clamp(12px,2vw,24px); background-image:linear-gradient(45deg,#121519 25%,transparent 25%),linear-gradient(-45deg,#121519 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#121519 75%),linear-gradient(-45deg,transparent 75%,#121519 75%); background-size:28px 28px; background-position:0 0,0 14px,14px -14px,-14px 0; }
    #image { max-width:100%; max-height:100%; object-fit:contain; border-radius:5px; box-shadow:0 18px 60px #0008; }
    .empty { color:var(--muted); text-align:center; max-width:34rem; padding:28px; }
    .empty strong { display:block; color:var(--text); font-size:20px; margin-bottom:6px; }
    aside { min-height:0; border-left:1px solid var(--line); background:var(--panel); display:grid; grid-template-rows:auto 1fr auto; }
    .meta { padding:18px; border-bottom:1px solid var(--line); }
    #filename { margin:0; font-size:17px; overflow-wrap:anywhere; }
    #counter { color:var(--muted); margin-top:4px; }
    .caption-wrap { min-height:0; padding:18px; display:flex; flex-direction:column; gap:8px; }
    label { color:var(--muted); font-size:13px; font-weight:650; text-transform:uppercase; letter-spacing:.07em; }
    #caption { width:100%; flex:1; min-height:130px; resize:none; padding:12px; line-height:1.55; }
    .save-row { display:flex; align-items:center; gap:10px; padding:0 18px 18px; }
    #save { flex:1; }
    #status { color:var(--muted); font-size:13px; min-width:72px; text-align:right; }
    #status.error { color:var(--danger); }
    footer { min-height:62px; padding:10px clamp(12px,2vw,24px) max(10px,env(safe-area-inset-bottom)); border-top:1px solid var(--line); background:var(--panel); display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:12px; }
    #previous { justify-self:end; }
    #next { justify-self:start; }
    .hint { color:var(--muted); font-size:12px; }
    dialog { width:min(560px,calc(100% - 24px)); max-height:min(680px,calc(100% - 24px)); padding:0; border:1px solid var(--line); border-radius:14px; background:var(--panel); color:var(--text); box-shadow:0 24px 90px #000c; }
    dialog::backdrop { background:#000a; backdrop-filter:blur(3px); }
    .dialog-head,.dialog-foot { padding:14px 16px; display:flex; align-items:center; gap:10px; }
    .dialog-head { border-bottom:1px solid var(--line); }
    .dialog-head strong { flex:1; overflow-wrap:anywhere; }
    .dialog-foot { border-top:1px solid var(--line); justify-content:flex-end; }
    #directoryList { padding:8px; overflow:auto; max-height:470px; }
    .directory { width:100%; text-align:left; border-color:transparent; background:transparent; display:flex; justify-content:space-between; gap:12px; }
    .directory span:last-child { color:var(--muted); white-space:nowrap; }
    @media (max-width:760px) {
      body { overflow:auto; }
      .app { min-height:100%; height:auto; grid-template-rows:auto auto auto; }
      header { align-items:flex-start; flex-wrap:wrap; }
      .brand { width:100%; }
      main { display:flex; flex-direction:column; }
      .viewer { height:52vh; min-height:300px; }
      aside { border-left:0; border-top:1px solid var(--line); min-height:330px; }
      .caption-wrap { min-height:210px; }
      #caption { resize:vertical; }
      footer { position:sticky; bottom:0; z-index:4; grid-template-columns:1fr 1fr; }
      .hint { display:none; }
      #previous,#next { width:100%; justify-self:stretch; min-height:44px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <header><div class="brand">Caption Editor</div><form class="folder-form" id="folderForm"><input id="folderInput" aria-label="Folder path" value="." autocomplete="off" autocapitalize="off" spellcheck="false"><button type="button" id="browse">Browse</button><button class="primary" type="submit">Open</button></form></header>
    <main>
      <section class="viewer"><img id="image" alt="Current image" hidden><div class="empty" id="empty"><strong>Choose an image folder</strong>Open a folder under the configured root to review its images and captions.</div></section>
      <aside><div class="meta"><h1 id="filename">No image selected</h1><div id="counter">0 / 0</div></div><div class="caption-wrap"><label for="caption">Caption</label><textarea id="caption" disabled spellcheck="true" placeholder="Caption text"></textarea></div><div class="save-row"><button class="primary" id="save" disabled>Save caption</button><span id="status">Ready</span></div></aside>
    </main>
    <footer><div class="hint">Page Up / Page Down also navigate</div><button id="previous" disabled>◀ Previous</button><button id="next" disabled>Next ▶</button></footer>
  </div>
  <dialog id="folderDialog"><div class="dialog-head"><strong id="browsePath">.</strong><button id="closeDialog" aria-label="Close">Close</button></div><div id="directoryList"></div><div class="dialog-foot"><button class="primary" id="chooseFolder">Use this folder</button></div></dialog>
  <script>
    const key=new URLSearchParams(location.search).get('key')||'';
    const state={folder:'.',files:[],index:-1,dirty:false,browseFolder:'.'};
    const el=Object.fromEntries([...document.querySelectorAll('[id]')].map(node=>[node.id,node]));
    async function api(path,options={}){const separator=path.includes('?')?'&':'?';const response=await fetch(`${path}${separator}key=${encodeURIComponent(key)}`,{...options,headers:{'Content-Type':'application/json',...(options.headers||{})}});if(!response.ok){let message=`Request failed (${response.status})`;try{message=(await response.json()).error||message}catch(_){}throw new Error(message)}return response.headers.get('content-type')?.includes('application/json')?response.json():response}
    function setStatus(message,isError=false){el.status.textContent=message;el.status.classList.toggle('error',isError)}
    function imageQuery(name){return `/api/image?${new URLSearchParams({folder:state.folder,name,key})}`}
    async function openFolder(folder){try{await saveCaption();setStatus('Loading…');const data=await api(`/api/images?${new URLSearchParams({folder})}`);state.folder=data.folder;state.files=data.files;state.index=data.files.length?0:-1;state.dirty=false;el.folderInput.value=data.folder;await showCurrent();if(!data.files.length)setStatus('No images')}catch(error){setStatus(error.message,true)}}
    async function showCurrent(){const hasImage=state.index>=0&&state.index<state.files.length;el.image.hidden=!hasImage;el.empty.hidden=hasImage;el.caption.disabled=!hasImage;el.save.disabled=!hasImage;el.previous.disabled=!hasImage||state.index===0;el.next.disabled=!hasImage||state.index===state.files.length-1;if(!hasImage){el.filename.textContent='No image selected';el.counter.textContent=`0 / ${state.files.length}`;el.caption.value='';el.empty.innerHTML='<strong>No images here</strong>Choose another folder containing PNG, JPG, WEBP, GIF, BMP, or AVIF files.';return}const file=state.files[state.index];el.filename.textContent=file.name;el.counter.textContent=`${state.index+1} / ${state.files.length}`;el.image.src=imageQuery(file.name);el.image.alt=file.name;try{const data=await api(`/api/caption?${new URLSearchParams({folder:state.folder,name:file.name})}`);el.caption.value=data.caption;state.dirty=false;setStatus(data.exists?'Loaded':'New caption')}catch(error){setStatus(error.message,true)}}
    async function saveCaption(){if(!state.dirty||state.index<0)return;const file=state.files[state.index];await api(`/api/caption?${new URLSearchParams({folder:state.folder,name:file.name})}`,{method:'PUT',body:JSON.stringify({caption:el.caption.value})});state.dirty=false;file.hasCaption=true;setStatus('Saved')}
    async function navigate(delta){const nextIndex=state.index+delta;if(nextIndex<0||nextIndex>=state.files.length)return;try{await saveCaption();state.index=nextIndex;await showCurrent()}catch(error){setStatus(error.message,true)}}
    async function browse(folder){try{const data=await api(`/api/browse?${new URLSearchParams({folder})}`);state.browseFolder=data.folder;el.browsePath.textContent=data.folder;el.directoryList.replaceChildren();if(data.parent!==null){const up=document.createElement('button');up.className='directory';up.innerHTML='<span>↰ Parent folder</span><span></span>';up.onclick=()=>browse(data.parent);el.directoryList.append(up)}for(const directory of data.directories){const button=document.createElement('button');button.className='directory';const name=document.createElement('span');name.textContent=`📁 ${directory.name}`;const count=document.createElement('span');count.textContent=directory.imageCount?`${directory.imageCount} images`:'';button.append(name,count);button.onclick=()=>browse(directory.path);el.directoryList.append(button)}if(!data.directories.length&&data.parent===null)el.directoryList.textContent='No subfolders found.'}catch(error){setStatus(error.message,true)}}
    el.folderForm.addEventListener('submit',event=>{event.preventDefault();openFolder(el.folderInput.value.trim()||'.')});
    el.caption.addEventListener('input',()=>{state.dirty=true;setStatus('Unsaved')});
    el.save.addEventListener('click',()=>saveCaption().catch(error=>setStatus(error.message,true)));
    el.previous.addEventListener('click',()=>navigate(-1));el.next.addEventListener('click',()=>navigate(1));
    el.browse.addEventListener('click',async()=>{await browse(state.folder);el.folderDialog.showModal()});
    el.closeDialog.addEventListener('click',()=>el.folderDialog.close());el.chooseFolder.addEventListener('click',()=>{el.folderDialog.close();openFolder(state.browseFolder)});
    document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'){event.preventDefault();el.save.click()}if(event.target===el.caption||event.target===el.folderInput)return;if(event.key==='PageUp')navigate(-1);if(event.key==='PageDown')navigate(1)});
    window.addEventListener('beforeunload',event=>{if(state.dirty){event.preventDefault();event.returnValue=''}});
    if(!key)setStatus('Open the full URL shown in the server window.',true);else openFolder('.');
  </script>
</body>
</html>
"""


class CaptionServer(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows, SO_REUSEADDR allows unrelated processes to bind the same
    # port. Requests can then be delivered to either process, which breaks the
    # per-launch access key and makes the UI appear empty. Require an exclusive
    # listening port instead.
    allow_reuse_address = False

    def server_bind(self) -> None:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(self, address: tuple[str, int], root: Path, access_key: str):
        super().__init__(address, CaptionRequestHandler)
        self.root = root.resolve()
        self.access_key = access_key

    def resolve_folder(self, relative: str) -> tuple[Path, str]:
        relative = relative.strip().replace("\\", "/") or "."
        if Path(relative).is_absolute():
            raise ValueError("Use a folder path relative to the configured root.")
        candidate = (self.root / relative).resolve()
        try:
            normalized = candidate.relative_to(self.root).as_posix() or "."
        except ValueError as error:
            raise ValueError("That folder is outside the configured root.") from error
        if not candidate.is_dir():
            raise FileNotFoundError("Folder not found.")
        return candidate, normalized

    def resolve_image(self, folder: str, name: str) -> Path:
        directory, _ = self.resolve_folder(folder)
        if not name or Path(name).name != name or Path(name).suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError("Invalid image name.")
        image = (directory / name).resolve()
        try:
            image.relative_to(directory)
        except ValueError as error:
            raise ValueError("Invalid image path.") from error
        if not image.is_file():
            raise FileNotFoundError("Image not found.")
        return image


class CaptionRequestHandler(BaseHTTPRequestHandler):
    server: CaptionServer

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {self.client_address[0]} {format % args}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            # A user opening localhost manually should still arrive at a working
            # UI. Remote clients must continue to use the keyed LAN URL printed
            # at startup so the access key is not disclosed to the network.
            if not self.authorized(parsed.query) and self.client_is_loopback():
                self.send_redirect(f"/?key={quote(self.server.access_key, safe='')}")
                return
            self.send_bytes(INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if not self.authorized(parsed.query):
            self.send_json({"error": "Invalid or missing access key."}, HTTPStatus.UNAUTHORIZED)
            return
        try:
            query = parse_qs(parsed.query)
            routes = {"/api/images": self.get_images, "/api/caption": self.get_caption, "/api/image": self.get_image, "/api/browse": self.get_browse}
            handler = routes.get(parsed.path)
            if handler is None:
                self.send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
            else:
                handler(query)
        except ValueError as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except FileNotFoundError as error:
            self.send_json({"error": str(error)}, HTTPStatus.NOT_FOUND)
        except OSError as error:
            self.send_json({"error": f"File operation failed: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        if not self.authorized(parsed.query):
            self.send_json({"error": "Invalid or missing access key."}, HTTPStatus.UNAUTHORIZED)
            return
        if parsed.path != "/api/caption":
            self.send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
            return
        temporary_path: Path | None = None
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > MAX_CAPTION_BYTES:
                raise ValueError("Caption request is empty or too large.")
            payload = json.loads(self.rfile.read(content_length))
            if not isinstance(payload, dict):
                raise ValueError("Caption request must be a JSON object.")
            caption = payload.get("caption")
            if not isinstance(caption, str) or len(caption.encode("utf-8")) > MAX_CAPTION_BYTES:
                raise ValueError("Caption must be text smaller than 1 MB.")
            query = parse_qs(parsed.query)
            image = self.server.resolve_image(self.param(query, "folder", "."), self.param(query, "name"))
            caption_path = image.with_suffix(".txt")
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=caption_path.parent, delete=False) as temporary:
                temporary.write(caption.strip())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, caption_path)
            temporary_path = None
            self.send_json({"saved": True})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json({"error": "Invalid JSON request."}, HTTPStatus.BAD_REQUEST)
        except ValueError as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except FileNotFoundError as error:
            self.send_json({"error": str(error)}, HTTPStatus.NOT_FOUND)
        except OSError as error:
            self.send_json({"error": f"Could not save caption: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def authorized(self, query_string: str) -> bool:
        supplied = parse_qs(query_string).get("key", [""])[0]
        return hmac.compare_digest(supplied, self.server.access_key)

    def client_is_loopback(self) -> bool:
        try:
            return ipaddress.ip_address(self.client_address[0]).is_loopback
        except ValueError:
            return False

    @staticmethod
    def param(query: dict[str, list[str]], name: str, default: str | None = None) -> str:
        values = query.get(name)
        if values:
            return values[0]
        if default is not None:
            return default
        raise ValueError(f"Missing {name} parameter.")

    def get_images(self, query: dict[str, list[str]]) -> None:
        directory, normalized = self.server.resolve_folder(self.param(query, "folder", "."))
        files = []
        for item in sorted(directory.iterdir(), key=lambda path: path.name.casefold()):
            if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
                files.append({"name": item.name, "hasCaption": item.with_suffix(".txt").is_file()})
        self.send_json({"folder": normalized, "files": files})

    def get_caption(self, query: dict[str, list[str]]) -> None:
        image = self.server.resolve_image(self.param(query, "folder", "."), self.param(query, "name"))
        caption_path = image.with_suffix(".txt")
        exists = caption_path.is_file()
        self.send_json({"caption": caption_path.read_text(encoding="utf-8") if exists else "", "exists": exists})

    def get_image(self, query: dict[str, list[str]]) -> None:
        image = self.server.resolve_image(self.param(query, "folder", "."), self.param(query, "name"))
        self.send_bytes(image.read_bytes(), mimetypes.guess_type(image.name)[0] or "application/octet-stream", cache_control="private, max-age=60")

    def get_browse(self, query: dict[str, list[str]]) -> None:
        directory, normalized = self.server.resolve_folder(self.param(query, "folder", "."))
        try:
            entries = sorted(directory.iterdir(), key=lambda path: path.name.casefold())
        except PermissionError as error:
            raise ValueError("This folder cannot be read.") from error
        directories = []
        for item in entries:
            if not item.is_dir():
                continue
            try:
                image_count = sum(1 for child in item.iterdir() if child.is_file() and child.suffix.lower() in IMAGE_EXTENSIONS)
            except OSError:
                image_count = 0
            directories.append({"name": item.name, "path": item.relative_to(self.server.root).as_posix(), "imageCount": image_count})
        parent = None if normalized == "." else (Path(normalized).parent.as_posix() or ".")
        self.send_json({"folder": normalized, "parent": parent, "directories": directories})

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

    def send_redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def send_bytes(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK, cache_control: str = "no-store") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)


def local_ip_address() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        sock.close()


def load_access_keys(path: Path) -> list[str]:
    try:
        lines = path.expanduser().read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise SystemExit(f"Could not read access-key file: {path}\n{error}") from error
    keys = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
    if not keys:
        raise SystemExit(f"Access-key file has no usable entries: {path}")
    return keys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Edit image caption files from a browser on your local network.")
    parser.add_argument("--root", type=Path, default=Path.home(), help="Top-level folder the app may access (default: home folder).")
    parser.add_argument("--host", default="0.0.0.0", help="Network interface to bind (default: all interfaces).")
    parser.add_argument("--port", type=int, default=8070, help="TCP port to listen on (default: 8070).")
    parser.add_argument(
        "--keys-file",
        type=Path,
        default=DEFAULT_KEYS_FILE,
        help="File containing one possible access key per line.",
    )
    parser.add_argument("--no-browser", action="store_true", help="Do not open the UI in the computer's browser.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Image root does not exist or is not a folder: {root}")
    keys_file = args.keys_file.expanduser().resolve()
    access_key = secrets.choice(load_access_keys(keys_file))
    try:
        server = CaptionServer((args.host, args.port), root, access_key)
    except OSError as error:
        if error.errno in {errno.EADDRINUSE, 10048}:
            raise SystemExit(
                f"Port {args.port} is already in use. Close the earlier Caption Editor window "
                "or start this one with --port 0 to choose a free port automatically."
            ) from error
        raise
    actual_port = server.server_address[1]
    query_key = quote(access_key, safe="")
    computer_url = f"http://127.0.0.1:{actual_port}/?key={query_key}"
    phone_url = f"http://{local_ip_address()}:{actual_port}/?key={query_key}"
    print("\nCaption Editor is running.")
    print(f"Image root: {root}")
    print(f"Access key: {access_key} (chosen from {keys_file})")
    print(f"This computer: {computer_url}")
    print(f"Phone / local network: {phone_url}")
    print("\nKeep this window open. Press Ctrl+C to stop the server.")
    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(computer_url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Caption Editor.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
