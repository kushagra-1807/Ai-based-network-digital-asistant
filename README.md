# Network assistant

A tool that watches a network, notices when something is wrong, and answers questions about it in plain English. You can ask why the internet is slow and it looks at the live readings, names the likely cause, and suggests a fix. In the simulation it can apply the fix as well.

This is a Computer Networks course project. It needs Python 3.9 or newer.

## Running it

    pip install flask psutil
    python run.py web

Then open http://127.0.0.1:5000. The page shows live throughput, latency, the device list, alerts and a chat box. It starts on a simulated network, which is the one to use for a demo (the reason is in the next section).

To see it work:

1. Ask "Which device uses the most bandwidth?" using the link under the chat box.
2. In the Simulation section at the bottom, press "streaming hog". Within a few seconds an alert appears.
3. Ask "Why is my network slow?". The assistant names the device, shows the evidence and offers a fix.
4. Type "yes". The Smart-TV is limited in the simulation and the readings recover.

The other faults you can start are isp latency, wifi interference, packet loss, unknown device, device offline, upload spike and internet outage.

## Simulation and live mode

A normal computer can measure its own traffic, ping the router and the internet, and read the ARP table to see which devices are present. It cannot see how much bandwidth the other devices use. That needs the router, through SNMP or its admin interface, or a mirrored switch port.

So there are two modes. The simulation is a made-up home network with six devices, and everything works in it, including per-device bandwidth and applying fixes. The evaluation runs on it because it knows which fault is active at every moment. Live mode, started with `python run.py web --live`, takes real readings from the machine it runs on. Per-device bandwidth shows as "n/a", and the assistant says so if asked. Fixes that need the router are not carried out; it prints the steps instead. Trusting a device works in both modes.

In live mode set `--capacity` to your plan speed in Mbps, or the percentages are measured against 100.

## Other commands

    python run.py chat        talk to the assistant in the terminal
    python run.py monitor     print readings every second
    python run.py evaluate    run the evaluation and write docs/EVALUATION_RESULTS.md
    python run.py speedtest   measure the link once (needs speedtest-cli)
    python crosscheck.py      re-check the evaluation on new seeds
    python -m unittest discover -s tests

Options include `--live`, `--capacity`, `--port`, `--gateway`, `--scan nmap` and `--ml`.

## How it is put together

The collector (or the simulator) produces one reading every second or two. Readings go into a SQLite file. The detector looks at each reading and raises alerts. The recommender turns an alert into a cause, some advice and sometimes an action. The assistant answers questions using all of that, and the web page shows it.

The collector pings the router and a public host separately. If the router answers quickly and the internet does not, the delay is upstream. If the router itself is slow, the problem is inside your own network, usually Wi-Fi. The assistant gives different advice in each case.

The detector has three parts. Fixed rules cover latency, packet loss, how full the link is, one device taking more than half the download, and devices that appear or vanish. A statistical baseline learns what is normal for this network and flags large jumps that no fixed rule covers, for example a big upload. An IsolationForest is available with `--ml`. An alert has to hold for two readings in a row before it fires.

Questions are matched against about 190 example sentences using TF-IDF and cosine similarity. The example sentences, the synonym list and the simulated devices are in `netassist/data/` as plain files, so they can be edited without touching the code.

If `ANTHROPIC_API_KEY` is set, questions the classifier cannot place are sent to a language model together with a text summary of the network. All numbers still come from the local readings. This path has only been tested with a stand-in for the API.

`DESIGN.md` records the choices behind the page.

## Files

    run.py                 command line entry point
    crosscheck.py          second look at the evaluation results
    DESIGN.md              design direction for the dashboard
    netassist/             the code
    netassist/data/        example sentences, synonyms, simulated devices, test questions
    netassist/static/      page styles and script
    netassist/templates/   the page
    tests/                 unit tests
    docs/                  report, demo guide, evaluation results
