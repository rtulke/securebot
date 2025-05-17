# Configuração do Bot do Telegram para SecureBot

Este guia vai orientá-lo através do processo de criação de um bot do Telegram e sua configuração para uso com o SecureBot.

## Criando um Bot com o BotFather

1. **Abra o Telegram** e procure por `@BotFather` ou clique neste link: [BotFather](https://t.me/botfather)

2. **Inicie uma conversa** com o BotFather clicando em "Iniciar" ou enviando `/start`

3. **Crie um novo bot** enviando o comando:
   ```
   /newbot
   ```

4. **Escolha um nome** para o seu bot quando solicitado. Este é o nome de exibição que aparecerá nas conversas (por exemplo, "SecureBot Monitor de Segurança")

5. **Escolha um nome de usuário** para o seu bot quando solicitado. Este deve terminar com "bot" e ser único (por exemplo, "seu_seguranca_bot" ou "sua_empresa_securebot")

6. **Salve seu token API!** O BotFather fornecerá um token API que se parece com:
   ```
   123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
   ```
   Este token é crucial para a configuração do SecureBot e deve ser mantido em segurança.

## Obtendo seu ID de Chat

### Método 1: Usando @userinfobot

1. Procure por `@userinfobot` no Telegram e inicie uma conversa
2. O bot responderá automaticamente com as informações da sua conta, incluindo seu ID de Chat

### Método 2: Usando @RawDataBot

1. Procure por `@RawDataBot` no Telegram e inicie uma conversa
2. O bot enviará uma mensagem JSON contendo suas informações
3. Procure pelo campo `"id"` na seção "from" para encontrar seu ID de Chat

### Método 3: Para Chats em Grupo

Se você quiser receber notificações em um grupo:

1. Adicione seu novo bot ao grupo
2. Envie uma mensagem no grupo
3. Visite a seguinte URL no seu navegador (substitua pelo token do seu bot):
   ```
   https://api.telegram.org/bot<SeuTOKENdeBot>/getUpdates
   ```
4. Procure por `"chat":{"id":-123456789,` na resposta. Note que IDs de chat de grupo são tipicamente números negativos

## Configurando Permissões do Bot

Para melhor segurança, você deve configurar estas configurações com o BotFather:

1. Use o comando `/mybots` no BotFather
2. Selecione seu bot recém-criado
3. Clique em "Bot Settings" > "Group Privacy"
4. Selecione "Disable" se seu bot precisar ver todas as mensagens em um grupo, ou mantenha "Enable" (recomendado) se ele só precisar ver comandos direcionados a ele
5. Você também pode definir uma descrição e uma seção sobre o seu bot a partir do menu de configurações do Bot

## Adicionando Permissões de Admin/Viewer no SecureBot

1. Determine os IDs de usuário do Telegram dos administradores e visualizadores
2. Edite o arquivo de configuração do SecureBot (diretamente ou via Ansible):

```toml
[telegram]
bot_token = "SEU_TOKEN_BOT"   # O token do BotFather
chat_id = "SEU_ID_CHAT"       # Seu ID de usuário ou ID de chat de grupo
admin_users = [123456789]     # IDs de usuário dos administradores
viewer_users = [987654321]    # IDs de usuário dos visualizadores
```

## Testando Sua Configuração de Bot

1. Após configurar o SecureBot com seu token de bot e ID de chat, inicie o serviço SecureBot:
   ```bash
   sudo systemctl start securebot
   ```

2. Abra seu cliente Telegram e envie a seguinte mensagem para o seu bot:
   ```
   /start
   ```

3. Seu bot deve responder com uma mensagem de boas-vindas se tudo estiver configurado corretamente

4. Teste os comandos básicos:
   ```
   /help
   /status
   ```

## Solução de Problemas

Se seu bot não estiver respondendo:

1. Verifique os logs do SecureBot:
   ```bash
   sudo journalctl -u securebot
   ```

2. Verifique se o token do seu bot está correto no arquivo de configuração
   
3. Certifique-se de que o serviço SecureBot está em execução:
   ```bash
   sudo systemctl status securebot
   ```

4. Verifique se o ID de usuário do Telegram está corretamente definido como admin ou visualizador na configuração

5. Certifique-se de que seu bot tenha permissões suficientes se usado em um grupo

## Considerações de Segurança

- Nunca compartilhe seu token de bot publicamente
- Faça rodízio do seu token de bot regularmente se suspeitar que ele possa ter sido comprometido
- Adicione apenas usuários confiáveis à lista admin_users
- Considere limitar o bot a um grupo privado em vez de usá-lo em canais públicos

## Próximos Passos

Após configurar com sucesso seu bot do Telegram, prossiga para configurar as configurações de monitoramento no arquivo de configuração do SecureBot para começar a receber notificações de segurança.
