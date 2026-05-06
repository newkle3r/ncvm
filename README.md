# ncvm

`ncvm` är ett Python CLI som orkestrerar Nextcloud VM-skripten (`lib.sh`, `n.sh`, `pp.sh`) utan att duplicera deras logik.

## Installera (pipx)

```bash
pipx install .
ncvm --help
```

## Exempel

```bash
ncvm update nc
ncvm update php
ncvm update all

# Använd kund-skripten (inbyggda i ncvm) + överstyr PHP-version
ncvm update php --flavor customer --phpver 8.3
ncvm update nc --flavor customer --debug --keep-tmp

# Använd VM-standard (kör /var/scripts/{n,pp}.sh och hämta från GitHub om saknas)
ncvm update all --flavor vm

ncvm status
ncvm maintenance on
ncvm maintenance off

ncvm restart
ncvm php-fpm optimize
ncvm doctor
```

## Krav i målmiljön

- Ubuntu/Nextcloud VM (körs normalt som root/sudo)
- `curl` installerat (för att hämta `*.sh` från GitHub när de saknas lokalt)
- `systemctl` (för restart/status)
