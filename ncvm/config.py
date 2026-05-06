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

    nextcloud_dir: str = "/var/www/nextcloud"
    occ_path: str = "/var/www/nextcloud/occ"
    php_bin: str = "php"
    www_user: str = "www-data"

    apache_service: str = "apache2"
    php_fpm_service: str = "php*-fpm"


def get_settings() -> Settings:
    return Settings()

