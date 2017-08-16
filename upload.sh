#!/bin/sh
python2.7 main.py
echo
read -n1 -r -p "If output says \"ImportError: No module named appengine.api\" then press Enter or Space... " CONDITION;
echo

if [ "$CONDITION" == "" ]; then
   python2.7 -u "$HOME/bin/google_appengine/appcfg.py" --oauth2_credential_file="$HOME/.appcfg_oauth2_tokens" update "$PWD"
fi
