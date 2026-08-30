# Caption Editor

A lightweight, browser-based image caption reviewer and editor written in Python. It runs locally and can be opened from another device on the same network.

## Installation

Python 3.9 or newer is the only requirement.

```sh
git clone https://github.com/tdtrumble/caption-editor
```

## Running

On Windows, double-click `0_RUN.bat`. By default, the app can browse image folders under your Windows user folder and automatically chooses an available network port. You can also drag a folder onto `0_RUN.bat`, or pass a root folder explicitly:

```bat
0_RUN.bat "D:\datasets"
```

On macOS or Linux:

```sh
python3 caption_editor.py --root /path/to/datasets
```

The app prints two URLs and opens the local one automatically. To use a phone, connect it to the same Wi-Fi network and open the **Phone / local network** URL. Keep the terminal window open while using the app. If Windows asks whether Python may communicate on private networks, allow private-network access.

When using the default command-line port, opening `http://127.0.0.1:8070` on the same computer without the query string automatically redirects to the current authenticated URL. `0_RUN.bat` chooses a free port, so use the URL it opens or prints. Other devices must use the complete **Phone / local network** URL printed by the app, including its port and `?key=...` part.

Useful options:

```text
--root PATH      Restrict the app to this folder and its subfolders
--port PORT      Listen on a different port (default: 8070)
--keys-file PATH Choose access keys from a different word-list file
--no-browser     Do not open the computer's browser automatically
```

The app randomly chooses an access key from `access_keys.txt` each time it starts. Put one key on each line to customize the choices. Blank lines and lines beginning with `#` are ignored.

## Usage

- Open or browse to a folder containing images.
- Caption files use the same base name as their image (for example, `photo.jpg` and `photo.txt`).
- Captions save automatically when moving to the previous or next image. You can also use **Save caption** or Ctrl+S.
- Page Up and Page Down navigate between images when the caption field is not focused.

The server listens on the local network. Anyone who knows the selected key while the server is running can view images and edit captions under the configured root, so use private words and only run it on a trusted network.
