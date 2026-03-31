"""OS definitions — category and version hierarchy, matching QuickEMU's supported OS list."""
from typing import NamedTuple


class OSVersion(NamedTuple):
    id: str       # e.g. "ubuntu-24.04"
    name: str     # e.g. "Ubuntu 24.04 LTS"


class OSCategory(NamedTuple):
    id: str          # e.g. "linux"
    name: str        # e.g. "Linux"
    versions: list[OSVersion]


# ── OS Catalog ────────────────────────────────────────────────────────────────

OS_CATALOG: dict[str, OSCategory] = {

    "linux": OSCategory(
        id="linux",
        name="Linux",
        versions=[
            # Ubuntu
            OSVersion("ubuntu-24.04", "Ubuntu 24.04 LTS"),
            OSVersion("ubuntu-22.04", "Ubuntu 22.04 LTS"),
            OSVersion("ubuntu-20.04", "Ubuntu 20.04 LTS"),
            # Fedora
            OSVersion("fedora-41", "Fedora 41"),
            OSVersion("fedora-40", "Fedora 40"),
            # Debian
            OSVersion("debian-12", "Debian 12"),
            OSVersion("debian-11", "Debian 11"),
            # Arch
            OSVersion("archlinux", "Arch Linux"),
            # Linux Mint
            OSVersion("linuxmint-21", "Linux Mint 21"),
            # openSUSE
            OSVersion("opensuse-15", "openSUSE Leap 15"),
            # CentOS / Alma / Rocky
            OSVersion("almalinux-9", "AlmaLinux 9"),
            OSVersion("rockylinux-9", "Rocky Linux 9"),
        ],
    ),

    "windows": OSCategory(
        id="windows",
        name="Windows",
        versions=[
            OSVersion("windows-11", "Windows 11"),
            OSVersion("windows-10", "Windows 10"),
            OSVersion("windows-server-2022", "Windows Server 2022"),
            OSVersion("windows-server-2019", "Windows Server 2019"),
        ],
    ),

    "macos": OSCategory(
        id="macos",
        name="macOS",
        versions=[
            OSVersion("tahoe",      "macOS Tahoe (16)"),
            OSVersion("sequoia",    "macOS Sequoia (15)"),
            OSVersion("sonoma",     "macOS Sonoma (14)"),
            OSVersion("ventura",    "macOS Ventura (13)"),
            OSVersion("monterey",   "macOS Monterey (12)"),
            OSVersion("big-sur",     "macOS Big Sur (11)"),
            OSVersion("catalina",    "macOS Catalina (10.15)"),
            OSVersion("mojave",      "macOS Mojave (10.14)"),
        ],
    ),

    "other": OSCategory(
        id="other",
        name="Other / Custom",
        versions=[
            OSVersion("generic",    "Generic ISO / CD-ROM"),
        ],
    ),
}


def get_category(category_id: str) -> OSCategory | None:
    return OS_CATALOG.get(category_id)


def get_version(category_id: str, version_id: str) -> OSVersion | None:
    cat = get_category(category_id)
    if not cat:
        return None
    for v in cat.versions:
        if v.id == version_id:
            return v
    return None


def all_categories() -> list[OSCategory]:
    return list(OS_CATALOG.values())


def all_versions(category_id: str) -> list[OSVersion]:
    cat = get_category(category_id)
    return cat.versions if cat else []
