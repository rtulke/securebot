# Configuration du Bot Telegram pour SecureBot

Ce guide vous accompagnera dans le processus de création d'un bot Telegram et sa configuration pour une utilisation avec SecureBot.

## Création d'un Bot avec BotFather

1. **Ouvrez Telegram** et recherchez `@BotFather` ou cliquez sur ce lien : [BotFather](https://t.me/botfather)

2. **Démarrez une conversation** avec BotFather en cliquant sur "Démarrer" ou en envoyant `/start`

3. **Créez un nouveau bot** en envoyant la commande :
   ```
   /newbot
   ```

4. **Choisissez un nom** pour votre bot lorsqu'on vous le demande. C'est le nom d'affichage qui apparaîtra dans les conversations (par exemple, "SecureBot Moniteur de Sécurité")

5. **Choisissez un nom d'utilisateur** pour votre bot lorsqu'on vous le demande. Celui-ci doit se terminer par "bot" et être unique (par exemple, "votre_securite_bot" ou "votre_entreprise_securebot")

6. **Sauvegardez votre token API !** BotFather vous fournira un token API qui ressemble à :
   ```
   123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
   ```
   Ce token est crucial pour la configuration de SecureBot et doit être conservé en sécurité.

## Obtention de votre ID de Chat

### Méthode 1 : Utilisation de @userinfobot

1. Recherchez `@userinfobot` sur Telegram et démarrez une conversation
2. Le bot répondra automatiquement avec les informations de votre compte, y compris votre ID de Chat

### Méthode 2 : Utilisation de @RawDataBot

1. Recherchez `@RawDataBot` sur Telegram et démarrez une conversation
2. Le bot vous enverra un message JSON contenant vos informations
3. Cherchez le champ `"id"` dans la section "from" pour trouver votre ID de Chat

### Méthode 3 : Pour les Chats de Groupe

Si vous souhaitez recevoir des notifications dans un groupe :

1. Ajoutez votre nouveau bot au groupe
2. Envoyez un message dans le groupe
3. Visitez l'URL suivante dans votre navigateur (remplacez par le token de votre bot) :
   ```
   https://api.telegram.org/bot<VotreTOKENdeBot>/getUpdates
   ```
4. Cherchez `"chat":{"id":-123456789,` dans la réponse. Notez que les ID de chat de groupe sont généralement des nombres négatifs

## Configuration des Permissions du Bot

Pour une meilleure sécurité, vous devriez configurer ces paramètres avec BotFather :

1. Utilisez la commande `/mybots` dans BotFather
2. Sélectionnez votre bot nouvellement créé
3. Cliquez sur "Bot Settings" > "Group Privacy"
4. Sélectionnez "Disable" si votre bot a besoin de voir tous les messages dans un groupe, ou gardez "Enable" (recommandé) s'il a seulement besoin de voir les commandes qui lui sont adressées
5. Vous pouvez également définir une description et une section "à propos" pour votre bot à partir du menu des paramètres du Bot

## Ajout des Permissions Admin/Viewer dans SecureBot

1. Déterminez les ID d'utilisateur Telegram des administrateurs et des observateurs
2. Modifiez le fichier de configuration SecureBot (soit directement, soit via Ansible) :

```toml
[telegram]
bot_token = "VOTRE_TOKEN_BOT"  # Le token de BotFather
chat_id = "VOTRE_ID_CHAT"      # Votre ID utilisateur ou ID de chat de groupe
admin_users = [123456789]      # IDs utilisateur des administrateurs
viewer_users = [987654321]     # IDs utilisateur des observateurs
```

## Test de votre Configuration Bot

1. Après avoir configuré SecureBot avec votre token bot et votre ID de chat, démarrez le service SecureBot :
   ```bash
   sudo systemctl start securebot
   ```

2. Ouvrez votre client Telegram et envoyez le message suivant à votre bot :
   ```
   /start
   ```

3. Votre bot devrait répondre avec un message de bienvenue si tout est correctement configuré

4. Testez les commandes de base :
   ```
   /help
   /status
   ```

## Dépannage

Si votre bot ne répond pas :

1. Vérifiez les journaux de SecureBot :
   ```bash
   sudo journalctl -u securebot
   ```

2. Vérifiez que votre token bot est correct dans le fichier de configuration
   
3. Assurez-vous que le service SecureBot est en cours d'exécution :
   ```bash
   sudo systemctl status securebot
   ```

4. Vérifiez que votre ID utilisateur Telegram est correctement défini comme admin ou observateur dans la configuration

5. Assurez-vous que votre bot dispose des permissions suffisantes s'il est utilisé dans un groupe

## Considérations de Sécurité

- Ne partagez jamais votre token bot publiquement
- Changez régulièrement votre token bot si vous soupçonnez qu'il a pu être compromis
- N'ajoutez que des utilisateurs de confiance à la liste admin_users
- Envisagez de limiter le bot à un groupe privé plutôt que de l'utiliser dans des canaux publics

## Prochaines Étapes

Après avoir configuré avec succès votre bot Telegram, procédez à la configuration des paramètres de surveillance dans le fichier de configuration de SecureBot pour commencer à recevoir des notifications de sécurité.
