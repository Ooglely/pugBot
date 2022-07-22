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
    
# curl -X POST -H "Content-Type: application/json" -d '{"reservation":{"starts_at":"2014-04-13T18:00:20.415+02:00","ends_at":"2014-04-13T20:00:20.415+02:00","rcon":"foo","password":"bar","server_id":1337}}' 'https://serveme.tf/api/reservations?api_key=your_api_key'
# '{"reservation":{"starts_at":"2014-04-13T18:00:20.415+02:00","ends_at":"2014-04-13T20:00:20.415+02:00","rcon":"foo","password":"bar","server_id":1337}}'
connectPassword = 'andrew.' + ''.join(random.choices(string.ascii_letters + string.digits, k=8))
rconPassword = 'rcon.andrew.' + ''.join(random.choices(string.ascii_letters + string.digits, k=20))

print(reserve['id'])
print(connectPassword)
print(rconPassword)

reserveString = {"reservation": {"starts_at": stepOne.json()['reservation']['starts_at'], "ends_at": stepOne.json()['reservation']['ends_at'], "rcon": rconPassword, "password": connectPassword, "server_id": reserve['id']}}

reserveJSON = json.dumps(reserveString)
# reserveString = '{"reservation": ' + time + ",'rcon':'" + rconPassword + "','password':'" + connectPassword + "','server_id':" + str(reserve['id']) + '}}'

print(reserveString)
stepThree = requests.post('https://na.serveme.tf/api/reservations?api_key=da8501910f804b4abebdfe8e8e048c2c', data=reserveJSON, headers=headers)
server = stepThree.json()

#connect nfo-chicago.serveme.tf:27015; password "andrew.pgOJBL2k"

connect = 'connect ' + server['reservation']['server']['ip'] + ':' + str(server['reservation']['server']['port']) + '; password "' + server['reservation']['password'] + '"'
rcon = 'rcon_address ' + server['reservation']['server']['ip'] + ':' + str(server['reservation']['server']['port']) + '; rcon_password "' + server['reservation']['rcon'] + '"'