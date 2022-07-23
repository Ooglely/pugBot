import requests
import random
import string
import json

headers = {'Content-type': 'application/json'}
stepOne = requests.get('https://na.serveme.tf/api/reservations/new?api_key=da8501910f804b4abebdfe8e8e048c2c', headers=headers)
times = stepOne.text

headers = {'Content-type': 'application/json'}
stepTwo = requests.post('https://na.serveme.tf/api/reservations/find_servers?api_key=da8501910f804b4abebdfe8e8e048c2c', data=times, headers=headers)

for server in stepTwo.json()['servers']:
    if "chi" in server['ip']:
        print(server)
        reserve = server
        break

connectPassword = 'andrew.' + ''.join(random.choices(string.ascii_letters + string.digits, k=8))
rconPassword = 'rcon.andrew.' + ''.join(random.choices(string.ascii_letters + string.digits, k=20))


reserveString = {"reservation": {"starts_at": stepOne.json()['reservation']['starts_at'], "ends_at": stepOne.json()['reservation']['ends_at'], "rcon": rconPassword, "password": connectPassword, "server_id": reserve['id']}}

reserveJSON = json.dumps(reserveString)

stepThree = requests.post('https://na.serveme.tf/api/reservations?api_key=da8501910f804b4abebdfe8e8e048c2c', data=reserveJSON, headers=headers)
server = stepThree.json()

connect = 'connect ' + server['reservation']['server']['ip'] + ':' + str(server['reservation']['server']['port']) + '; password "' + server['reservation']['password'] + '"'
rcon = 'rcon_address ' + server['reservation']['server']['ip'] + ':' + str(server['reservation']['server']['port']) + '; rcon_password "' + server['reservation']['rcon'] + '"'