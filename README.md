# Evaluation finale GNU/Linux avance

## Problème choisi

- Probleme 2 : configuration d'une application web avec reverse proxy, gestionnaire de processus et détection d'activité malveillante.

## Membres du groupe

- **Chef de projet :**  ORGEVAL Leo
- LEVILLAIN Carl


## Remarques et motivations
 >Nous avons retenu Flask + Gunicorn + Caddy + Fail2ban pour proposer une solution simple, lisible et testable rapidement sur Debian.
>
>Les credentials sont places dans le code, comme demande dans l'énoncé, pour éviter toute complexité inutile de base de données.

## Objectif fonctionnel

L'application expose une route `/login` pour s'authentifier. Une fois connecté, l'utilisateur peut accéder à `/private`, qui retourne le message :

`Accès au contenu prive autorisé`

On attend ce comportement :

- `GET /login`: affiche le formulaire de connexion.
- `POST /login` avec credentials valides : redirige vers `/private`.
- `POST /login` invalide: retourne HTTP `401`.
- Chaque échec de connexion génère un log `AUTH_FAIL`, utilise ensuite par fail2ban.

## Arborescence utile

- Application web : `probleme2/app/app.py`
- Dépendances Python : `probleme2/app/requirements.txt`
- Service systemd Gunicorn : `probleme2/config/gunicorn.service`
- Configuration Caddy : `probleme2/config/Caddyfile`
- Filtre fail2ban : `probleme2/config/fail2ban/filter.d/flask-login.conf`
- Jail fail2ban : `probleme2/config/fail2ban/jail.d/flask-login.local`
- Script de test : `probleme2/scripts/test_login.sh`

## Situation initiale et prerequis

Hypothèses de départ :

- Machine Debian neuve
- Utilisateur `user` dans le groupe `sudo`
- Firewall `nftables` installe et actif

Installer les paquets nécessaires :

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip caddy fail2ban curl
```

## Mise en place de l'application

Copier l'application dans `/opt/probleme2` :

```bash
sudo mkdir -p /opt/probleme2
sudo cp -r probleme2/app /opt/probleme2/
sudo chown -R www-data:www-data /opt/probleme2
```

Créer un environnement virtuel Python et installer les dépendances :

```bash
sudo -u www-data python3 -m venv /opt/probleme2/venv
sudo -u www-data /opt/probleme2/venv/bin/pip install -r /opt/probleme2/app/requirements.txt
```

Créer le dossier de logs applicatifs :

```bash
sudo mkdir -p /var/log/flask-auth
sudo chown www-data:www-data /var/log/flask-auth
```

## Gunicorn (gestionnaire de processus)

Installer le service systemd :

```bash
sudo cp probleme2/config/gunicorn.service /etc/systemd/system/gunicorn-flask-auth.service
sudo sed -i 's|/usr/bin/gunicorn|/opt/probleme2/venv/bin/gunicorn|' /etc/systemd/system/gunicorn-flask-auth.service
```

Activer et vérifier le service :

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn-flask-auth
sudo systemctl status gunicorn-flask-auth --no-pager
```

## Partie 2 - Caddy en reverse proxy

>Choix : Caddy. Il ecoute sur le port 80 et reverse-proxy l'application Gunicorn locale sur `127.0.0.1:8000`.

Installer la configuration Caddy :

```bash
sudo cp probleme2/config/Caddyfile /etc/caddy/Caddyfile
```

Vérifier la validité de la configuration puis recharger le service :

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl enable --now caddy
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

Vérifier le reverse proxy :

```bash
curl -i http://127.0.0.1/login
```

Résultat attendu: une réponse HTTP `200` avec une page HTML de connexion.

## Partie 3 - fail2ban (jail anti brute force)

Définition de l'activité suspecte:

- 5 échecs de connexion sur `/login`
- Dans une fenetre de 10 minutes
- Même IP source
- SoftBan pendant 1 heure

Installer le filtre et la jail :

```bash
sudo cp probleme2/config/fail2ban/filter.d/flask-login.conf /etc/fail2ban/filter.d/flask-login.conf
sudo cp probleme2/config/fail2ban/jail.d/flask-login.local /etc/fail2ban/jail.d/flask-login.local
```

Activer et vérifier fail2ban :

```bash
sudo systemctl enable --now fail2ban
sudo systemctl restart fail2ban
sudo fail2ban-client status
sudo fail2ban-client status flask-login
```

Résultat attendu :

- La jail `flask-login` apparait active
- Le log surveille est `/var/log/flask-auth/app.log`
- La regex detecte les lignes `AUTH_FAIL ip=<HOST> ... path=/login`

## Tests fonctionnels et test de la jail

Credentials de test disponibles dans le code :

- `admin / admin123`
- `test / test123`

Lancer le script de vérification :

```bash
bash probleme2/scripts/test_login.sh http://127.0.0.1
```

Ce script valide 3 points :

- Login valide puis accès à `/private`
- Login invalide avec retour HTTP `401`
- Simulation de 5 échecs pour déclencher fail2ban

Vérifier ensuite le ban :

```bash
sudo fail2ban-client status flask-login
```

Contrôler la section `Banned IP list`.

Pour déban localement et relancer un test :

```bash
sudo fail2ban-client set flask-login unbanip 127.0.0.1
```

## Verification rapide de bout en bout

Si tous les composants sont actifs :

```bash
sudo systemctl status gunicorn-flask-auth --no-pager
sudo systemctl status caddy --no-pager
sudo systemctl status fail2ban --no-pager
```

Et si les tests passent, la solution répond aux parties 1, 2 et 3.

## Dépannage

Si la page `/login` ne repond pas :

- Vérifier `gunicorn-flask-auth` puis `caddy`.
- Vérifier que Gunicorn écoute bien `127.0.0.1:8000`.

Si fail2ban ne ban pas :

- Vérifier que le fichier `/var/log/flask-auth/app.log` est bien alimenté.
- Vérifier la jail : `sudo fail2ban-client status flask-login`.
- Vérifier que 5 échecs réels ont été envoyés dans la fenêtre `findtime`.

## Références

- [Documentation Caddy](https://caddyserver.com/docs/)
- [Documentation Fail2ban](https://fail2ban.readthedocs.io/en/latest/)
- [Documentation Flask](https://flask.palletsprojects.com/en/stable/)
- [Documentation Gunicorn](https://gunicorn.org/quickstart/)
