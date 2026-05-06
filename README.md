`ncvm` är ett Python CLI som orkestrerar Nextcloud VM.


## Installera (pipx)

```bash
pipx install .
ncvm --help
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

## Krav

- Ubuntu-server med Nextcloud under `/var/www/nextcloud` (standard VM)
- Root eller `sudo`
- `curl`, `gpg`, `rsync`, `tar` (för NC-uppgradering)
