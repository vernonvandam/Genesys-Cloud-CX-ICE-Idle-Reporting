# Genesys-Cloud-CX-ICE-Idle-Reporting

## How to run
1. On Genesys Cloud, create a new role called "OAuth for WebRTC Reporting" and add the following permissions:
 - Analytics > Agent Conversation Detail > View
 - Analytics > Conversation Aggregate > View
 - Analytics > Conversation Detail > View
 - Telephony > PCAP > Add
 - Telephony > PCAP > View

2. Create a new OAuth credential called OAuth for WebRTC Reporting with grant type "Client Credentials"

3. Copy the client id, client secret and API host into a file in the root directory of this project called .env.
   For example
```
# My Customer
API_HOST="https://api.mypurecloud.com.au"
GENESYS_CLOUD_CLIENT_ID="XXXXXXX-XXXX-XXXX"
GENESYS_CLOUD_CLIENT_SECRET="YYYYYY"
```

4. Carefully watch for the TkInter window to open in the background, which is waiting for you to provide the name of the output file for your results
