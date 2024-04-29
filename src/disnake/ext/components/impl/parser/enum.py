"""Parser implementations for standard library and disnake enums and flags."""

import enum
import typing

import disnake
from disnake.ext.components.impl.parser import base as parser_base
from disnake.ext.components.internal import aio

__all__: typing.Sequence[str] = ("EnumParser", "FlagParser")

_EnumT = typing.TypeVar("_EnumT", bound=typing.Union[enum.Enum, disnake.Enum])


def _get_enum_type(
    enum_class: typing.Type[typing.Union[enum.Enum, disnake.flags.BaseFlags]]
) -> type:
    maybe_type = getattr(enum_class, "_member_type_", object)
    if maybe_type is not object:
        return maybe_type

    # Get first member's type
    member_iter = iter(enum_class)
    maybe_type = type(next(member_iter).value)

    # If all members match this type, return it.
    if all(type(member.value) == maybe_type for member in member_iter):
        return maybe_type

    # No concrete type, throw hands.
    msg = "Cannot parse enums with more than one value type."
    raise TypeError(msg)


class EnumParser(
    parser_base.Parser[_EnumT],
    is_default_for=(enum.Enum, disnake.Enum, enum.Flag, disnake.flags.BaseFlags),
):
    """Parser type for enums and flags.

    Enums and flags are stored by value instead of by name. This makes parsing
    a bit slower, but values are generally shorter than names.

    This parser type works for standard library and disnake enums and flags.
    Note that this only works for enums and flags where all values are of the
    same type.

    Parameters
    ----------
    enum_class:
        The enum or flag class to use for parsing.
    """

    enum_class: typing.Type[_EnumT]
    value_parser: parser_base.Parser[typing.Any]

    def __init__(self, enum_class: typing.Type[_EnumT]) -> None:
        self.enum_class = enum_class
        self.value_parser = parser_base.get_parser(_get_enum_type(enum_class))

    async def loads(  # noqa: D102
        self, interaction: disnake.Interaction, argument: str
    ) -> _EnumT:
        # <<docstring inherited from parser_api.Parser>>

        parsed = await aio.eval_maybe_coro(
            self.value_parser.loads(interaction, argument)
        )
        return self.enum_class(parsed)

    def dumps(self, argument: _EnumT) -> parser_base.MaybeCoroutine[str]:  # noqa: D102
        # <<docstring inherited from parser_api.Parser>>

        return self.value_parser.dumps(argument.value)


FlagParser = EnumParser
