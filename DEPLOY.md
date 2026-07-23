# Deploy di CiccioTV su una VM Ubuntu (Oracle Cloud)

Obiettivo: raggiungere CiccioTV da **qualsiasi browser, ovunque**, tramite un
dominio gratuito **`cicciotv.duckdns.org`** con **HTTPS**, protetto da un **login
con PIN** dentro l'app, senza esporre il backend direttamente su internet.

Architettura:

```
Internet ──HTTPS──► Caddy (porte 80/443, certificato)
                      ├── /api/* ──► uvicorn/FastAPI su 127.0.0.1:8000  (login via PIN)
                      └── tutto il resto ──► sito React (frontend/dist)
```

Il backend ascolta **solo su localhost**: da fuori si passa obbligatoriamente da
Caddy. L'accesso è protetto dal login con PIN gestito dall'app stessa (tabelle
utenti/sessioni). Sostituisci `cicciotv.duckdns.org` col tuo dominio vero se ne
scegli un altro.

---

## 1. Dominio gratuito (DuckDNS)

1. Vai su <https://www.duckdns.org> e accedi (Google/GitHub).
2. Crea il sottodominio **`cicciotv`** → diventa `cicciotv.duckdns.org`.
3. Nel campo **current ip** metti l'**IP pubblico della VM Oracle** (lo trovi nel
   pannello Oracle, "Public IP address" dell'istanza) e premi **update ip**.
4. Segnati il **token** in cima alla pagina DuckDNS: serve per l'aggiornamento
   automatico dell'IP (passo 8, opzionale ma consigliato).

Verifica dal tuo PC che il dominio punti alla VM:

```bash
ping cicciotv.duckdns.org
```

Deve rispondere l'IP pubblico della VM.

---

## 2. Aprire le porte 80 e 443 su Oracle (Security List)

Nel pannello Oracle Cloud:

1. **Networking → Virtual Cloud Networks →** la tua VCN **→ Security Lists →**
   la Default Security List.
2. **Add Ingress Rules**, due regole:
   - Source `0.0.0.0/0`, IP Protocol `TCP`, Destination Port `80`
   - Source `0.0.0.0/0`, IP Protocol `TCP`, Destination Port `443`

> La porta 22 (SSH) è di solito già aperta. **Non** aprire la 8000: il backend
> non deve essere raggiungibile da fuori.

---

## 3. Collegarsi alla VM e aprire il firewall interno di Ubuntu

Le immagini Ubuntu di Oracle partono con un `iptables` chiuso: **anche dopo** aver
aperto la Security List, senza questo passo le porte restano bloccate (il tranello
classico di Oracle).

Collegati via SSH (dal tuo PC):

```bash
ssh ubuntu@cicciotv.duckdns.org
```

Poi, sulla VM:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

---

## 4. Installare le dipendenze sulla VM

```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip

# Node 20 (serve per buildare il frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Caddy (reverse proxy + HTTPS)
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

---

## 5. Clonare il progetto

```bash
cd ~
git clone https://github.com/Webmasterciccio/cicciotv.git
cd cicciotv
```

---

## 6. Copiare i due file NON versionati dal tuo PC Windows

`git clone` non porta `.env` (chiave TMDB) né `cicciotv.db` (la tua libreria):
sono esclusi apposta. Copiali dal PC alla VM. **Da PowerShell sul tuo PC**, nella
cartella del progetto:

```powershell
scp .env ubuntu@cicciotv.duckdns.org:/home/ubuntu/cicciotv/.env
scp cicciotv.db ubuntu@cicciotv.duckdns.org:/home/ubuntu/cicciotv/cicciotv.db
```

> Se non copi `cicciotv.db`, la VM parte con una libreria vuota (il file viene
> creato al primo avvio). Se invece la vuoi trasferire, fallo a backend **spento**
> per non copiarlo a metà scrittura.

---

## 7. Backend come servizio (systemd)

```bash
cd ~/cicciotv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Installa il servizio
sudo cp deploy/cicciotv.service /etc/systemd/system/cicciotv.service
sudo systemctl daemon-reload
sudo systemctl enable --now cicciotv

