# DiffNotifier

### Program Files ###
* diffnotifier.py : Diffs latest_contents and `fetch_url(target_url)` and report using Graph API. Register it to crontab.
* secure_canvas_server.py : Redirects the user to get[redirect_uri] for notification processing.

### Parameter Files ###
* app_access_token : You need to set this to send app request (notification) to yourself.
* user_access_token : You need to set this to use any reporting feature (app request, posting, ...)
* user_access_token_expires : You can optionally set this. If you set, diffnotifier.py will notify it when the expire date come close (in 3 days) via app request.
* target_id : The identifier of facebook (group, person, ...). Your posts are going to be written to the target you set here.
* target_url : The target url which you want to fetch and diff data from.
* latest_contents : It's the lastest data from target_url.
* server.pem : Canvas server should make HTTPS Connections. That's why you need it here.

*FYI, you don't have to set all parameter files.*
