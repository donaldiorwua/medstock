from typing import Annotated, cast

from fastapi import Depends, Request

from app.core.config import Settings
from app.core.db import Database


def get_db(request: Request) -> Database:
    return cast(Database, request.app.state.db)


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


DbDep = Annotated[Database, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
