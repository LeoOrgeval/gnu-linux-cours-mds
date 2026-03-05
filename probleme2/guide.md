# Probleme 2 - Reverse proxy, process manager et fail2ban

## 1) Objectif

- Exposer une application web dynamique avec `/login` et `/private`.
- Placer Caddy en reverse proxy devant l'application.
- Utiliser Gunicorn comme gestionnaire de processus.
- Bannir automatiquement une IP apres activite suspecte sur l'authentification.

> Choix technique: Flask + Gunicorn + Caddy + Fail2ban. Le montage est minimal, reproductible et facilement testable sur Debian.

## 2) Comportement attendu

- `/login` affiche un formulaire et accepte un `POST` (credentials en dur).
- Si authentification reussie: acces a `/private`.
- `/private` affiche: `Acces au contenu prive autorise`.
- Si echec de login: reponse HTTP `401` et log d'echec `AUTH_FAIL`.

## 3) Arborescence du rendu

- `probleme2/app/app.py`
- `probleme2/app/requirements.txt`
- `probleme2/config/gunicorn.service`
- `probleme2/config/Caddyfile`
- `probleme2/config/fail2ban/filter.d/flask-login.conf`
- `probleme2/config/fail2ban/jail.d/flask-login.local`
- `probleme2/scripts/test_login.sh`

## 4) Installation (machine Debian neuve)

### 4.1 Installer paquets systeme

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip caddy fail2ban curl
```

### 4.2 Copier l'application

```bash
sudo mkdir -p /opt/probleme2
sudo cp -r probleme2/app /opt/probleme2/
sudo chown -R www-data:www-data /opt/probleme2
```

### 4.3 Installer dependances Python

```bash
sudo -u www-data python3 -m venv /opt/probleme2/venv
sudo -u www-data /opt/probleme2/venv/bin/pip install -r /opt/probleme2/app/requirements.txt
```

## 5) Gunicorn (process manager)

### 5.1 Installer le service

```bash
sudo cp probleme2/config/gunicorn.service /etc/systemd/system/gunicorn-flask-auth.service
sudo sed -i 's|/usr/bin/gunicorn|/opt/probleme2/venv/bin/gunicorn|' /etc/systemd/system/gunicorn-flask-auth.service
```

### 5.2 Creer dossier de logs

```bash
sudo mkdir -p /var/log/flask-auth
sudo chown www-data:www-data /var/log/flask-auth
```

### 5.3 Activer et verifier

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn-flask-auth
sudo systemctl status gunicorn-flask-auth --no-pager
```

## 6) Caddy (reverse proxy)

### 6.1 Installer la configuration

```bash
sudo cp probleme2/config/Caddyfile /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

### 6.2 Test rapide HTTP

```bash
curl -i http://127.0.0.1/login
```

## 7) Fail2ban (jail anti brute-force)

### 7.1 Installer filtre et jail

```bash
sudo cp probleme2/config/fail2ban/filter.d/flask-login.conf /etc/fail2ban/filter.d/flask-login.conf
sudo cp probleme2/config/fail2ban/jail.d/flask-login.local /etc/fail2ban/jail.d/flask-login.local
```

### 7.2 Redemarrer fail2ban

```bash
sudo systemctl enable --now fail2ban
sudo systemctl restart fail2ban
sudo fail2ban-client status
sudo fail2ban-client status flask-login
```

> Activite suspecte retenue: 5 echecs de connexion en moins de 10 minutes depuis la meme IP. Bannissement 1h.

## 8) Verification fonctionnelle

### 8.1 Test login valide + acces prive

```bash
bash probleme2/scripts/test_login.sh http://127.0.0.1
```

### 8.2 Test du bannissement

1. Lancer `test_login.sh` (il envoie 5 echecs).
2. Verifier la jail:

```bash
sudo fail2ban-client status flask-login
```

3. Controler les IP bannies (`Banned IP list`).
4. Optionnel: debannir IP de test:

```bash
sudo fail2ban-client set flask-login unbanip 127.0.0.1
```

## 9) Credentials de test

- `admin / admin123`
- `alice / alice123`

> Les credentials sont volontairement hardcodes dans `app.py` pour respecter la contrainte du sujet (pas de base de donnees).
