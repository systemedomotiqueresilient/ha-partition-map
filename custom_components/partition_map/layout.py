"""Modèle disques → partitions construit à partir de la réponse /hardware/info.

Module pur (aucun import Home Assistant) pour pouvoir être testé hors HA.

Sources croisées :
- data["devices"] (udev, subsystem "block") : nom GPT, offset, taille, type FS,
  y compris les partitions sans système de fichiers (bootstate…).
- data["drives"] (UDisks2) : modèle, numéro de série, taille, points de montage.
Le lien entre les deux se fait par le numéro de série court
(drive["serial"] == udev ID_SERIAL_SHORT), puis par chemin /dev pour les partitions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SECTOR_SIZE = 512  # udev exprime toujours offset et taille en secteurs de 512 octets
MIN_GAP = 4 * 1024 * 1024  # 1 Mio d'alignement + GPT de secours : ignorés

ROLE_BOOT = "boot"
ROLE_KERNEL = "kernel"
ROLE_SYSTEM = "system"
ROLE_BOOTSTATE = "bootstate"
ROLE_OVERLAY = "overlay"
ROLE_DATA = "data"
ROLE_DATA_ORPHAN = "data_orphan"
ROLE_OTHER = "other"


@dataclass(slots=True)
class Partition:
    """Une partition GPT."""

    device: str
    number: int
    part_name: str
    fs_label: str
    fs_type: str | None
    start: int
    size: int
    mount_points: list[str] = field(default_factory=list)
    role: str = ROLE_OTHER
    slot: str | None = None  # "A" / "B" pour noyau et système HAOS
    active: bool | None = None  # emplacement A/B en service

    @property
    def mounted(self) -> bool:
        return bool(self.mount_points)

    @property
    def end(self) -> int:
        return self.start + self.size


@dataclass(slots=True)
class Gap:
    """Espace non alloué sur un disque."""

    start: int
    size: int


@dataclass(slots=True)
class Disk:
    """Un disque physique (ou virtuel) et son contenu."""

    device: str
    vendor: str
    model: str
    serial: str
    size: int
    is_boot: bool
    is_data: bool
    partitions: list[Partition] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)

    @property
    def allocated(self) -> int:
        return sum(p.size for p in self.partitions)

    @property
    def unallocated(self) -> int:
        return sum(g.size for g in self.gaps)

    @property
    def orphans(self) -> list[Partition]:
        return [p for p in self.partitions if p.role == ROLE_DATA_ORPHAN]


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _role(part_name: str, fs_label: str, mounted: bool) -> tuple[str, str | None]:
    """Déduit le rôle HAOS d'une partition depuis son nom GPT et son label."""
    names = {part_name, fs_label}
    if "hassos-boot" in names:
        return ROLE_BOOT, None
    if "hassos-bootstate" in names:
        return ROLE_BOOTSTATE, None
    if "hassos-overlay" in names:
        return ROLE_OVERLAY, None
    for prefix, role in (("hassos-kernel", ROLE_KERNEL), ("hassos-system", ROLE_SYSTEM)):
        if part_name.startswith(prefix):
            return role, "A" if part_name.endswith("0") else "B"
    if any(n.startswith("hassos-data") for n in names):
        # HAOS renomme l'ancienne partition "hassos-data-old" après un déplacement ;
        # toute partition data non montée est de l'espace mort.
        if mounted and fs_label != "hassos-data-old":
            return ROLE_DATA, None
        return ROLE_DATA_ORPHAN, None
    return ROLE_OTHER, None


def build_layout(hardware: dict[str, Any]) -> list[Disk]:
    """Construit la liste des disques à partir de la réponse /hardware/info."""
    data = hardware.get("data", hardware)
    block = [d for d in data.get("devices", []) if d.get("subsystem") == "block"]

    mounts: dict[str, list[str]] = {}
    drives_by_serial: dict[str, dict[str, Any]] = {}
    for drive in data.get("drives", []):
        drives_by_serial[drive.get("serial", "")] = drive
        for fs in drive.get("filesystems", []):
            mounts[fs["device"]] = list(fs.get("mount_points", []))

    disks: list[Disk] = []
    for dev in block:
        attrs = dev.get("attributes", {})
        if attrs.get("DEVTYPE") != "disk" or not attrs.get("ID_PART_TABLE_TYPE"):
            continue  # ignore zram, loop, partitions…
        serial = attrs.get("ID_SERIAL_SHORT", "")
        drive = drives_by_serial.get(serial, {})
        disk = Disk(
            device=dev["dev_path"],
            vendor=drive.get("vendor") or attrs.get("ID_VENDOR", ""),
            model=drive.get("model") or attrs.get("ID_MODEL", "").replace("_", " "),
            serial=serial,
            size=_int(drive.get("size")),
            is_boot=False,
            is_data=False,
        )
        children = set(dev.get("children", []))
        for part in block:
            pattrs = part.get("attributes", {})
            if part.get("sysfs") not in children or pattrs.get("DEVTYPE") != "partition":
                continue
            mount_points = mounts.get(part["dev_path"], [])
            part_name = pattrs.get("ID_PART_ENTRY_NAME", "")
            fs_label = pattrs.get("ID_FS_LABEL", "")
            role, slot = _role(part_name, fs_label, bool(mount_points))
            disk.partitions.append(
                Partition(
                    device=part["dev_path"],
                    number=_int(pattrs.get("ID_PART_ENTRY_NUMBER")),
                    part_name=part_name,
                    fs_label=fs_label,
                    fs_type=pattrs.get("ID_FS_TYPE"),
                    start=_int(pattrs.get("ID_PART_ENTRY_OFFSET")) * SECTOR_SIZE,
                    size=_int(pattrs.get("ID_PART_ENTRY_SIZE")) * SECTOR_SIZE,
                    mount_points=mount_points,
                    role=role,
                    slot=slot,
                )
            )
        disk.partitions.sort(key=lambda p: p.start)
        _mark_active_slot(disk)
        disk.is_boot = any(p.role == ROLE_BOOT for p in disk.partitions)
        disk.is_data = any(p.role == ROLE_DATA for p in disk.partitions)
        if not disk.size and disk.partitions:
            disk.size = disk.partitions[-1].end
        disk.gaps = _gaps(disk)
        disks.append(disk)

    # Disque de démarrage d'abord, puis disque data, puis le reste
    disks.sort(key=lambda d: (not d.is_boot, not d.is_data, d.device))
    return disks


def _mark_active_slot(disk: Disk) -> None:
    """L'emplacement système monté sur / est actif ; son noyau aussi."""
    active_slot = next(
        (p.slot for p in disk.partitions if p.role == ROLE_SYSTEM and "/" in p.mount_points),
        None,
    )
    if active_slot is None:
        return
    for p in disk.partitions:
        if p.slot is not None:
            p.active = p.slot == active_slot


def _gaps(disk: Disk) -> list[Gap]:
    gaps: list[Gap] = []
    cursor = 0
    for p in disk.partitions:
        if p.start - cursor >= MIN_GAP:
            gaps.append(Gap(cursor, p.start - cursor))
        cursor = max(cursor, p.end)
    if disk.size - cursor >= MIN_GAP:
        gaps.append(Gap(cursor, disk.size - cursor))
    return gaps


def as_dict(disks: list[Disk]) -> list[dict[str, Any]]:
    """Sérialisation pour le panneau frontend et les diagnostics."""
    out = []
    for d in disks:
        item = asdict(d)
        item["allocated"] = d.allocated
        item["unallocated"] = d.unallocated
        out.append(item)
    return out
