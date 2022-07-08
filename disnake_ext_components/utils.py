import inspect
import re
import typing as t

import disnake
from disnake.ext import commands

__all__ = [
    "id_spec_from_signature",
    "id_spec_from_regex",
    "extract_listener_params",
    "ensure_compiled",
]


def id_spec_from_signature(name: str, sep: str, signature: inspect.Signature) -> str:
    """Analyze a function signature to create a format string for creating new custom_ids.

    Parameters
    ----------
    name: :class:`str`
        The name of the listener function to which the signature belongs.
    signature: :class:`inspect.Signature`
        The function signature of the listener function.
    """
    _, custom_id_params = extract_listener_params(signature)
    if not custom_id_params:
        return name

    return name + sep + sep.join(f"{{{param.name}}}" for param in custom_id_params)


def id_spec_from_regex(regex: t.Pattern[str]) -> str:
    """Analyze a regex pattern for a component custom_id to create a format string for creating
    new custom_ids.

    Parameters
    ----------
    regex: :class:`re.Pattern`
        The regex pattern that is to be deconstructed.
    """
    return re.sub(r"\(\?P<(.+?)>.*?\)", lambda m: f"{{{m[1]}}}", regex.pattern)


def extract_listener_params(
    signature: inspect.Signature,
) -> t.Tuple[t.Tuple[inspect.Parameter, ...], t.Tuple[inspect.Parameter, ...]]:
    """Extract the parameters of the listener function that are used to analyze incoming
    custom_ids. This function strips `self` if the listener is in a Cog, and the
    :class:`disnake.MessageInteraction` parameter.
    It then splits any special type annotations used to denote the :class:`disnake.ui.Select`
    value parameter: :class:`.SelectValue`, or the :class:`disnake.ui.Modal` text value parameters:
    :class:`.ModalValue`.

    Parameters
    ----------
    signature: :class:`inspect.Signature`
        The (full) function signature of the listener function.

    Raises
    ------
    TypeError:
        The function signature did not contain any parameters annotated as
        :class:`disnake.MessageInteraction`. This is required to properly split the signature.

    Returns
    -------
    Tuple[Tuple[:class:`inspect.Parameter`, ...], Tuple[:class:`inspect.Parameter`, ...]]:
        A tuple containing two tuples:
        - The first tuple contains special parameters that denote select or modal input values,
        - The second tuple contains all remaining parameters, which are parsed from the `custom_id`.
    """
    param_iter = iter(signature.parameters.values())
    for param in param_iter:
        if commands.params.issubclass_(param.annotation, disnake.Interaction):
            break
    else:
        raise TypeError(
            "No interaction parameter (annotated as any kind of 'disnake.Interaction') was found.\n"
            "Please make sure the interaction parameter is properly annotated in the listener."
        )

    special_params: t.List[inspect.Parameter] = []
    for param in param_iter:

        # Continue until keyword-only...
        if param.kind is inspect.Parameter.KEYWORD_ONLY:
            break

        special_params.append(param)

    else:
        # No keyword-only params, thus only special params if any params at all.
        return tuple(special_params), ()

    return tuple(special_params), (param, *param_iter)


def ensure_compiled(
    pattern: t.Union[str, t.Pattern[str]],
    flags: re.RegexFlag = re.UNICODE,  # seems to be the default of re.compile
) -> t.Pattern[str]:
    """Ensure a regex pattern is compiled.

    Parameters
    ----------
    pattern: Union[:class:`str`, :class:`re.Pattern`]
        The pattern that should be force-compiled into a :class:`re.Pattern`. If this already is
        compiled, it is returned as-is.
    flags: :class:`re.RegexFlag`
        Any flags to apply to compilation. By default this has the same behaviour as `re.compile`.
    """
    return re.compile(pattern, flags) if isinstance(pattern, str) else pattern