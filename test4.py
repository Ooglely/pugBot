
string = 'rcon_address nfo-chicago.serveme.tf:27015; rcon_password "rcon.andrew.GqbeVEbKwhGIjxD6eFLQ"'

ip = string.split(' ')[1].split(':')[0]
port = string.split(' ')[1].split(':')[1].split(';')[0]
password = string.split(' ')[3].split('"')[1]

print(ip + ':' + port + ' ' + password)