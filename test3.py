import json

string = {'reservation': {'status': 'Starting', 'starts_at': '2022-07-22T23:44:58.175+02:00', 'ends_at': '2022-07-23T01:44:58.175+02:00', 'server_id': 536, 'password': 'andrew.pgOJBL2k', 'rcon': 'rcon.andrew.H7Q2zenPQteV8MY82DZv', 'first_map': None, 'tv_password': 'tv', 'tv_relaypassword': 'tv', 'server_config_id': None, 'whitelist_id': None, 'custom_whitelist_id': None, 'auto_end': True, 'enable_plugins': False, 'enable_demos_tf': False, 'sdr_ip': None, 'sdr_port': None, 'sdr_tv_port': None, 'id': 476465, 'last_number_of_players': 0, 'inactive_minute_counter': 0, 'logsecret': '107867842778479789326985577840124851233', 'start_instantly': True, 'end_instantly': False, 'provisioned': False, 'ended': False, 'steam_uid': '76561198171178258', 'server': {'id': 536, 'name': 'serveme.tf Chicago #01 (Anti-DDoS)', 'flag': 'us', 'ip': 'nfo-chicago.serveme.tf', 'port': '27015', 'ip_and_port': 'nfo-chicago.serveme.tf:27015', 'sdr': False, 'latitude': 41.8868, 'longitude': -87.6386}}, 'actions': {'delete': 'https://na.serveme.tf/api/reservations/476465', 'idle_reset': 'https://na.serveme.tf/api/reservations/476465/idle_reset'}}

#connect nfo-chicago.serveme.tf:27015; password "andrew.pgOJBL2k"
print(string['reservation']['server'])

connect = 'connect ' + string['reservation']['server']['ip'] + ':' + str(string['reservation']['server']['port']) + '; password "' + string['reservation']['password'] + '"'
print(connect)

#rcon_address nfo-chicago.serveme.tf:27015; rcon_password "rcon.andrew.H7Q2zenPQteV8MY82DZv"

rcon = 'rcon_address ' + string['reservation']['server']['ip'] + ':' + str(string['reservation']['server']['port']) + '; rcon_password "' + string['reservation']['rcon'] + '"'
print(rcon)