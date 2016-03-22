# DiffNotifier

### Script Files ###
* diffnotifier.py : Diffs latest_contents and `fetch_url(target_url)` and report using Graph API. Register it to crontab.
* secure_canvas_server.py : Redirects the user to get[redirect_uri] for notification processing.

### Parameter Files ###
* app_access_token.txt : *(Optional)* If set, <strong>diffnotifier.py</strong> will additionally send an app request (notification) to the user.
* user_access_token.txt : If set, <strong>diffnotifier.py</strong> will report diff result using it (app request, posting, ....)
* user_access_token_expires.txt : *(Optional)* If set, <strong>diffnotifier.py</strong> will notify it when the expire date come close (in 3 days) via app request.
* target_list.json : `target_id` is an identifier in facebook (for a group, a person, etc.) and `target_url` is an url which you want to fetch from. <strong>diffnotifier.py</strong> will fetch and diff from `target_url`, and write posts to `target_id`. The format is `[[target_id1, target_url1(, encoding, regex_filter1, regex_filter2, ...)], [target_id2, target_url2], ...]`
* latest_contents_list.pkl : *(Optional, generated by <strong>diffnotifier.py</strong>)* It's the lastest data fetched from `target_url`.
* server.pem : SSL certificate for <strong>secure_canvas_server.py</strong>
