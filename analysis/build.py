"""Build every chart on the site.

Runs make_charts.py in each topic folder under analysis/, then writes
charts/index.json and the All charts list.

Usage (from the repo root):
    pip install -r analysis/requirements.txt
    python3 analysis/build.py              # build from the saved copies of the data
    python3 analysis/build.py --refresh    # fetch the latest data from each publisher first
    python3 analysis/build.py population   # build one topic
"""
import glob
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ibn import chart, cso  # noqa: E402


def main(argv):
    if "--refresh" in argv:
        cso.REFRESH = True
    only = [a for a in argv if not a.startswith("--")]
    chart.load_topics()
    for path in sorted(glob.glob(os.path.join(HERE, "*", "make_charts.py"))):
        topic = os.path.basename(os.path.dirname(path))
        if only and topic not in only:
            continue
        print(f"\n# {topic}")
        spec = importlib.util.spec_from_file_location(f"{topic}_charts", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build()
    chart.write_index()


if __name__ == "__main__":
    main(sys.argv[1:])
