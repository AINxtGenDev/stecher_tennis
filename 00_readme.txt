#######################################################################
## GSD
#######################################################################
https://github.com/gsd-build/get-shit-done

/gsd:do "Add a blue button in the db_settings.html file above the “Danger Zone” section that resets the “Completed Challenges” list
in index.html to 0 without deleting the data; in other words, all data must remain stored in the database. Everything must be displayed in German."

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

