from __future__ import annotations

from typing import Dict, Tuple
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import FancyArrowPatch


def make_animation(sim, outfile: str = "traffic.gif", fps: int = 2, display_interval: int = 500, frame_step: int = 1):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_aspect("equal")
    ax.set_title("Traffic simulator")
    ax.axis("off")

    # Prepare static network drawing.
    junction_pos = {jid: j.pos() for jid, j in sim.junctions.items()}
    for rid, road in sim.roads.items():
        x1, y1 = junction_pos[road.start]
        x2, y2 = junction_pos[road.end]
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                                arrowstyle='-|>',
                                mutation_scale=12,
                                linewidth=1.5,
                                alpha=0.6)
        ax.add_patch(arrow)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my, rid, fontsize=8, alpha=0.75)

    xs = [p[0] for p in junction_pos.values()]
    ys = [p[1] for p in junction_pos.values()]
    pad = 1.0
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)

    # Junction labels
    for jid, (x, y) in junction_pos.items():
        ax.scatter([x], [y], s=120, marker='s', zorder=3)
        ax.text(x + 0.05, y + 0.05, jid, fontsize=10, weight='bold')

    scat = ax.scatter([], [], s=80, zorder=4)

    def init():
        scat.set_offsets(np.empty((0, 2)))
        return (scat,)

    def update(frame_idx):
        snap = sim.snapshots[frame_idx]
        pts = []
        colors = []
        for vid, (x, y) in snap.vehicle_positions.items():
            pts.append((x, y))
            colors.append(snap.vehicle_colors.get(vid, "tab:blue"))
        if pts:
            scat.set_offsets(np.array(pts))
            scat.set_color(colors)
        else:
            scat.set_offsets(np.empty((0, 2)))
        ax.set_title(f"Traffic simulator | t={snap.time}")
        return (scat,)

    frames = range(0, len(sim.snapshots), max(1, int(frame_step)))
    anim = FuncAnimation(fig, update, frames=frames, init_func=init, interval=display_interval, blit=True)

    try:
        anim.save(outfile, writer=PillowWriter(fps=fps))
    except Exception:
        # Fall back to just saving a png if GIF writer is unavailable.
        fig.savefig(outfile.rsplit(".", 1)[0] + ".png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return outfile
