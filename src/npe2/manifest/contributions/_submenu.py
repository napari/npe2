from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from npe2.manifest import _validators

from ._icon import Icon


class SubmenuContribution(BaseModel):
    """Contributes a submenu that can contain menu items or other submenus.

    Submenus allow you to organize menu items into hierarchical structures.
    Each submenu defines an id, label, and optional icon that can be
    referenced by menu items to create nested menu structures.
    """

    id: str = Field(description="Identifier of the menu to display as a submenu.")
    label: str = Field(
        description="The label of the menu item which leads to this submenu."
    )
    icon: Annotated[str | Icon | None, AfterValidator(_validators.coerce_icon)] = Field(
        None,
        description="Icon used to represent this submenu in the UI, on"
        " buttons or in menus. Can be a single string or two different options"
        " for light and dark themes. These values may be:"
        "<ul><li> a secure (https) URL </li>"
        "<li>a string in the format `{package}:{resource}`, where `package` and "
        "`resource` are arguments to `importlib.resources.path(package, resource)` "
        "(e.g. `my_plugin.some_module:my_logo.png`). This resource must be "
        "shipped with the sdist)"
        "<li> a [superqt](https://github.com/napari/superqt) fonticon key, such as "
        "`'fa6s.arrow_down'` (though note that plugins are expected to depend on "
        "any fonticon libraries they use, e.g "
        "[fonticon-fontawesome6](https://github.com/tlambert03/fonticon-fontawesome6))</li></ul>",
    )
