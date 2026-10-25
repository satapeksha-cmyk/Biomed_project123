# PharmaGuard

## Deploy on Streamlit Community Cloud

`app.py` imports `auth.py`, `database.py`, and `faiss_engine.py` as local modules.
Keep all four Python files in the same directory in the GitHub repository, with
the filenames and capitalization shown here. In Streamlit Community Cloud, select
that repository and set the app file path to `app.py` (or the relative path to
`app.py` if the files are in a subdirectory).

The `requirements.txt` file must be in that same app directory. Commit and push
all project files before redeploying. If the app was already deployed, use
**Manage app → Reboot app** after pushing the corrected files.

The SQLite database is created by `database.py` when the app starts; it is not
an installable Python dependency and does not need to be uploaded.

## Fix `ModuleNotFoundError: No module named 'database'`

Streamlit Cloud runs the files in the GitHub repository; it does not import
Python files from a ZIP that has only been uploaded as an attachment. Extract
`PharmaGuard_Streamlit_Deploy.zip`, then commit and push these files together
to the same directory in the repository:

```text
app.py
auth.py
database.py
faiss_engine.py
requirements.txt
README.md
```

In the Streamlit Cloud app settings, point **Main file path** to the extracted
`app.py` (for example, `app.py` when those files are at the repository root, or
`biomed_project123/app.py` when they are in that subdirectory). Check that the
filename is exactly `database.py` (lowercase) and is not nested in a different
folder. Push the files to the branch selected in the app settings and reboot
the app. The app path from an error traceback can be used to confirm which
directory Streamlit is running.
