from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NCVM_",
        case_sensitive=False,
        extra="ignore",
    )

    scripts_dir: str = "/var/scripts"
    github_base: str = "https://raw.githubusercontent.com/nextcloud/vm/master"

    html_dir: str = "/var/www"
    nextcloud_dir: str = "/var/www/nextcloud"
    occ_path: str = "/var/www/nextcloud/occ"
    php_bin: str = "php"
    www_user: str = "www-data"

    apache_service: str = "apache2"
    php_fpm_service: str = "php*-fpm"

    # Nextcloud releases (lib.sh NCREPO)
    nc_download_base: str = "https://download.nextcloud.com/server/releases"
    nextcloud_gpg_fingerprint: str = "28806A878AE423A28372792ED75899B9A724937A"

    redis_conf: str = "/etc/redis/redis.conf"
    redis_sock: str = "/var/run/redis/redis-server.sock"
    vm_log_dir: str = "/var/log/nextcloud"
    backup_dir: str = "/mnt/NCBACKUP"

    default_phpver: str = "8.3"


def get_settings() -> Settings:
    return Settings()

