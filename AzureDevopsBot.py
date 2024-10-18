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

import logging
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

DISCORD_TOKEN = 'SEU_DISCORD_TOKEN'
DISCORD_CHANNEL_ID = 'SEU_Channel_ID'
AZURE_ORGANIZATION_URL = 'https://dev.azure.com/sua_organizacao/'
AZURE_PROJECT = 'Seu_Projeto'
AZURE_TEAM = 'Seu_Time'
AZURE_PAT = 'SEU_PAT'
CACHE_FILE = 'notified_work_items.pkl'
ROLE_ID = 'SEU_ROLE_ID'
LOG_FILE = 'bot_log.txt'

# Configuração do logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[
    logging.FileHandler(LOG_FILE, 'a', 'utf-8'),
    logging.StreamHandler(sys.stdout)
])

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
        logging.info(f'Bot conectado como {self.user}!')
        self.channel = self.get_channel(DISCORD_CHANNEL_ID)
        if self.channel is None:
            logging.error(f'Erro: Canal com ID {DISCORD_CHANNEL_ID} não encontrado.')
        else:
            logging.info(f'Canal encontrado: {self.channel.name}')
            self.loop.create_task(self.check_updates())

    async def check_updates(self):
        while True:
            try:
                team_context = TeamContext(project=AZURE_PROJECT, team=AZURE_TEAM)
                iterations = work_client.get_team_iterations(team_context, 'current')
                
                if not iterations:
                    logging.warning("Nenhuma iteração atual encontrada.")
                    await asyncio.sleep(60)
                    continue
                
                current_iteration = iterations[0]
                logging.info(f'Iteração atual: {current_iteration.name}')
                
                query = Wiql(query=f"""
                    SELECT [System.Id], [System.Title], [System.State], [System.CreatedDate], [System.ChangedDate]
                    FROM WorkItems
                    WHERE [System.TeamProject] = '{AZURE_PROJECT}'
                    AND [System.IterationPath] = '{current_iteration.path}'
                """)
                result = wit_client.query_by_wiql(query)
                
                if not result.work_items:
                    logging.info("Nenhum item de trabalho atualizado encontrado.")
                
                for work_item in result.work_items:
                    logging.info(f"Verificando item de trabalho: {work_item.id}")
                    item = wit_client.get_work_item(work_item.id, expand='all')
                    
                    created_date = self.parse_date(item.fields["System.CreatedDate"])
                    changed_date = self.parse_date(item.fields["System.ChangedDate"])
                    
                    logging.info(f"Item de trabalho encontrado: {item.fields['System.Title']} - Estado: {item.fields['System.State']} - Data de criação: {created_date} - Data de alteração: {changed_date}")
                    
                    if created_date > self.last_checked:
                        await self.notify_new_work_item(current_iteration, item)
                        self.notified_work_items.add(work_item.id)
                    
                    elif changed_date > self.last_checked:
                        await self.notify_updated_work_item(current_iteration, item, work_item.id)
                    
                    await self.check_comments(item, work_item.id)
                    
                self.last_checked = datetime.now(timezone.utc)
                save_cache(self.notified_work_items)
                
            except Exception as e:
                logging.error(f'Erro ao obter atualizações: {e}')
            
            await asyncio.sleep(300)

    def parse_date(self, date_str):
        if isinstance(date_str, datetime):
            return date_str
        try:
            return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    async def notify_new_work_item(self, current_iteration, item):
        embed = discord.Embed(
            title="‼ Novo Work Item Criado",
            description=f"**Sprint Atual:** {current_iteration.name}",
            color=discord.Color.green()
        )
        embed.add_field(name="Título", value=item.fields["System.Title"], inline=False)
        embed.add_field(name="Status", value=f'{state_emojis.get(item.fields["System.State"], "")} {item.fields["System.State"]}', inline=True)
        
        logging.info(f"Enviando notificação para o Discord: {embed.to_dict()}")
        await self.channel.send(embed=embed)

    async def notify_updated_work_item(self, current_iteration, item, work_item_id):
        revisions = wit_client.get_revisions(work_item_id)
        if len(revisions) > 1:
            previous_revision = revisions[-2]
            previous_state = previous_revision.fields["System.State"]
        else:
            previous_state = "N/A"
        
        previous_state_emoji = state_emojis.get(previous_state, "")
        current_state_emoji = state_emojis.get(item.fields["System.State"], "")
        
        if previous_state != item.fields["System.State"]:
            embed = discord.Embed(
                title="📢 Alteração de Status do Item",
                description=f"**Sprint Atual:** {current_iteration.name}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Título", value=item.fields["System.Title"], inline=False)
            embed.add_field(name="Status", value=f'{previous_state_emoji} {previous_state} > {current_state_emoji} {item.fields["System.State"]}', inline=True)
  
            
            if item.fields["System.State"] == "Testing":
                embed.add_field(name="Ação Requerida", value=f'<@&{ROLE_ID}> 🙋‍♂️', inline=False)
        else:
            embed = discord.Embed(
                title="✍ Edição do Item",
                description=f"**Sprint Atual:** {current_iteration.name}",
                color=discord.Color.orange()
            )
            embed.add_field(name="Título", value=item.fields["System.Title"], inline=False)
            embed.add_field(name="Status", value=f'{current_state_emoji} {item.fields["System.State"]}', inline=True)
  
        
        logging.info(f"Enviando notificação para o Discord: {embed.to_dict()}")
        await self.channel.send(embed=embed)

    async def check_comments(self, item, work_item_id):
        try:
            comments = wit_client.get_comments(project=AZURE_PROJECT, work_item_id=work_item_id)
            for comment in comments.comments:
                comment_date = self.parse_date(comment.created_date)
                if comment_date > self.last_checked:
                    await self.notify_new_comment(item, comment)
        except Exception as e:
            logging.error(f'Erro ao obter comentários: {e}')

    async def notify_new_comment(self, item, comment):
        embed = discord.Embed(
            title="💬 Novo Comentário",
            description=f"**Item:** {item.fields['System.Title']}",
            color=discord.Color.purple()
        )
        embed.add_field(name="Comentário", value=comment.text, inline=False)
        embed.add_field(name="Autor", value=comment.revised_by.display_name, inline=True)
        embed.add_field(name="Data", value=comment.created_date, inline=True)
        
        logging.info(f"Enviando notificação para o Discord: {embed.to_dict()}")
        await self.channel.send(embed=embed)

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True

client = SprintUpdatesBot(intents=intents)
client.run(DISCORD_TOKEN)
