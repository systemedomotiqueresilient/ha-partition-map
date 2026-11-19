"""Affiche le modèle construit depuis un export `ha hardware info --raw-json`.

Usage : python3 tools/check_layout.py hw.json
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "partition_map"))
from layout import build_layout


def gb(n: int) -> str:
    return f"{n / 1e9:6.2f} GB"


disks = build_layout(json.loads(Path(sys.argv[1]).read_text()))
for d in disks:
    tags = [t for t, ok in (("démarrage", d.is_boot), ("data", d.is_data)) if ok]
    print(f"\n{d.device}  {d.model}  série={d.serial}  {gb(d.size)}  [{', '.join(tags)}]")
    for p in d.partitions:
        state = ""
        if p.active is not None:
            state = "actif" if p.active else "inactif"
        print(
            f"  {p.device:<10} {p.part_name:<17} {p.fs_type or '-':<9} "
            f"début {gb(p.start)}  taille {gb(p.size)}  {p.role:<12} {p.slot or ''} {state:<8} "
            f"{p.mount_points[0] if p.mounted else '(non monté)'}"
        )
    for g in d.gaps:
        print(f"  {'—':<10} {'non alloué':<17} {'':<9} début {gb(g.start)}  taille {gb(g.size)}")
    if d.orphans:
        print(f"  ⚠ espace mort : {gb(sum(p.size for p in d.orphans))}")
