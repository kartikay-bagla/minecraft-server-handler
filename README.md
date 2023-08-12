# Minecraft Server Handler

Quick and dirty way to autostop and autostart ec2 instance.

Start and see status of the server with endpoints.

Server is stopped after 3 minutes of 0 players logged in.

Minecraft is running in a docker instance with `restart: unless-stopped`, so you don't need to do anything there.

Access control is done using a secret key.