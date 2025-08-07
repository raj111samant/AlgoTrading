# WhatsApp Automation
For WhatsApp Automation we will be using WAHA platform which provides interactive APIs to talk to WhatsApp service. We use WAHA docker to run it in container. Our scripts will also run inside container.

> Note:
- This is tested on Linux platform.
- Make sure to fill up all TODOs listed in script before running.


## How to run
1. Install docker on your platform. Follow guide from https://docs.docker.com/engine/install/.
2. Download and run WAHA docker inside this folder using command 
```bash
docker run --env "WHATSAPP_DEFAULT_ENGINE=GOWS" -p '3000:3000/tcp' -v './sessions:/app/.sessions' -v './media:/app/.media' -v './scripts:/app/scripts'  --env-file '.env' devlikeapro/waha`
```
3. Inside container run following command
```bash
cd /app/scripts
python3 jobsMain.py
```