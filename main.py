from traffic_sim.simulation import Simulation
from traffic_sim.visualize import make_animation


def build_network():
    sim = Simulation()

    # Junctions (edit only this section for the final topology).
    sim.add_junction("A", 0, 0)
    sim.add_junction("B", 3, 1)
    sim.add_junction("C", 3, -1)
    sim.add_junction("D", 6, 1)
    sim.add_junction("E", 6, -1)
    sim.add_junction("F", 9, 0)

    # Directional roads. Use slower speeds so the motion is easy to follow.
    sim.add_road("R1", "A", "B", capacity=2, speed=0.35)
    sim.add_road("R2", "A", "C", capacity=2, speed=0.35)
    sim.add_road("R3", "B", "D", capacity=2, speed=0.30)
    sim.add_road("R4", "C", "E", capacity=2, speed=0.30)
    sim.add_road("R5", "B", "E", capacity=2, speed=0.30)
    sim.add_road("R6", "C", "D", capacity=2, speed=0.30)
    sim.add_road("R7", "D", "F", capacity=2, speed=0.40)
    sim.add_road("R8", "E", "F", capacity=2, speed=0.40)

    # Sources and sinks. Lower rates so the animation is readable.
    sim.add_sink("F")
    sim.add_source("A", "F", rate=0.3, mode="constant", color="tab:red")
    sim.add_source("A", "F", rate=0.2, mode="poisson", color="tab:green", start_time=4)

    return sim


def main():
    sim = build_network()
    sim.run(steps=80)

    print("Simulation summary")
    for k, v in sim.summary().items():
        print(f"{k}: {v}")

    sim.save_stats_csv("stats.csv")
    sim.save_stats_json("stats.json")

    outfile = make_animation(sim, outfile="traffic.gif", fps=2, display_interval=500, frame_step=1)
    print(f"Saved animation to {outfile}")
    print("Saved stats to stats.csv and stats.json")


if __name__ == "__main__":
    main()
