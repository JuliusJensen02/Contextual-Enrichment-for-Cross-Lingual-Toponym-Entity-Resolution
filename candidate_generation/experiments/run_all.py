"""Runs every experiment behind pipeline_explained.html, in parallel, and keeps a status file.

  Step 1  geo_threshold.py             the distance threshold, per test set
  Step 2  run_candidate_generation.py  every parameter of the four letter-based methods on title_ipa
  Step 3  combination.py               each method as the title score
  Step 4  combination.py               the weight, k and each phonetic method in the combined score

  python experiments/run_all.py                 # run everything (skips jobs that already finished)
  python experiments/run_all.py --status        # how far it is and how long is left
  python experiments/run_all.py --testset pleiades-tm --steps 2 3
  python experiments/run_all.py --fresh         # forget earlier results and run everything again

Every job is one small command with its own log in results/rerun/logs/. A job that runs longer
than its time limit is stopped and reported as "timeout" (no result for that setting).
results/rerun/status.json is rewritten every few seconds; --status reads it.
"""
import argparse
import csv
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from common import CANDIDATE_GENERATION, LABELS, RERUN, TESTSETS

LOGS = RERUN / "logs"
STATUS = RERUN / "status.json"
OLD_SWEEP = Path(__file__).with_name("previous_seconds.csv")  # the step 2 sweep of 16 November: its run times
TIME_LIMIT = 25 * 60  # seconds, for one setting of one method (step 2)

# Step 2: the settings of experiment 12 (flags of run_candidate_generation.py -> the params text it reports).
STEP2 = (
    [("Q_grams", ["--qgram-q", str(q), "--qgram-t", str(t)], f"q={q},t={t:g}") for q in (2, 3, 4) for t in (0.4, 0.6, 0.8)]
    + [("Q_grams", ["--qgram-q", "3", "--qgram-t", str(t), "--qgram-max-keys", str(keys)], f"q=3,t={t:g},keys={keys}")
       for t in (0.4, 0.6) for keys in (100, 2000)]
    + [("MinHash_LSH", ["--minhash-n", str(n), "--minhash-threshold", str(thr)], f"n={n},thr={thr:g}")
       for n in (2, 3, 4) for thr in (0.2, 0.3, 0.5, 0.7)]
    + [("MinHash_LSH", ["--minhash-n", "3", "--minhash-threshold", str(thr), "--minhash-num-perm", str(perm)],
        f"n=3,thr={thr:g},perm={perm}") for thr in (0.2, 0.3) for perm in (64, 256)]
    + [("PassJoin", ["--tau", str(tau)], f"tau={tau}") for tau in (0, 1, 2)]
    + [("TFIDF_kNN", ["--tfidf-ngrams", grams, "--k", "1", "3", "5", "10"], f"n={grams}")
       for grams in ("1-2", "1-3", "2-3", "2-4", "3-3")]
)

# Steps 3 and 4: (title score, phonetic score) combinations.
STEP3 = [("edit", "tfidf:2-3"), ("tfidf:2-3", "tfidf:2-3"), ("jaccard:3", "tfidf:2-3"), ("qgram:3", "tfidf:2-3"),
         ("none", "tfidf:2-3")]
STEP4 = [("labse", phonetic) for phonetic in ("tfidf:2-3", "tfidf:1-3", "tfidf:2-4", "jaccard:2", "jaccard:3",
                                              "qgram:2", "qgram:3", "edit", "jaro", "none")]

# Rough seconds per job where there is no earlier run to go by.
GUESS = {"prepare": {"mehdie": 240, "pleiades-tm": 40, "zh-ru": 180},
         "geo": {"mehdie": 150, "pleiades-tm": 10, "zh-ru": 120},
         "combination": {"mehdie": 400, "pleiades-tm": 10, "zh-ru": 150}}


@dataclass
class Job:
    id: str
    step: str
    command: list
    estimate: float
    limit: float = 3 * 3600
    needs: list = field(default_factory=list)
    threads: int = 1
    state: str = "waiting"   # waiting, running, done, failed, timeout
    started: float = 0.0
    seconds: float = 0.0
    process: object = None
    log: object = None


def old_seconds() -> dict:
    """(testset, method, params) -> seconds in the previous sweep, where it finished."""
    if not OLD_SWEEP.is_file():
        return {}
    with OLD_SWEEP.open(encoding="utf8", newline="") as file:
        return {(r["testset"], r["method"], r["params"]): float(r["seconds"]) for r in csv.DictReader(file)}


