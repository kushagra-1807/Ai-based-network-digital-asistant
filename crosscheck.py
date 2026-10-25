import sys

from netassist import evaluation
from netassist.config import Config
from netassist.detector import Detector
from netassist.simulator import NetworkSimulator


def fresh_seeds():
    print("Detection rate on seeds 100 to 109")
    for name in ("rules only", "rules + statistics"):
        conf = evaluation.detector_configs()[name]
        rates = {}
        for fault in evaluation.expected_kinds():
            hits = sum(1 for seed in range(100, 110) if evaluation.run_trial(fault, seed, conf)["detected"])
            rates[fault] = hits / 10.0
        missed = {k: int(v * 100) for k, v in rates.items() if v < 1}
        print("  %-20s %.0f%%, below 100%%: %s" % (name, 100 * sum(rates.values()) / len(rates), missed or "none"))


def quiet_network():
    print("False alarms on normal traffic, 20 runs of 1500 readings")
    for use_stats in (False, True):
        alarms = 0
        readings = 0
        for seed in range(200, 220):
            sim = NetworkSimulator(seed=seed)
            detector = Detector(Config(), use_stats=use_stats)
            before = False
            for i in range(1500):
                now = bool(detector.evaluate(sim.collect(ts=i * 2.0)))
                if i >= 80:
                    readings += 1
                    alarms += now and not before
                before = now
        print("  statistics=%-5s %d alarms in %d readings (%.1f hours)" % (use_stats, alarms, readings, readings * 2 / 3600.0))


def wanted_download():
    print("One device starts a large download that the user wants")
    sim = NetworkSimulator(seed=5)
    detector = Detector(Config(), use_stats=True)
    for i in range(100):
        detector.evaluate(sim.collect(ts=i * 2.0))
    raised = {}
    for i in range(100, 130):
        sample = sim.collect(ts=i * 2.0)
        laptop = [d for d in sample.devices if d.name == "Laptop-Dev"][0]
        laptop.down_mbps = 35.0
        sample.down_mbps = sum(d.down_mbps for d in sample.devices)
        for alert in detector.evaluate(sample):
            raised[alert.kind] = raised.get(alert.kind, 0) + 1
    print("  alerts raised:", raised)
    print("  The detector cannot tell a wanted download from a problem.")


def main():
    fresh_seeds()
    quiet_network()
    wanted_download()


if __name__ == "__main__":
    sys.exit(main())
