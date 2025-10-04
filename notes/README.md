# Find out what is using port 5000
sudo lsof -i :5000
sudo lsof -iTCP:5000 -sTCP:LISTEN