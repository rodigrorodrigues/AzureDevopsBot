"""
Este script implementa um bot do Discord que monitora atualizações de work items no Azure DevOps.
Ele notifica um canal do Discord sobre a criação de novos work items, mudanças de estado e novos comentários.

Dependências:
- discord.py: Biblioteca para interagir com a API do Discord.
- azure-devops: Biblioteca para interagir com a API do Azure DevOps.
- msrest: Biblioteca para autenticação com o Azure DevOps.

Configuração:
- Substitua os valores de DISCORD_TOKEN, DISCORD_CHANNEL_ID, AZURE_ORGANIZATION_URL, AZURE_PROJECT, AZURE_TEAM, AZURE_PAT e ROLE_ID pelos valores apropriados.
- Instale as dependências necessárias com `pip install discord.py azure-devops`.

Funcionamento:
- O bot se conecta ao Discord e ao Azure DevOps.
- Verifica atualizações nos work items do backlog da sprint atual a cada 10 segundos.
- Notifica o canal do Discord sobre novas criações de work items, mudanças de estado e novos comentários.
- Salva logs das operações em um arquivo de log.
"""

import discord
import asyncio
import pickle
from datetime import datetime, timezone
from azure.devops.connection import Connection
from azure.devops.v7_0.work.models import TeamContext
from azure.devops.v7_0.work_item_tracking.models import Wiql
from msrest.authentication import BasicAuthentication
import os
import sys

DISCORD_TOKEN = 'COLOQUE SEU TOKEN AQUI'
DISCORD_CHANNEL_ID = COLOQUE O ID DO CANAL AQUI
AZURE_ORGANIZATION_URL = 'https://dev.azure.com/SUA_ORGANIZACAO/'
AZURE_PROJECT = 'NOME_DO_PROJETO'
AZURE_TEAM = 'NOME_DA_EQUIPE'
AZURE_PAT = 'COLOQUE SEU PAT AQUI'
CACHE_FILE = 'notified_work_items.pkl'
ROLE_ID = COLOQUE O ID DO CARGO AQUI PARA MENCIONAR EM CASO DE MUDANÇA DE STATUS PARA "Testing"
LOG_FILE = 'bot_log.txt'

class Tee:
    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()

    def flush(self):
        for f in self.files:
            f.flush()

log_file = open(LOG_FILE, 'a', encoding='utf-8')
sys.stdout = Tee(sys.stdout, log_file)
sys.stderr = Tee(sys.stderr, log_file)

credentials = BasicAuthentication('', AZURE_PAT)
connection = Connection(base_url=AZURE_ORGANIZATION_URL, creds=credentials)

work_client = connection.clients.get_work_client()
wit_client = connection.clients.get_work_item_tracking_client()

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'rb') as f:
            return pickle.load(f)
    return set()

def save_cache(cache):
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(cache, f)

state_emojis = {
    "New": "🆕",
    "Active": "⚡",
    "Pending": "⏳",
    "Code Review": "🔍",
    "Testing": "🧪",
    "Test reproved": "❌",
    "Closed": "✅",
    "Removed": "🗑️"
}

class SprintUpdatesBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.notified_work_items = load_cache()
        self.last_checked = datetime.now(timezone.utc)

    async def on_ready(self):
        print(f'Bot conectado como {self.user}!')
        self.channel = self.get_channel(DISCORD_CHANNEL_ID)
        if self.channel is None:
            print(f'Erro: Canal com ID {DISCORD_CHANNEL_ID} não encontrado.')
        else:
            print(f'Canal encontrado: {self.channel.name}')
            self.loop.create_task(self.check_updates())

    async def check_updates(self):
        while True:
            try:
                team_context = TeamContext(project=AZURE_PROJECT, team=AZURE_TEAM)
                iterations = work_client.get_team_iterations(team_context, 'current')
                
                if not iterations:
                    print("Nenhuma iteração atual encontrada.")
                    await asyncio.sleep(60)
                    continue
                
                current_iteration = iterations[0]
                print(f'Iteração atual: {current_iteration.name}')
                
                query = Wiql(query=f"""
                    SELECT [System.Id], [System.Title], [System.State], [System.CreatedDate], [System.ChangedDate]
                    FROM WorkItems
                    WHERE [System.TeamProject] = '{AZURE_PROJECT}'
                    AND [System.IterationPath] = '{current_iteration.path}'
                """)
                result = wit_client.query_by_wiql(query)
                
                if not result.work_items:
                    print("Nenhum item de trabalho atualizado encontrado.")
                
                for work_item in result.work_items:
                    print(f"Verificando item de trabalho: {work_item.id}")
                    item = wit_client.get_work_item(work_item.id, expand='all')
                    
                    try:
                        created_date = datetime.strptime(item.fields["System.CreatedDate"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                    except ValueError:
                        created_date = datetime.strptime(item.fields["System.CreatedDate"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    
                    try:
                        changed_date = datetime.strptime(item.fields["System.ChangedDate"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                    except ValueError:
                        changed_date = datetime.strptime(item.fields["System.ChangedDate"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    
                    print(f"Item de trabalho encontrado: {item.fields['System.Title']} - Estado: {item.fields['System.State']} - Data de criação: {created_date} - Data de alteração: {changed_date}")
                    
                    if created_date > self.last_checked:
                        message = (
                            f'ㅤ\n **Sprint Atual:** {current_iteration.name}\n'
                            f'‼ **Novo Work Item Criado:** {item.fields["System.Title"]}\n'
                            f'**Status:** {state_emojis.get(item.fields["System.State"], "")} {item.fields["System.State"]} \n\nㅤ'
                        )
                        print(f"Enviando notificação para o Discord: {message}")
                        await self.channel.send(message)
                        self.notified_work_items.add(work_item.id)
                    
                    elif changed_date > self.last_checked:
                        revisions = wit_client.get_revisions(work_item.id)
                        if len(revisions) > 1:
                            previous_revision = revisions[-2]
                            previous_state = previous_revision.fields["System.State"]
                        else:
                            previous_state = "N/A"
                        
                        previous_state_emoji = state_emojis.get(previous_state, "")
                        current_state_emoji = state_emojis.get(item.fields["System.State"], "")
                        
                        if previous_state != item.fields["System.State"]:
                            message = (
                                f'ㅤ\n **Sprint Atual:** {current_iteration.name}\n'
                                f'📢 **Alteração de Status do Item:** {item.fields["System.Title"]}\n'
                                f'**Status:** {previous_state_emoji} {previous_state} > {current_state_emoji} {item.fields["System.State"]} \nㅤ'
                            )
                            
                            if item.fields["System.State"] == "Testing":
                                message += f'<@&{ROLE_ID}> 🙋‍♂️\nㅤ'
                        else:
                            message = (
                                f'ㅤ\n **Sprint Atual:** {current_iteration.name}\n'
                                f'✍ **Edição do Item:** {item.fields["System.Title"]}\n'
                                f'**Status:** {current_state_emoji} {item.fields["System.State"]} \n\nㅤ'
                            )
                        
                        print(f"Enviando notificação para o Discord: {message}")
                        await self.channel.send(message)
                        self.notified_work_items.add(work_item.id)
                    
                if 'System.History' in item.fields:
                    history = item.fields['System.History']
                    history_date = changed_date
                    if history_date > self.last_checked:
                        print(f"Novo comentário encontrado")
                        await self.channel.send(
                            f'ㅤ\n **Sprint Atual:** {current_iteration.name}\n'
                            f'📩 **Novo comentário em** {item.fields["System.Title"]}\nㅤ' 
                        )
                
                self.last_checked = datetime.now(timezone.utc)
                save_cache(self.notified_work_items)
                
            except Exception as e:
                print(f'Erro ao obter atualizações: {e}')
            
            await asyncio.sleep(10)

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True

client = SprintUpdatesBot(intents=intents)
client.run(DISCORD_TOKEN)