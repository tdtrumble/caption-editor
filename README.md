# Caption Editor

A lightweight, browser-based image caption reviewer and editor written in Python. It runs locally and can be opened from another device on the same network.

## Installation

Python 3.9 or newer is the only requirement.

```sh
git clone https://github.com/tdtrumble/caption-editor
```

## Running

On Windows, double-click `0_RUN.bat`. The launcher asks for each available setting; press Enter at any prompt to accept its current default. By default, the app can browse image folders under your Windows user folder, runs in edit mode, and listens on port 8070. You can also drag a folder onto `0_RUN.bat`, or pass a root folder explicitly; that folder becomes the root prompt's default:

```bat
0_RUN.bat "D:\datasets"
```

On macOS or Linux:

```sh
python3 caption_editor.py --root /path/to/datasets
```

The app prints two URLs and opens the local one automatically. To use a phone, connect it to the same Wi-Fi network and open the **Phone / local network** URL. Keep the terminal window open while using the app. If Windows asks whether Python may communicate on private networks, allow private-network access.

Opening `http://127.0.0.1:8070` on the same computer without the query string automatically redirects to the current authenticated URL. If port 8070 is unavailable, startup stops and reports the process name and PID using it. Other devices must use the complete **Phone / local network** URL printed by the app, including its port and `?key=...` part.

Useful options:

```text
--root PATH      Restrict the app to this folder and its subfolders
--host ADDRESS   Bind to a specific network interface (default: 0.0.0.0)
--port PORT      Listen on a different port (default: 8070)
--keys-file PATH Choose access keys from a different word-list file
--read-only      Allow browsing and caption viewing, but prevent changes
--no-browser     Do not open the computer's browser automatically
```

The app randomly chooses an access key from `access_keys.txt` each time it starts. Put one key on each line to customize the choices. Blank lines and lines beginning with `#` are ignored.

## Usage

- Open or browse to a folder containing images.
- Caption files use the same base name as their image (for example, `photo.jpg` and `photo.txt`).
- Use the **Caption files** field to switch from `.txt` to another caption extension, such as `.sdxl_caption`. The current folder and image refresh immediately; existing files are not renamed or modified.
- If the selected image has no caption file for the current extension, entering text and saving creates one.
- Captions save automatically when moving to the previous or next image. You can also use **Save caption** or Ctrl+S.
- In read-only mode, images, folders, and existing captions remain viewable, while caption editing and saving are disabled.
- Page Up and Page Down navigate between images when the caption field is not focused.

The server listens on the local network. Anyone who knows the selected key while the server is running can view images and, in edit mode, change captions under the configured root, so use private words and only run it on a trusted network.
