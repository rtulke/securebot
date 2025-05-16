# Einrichtung des Telegram-Bots für SecureBot

Diese Anleitung führt Sie durch den Prozess der Erstellung eines Telegram-Bots und dessen Konfiguration für die Verwendung mit SecureBot.

## Erstellung eines Bots mit BotFather

1. **Öffnen Sie Telegram** und suchen Sie nach `@BotFather` oder klicken Sie auf diesen Link: [BotFather](https://t.me/botfather)

2. **Starten Sie eine Konversation** mit BotFather, indem Sie auf "Start" klicken oder `/start` senden

3. **Erstellen Sie einen neuen Bot** durch Senden des Befehls:
   ```
   /newbot
   ```

4. **Wählen Sie einen Namen** für Ihren Bot. Dies ist der Anzeigename, der in Konversationen erscheint (z.B. "SecureBot Sicherheitsmonitor")

5. **Wählen Sie einen Benutzernamen** für Ihren Bot. Dieser muss mit "bot" enden und einzigartig sein (z.B. "ihr_sicherheit_bot" oder "ihre_firma_securebot")

6. **Speichern Sie Ihren API-Token!** BotFather wird Ihnen einen API-Token zur Verfügung stellen, der etwa so aussieht:
   ```
   123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
   ```
   Dieser Token ist entscheidend für die SecureBot-Konfiguration und sollte sicher aufbewahrt werden.

## Ermittlung Ihrer Chat-ID

### Methode 1: Verwendung von @userinfobot

1. Suchen Sie in Telegram nach `@userinfobot` und starten Sie eine Konversation
2. Der Bot antwortet automatisch mit Ihren Kontoinformationen, einschließlich Ihrer Chat-ID

### Methode 2: Verwendung von @RawDataBot

1. Suchen Sie in Telegram nach `@RawDataBot` und starten Sie eine Konversation
2. Der Bot sendet Ihnen eine JSON-Nachricht mit Ihren Informationen
3. Suchen Sie nach dem Feld `"id"` im Abschnitt "from", um Ihre Chat-ID zu finden

### Methode 3: Für Gruppenchats

Wenn Sie Benachrichtigungen in einer Gruppe erhalten möchten:

1. Fügen Sie Ihren neuen Bot zur Gruppe hinzu
2. Senden Sie eine Nachricht in der Gruppe
3. Besuchen Sie die folgende URL in Ihrem Browser (ersetzen Sie mit dem Token Ihres Bots):
   ```
   https://api.telegram.org/bot<IhrBOTToken>/getUpdates
   ```
4. Suchen Sie nach `"chat":{"id":-123456789,` in der Antwort. Beachten Sie, dass Gruppen-Chat-IDs typischerweise negative Zahlen sind

## Konfiguration der Bot-Berechtigungen

Für bessere Sicherheit sollten Sie diese Einstellungen mit BotFather konfigurieren:

1. Verwenden Sie den Befehl `/mybots` in BotFather
2. Wählen Sie Ihren neu erstellten Bot aus
3. Klicken Sie auf "Bot Settings" > "Group Privacy"
4. Wählen Sie "Disable", wenn Ihr Bot alle Nachrichten in einer Gruppe sehen muss, oder behalten Sie "Enable" (empfohlen), wenn er nur Befehle sehen muss, die an ihn gerichtet sind
5. Sie können auch eine Beschreibung und einen "About"-Bereich für Ihren Bot über das Bot-Einstellungsmenü festlegen

## Hinzufügen von Bot-Admin/Viewer-Berechtigungen in SecureBot

1. Ermitteln Sie die Telegram-Benutzer-IDs von Administratoren und Betrachtern
2. Bearbeiten Sie die SecureBot-Konfigurationsdatei (entweder direkt oder über Ansible):

```toml
[telegram]
bot_token = "IHR_BOT_TOKEN"   # Der Token von BotFather
chat_id = "IHRE_CHAT_ID"      # Ihre Benutzer-ID oder Gruppen-Chat-ID
admin_users = [123456789]     # Benutzer-IDs der Administratoren
viewer_users = [987654321]    # Benutzer-IDs der Betrachter
```

## Testen Ihrer Bot-Konfiguration

1. Nach der Konfiguration von SecureBot mit Ihrem Bot-Token und Ihrer Chat-ID starten Sie den SecureBot-Dienst:
   ```bash
   sudo systemctl start securebot
   ```

2. Öffnen Sie Ihren Telegram-Client und senden Sie die folgende Nachricht an Ihren Bot:
   ```
   /start
   ```

3. Ihr Bot sollte mit einer Willkommensnachricht antworten, wenn alles korrekt konfiguriert ist

4. Testen Sie die grundlegenden Befehle:
   ```
   /help
   /status
   ```

## Fehlerbehebung

Wenn Ihr Bot nicht reagiert:

1. Überprüfen Sie die SecureBot-Logs:
   ```bash
   sudo journalctl -u securebot
   ```

2. Vergewissern Sie sich, dass Ihr Bot-Token in der Konfigurationsdatei korrekt ist
   
3. Stellen Sie sicher, dass der SecureBot-Dienst läuft:
   ```bash
   sudo systemctl status securebot
   ```

4. Prüfen Sie, ob Ihre Telegram-Benutzer-ID korrekt als Admin oder Viewer in der Konfiguration eingestellt ist

5. Stellen Sie sicher, dass Ihr Bot über ausreichende Berechtigungen verfügt, wenn er in einer Gruppe verwendet wird

## Sicherheitsüberlegungen

- Teilen Sie Ihren Bot-Token niemals öffentlich
- Wechseln Sie Ihren Bot-Token regelmäßig, wenn Sie vermuten, dass er kompromittiert wurde
- Fügen Sie nur vertrauenswürdige Benutzer zur admin_users-Liste hinzu
- Erwägen Sie, den Bot auf eine private Gruppe zu beschränken, anstatt ihn in öffentlichen Kanälen zu verwenden

## Nächste Schritte

Nachdem Sie Ihren Telegram-Bot erfolgreich eingerichtet haben, fahren Sie mit der Konfiguration der Überwachungseinstellungen in der Konfigurationsdatei von SecureBot fort, um Sicherheitsbenachrichtigungen zu erhalten.