def build_jobs(testsets, steps) -> list[Job]:
    python, jobs, earlier = sys.executable, [], old_seconds()
    for testset in testsets:
        slug = testset.replace("-", "")
        if steps & {"3", "4"}:
            jobs.append(Job(f"prepare_{slug}", "prepare", [python, "experiments/prepare.py", "--testset", testset],
                            GUESS["prepare"][testset], threads=4))
        if "1" in steps:
            jobs.append(Job(f"step1_{slug}", "1", [python, "experiments/geo_threshold.py", "--testset", testset,
                                                    "--out", str(RERUN / "step1" / f"{testset}.json")],
                            GUESS["geo"][testset], threads=2))
        if "2" in steps:
            for method, flags, params in STEP2:
                name = f"step2_{slug}_{method}_{params}".replace("=", "").replace(",", "_").replace(".", "")
                if method == "TFIDF_kNN":  # reported per k
                    known = [earlier.get((testset, method, f"k={k}" + ("" if params == "n=2-3" else f",{params}")))
                             for k in (1, 3, 5, 10)]
                    known = [s for s in known if s is not None and s < 3600]  # one old row slept for hours
                    estimate = statistics.median(known) * 4 if known else None
                else:
                    estimate = earlier.get((testset, method, params))
                if estimate is None:
                    estimate = TIME_LIMIT      # it did not finish last time either
                elif testset == "pleiades-tm":
                    estimate = estimate * 3    # the new Pleiades-TM has three times as many pairs
                jobs.append(Job(name, "2", [python, "run_candidate_generation.py", "--testset", testset, "--full",
                                            "--phonetic", "on", "--methods", method, *flags,
                                            "--out", str(RERUN / "step2" / f"{name}.csv")],
                                max(estimate, 3) + 5, limit=TIME_LIMIT))
        for step, combinations in (("3", STEP3), ("4", STEP4)):
            if step in steps:
                for title, phonetic in combinations:
                    name = f"step{step}_{slug}_{title}_{phonetic}".replace(":", "")
                    jobs.append(Job(name, step, [python, "experiments/combination.py", "--testset", testset, "--title",
                                                 title, "--phonetic", phonetic, "--out",
                                                 str(RERUN / f"step{step}" / f"{name}.csv")],
                                    GUESS["combination"][testset], needs=[f"prepare_{slug}"]))
    return jobs


# ---------------------------------------------------------------------------- time left
def time_left(jobs, workers, now) -> float:
    """Simulates the rest of the run. Estimates are scaled by how the finished jobs compared
    with theirs."""
    ratios = [j.seconds / j.estimate for j in jobs if j.state == "done" and j.estimate >= 5]
    scale = min(3.0, max(0.5, statistics.median(ratios))) if len(ratios) >= 5 else 1.0
    remaining = lambda j: min(j.limit, max(j.estimate * scale, 5))  # noqa: E731
    slots = sorted(max(remaining(j) - (now - j.started), 5) for j in jobs if j.state == "running")
    waiting = sorted((remaining(j) for j in jobs if j.state == "waiting"), reverse=True)
    clock = 0.0
    while waiting or slots:
        while waiting and len(slots) < workers:
            slots.append(clock + waiting.pop(0))
            slots.sort()
        clock = slots.pop(0)
    return clock


def write_status(jobs, workers, started, finished=False):
    now = time.time()
    steps = {}
    for job in jobs:
        s = steps.setdefault(job.step, {"total": 0, "done": 0, "running": 0, "failed": 0, "timeout": 0})
        s["total"] += 1
        if job.state in s:
            s[job.state] += 1
    status = {
        "updated": now, "started": started, "finished": finished, "workers": workers,
        "elapsed_seconds": round(now - started), "seconds_left": 0 if finished else round(time_left(jobs, workers, now)),
        "jobs_total": len(jobs), "jobs_done": sum(j.state == "done" for j in jobs), "steps": steps,
        "running": [{"id": j.id, "seconds": round(now - j.started), "estimate": round(j.estimate), "limit": j.limit}
                    for j in jobs if j.state == "running"],
        "problems": [{"id": j.id, "state": j.state, "seconds": round(j.seconds)} for j in jobs
                     if j.state in ("failed", "timeout")],
    }
    temporary = STATUS.with_suffix(".tmp")
    temporary.write_text(json.dumps(status, indent=1), encoding="utf8")
    for _ in range(20):  # on Windows the replace fails while --status is reading the file
        try:
            os.replace(temporary, STATUS)
            break
        except PermissionError:
            time.sleep(0.1)


