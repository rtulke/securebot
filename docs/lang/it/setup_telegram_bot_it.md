# Configurazione del Bot Telegram per SecureBot

Questa guida ti accompagnerà nel processo di creazione di un bot Telegram e nella sua configurazione per l'uso con SecureBot.

## Creazione di un Bot con BotFather

1. **Apri Telegram** e cerca `@BotFather` o clicca su questo link: [BotFather](https://t.me/botfather)

2. **Inizia una conversazione** con BotFather cliccando su "Avvia" o inviando `/start`

3. **Crea un nuovo bot** inviando il comando:
   ```
   /newbot
   ```

4. **Scegli un nome** per il tuo bot quando richiesto. Questo è il nome che apparirà nelle conversazioni (ad esempio, "SecureBot Monitor di Sicurezza")

5. **Scegli un nome utente** per il tuo bot quando richiesto. Questo deve terminare con "bot" ed essere unico (ad esempio, "tuo_sicurezza_bot" o "tua_azienda_securebot")

6. **Salva il tuo token API!** BotFather ti fornirà un token API che assomiglia a:
   ```
   123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
   ```
   Questo token è cruciale per la configurazione di SecureBot e deve essere mantenuto al sicuro.

## Ottenere il tuo Chat ID

### Metodo 1: Utilizzando @userinfobot

1. Cerca `@userinfobot` su Telegram e inizia una conversazione
2. Il bot risponderà automaticamente con le informazioni del tuo account, incluso il tuo Chat ID

### Metodo 2: Utilizzando @RawDataBot

1. Cerca `@RawDataBot` su Telegram e inizia una conversazione
2. Il bot ti invierà un messaggio JSON contenente le tue informazioni
3. Cerca il campo `"id"` nella sezione "from" per trovare il tuo Chat ID

### Metodo 3: Per le Chat di Gruppo

Se desideri ricevere notifiche in un gruppo:

1. Aggiungi il tuo nuovo bot al gruppo
2. Invia un messaggio nel gruppo
3. Visita il seguente URL nel tuo browser (sostituisci con il token del tuo bot):
   ```
   https://api.telegram.org/bot<IlTuoTOKENbot>/getUpdates
   ```
4. Cerca `"chat":{"id":-123456789,` nella risposta. Nota che gli ID delle chat di gruppo sono tipicamente numeri negativi

## Configurazione dei Permessi del Bot

Per una migliore sicurezza, dovresti configurare queste impostazioni con BotFather:

1. Usa il comando `/mybots` in BotFather
2. Seleziona il tuo bot appena creato
3. Clicca su "Bot Settings" > "Group Privacy"
4. Seleziona "Disable" se il tuo bot ha bisogno di vedere tutti i messaggi in un gruppo, o mantieni "Enable" (consigliato) se ha solo bisogno di vedere i comandi indirizzati ad esso
5. Puoi anche impostare una descrizione e una sezione "info" per il tuo bot dal menu delle impostazioni del Bot

## Aggiunta dei Permessi Admin/Viewer in SecureBot

1. Determina gli ID utente Telegram degli amministratori e dei visualizzatori
2. Modifica il file di configurazione SecureBot (direttamente o tramite Ansible):

```toml
[telegram]
bot_token = "IL_TUO_TOKEN_BOT"  # Il token da BotFather
chat_id = "IL_TUO_CHAT_ID"      # Il tuo ID utente o ID chat di gruppo
admin_users = [123456789]       # ID utente degli amministratori
viewer_users = [987654321]      # ID utente dei visualizzatori
```

## Test della Configurazione del Bot

1. Dopo aver configurato SecureBot con il token del bot e l'ID chat, avvia il servizio SecureBot:
   ```bash
   sudo systemctl start securebot
   ```

2. Apri il tuo client Telegram e invia il seguente messaggio al tuo bot:
   ```
   /start
   ```

3. Il tuo bot dovrebbe rispondere con un messaggio di benvenuto se tutto è configurato correttamente

4. Testa i comandi di base:
   ```
   /help
   /status
   ```

## Risoluzione dei Problemi

Se il tuo bot non risponde:

1. Controlla i log di SecureBot:
   ```bash
   sudo journalctl -u securebot
   ```

2. Verifica che il token del tuo bot sia corretto nel file di configurazione
   
3. Assicurati che il servizio SecureBot sia in esecuzione:
   ```bash
   sudo systemctl status securebot
   ```

4. Controlla che il tuo ID utente Telegram sia correttamente impostato come admin o viewer nella configurazione

5. Assicurati che il tuo bot abbia permessi sufficienti se utilizzato in un gruppo

## Considerazioni sulla Sicurezza

- Non condividere mai pubblicamente il token del tuo bot
- Ruota regolarmente il token del tuo bot se sospetti che possa essere stato compromesso
- Aggiungi solo utenti fidati alla lista admin_users
- Considera di limitare il bot a un gruppo privato piuttosto che utilizzarlo in canali pubblici

## Prossimi Passi

Dopo aver configurato con successo il tuo bot Telegram, procedi alla configurazione delle impostazioni di monitoraggio nel file di configurazione di SecureBot per iniziare a ricevere notifiche di sicurezza.
