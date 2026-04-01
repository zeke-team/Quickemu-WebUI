"""
OS catalog — hierarchical OS category and version definitions.

Mirrors the OS support provided by QuickEMU. Used to populate the cascading
dropdown (Category → Version) in the VM creation form.

Structure:
    OS_CATALOG (dict)
    └── OSCategory (per category)
        ├── id, name
        └── versions: list of OSVersion (per release)

Adding a new OS or version is done by editing OS_CATALOG in this file.
No other code changes are needed.
"""

from typing import NamedTuple


class OSVersion(NamedTuple):
    """
    Represents a specific OS release.

    Attributes:
        id:    Unique identifier used in VM configs and API (e.g. "ubuntu-24.04").
               Stored as os_version in the VM JSON.
        name:  Human-readable display name (e.g. "Ubuntu 24.04 LTS").
    """
    id: str
    name: str


class OSCategory(NamedTuple):
    """
    Represents an OS family/category.

    Attributes:
        id:       Unique identifier (e.g. "linux", "windows", "macos").
                  Stored as os_category in the VM JSON.
        name:     Human-readable display name (e.g. "Linux", "macOS").
        versions: List of OSVersion entries available under this category.
    """
    id: str
    name: str
    versions: list[OSVersion]


# ── OS Catalog ────────────────────────────────────────────────────────────────
# QuickEMU-compatible OS list. Version IDs match quickemu's naming convention
# so that configs generated here can potentially be shared with quickemu.

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
            OSVersion("fedora-41",    "Fedora 41"),
            OSVersion("fedora-40",    "Fedora 40"),
            # Debian
            OSVersion("debian-12",    "Debian 12"),
            OSVersion("debian-11",    "Debian 11"),
            # Arch
            OSVersion("archlinux",    "Arch Linux"),
            # Linux Mint
            OSVersion("linuxmint-21", "Linux Mint 21"),
            # openSUSE
            OSVersion("opensuse-15",  "openSUSE Leap 15"),
            # AlmaLinux / Rocky
            OSVersion("almalinux-9",  "AlmaLinux 9"),
            OSVersion("rockylinux-9",  "Rocky Linux 9"),
        ],
    ),

    "windows": OSCategory(
        id="windows",
        name="Windows",
        versions=[
            OSVersion("windows-11",           "Windows 11"),
            OSVersion("windows-10",           "Windows 10"),
            OSVersion("windows-server-2022",  "Windows Server 2022"),
            OSVersion("windows-server-2019",  "Windows Server 2019"),
        ],
    ),

    "macos": OSCategory(
        id="macos",
        name="macOS",
        versions=[
            OSVersion("tahoe",     "macOS Tahoe (16)"),
            OSVersion("sequoia",   "macOS Sequoia (15)"),
            OSVersion("sonoma",    "macOS Sonoma (14)"),
            OSVersion("ventura",   "macOS Ventura (13)"),
            OSVersion("monterey",  "macOS Monterey (12)"),
            OSVersion("big-sur",   "macOS Big Sur (11)"),
            OSVersion("catalina",  "macOS Catalina (10.15)"),
            OSVersion("mojave",    "macOS Mojave (10.14)"),
        ],
    ),

    "other": OSCategory(
        id="other",
        name="Other / Custom",
        versions=[
            # Generic ISO boots via SeaBIOS without special guest tweaks.
            # Use this for BSDs,_minimal ISOs, live CDs, etc.
            OSVersion("generic", "Generic ISO / CD-ROM"),
        ],
    ),
}


def get_category(category_id: str) -> OSCategory | None:
    """Look up an OS category by its ID."""
    return OS_CATALOG.get(category_id)


def get_version(category_id: str, version_id: str) -> OSVersion | None:
    """Look up a specific OS version within a category."""
    cat = get_category(category_id)
    if not cat:
        return None
    for v in cat.versions:
        if v.id == version_id:
            return v
    return None


def all_categories() -> list[OSCategory]:
    """Return all OS categories in definition order."""
    return list(OS_CATALOG.values())


def all_versions(category_id: str) -> list[OSVersion]:
    """Return all versions for a given category ID."""
    cat = get_category(category_id)
    return cat.versions if cat else []


# ── QuickEMU/QuickGet integration ──────────────────────────────────────────────
# Mapping from webvm os_version ID → (quickemu_os, quickemu_release).
# quickemu OS names must match the function names in quickget (e.g. ubuntu,
# fedora, debian, archlinux, linuxmint, opensuse, almalinux, rockylinux, windows,
# macos).  Release is the version string quickget expects after the OS arg.

_QUICKEMU_OS_MAP: dict[str, tuple[str, str]] = {
    # Linux
    "ubuntu-24.04":  ("ubuntu",     "24.04"),
    "ubuntu-22.04":  ("ubuntu",     "22.04"),
    "ubuntu-20.04":  ("ubuntu",     "20.04"),
    "fedora-41":     ("fedora",     "41"),
    "fedora-40":     ("fedora",     "40"),
    "debian-12":     ("debian",     "12"),
    "debian-11":     ("debian",     "11"),
    "archlinux":     ("archlinux",  ""),
    "linuxmint-21":  ("linuxmint",  "21"),
    "opensuse-15":   ("opensuse",   "15"),
    "almalinux-9":   ("almalinux", "9"),
    "rockylinux-9":  ("rockylinux","9"),
    # Windows
    "windows-11":            ("windows", "11"),
    "windows-10":            ("windows", "10"),
    "windows-server-2022":   ("windows", "server-2022"),
    "windows-server-2019":   ("windows", "server-2019"),
    # macOS
    "tahoe":         ("macos", "tahoe"),
    "sequoia":       ("macos", "sequoia"),
    "sonoma":        ("macos", "sonoma"),
    "ventura":       ("macos", "ventura"),
    "monterey":      ("macos", "monterey"),
    "big-sur":       ("macos", "big-sur"),
    "catalina":      ("macos", "catalina"),
    "mojave":        ("macos", "mojave"),
    # Other
    "generic":       ("",       ""),   # no auto-download
}


def quickemu_os_release(os_version: str) -> tuple[str, str] | None:
    """
    Map a webvm os_version ID to (quickemu_os, quickemu_release) for use with
    quickget --download <os> <release>.

    Returns None if the OS has no quickemu equivalent or cannot be downloaded.
    """
    return _QUICKEMU_OS_MAP.get(os_version)
