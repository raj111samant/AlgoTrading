import datetime
import urllib.request
import json, time,  logging, os

# Set up logging to file with same name but .log extension
log_filename = os.path.splitext(os.path.basename(__file__))[0] + ".log"
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S'
)

# TODO
# Fill dictionary {"GroupName" : "WhatsAppGroupId"}
WAGroupDict = { "ABC" : "XXX@g.us",
                "DEF" : "UVW@g.us"}

def GetResponseFromRequest(url, headers=None, method=None):
    baseUrl = "http://127.0.0.1:3000/api"
    if headers is None: headers = {'accept': '*/*', 'X-Api-Key': 'admin'}
    req = urllib.request.Request(f"{baseUrl}/{url}", headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(e)
        return None

def GetParticipantsListFromGroup(group_id):
    url = f'default/groups/{group_id}/participants'
    participantsList = GetResponseFromRequest(url, None, 'GET')
    return participantsList

def GetPhoneNumberFromLID(lid):
    url = f'default/lids/{lid}'
    lidData = GetResponseFromRequest(url, None, 'GET')
    return lidData["pn"]

def GetParticipantsListFromAllGroups():
    outputList= []
    for group_name, group_id in WAGroupDict.items():
        logging.info(f"Getting participants list from '{group_name}'")
        participantsList = GetParticipantsListFromGroup(group_id)
        print(participantsList)
        logging.info(f"Participants Count: {len(participantsList)}")
        for participant in participantsList:
            # Sometimes PhoneNumber is not present but JID == LID. In this case we can query PhoneNumber from LID
            if "@JID" not in participant['JID'] and "@lid" in participant['JID'] and participant['PhoneNumber'] == "":
                phoneNumber = GetPhoneNumberFromLID(participant['JID'])
                participant['PhoneNumber'] = phoneNumber
            # Sometimes PhoneNumber is not present but JID contains phone number
            if participant['PhoneNumber'] != "" and "@s.whatsapp.net" in participant['JID']:
                participant['PhoneNumber'] = participant['JID']
            # Sometimes PhoneNumber is directly present
            if participant['PhoneNumber'] != None: phoneNumber = participant['PhoneNumber'].split('@')[0]
            else: phoneNumber = None
            outputList.append((group_name, phoneNumber, participant['JID']))
    return outputList

def SendEmail(attachment=None):
    import smtplib, ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.application import MIMEApplication

    sender_email = "sender@email.com"
    receiver_email = "reciever@email.com"
    password = 'XYZ'  # User's app password

    message = MIMEMultipart()
    message["Subject"] = "Participants List " + datetime.datetime.now().strftime('%Y-%m-%d')
    message["From"], message["To"] = sender_email, receiver_email

    body = MIMEText("Please find the attached participants list.", "plain")
    message.attach(body)

    filename = f"Participants_{datetime.datetime.now().strftime('%Y-%m-%d')}.csv"

    with open(attachment, "rb") as f:
        part = MIMEApplication(f.read(), Name=filename)
        part['Content-Disposition'] = f'attachment; filename="{filename}"'
        message.attach(part)

    server = None
    try:
        server = smtplib.SMTP("smtp.mail.yahoo.com", 587)
        server.starttls(context=ssl.create_default_context())
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        print("Email with attachment sent successfully!")
    except smtplib.SMTPAuthenticationError:
        print("Authentication failed. Please check your sender_email and app password.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if server:
            try: server.quit()
            except smtplib.SMTPServerDisconnected: pass

def SendParticipantListToAdmin():
    outputList = GetParticipantsListFromAllGroups()
    import tempfile, base64
    with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8", delete=False) as f:
        for group_name, phoneNumber, jid in outputList:
            f.write(f"{group_name}, {phoneNumber}, {jid}\n")
            f.flush()
        filename = f.name
        SendEmail(filename)
    return outputList

RunSendParticipantListToAdminJob = {   'function':SendParticipantListToAdmin,
                                        'duration':datetime.timedelta(minutes = 60)}

if __name__ == "__main__":
    logging.info(f"Script started {os.path.splitext(os.path.basename(__file__))[0]}")
    SendParticipantListToAdmin()
    logging.info(f"Script finished {os.path.splitext(os.path.basename(__file__))[0]}")
