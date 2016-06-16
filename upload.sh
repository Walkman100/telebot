#!/bin/sh
python2.7 main.py
echo
read -n1 -r -p "If output says \"ImportError: No module named google.appengine.api\" then press enter... "
python2.7 -u "$HOME/bin/google_appengine/appcfg.py" --oauth2_credential_file="$HOME/.appcfg_oauth2_tokens" update "$PWD"
