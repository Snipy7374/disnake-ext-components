"""Parser implementations for disnake permissions types."""

from __future__ import annotations

import typing

import disnake
from disnake.ext.components.impl.parser import base

__all__: typing.Sequence[str] = ("PermissionsParser",)


class PermissionsParser(
    base.Parser[disnake.Permissions],
    is_default_for=(disnake.Permissions,),
):
    # <<docstring inherited from parser_api.Parser>>

    def dumps(self, argument: disnake.Permissions) -> str:
        # <<docstring inherited from parser_api.Parser>>

        return str(argument.value)

    def loads(self, _: disnake.Interaction, argument: str) -> disnake.Permissions:
        # <<docstring inherited from parser_api.Parser>>

        return disnake.Permissions(int(argument))
