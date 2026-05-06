#!/bin/bash
# T&M Hansson IT AB © - 2021, https://www.hanssonit.se/

true
SCRIPT_NAME="Update Server + Nextcloud"
source <(curl -sL https://raw.githubusercontent.com/nextcloud/vm/master/lib.sh)

# 1 = ON, 0 = OFF (kan överstyras via env DEBUG)
DEBUG="${DEBUG:-0}"
debug_mode

root_check
nc_update

mkdir -p "$SCRIPTS"

echo "$((${CURRENTVERSION%%.*}-2))" > /tmp/nextmajor.version

# Delete, download, run
run_script GITHUB_REPO nextcloud_update

# Delete the actual script
if [ -f /root/major.sh ]
then
    rm /root/major.sh
fi

exit

