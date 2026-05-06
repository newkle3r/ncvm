`ncvm` är ett Python-CLI för att serva en Nextcloud VM (Ubuntu), utan bash-orchestrering.

- Fokus: **uppgraderingar**, **status/doctor**, och **service-hantering**
- Målmiljö: Nextcloud installerad i `/var/www/nextcloud` (standard för Nextcloud VM)


## Installera (pipx)

```bash
# Från repo (utveckling)
pipx install .

# Alternativt: uppdatera efter ny pull
pipx install --force .

ncvm --help
```

## Snabbstart

```bash
# Visa status
ncvm status
ncvm status --json

# Kör en säkerhetscheck (doctor)
ncvm doctor

# Nextcloud-uppgradering
ncvm update nc --debug

# Hoppa över backup helt (snabbare, men mindre säkert)
ncvm update nc --skip-backup --debug

# PHP-uppgradering (default-version från config om --phpver saknas)
ncvm update php --phpver 8.3 --debug

# Uppgradera allt (först Nextcloud, sedan PHP)
ncvm update all --phpver 8.3 --debug
```

## Kommandon

```bash
# Nextcloud: ladda ner senaste release, verifiera (sha256+gpg), rsync till installation, occ upgrade
ncvm update nc
ncvm update nc --skip-backup --debug

# PHP-stack (PPA ondrej vid behov), FPM-pool, OPcache, moduler, Redis-server + Nextcloud Redis-config
ncvm update php --phpver 8.3

# Först Nextcloud, sedan PHP
ncvm update all --phpver 8.3

ncvm status --json
ncvm maintenance on
ncvm maintenance off
ncvm restart
ncvm php-fpm optimize
ncvm doctor
```

## Viktiga flaggor

- **`--debug`**: mer loggning (DEBUG) och körda kommandon
- **`--dry-run`** (på `update`): skriv vad som skulle göras utan att köra
- **`--skip-backup`** (på `update nc`/`all`): hoppa över rsync-backup av `config/` + `apps/`
- **`--phpver`** (på `update php`/`all`): välj PHP-version, t.ex. `8.3`

## Krav

- Ubuntu-server med Nextcloud under `/var/www/nextcloud` (standard VM)
- Root eller `sudo`
- `curl`, `gpg`, `rsync`, `tar` (för NC-uppgradering)

## Utveckling

```bash
python -m pip install -e .
python -m ncvm.cli --help
```
