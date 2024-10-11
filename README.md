# AzureDevopsBot

Este script implementa um bot do Discord que monitora atualizações de work items no Azure DevOps. Ele notifica um canal do Discord sobre a criação de novos work items, mudanças de estado e novos comentários.

## Dependências:

- `discord.py`: Biblioteca para interagir com a API do Discord.
- `azure-devops`: Biblioteca para interagir com a API do Azure DevOps.
- `msrest`: Biblioteca para autenticação com o Azure DevOps.

## Configuração:

1. Substitua os valores de `DISCORD_TOKEN`, `DISCORD_CHANNEL_ID`, `AZURE_ORGANIZATION_URL`, `AZURE_PROJECT`, `AZURE_TEAM`, `AZURE_PAT` e `ROLE_ID` pelos valores apropriados.
2. Instale as dependências necessárias com:
   ```sh
   pip install discord.py azure-devops
   ```

## Funcionamento:

- O bot se conecta ao Discord e ao Azure DevOps.
- Verifica atualizações nos work items do backlog da sprint atual a cada 10 segundos.
- Notifica o canal do Discord sobre novas criações de work items, mudanças de estado e novos comentários.
- Salva logs das operações em um arquivo de log.
```

Vou criar esse arquivo no seu repositório.Aqui está um exemplo de README.md em markdown para o seu projeto:

```markdown
# Azure DevOps Discord Bot

Este script implementa um bot do Discord que monitora atualizações de work items no Azure DevOps. Ele notifica um canal do Discord sobre a criação de novos work items, mudanças de estado e novos comentários.

## Dependências

- `discord.py`: Biblioteca para interagir com a API do Discord.
- `azure-devops`: Biblioteca para interagir com a API do Azure DevOps.
- `msrest`: Biblioteca para autenticação com o Azure DevOps.

## Configuração

1. Substitua os valores das seguintes variáveis com os valores apropriados:
   - `DISCORD_TOKEN`
   - `DISCORD_CHANNEL_ID`
   - `AZURE_ORGANIZATION_URL`
   - `AZURE_PROJECT`
   - `AZURE_TEAM`
   - `AZURE_PAT`
   - `ROLE_ID`

2. Instale as dependências necessárias com o comando:
   ```bash
   pip install discord.py azure-devops
   ```

## Funcionamento

- O bot se conecta ao Discord e ao Azure DevOps.
- Verifica atualizações nos work items do backlog da sprint atual a cada 10 segundos.
- Notifica o canal do Discord sobre novas criações de work items, mudanças de estado e novos comentários.
- Salva logs das operações em um arquivo de log.

## Como Executar

Após configurar as variáveis e instalar as dependências, execute o script com o comando:
```bash
python AzureDevopsBot.py
```

## Logs

Os logs das operações são salvos em um arquivo de log para monitoramento e depuração.

---

Sinta-se à vontade para contribuir ou relatar problemas no repositório.

