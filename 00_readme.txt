#######################################################################
## GSD
#######################################################################
https://github.com/gsd-build/get-shit-done

/gsd:do "Add a blue button in the db_settings.html file above the “Danger Zone” section that resets the “Completed Challenges” list
in index.html to 0 without deleting the data; in other words, all data must remain stored in the database. Everything must be displayed in German."

/gsd:do "Add the posibillity within db_settings.html to upload and download the database"

Here's the right sequence:

  1. /gsd:new-project — tell it you want to Dockerize the app (it will create PROJECT.md, REQUIREMENTS.md, ROADMAP.md)
  2. /gsd:discuss-phase 1 — discuss best practices for the first phase
  3. /gsd:plan-phase 1 — create the execution plan
  4. /gsd:execute-phase 1 — build it

/gsd:settings
/gsd:set-profile quality

update SESSION_CHECKPOINT.md
/clear

@SESSION_CHECKPOINT.md /gsd:execute-phase 4


Personal access tokens (classic): ghp_................
export GHCR_TOKEN=ghp_...........

Use the alias “stecher” from ~/.bash_aliases to check the configuration of the production Caddy, for example.
Please exercise extreme caution when doing so, as this server is in production and is part of the critical infrastructure.

/gsd:do "In db_settings.html, add a new settings card above the existing "Herausforderungen" card with the title "Datenbank Import / Export". It must contain:
Download button – triggers a full database export and downloads it to the client as db_backup_<ISO-timestamp>.db
Upload / Import area – a file input (accept=".db) plus a confirmation button that POSTs the file to the backend and restores the database from it.
Backend endpoints to add (Flask — match the existing stack):
GET /api/settings/db/export → streams the database file
POST /api/settings/db/import → accepts multipart file upload, validates format, replaces DB content
Requirements:
The import button must show a confirmation dialog ("Achtung: Die bestehende Datenbank wird überschrieben.") before submitting.
Match the existing card styling (white card with border-radius, same as the "Herausforderungen" card above it).
Handle errors (wrong file type, corrupt file) with visible inline error messages.
No page reload on export; use a hidden <a> with download attribute or window.location."

#######################################################################
## How to start the app
#######################################################################
*) cd /home/nuc8/05_development/02_python/01_stecher_tennis
*) conda activate stecher_tennis
*) python3 app.py
*) http://localhost:5000/index

#######################################################################
## git 
#######################################################################
git status
git add .
git commit -m "Initial commit"
git push

