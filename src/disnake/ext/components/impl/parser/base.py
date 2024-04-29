"""Implementation of parser base classes upon which actual parsers are built."""

from __future__ import annotations

import types
import typing

from disnake.ext.components.api import parser as parser_api

if typing.TYPE_CHECKING:
    import disnake
    import typing_extensions

__all__: typing.Sequence[str] = (
    "register_parser",
    "get_parser",
    "Parser",
)

_PARSERS: typing.Dict[typing.Type[typing.Any], typing.Type[Parser[typing.Any]]] = {}
_REV_PARSERS: typing.Dict[
    typing.Type[Parser[typing.Any]], typing.Tuple[typing.Type[typing.Any]]
] = {}


_T = typing.TypeVar("_T")

MaybeCoroutine = typing.Union[typing.Coroutine[None, None, _T], _T]
TypeSequence = typing.Sequence[typing.Type[typing.Any]]


def _issubclass(
    cls: type, class_or_tuple: typing.Union[type, typing.Tuple[type, ...]]
) -> bool:
    try:
        return issubclass(cls, class_or_tuple)

    except TypeError:
        if isinstance(class_or_tuple, tuple):
            return any(cls is cls_ for cls_ in class_or_tuple)

        return cls is class_or_tuple


def register_parser(
    parser: typing.Type[Parser[_T]],
    *types: typing.Type[_T],
    force: bool = True,
) -> None:
    """Register a parser class as the default parser for the provided type.

    The default parser will automatically be used for any field annotated
    with that type. For example, the default parser for integers is
    :class:`components.IntParser`, an instance of which will automatically be
    assigned to any custom id fields annotated with `int`.

    Parameters
    ----------
    parser:
        The parser to register.
    types:
        The types for which to register the provided parser as the default.
    force:
        Whether or not to overwrite existing defaults. Defaults to ``True``.
    """
    # This allows e.g. is_default_for=(Tuple[Any, ...],) so pyright doesn't complain.
    # The stored type will then still be tuple, as intended.
    types = tuple(typing.get_origin(type_) or type_ for type_ in types)

    if force:
        _REV_PARSERS[parser] = types
        for type in types:
            _PARSERS[type] = parser

    else:
        _REV_PARSERS.setdefault(parser, types)
        for type in types:
            _PARSERS.setdefault(type, parser)


def _get_parser_type(type_: typing.Type[_T]) -> typing.Type[Parser[_T]]:
    # Fast lookup...
    if type_ in _PARSERS:
        return _PARSERS[type_]

    # TODO: Make parsers accept a type and provide it to the parser here,
    #       in the same way collection parsers support a collection type.

    # Slow lookup for subclasses of existing types...
    for parser, parser_types in _REV_PARSERS.items():
        if _issubclass(type_, parser_types):
            return parser

    msg = f"No parser available for type {type_.__name__!r}."
    raise TypeError(msg)


# TODO: Maybe cache this?
def get_parser(type_: typing.Type[_T]) -> Parser[_T]:
    """Get the default parser for the provided type.

    Note that type annotations such as ``Union[int, str]`` are also valid.

    Parameters
    ----------
    type_:
        The type for which to return the default parser.

    Returns
    -------
    :class:`Parser`:
        The default parser for the provided type.

    Raises
    ------
    TypeError:
        Could not create a parser for the provided type.
    """
    # TODO: Somehow allow more flexibility here. It would at the very least
    #       be neat to be able to pick between strictly sync/async parsers
    #       (mainly for the purpose of not making api requests); but perhaps
    #       allowing the user to pass a filter function could be cool?
    origin = typing.get_origin(type_)

    if not origin:
        return _get_parser_type(type_).default()

    parser_type = _get_parser_type(origin)
    type_args = typing.get_args(type_)

    if origin is typing.Union:
        inner_parsers = [
            get_parser(arg)  # Explicitly allow None to stay
            for arg in type_args
        ]  # fmt: skip
        return parser_type(*inner_parsers)  # see UnionParser

    if issubclass(origin, typing.Tuple):
        inner_parsers = [get_parser(arg) for arg in type_args]
        return parser_type(*inner_parsers)  # see TupleParser

    if issubclass(origin, typing.Collection):
        inner_type = next(iter(type_args), str)  # Get first element, default to str
        inner_parser = get_parser(inner_type)
        return parser_type(inner_parser, collection_type=origin)  # see CollectionParser

    msg = f"Coult not create a parser for type {type_.__name__!r}."
    raise TypeError(msg)


