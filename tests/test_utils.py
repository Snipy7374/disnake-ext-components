import disnake
import pytest
from disnake.ext import commands, components


async def test_incorrect_litener():

    with pytest.raises(TypeError):

        class A(commands.Cog):
            @components.component_listener()
            async def incorrect_listener(self, inter, a):
                pass


async def test_id_builder_pass(inter):
    """Test ComponentListener.build_custom_id"""

    class A(commands.Cog):
        @components.component_listener()
        async def listener(
            self,
            inter: disnake.MessageInteraction,
            a: int,
            b: str,
            c: bool,
            d: float,
        ):
            return a, b, c, d

    actual = A().listener

    abcd = (1, "b", True, 1.12)
    custom_id = actual.build_custom_id(*abcd)
    assert custom_id == "listener:1:b:True:1.12"

    inter.component.custom_id = custom_id
    assert await actual(inter) == abcd


def test_id_builder_overlap():
    """Test the failure procedure for passing overlapping args to ComponentListener.build_custom_id"""

    class A(commands.Cog):
        @components.component_listener()
        async def listener(
            self,
            inter: disnake.MessageInteraction,
            a: int,
            b: str,
        ):
            return a, b

    actual = A().listener

    assert actual.build_custom_id(1, "a") == "listener:1:a"

    with pytest.raises(TypeError):
        actual.build_custom_id(1, a="1")


def test_id_builder_regex():
    """Test the failure procedure for passing overlapping args to ComponentListener.build_custom_id"""

    class A(commands.Cog):
        @components.component_listener(regex=r"blah(?P<a>.+)/(?P<b>/+)")
        async def listener(
            self,
            inter: disnake.MessageInteraction,
            a: int,
            b: str,
        ):
            return a, b

    actual = A().listener

    assert actual.id_spec == "blah{a}/{b}"
    assert actual.build_custom_id(1, "a") == "blah1/a"
