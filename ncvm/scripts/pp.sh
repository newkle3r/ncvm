#!/bin/bash
# T&M Hansson IT AB © - 2021, https://www.hanssonit.se/
# Fixed: Uses apt instead of PECL for igbinary + redis

true
. <(curl -sL https://raw.githubusercontent.com/nextcloud/vm/master/lib.sh)

root_check
is_process_running apt
is_process_running dpkg

install_if_not software-properties-common ca-certificates
update-ca-certificates

if version 16.04.10 "$DISTRO" 24.04.10; then
    check_command yes | add-apt-repository ppa:ondrej/php
fi

apt-mark unhold php*
apt-get update -q

# Standard: 8.3 (kan överstyras via env PHPVER)
PHPVER="${PHPVER:-8.3}"

export PHP_FPM_DIR=/etc/php/$PHPVER/fpm
export PHP_INI=$PHP_FPM_DIR/php.ini
export PHP_POOL_DIR=$PHP_FPM_DIR/pool.d
export PHP_MODS_DIR=/etc/php/"$PHPVER"/mods-available

print_text_in_color "$ICyan" "Entering maintenance mode..."
nextcloud_occ_no_check maintenance:mode --on

systemctl stop apache2.service

# Remove old Redis config from Nextcloud
print_text_in_color "$ICyan" "Removing old Redis configuration..."
nextcloud_occ config:system:delete memcache.local
nextcloud_occ config:system:delete memcache.distributed
nextcloud_occ config:system:delete filelocking.enabled
nextcloud_occ config:system:delete memcache.locking
nextcloud_occ config:system:delete redis

# Uninstall old PHP
print_text_in_color "$ICyan" "Removing old PHP..."
apt-get purge php* -y
apt-get autoremove -y
rm -Rf /etc/php

# Install new PHP + required modules via apt
print_text_in_color "$ICyan" "Installing PHP $PHPVER and modules..."
apt-get update -q
check_command apt-get install -y \
    php"$PHPVER"-fpm \
    php"$PHPVER"-intl \
    php"$PHPVER"-ldap \
    php"$PHPVER"-imap \
    php"$PHPVER"-gd \
    php"$PHPVER"-pgsql \
    php"$PHPVER"-curl \
    php"$PHPVER"-xml \
    php"$PHPVER"-zip \
    php"$PHPVER"-mbstring \
    php"$PHPVER"-soap \
    php"$PHPVER"-gmp \
    php"$PHPVER"-bz2 \
    php"$PHPVER"-bcmath \
    php"$PHPVER"-igbinary \
    php"$PHPVER"-redis \
    php"$PHPVER"-smbclient \
    php-pear \
    apache2

# Enable Apache modules
a2enmod rewrite headers proxy proxy_fcgi setenvif env mime dir authz_core alias mpm_event ssl http2
a2dismod mpm_prefork
a2enconf php"$PHPVER"-fpm

# Create PHP-FPM pool
cat << POOL_CONF > "$PHP_POOL_DIR"/nextcloud.conf
[Nextcloud]
user = www-data
group = www-data
listen = /run/php/php"$PHPVER"-fpm.nextcloud.sock
listen.owner = www-data
listen.group = www-data
pm = dynamic
pm.max_children = 8
pm.start_servers = 3
pm.min_spare_servers = 2
pm.max_spare_servers = 3
env[HOSTNAME] = $(hostname -f)
env[PATH] = /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin
env[TMP] = /tmp
env[TMPDIR] = /tmp
env[TEMP] = /tmp
security.limit_extensions = .php
php_admin_value[cgi.fix_pathinfo] = 1
POOL_CONF

mv "$PHP_POOL_DIR"/www.conf "$PHP_POOL_DIR"/www.conf.backup 2>/dev/null || true

# Enable igbinary + redis (from apt)
phpenmod -v ALL igbinary
phpenmod -v ALL redis

# OPcache + performance settings
phpenmod opcache
cat << OPCACHE >> "$PHP_INI"
; OPcache for Nextcloud
opcache.enable=1
opcache.enable_cli=1
opcache.interned_strings_buffer=16
opcache.max_accelerated_files=10000
opcache.memory_consumption=256
opcache.save_comments=1
opcache.revalidate_freq=1
OPCACHE

# Restart services
restart_webserver

# Install/Configure Redis server
run_script ADDONS redis-server-ubuntu

print_text_in_color "$IGreen" "PHP $PHPVER + igbinary + redis (apt version) installed successfully!"

# Exit maintenance mode
nextcloud_occ maintenance:mode --off

print_text_in_color "$IGreen" "Script finished! You can now run your normal upgrade if needed."
