FROM eclipse-mosquitto:2
# Configuration de production : mots de passe tirés des variables d'environnement au démarrage
# (jamais ceux de développement, server/server et device/device).
COPY mosquitto.prod.conf /mosquitto/config/mosquitto.conf
COPY entrypoint.sh /entrypoint-wattou.sh
RUN chmod +x /entrypoint-wattou.sh
ENTRYPOINT ["/entrypoint-wattou.sh"]