class Parser(parser_api.Parser[_T], typing.Protocol[_T]):
    """Class that handles parsing of one custom id field to and from a desired type.

    A parser contains two main methods, :meth:`loads` and :meth:`dumps`.
    ``loads``, like :func:`json.loads` serves to turn a string value into
    a different type. Similarly, ``dumps`` serves to convert that type
    back into a string.

    Simpler parsers can also be generated from ``loads`` and ``dumps`` functions
    using :meth:`from_funcs`, so as to not have to define an entire class.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

    def __init_subclass__(
        cls,
        *,
        is_default_for: typing.Optional[TypeSequence] = None,
        **kwargs: object,
    ) -> None:
        # Allows defining a parser with `is_default_for=[type1, ...]` to
        # auto-register the parser for the provided types to reduce
        # boilerplate.
        super().__init_subclass__(**kwargs)
        if is_default_for:
            register_parser(cls, *is_default_for)

    @classmethod
    def default(cls) -> typing_extensions.Self:
        """Return the default implementation of this parser type.

        By default, this will just create the parser class with no arguments,
        but this can be overwritten on child classes for customised behaviour.

        Returns
        -------
        Parser:
            The default parser instance for this parser type.
        """
        return cls()

    @classmethod
    def default_types(cls) -> typing.Tuple[typing.Type[typing.Any]]:
        """Return the types for which this parser type is the default implementation.

        Returns
        -------
        Sequence[type]:
            The types for which this parser type is the default implementation.
        """
        return _REV_PARSERS[cls]

    @classmethod
    def from_funcs(
        cls,
        loads: typing.Callable[[disnake.Interaction, str], MaybeCoroutine[_T]],
        dumps: typing.Callable[[_T], MaybeCoroutine[str]],
        *,
        is_default_for: typing.Optional[TypeSequence] = None,
    ) -> typing.Type[typing_extensions.Self]:
        """Generate a parser class from ``loads`` and ``dumps`` functions.

        Note that these ``loads`` and ``dumps`` functions must **not** have
        a ``self`` argument. They are treated as static methods. If a ``self``
        argument is required, consider making a parser class through
        inheritance instead.

        Parameters
        ----------
        loads:
            A function that serves to turn a string value into a different type,
            similar to :func:`json.loads`.
        dumps:
            A function that serves to turn a value of a given type back into a
            string, similar to :func:`json.dumps`.
        is_default_for:
            The types for which to register the newly created parser class as
            the default parser. By default, the parser is not registered as the
            default for any types.

        Returns
        -------
        typing.Type[:class:`Parser`]:
            The newly created parser class.
        """
        new_cls = typing.cast(
            "typing.Type[typing_extensions.Self]",
            types.new_class(
                f"{type.__name__}Parser",
                (cls,),
                {"is_default_for": is_default_for},
            ),
        )

        # XXX: Not really type-safe whatsoever but it'll suffice.
        new_cls.loads = staticmethod(loads)  # pyright: ignore
        new_cls.dumps = staticmethod(dumps)  # pyright: ignore

        return new_cls

    def loads(  # noqa: D102
        self, __interaction: disnake.Interaction, __argument: str
    ) -> MaybeCoroutine[_T]:
        # <<Docstring inherited from parser_api.Parser>>
        ...

    def dumps(self, __argument: _T) -> MaybeCoroutine[str]:  # noqa: D102
        # <<Docstring inherited from parser_api.Parser>>
        ...
