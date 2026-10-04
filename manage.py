#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

from decouple import Config, RepositoryEnv

ENV_FILE = Path(__file__).resolve().parent / 'settings' / '.env'
ENV_ID_KEY = 'BLOG_ENV_ID'
DEFAULT_ENV_ID = 'local'
SETTINGS_MODULE_TEMPLATE = 'settings.env.{}'


def main() -> None: 
    env_id = Config(RepositoryEnv(ENV_FILE))(ENV_ID_KEY, default=DEFAULT_ENV_ID)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', SETTINGS_MODULE_TEMPLATE.format(env_id))
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Ne gruzitsya django") from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
