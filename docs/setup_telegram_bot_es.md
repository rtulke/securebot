# Configuración del Bot de Telegram para SecureBot

Esta guía le ayudará a crear un bot de Telegram y configurarlo para su uso con SecureBot.

## Creación de un Bot con BotFather

1. **Abra Telegram** y busque `@BotFather` o haga clic en este enlace: [BotFather](https://t.me/botfather)

2. **Inicie una conversación** con BotFather haciendo clic en "Iniciar" o enviando `/start`

3. **Cree un nuevo bot** enviando el comando:
   ```
   /newbot
   ```

4. **Elija un nombre** para su bot cuando se le solicite. Este es el nombre de visualización que aparecerá en las conversaciones (por ejemplo, "SecureBot Monitor de Seguridad")

5. **Elija un nombre de usuario** para su bot cuando se le solicite. Este debe terminar con "bot" y ser único (por ejemplo, "su_bot_seguridad" o "su_empresa_securebot")

6. **¡Guarde su token API!** BotFather le proporcionará un token API que se parece a:
   ```
   123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
   ```
   Este token es crucial para la configuración de SecureBot y debe mantenerse seguro.

## Obtención de su ID de Chat

### Método 1: Usando @userinfobot

1. Busque `@userinfobot` en Telegram e inicie una conversación
2. El bot responderá automáticamente con la información de su cuenta, incluyendo su ID de Chat

### Método 2: Usando @RawDataBot

1. Busque `@RawDataBot` en Telegram e inicie una conversación
2. El bot le enviará un mensaje JSON que contiene su información
3. Busque el campo `"id"` en la sección "from" para encontrar su ID de Chat

### Método 3: Para Chats Grupales

Si desea recibir notificaciones en un grupo:

1. Añada su nuevo bot al grupo
2. Envíe un mensaje en el grupo
3. Visite la siguiente URL en su navegador (reemplace con el token de su bot):
   ```
   https://api.telegram.org/bot<SuTokenDeBOT>/getUpdates
   ```
4. Busque `"chat":{"id":-123456789,` en la respuesta. Tenga en cuenta que los ID de chat de grupo son típicamente números negativos

## Configuración de Permisos del Bot

Para una mejor seguridad, debe configurar estos ajustes con BotFather:

1. Use el comando `/mybots` en BotFather
2. Seleccione su bot recién creado
3. Haga clic en "Bot Settings" > "Group Privacy"
4. Seleccione "Disable" si su bot necesita ver todos los mensajes en un grupo, o mantenga "Enable" (recomendado) si solo necesita ver comandos dirigidos a él
5. También puede establecer una descripción y una sección "about" para su bot desde el menú de configuración del Bot

## Añadir Permisos de Administrador/Visor en SecureBot

1. Determine los IDs de usuario de Telegram de los administradores y visores
2. Edite el archivo de configuración de SecureBot (ya sea directamente o a través de Ansible):

```toml
[telegram]
bot_token = "SU_TOKEN_DE_BOT"  # El token de BotFather
chat_id = "SU_ID_DE_CHAT"      # Su ID de usuario o ID de chat grupal
admin_users = [123456789]      # IDs de usuario de los administradores
viewer_users = [987654321]     # IDs de usuario de los visores
```

## Prueba de su Configuración de Bot

1. Después de configurar SecureBot con su token de bot y ID de chat, inicie el servicio SecureBot:
   ```bash
   sudo systemctl start securebot
   ```

2. Abra su cliente de Telegram y envíe el siguiente mensaje a su bot:
   ```
   /start
   ```

3. Su bot debería responder con un mensaje de bienvenida si todo está configurado correctamente

4. Pruebe los comandos básicos:
   ```
   /help
   /status
   ```

## Solución de Problemas

Si su bot no responde:

1. Revise los logs de SecureBot:
   ```bash
   sudo journalctl -u securebot
   ```

2. Verifique que su token de bot sea correcto en el archivo de configuración
   
3. Asegúrese de que el servicio SecureBot esté funcionando:
   ```bash
   sudo systemctl status securebot
   ```

4. Compruebe que su ID de usuario de Telegram esté correctamente establecido como administrador o visor en la configuración

5. Asegúrese de que su bot tenga permisos suficientes si se usa en un grupo

## Consideraciones de Seguridad

- Nunca comparta su token de bot públicamente
- Rote regularmente su token de bot si sospecha que puede haber sido comprometido
- Solo añada usuarios confiables a la lista admin_users
- Considere limitar el bot a un grupo privado en lugar de usarlo en canales públicos

## Siguientes Pasos

Después de configurar con éxito su bot de Telegram, proceda a configurar los ajustes de monitoreo en el archivo de configuración de SecureBot para comenzar a recibir notificaciones de seguridad.