def clock(seconds) -> str:
    seconds = int(seconds)
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}" if seconds >= 3600 else \
        f"{seconds // 60}:{seconds % 60:02d}"


def print_status():
    if not STATUS.is_file():
        print("No run has been started.")
        return
    status = json.loads(STATUS.read_text(encoding="utf8"))
    age = time.time() - status["updated"]
    state = "finished" if status["finished"] else "running" if age < 60 else f"STOPPED (no update for {clock(age)})"
    print(f"{state}: {status['jobs_done']} of {status['jobs_total']} jobs done, elapsed {clock(status['elapsed_seconds'])}"
          + ("" if status["finished"] else f", about {clock(max(0, status['seconds_left'] - age))} left"))
    names = {"prepare": "Prepare (embeddings, geo filter)", "1": "Step 1 geo threshold", "2": "Step 2 phonetic methods",
             "3": "Step 3 title methods", "4": "Step 4 combination"}
    for step, s in status["steps"].items():
        extra = "".join(f", {s[key]} {key}" for key in ("running", "failed", "timeout") if s[key])
        print(f"  {names[step]:34s} {s['done']:3d} / {s['total']:3d}{extra}")
    for job in sorted(status["running"], key=lambda j: -j["seconds"]):
        print(f"  running {clock(job['seconds'] + age):>7s} (expected {clock(job['estimate'])}, limit "
              f"{clock(job['limit'])})  {job['id']}")
    for job in status["problems"]:
        print(f"  {job['state'].upper():7s} after {clock(job['seconds'])}  {job['id']}")


# ---------------------------------------------------------------------------- running
def start(job: Job):
    environment = dict(os.environ, PYTHONIOENCODING="utf8", PYTHONUNBUFFERED="1", TOKENIZERS_PARALLELISM="false",
                       HF_HUB_OFFLINE="1", **{name: str(job.threads) for name in
                                              ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")})
    job.log = open(LOGS / f"{job.id}.log", "w", encoding="utf8")
    job.process = subprocess.Popen(job.command, cwd=CANDIDATE_GENERATION, env=environment, stdout=job.log,
                                   stderr=subprocess.STDOUT)
    job.state, job.started = "running", time.time()


def finish(job: Job, state: str):
    job.state, job.seconds = state, time.time() - job.started
    job.log.close()
    if state == "done":
        (LOGS / f"{job.id}.done").write_text(f"{job.seconds:.1f}", encoding="utf8")
    print(f"[{time.strftime('%H:%M:%S')}] {state:7s} {clock(job.seconds):>7s}  {job.id}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true", help="print how far the run is and stop")
    ap.add_argument("--testset", nargs="+", choices=list(TESTSETS), default=list(TESTSETS))
    ap.add_argument("--steps", nargs="+", choices=["1", "2", "3", "4"], default=["1", "2", "3", "4"])
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 8), help="jobs at a time")
    ap.add_argument("--fresh", action="store_true", help="delete earlier results and run everything again")
    args = ap.parse_args()
    if args.status:
        return print_status()

    if args.fresh and RERUN.exists():
        shutil.rmtree(RERUN)
    LOGS.mkdir(parents=True, exist_ok=True)
    for folder in ("step1", "step2", "step3", "step4"):
        (RERUN / folder).mkdir(exist_ok=True)
    jobs = build_jobs(args.testset, set(args.steps))
    for job in jobs:  # finished in an earlier run: keep its result
        marker = LOGS / f"{job.id}.done"
        if marker.is_file():
            job.state, job.seconds = "done", float(marker.read_text(encoding="utf8"))
    by_id = {job.id: job for job in jobs}
    started = time.time()
    print(f"{len(jobs)} jobs ({sum(j.state == 'done' for j in jobs)} already done), {args.workers} at a time, "
          f"about {clock(time_left(jobs, args.workers, started))}. Test sets: "
          f"{', '.join(LABELS[t] for t in args.testset)}", flush=True)

    last_status = 0.0
    while any(job.state in ("waiting", "running") for job in jobs):
        now = time.time()
        for job in jobs:
            if job.state == "running":
                code = job.process.poll()
                if code is not None:
                    finish(job, "done" if code == 0 else "failed")
                elif now - job.started > job.limit:
                    job.process.kill()
                    job.process.wait()
                    finish(job, "timeout")
        for job in jobs:  # a job whose preparation failed cannot run
            if job.state == "waiting" and any(by_id[need].state in ("failed", "timeout") for need in job.needs):
                job.state = "failed"
        busy = sum(job.threads for job in jobs if job.state == "running")
        ready = [job for job in jobs if job.state == "waiting" and all(by_id[n].state == "done" for n in job.needs)]
        # preparation first (others wait for it), then the longest jobs
        for job in sorted(ready, key=lambda j: (j.step != "prepare", -j.estimate)):
            if busy + job.threads <= args.workers:
                start(job)
                busy += job.threads
        if now - last_status > 5:
            write_status(jobs, args.workers, started)
            last_status = now
        time.sleep(1)
    write_status(jobs, args.workers, started, finished=True)
    print_status()


if __name__ == "__main__":
    main()
