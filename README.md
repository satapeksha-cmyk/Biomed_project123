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

## Configure Google sign-in

PharmaGuard uses Streamlit's OpenID Connect login with Google. Create an OAuth
client in Google Cloud Console, configure the OAuth consent screen, and add your
Streamlit app's OAuth callback URL as an authorized redirect URI. The callback
URL is your app URL followed by `/oauth2callback` (for local development, use
`http://localhost:8501/oauth2callback`).

Add the following to Streamlit secrets (Streamlit Community Cloud: **App
settings → Secrets**). Keep client secrets private and do not commit them to
GitHub:

```toml
[auth]
redirect_uri = "https://YOUR-APP.streamlit.app/oauth2callback"
cookie_secret = "REPLACE_WITH_A_LONG_RANDOM_SECRET"
client_id = "YOUR_GOOGLE_OAUTH_CLIENT_ID"
client_secret = "YOUR_GOOGLE_OAUTH_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[pharmaguard]
admin_emails = ["admin@example.com"]
```

Google accounts with verified emails listed in `admin_emails` receive the
Admin role; all other verified Google accounts receive the User role. Add an
email to the list only when that person should have permission to edit the
interaction knowledge base.

## Local accounts

Users can also register and sign in with an email address and password from
the app's login page. Passwords must be at least 12 characters and are stored
as salted scrypt hashes in the SQLite database. Newly registered accounts are
always regular Users; configure Google admin emails as above to grant Admin
access. Protect and back up `pharma_guard.db` appropriately if retaining
accounts between deployments.

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