# Verifica che risponda in locale
curl http://127.0.0.1:8000/
```

Deve restituire il messaggio di stato del server. Log: `journalctl -u cicciotv -f`.

### 7b. Il primo utente (PIN di accesso)

Il login usa un **PIN**, ma **non serve creare nulla da terminale**: al primo
accesso da browser/app, se non esiste ancora nessun utente, appare un form
"Primo avvio: crea il tuo accesso" (nome + PIN) che ti registra e ti fa entrare
subito. Questo **primo utente è l'amministratore**: è l'unico che può creare
altri utenti (dall'app, Impostazioni → Utenti). Ogni utente ha la **sua libreria**
separata (serie, film, statistiche, preferenze).

> In alternativa, se preferisci crearlo da riga di comando:
> `cd ~/cicciotv && .venv/bin/python -m app.create_user`

---

## 8. (Opzionale) Aggiornamento automatico IP DuckDNS

L'IP pubblico della VM può cambiare se fermi/riavvii l'istanza (a meno che tu non
abbia riservato un IP statico). Questo cron tiene DuckDNS aggiornato. Sostituisci
`IL_TUO_TOKEN`:

```bash
mkdir -p ~/duckdns
cat > ~/duckdns/update.sh <<'EOF'
#!/bin/bash
curl -s "https://www.duckdns.org/update?domains=cicciotv&token=IL_TUO_TOKEN&ip=" -o ~/duckdns/duck.log
EOF
chmod +x ~/duckdns/update.sh
(crontab -l 2>/dev/null; echo "*/5 * * * * ~/duckdns/update.sh >/dev/null 2>&1") | crontab -
~/duckdns/update.sh   # esegui subito una volta
```

---

## 9. Build del frontend per il browser

Il sito servito da Caddy usa il percorso **relativo** `/api`, così il browser
riusa da solo la password.

```bash
cd ~/cicciotv/frontend
npm install
# File d'ambiente per la build "browser" (percorso relativo, niente credenziali)
echo 'VITE_API_BASE_URL=/api' > .env.production.local
npm run build
```

Questo genera `frontend/dist`, che è il percorso indicato nel Caddyfile.

---

## 10. Configurare Caddy (HTTPS + reverse proxy)

Il login è dentro l'app (PIN), quindi Caddy serve solo per HTTPS e proxy: niente
password da configurare qui.

1. Copia il Caddyfile:

   ```bash
   sudo cp ~/cicciotv/deploy/Caddyfile /etc/caddy/Caddyfile
   sudo nano /etc/caddy/Caddyfile
   ```

   Controlla solo che il dominio sia il tuo e che il percorso `root *` punti a
   `/home/ubuntu/cicciotv/frontend/dist`. Salva con Ctrl+O, Invio, Ctrl+X.

2. Riavvia Caddy:

   ```bash
   sudo systemctl restart caddy
   sudo systemctl status caddy    # deve essere "active (running)"
   ```

   Al primo avvio Caddy ottiene il certificato HTTPS da Let's Encrypt (pochi
   secondi; serve la porta 80 raggiungibile, vedi passi 2 e 3).

---

## 11. Prova dal browser

Apri **`https://cicciotv.duckdns.org`** da qualsiasi dispositivo:

- al **primissimo** accesso appare il form "crea il tuo accesso" (nome + PIN),
- dalle volte successive appare il **tastierino PIN** → inserisci il PIN scelto,
- dopo il login vedi la tua libreria,
- lucchetto verde = HTTPS a posto.

Resti connesso per ~2 giorni; il pulsante **Esci** in alto a destra chiude la sessione.
Sul telefono puoi **"Aggiungi a schermata Home"** per avere un'icona come un'app,
usando solo il browser.

---

## 12. App Android (guscio Capacitor) verso il dominio

Ora l'app mostra la **stessa pagina di login** del browser: nessuna password
incorporata nell'APK, si digita il PIN all'avvio. Basta puntarla al dominio.
**Sul tuo PC Windows**, nella cartella `frontend`:

1. Metti in `frontend/.env` solo l'indirizzo del backend:

   ```
   VITE_API_BASE_URL=https://cicciotv.duckdns.org/api
   ```

2. Ricostruisci e sincronizza:

   ```powershell
   cd frontend
   npm run build
   npx cap sync android
   npx cap open android
   ```

   In Android Studio: **Build → Build APK(s)**, installa l'APK sul telefono.

Da ora l'app funziona **ovunque** (Wi-Fi, 4G), non più solo in rete locale, e
all'apertura chiede il PIN come il sito.

---

## Comandi utili

| Cosa | Comando (sulla VM) |
|------|--------------------|
| Log backend | `journalctl -u cicciotv -f` |
| Riavvia backend | `sudo systemctl restart cicciotv` |
| Log/stato Caddy | `sudo systemctl status caddy` / `journalctl -u caddy -f` |
| Aggiornare il codice | `cd ~/cicciotv && git pull` poi rebuild frontend + `sudo systemctl restart cicciotv` |
| Backup libreria | `scp ubuntu@cicciotv.duckdns.org:/home/ubuntu/cicciotv/cicciotv.db ./backup.db` |
