import websocket 
import json
import requests
import re
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem

class Client:

    def __init__(self, token: str, user_agent: str):
        self.token = token
        self.user_agent = user_agent
        self.ws = websocket.WebSocket()
        self.gateway = 'wss://gateway.discord.gg/?encoding=json&v=9'

    def get_build_number(self) -> int:
        headers = {
            'User-Agent': self.user_agent
        }

        response = requests.get(
            'https://discord.com/login', 
            headers=headers
        )

        if response.status_code != 200:
            return 0

        matches = re.findall(r'<script defer src="\/assets\/([a-zA-Z0-9]+\.)?([a-zA-Z0-9]+)\.js', response.text) 
        
        for match in matches:
            response = requests.get(
                f'https://discord.com/assets/{match[0]}{match[1]}.js', 
                headers=headers
            )

            if "buildNumber" not in response.text:
                continue
            else:
                build_number = response.text.split('buildNumber:"')[1].split('"')[0]
                return build_number

        return 0
        
    def send(self, payload: dict) -> None:
        self.ws.send(json.dumps(payload))

    def receive(self) -> dict:
        response = self.ws.recv()
        if response:
            return json.loads(response)

    def fetch_members(self, guild_id: str, channel_id: str) -> dict:
        payload = {
            'op': 14,
            'd': {
                'guild_id': guild_id,
                'typing': True,
                'threads': False,
                'activities': True,
                'members': [],
                'channels': {
                    channel_id: [[0, 99]]
                },
            },
        }
        
        self.ws.send(json.dumps(payload))
        print(f'subscribed to guild: {guild_id} on channel: {channel_id}')
        print(f'fetching members...')

        member_range = [[0, 99]]
        member_count = 0
        index = 0
        members = []

        while True:
            response = self.receive()
            if not response:
                continue
            #print(f'event received: {response["t"]}')

            if response['t'] == 'GUILD_MEMBER_LIST_UPDATE':
                for op in response['d']['ops']:
                    match(op['op']):

                        case 'SYNC':
                            if not member_count:
                                member_count = response['d']['online_count']

                            for item in op['items']:
                                if item.get('member'):
                                    if item not in members:
                                        members.append(item)

                            match(len(member_range)):
                                case 1: 
                                    member_range.append([member_range[0][1] + 1, member_range[0][1] + 100])

                                case 2: 
                                    member_range.append([member_range[1][1] + 1, member_range[1][1] + 100])
                                    
                                case 3:
                                    member_range.append([member_range[1][1] + 1, member_range[1][1] + 100])
                                    member_range.append([member_range[2][1] + 1, member_range[2][1] + 100])
                                    member_range.pop(1)
                                    member_range.pop(2)

                            #print(f'requesting members with range: {member_range}')
                            self.send({
                                'op': 14, 
                                'd': {
                                    'guild_id': guild_id,
                                    'channels': {
                                        channel_id: member_range
                                    },
                                }
                            })
                           
                        case 'INVALIDATE':
                            if op['range'][0] >= member_count: 
                                print(f'successfully fetched {len(members)} members')
                                return members

    def connect(self) -> None:
        self.ws.connect(self.gateway)
        response = self.receive()
      
        build_number = self.get_build_number()
        print(f'discord build number: {build_number}')

        payload = {
            'op': 2,
            'd': {
                'token': self.token,
                'capabilities': 30717,
                'properties': {
                    'os': 'Windows', 
                    'browser': 'Chrome',
                    'device': '',
                    'system_locale': 'pl-PL',
                    'has_client_mods': False,
                    'browser_user_agent': self.user_agent,
                    'browser_version': '133.0.0.0', 
                    'os_version': '10', 
                    'referrer': '', 
                    'referring_domain': '', 
                    'referrer_current': '', 
                    'referring_domain_current': '', 
                    'release_channel': 'stable',
                    'client_build_number': build_number,
                    'client_event_source': None
                },
                'presence': { 
                    'status': 'unknown',
                    'since': 0,
                    'activities': [],
                    'afk': False 
                },
                'compress': False,
                'client_state': {
                    'guild_versions':{}
                }
            }
        }

        self.send(payload)
        response = self.receive()
        
        if response['t'] == 'READY':
            print(f'connected to: {response["d"]["user"]["username"]}')

if __name__ == '__main__':

    software_names = [SoftwareName.CHROME.value]
    operating_systems = [OperatingSystem.WINDOWS.value]   

    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)
    user_agents = user_agent_rotator.get_user_agents()

    user_agent = user_agent_rotator.get_random_user_agent()

    TOKEN = 'token-here'
    GUILD_ID = 'guild-id-here'
    CHANNEL_ID = 'channel-id-here'

    client = Client(TOKEN, user_agent)
    client.connect()

    members = client.fetch_members(GUILD_ID, CHANNEL_ID)
    json.dump(members, open('members.json', 'w'), indent=4, sort_keys=False)
