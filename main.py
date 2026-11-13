"""Run Review: a small Drafter running log and pace calculator."""

from dataclasses import dataclass
from drafter import (
    Button, Header, Label, Page, SelectBox, Table, TextArea, TextBox,
    route, set_site_information, start_server,
)


@dataclass
class Run:
    """Store one run, with distance in miles and times in seconds."""

    run_id: int
    title: str
    distance: float
    seconds: int
    effort: str
    halfway_seconds: int
    notes: str


@dataclass
class State:
    """Remember saved runs, the selected run, and the user's settings."""

    runs: list[Run]
    selected_id: int
    next_id: int
    runner_name: str
    reference_pace: int
    status: str


def initial_state() -> State:
    """Return a fresh log with an 8:00 per mile reference pace."""
    return State([], 0, 1, "Runner", 480, "Welcome! Add your first run.")


def read_time(value: str) -> int:
    """Convert minutes:seconds to seconds, or return -1 for bad input."""
    parts = value.strip().split(":")
    if len(parts) != 2:
        return -1
    if not parts[0] or len(parts[1]) != 2:
        return -1
    # Checking ASCII digits first prevents invalid int conversions.
    for part in parts:
        for character in part:
            if character not in "0123456789":
                return -1
    if len(parts[0]) > 6 or int(parts[1]) >= 60:
        return -1
    return int(parts[0]) * 60 + int(parts[1])


def read_distance(value: str) -> float:
    """Read a positive decimal mile value, or return -1 for bad input."""
    value = value.strip()
    if not value or len(value) > 12 or value.count(".") > 1:
        return -1
    digit_count = 0
    for character in value:
        if character in "0123456789":
            digit_count += 1
        elif character != ".":
            return -1
    if digit_count == 0:
        return -1
    distance = float(value)
    if distance <= 0 or distance > 1000:
        return -1
    return distance


def clock(seconds: float) -> str:
    """Round seconds once and display minutes:seconds, including long runs."""
    total = int(round(seconds))
    minutes = total // 60
    remainder = total % 60
    if remainder < 10:
        return str(minutes) + ":0" + str(remainder)
    return str(minutes) + ":" + str(remainder)


def find_run(state: State) -> Run:
    """Find the selected run, or return an empty placeholder run."""
    for run in state.runs:
        if run.run_id == state.selected_id:
            return run
    return Run(0, "", 0, 0, "Easy", 0, "")


def totals(runs: list[Run]) -> list[float]:
    """Add stored Run attributes to find total miles and seconds."""
    miles = 0.0
    seconds = 0.0
    for run in runs:
        miles += run.distance
        seconds += run.seconds
    return [miles, seconds]


def navigation() -> list:
    """Create navigation buttons shared by every page."""
    return [
        Button("Home", index), Button("Add run", add_run),
        Button("Run log", run_log), Button("Settings", settings),
        Button("Help", help_page),
    ]


@route
def index(state: State) -> Page:
    """Show the runner's totals and distance-weighted average pace."""
    summary = totals(state.runs)
    content = [Header("Run Review"), "Hello, " + state.runner_name + ".",
               state.status, Header("Your running log", level=2),
               "Runs saved: " + str(len(state.runs)),
               "Total distance: " + str(round(summary[0], 2)) + " mi",
               "Total time: " + clock(summary[1])]
    if summary[0] > 0:
        content.append("Overall pace: " + clock(summary[1] / summary[0])
                       + " /mi")
    else:
        content.append("Add a run to see your average pace.")
    content.append("Reference pace: " + clock(state.reference_pace) + " /mi")
    return Page(state, content + navigation())


def run_form(state: State, title: str, distance: str, duration: str,
             effort: str, halfway: str, notes: str) -> Page:
    """Build the form and preserve entered values after a validation error."""
    return Page(state, [
        Header("Add a run"), state.status,
        Label("Run name", "title"), TextBox("title", title),
        Label("Distance in miles", "distance"), TextBox("distance", distance),
        Label("Total time (minutes:seconds, e.g. 42:30 or 133:20)", "duration"),
        TextBox("duration", duration),
        Label("Effort", "effort"),
        SelectBox("effort", ["Easy", "Moderate", "Hard"], effort),
        Label("Time at halfway DISTANCE (optional, minutes:seconds)", "halfway"),
        TextBox("halfway", halfway),
        "Example: for 6 miles, enter your elapsed time at 3 miles.",
        Label("Notes (optional)", "notes"), TextArea("notes", notes),
        Button("Save and analyze", save_run),
    ] + navigation())


@route
def add_run(state: State) -> Page:
    """Show a blank form for manually entering run data."""
    return run_form(state, "", "", "", "Easy", "", "")


@route
def save_run(state: State, title: str, distance: str, duration: str,
             effort: str, halfway: str, notes: str) -> Page:
    """Validate all fields before adding a run and selecting its analysis."""
    miles = read_distance(distance)
    seconds = read_time(duration)
    halfway_seconds = 0
    if halfway.strip():
        halfway_seconds = read_time(halfway)
    error = ""
    if not title.strip():
        error = "Enter a name for this run."
    elif miles <= 0:
        error = "Enter a distance greater than 0 and at most 1000 miles."
    elif seconds <= 0:
        error = "Use minutes:seconds for total time, with seconds from 00 to 59."
    elif halfway.strip() and (halfway_seconds <= 0 or halfway_seconds >= seconds):
        error = "Halfway time must be greater than zero and less than total time."
    elif effort not in ["Easy", "Moderate", "Hard"]:
        error = "Choose Easy, Moderate, or Hard."
    if error:
        state.status = error
        # A forged effort value cannot be used as a SelectBox default.
        if effort not in ["Easy", "Moderate", "Hard"]:
            effort = "Easy"
        return run_form(state, title, distance, duration, effort, halfway, notes)
    state.runs.append(Run(state.next_id, title.strip(), miles, seconds,
                          effort, halfway_seconds, notes.strip()))
    state.selected_id = state.next_id
    state.next_id += 1
    state.status = "Run saved."
    return analysis(state)


@route
def run_log(state: State) -> Page:
    """List every run with a button that opens its analysis."""
    rows = []
    for run in state.runs:
        rows.append([run.title, run.distance, clock(run.seconds),
                     clock(run.seconds / run.distance), run.effort,
                     Button("View", view_run, {"run_id": run.run_id})])
    content = [Header("Run log"), state.status]
    if not rows:
        content.append("No runs saved yet.")
    else:
        content.append(Table(rows, ["Run", "Miles", "Time", "Pace /mi",
                                    "Effort", "Analysis"]))
    return Page(state, content + navigation())


@route
def view_run(state: State, run_id: int) -> Page:
    """Select a run by its stable identifier and show its analysis."""
    state.selected_id = run_id
    state.status = "Viewing saved run."
    return analysis(state)


def split_feedback(run: Run) -> list:
    """Compare equal-distance halves when a halfway time was entered."""
    if run.halfway_seconds == 0:
        return ["No halfway time entered. Add it on a future run to compare halves."]
    second_half = run.seconds - run.halfway_seconds
    difference = second_half - run.halfway_seconds
    result = ["First-half pace: "
              + clock(run.halfway_seconds / (run.distance / 2)) + " /mi",
              "Second-half pace: "
              + clock(second_half / (run.distance / 2)) + " /mi"]
    if difference < 0:
        result.append("Negative split: second half was "
                      + clock(-difference) + " faster in total time.")
    elif difference > 0:
        result.append("Positive split: second half was "
                      + clock(difference) + " slower in total time.")
    else:
        result.append("Even split: both halves took the same time.")
    return result


@route
def analysis(state: State) -> Page:
    """Show selected run pace, reference comparison, halves, and notes."""
    run = find_run(state)
    if run.run_id == 0:
        return Page(state, [Header("Run analysis"), "Select a run from the log."]
                    + navigation())
    pace = run.seconds / run.distance
    difference = pace - state.reference_pace
    content = [Header(run.title), state.status,
               "Distance: " + str(run.distance) + " mi",
               "Time: " + clock(run.seconds),
               "Average pace: " + clock(pace) + " /mi",
               "Effort: " + run.effort,
               Header("Reference pace comparison", level=2)]
    if abs(difference) < 0.5:
        content.append("Your average pace matched the reference to the nearest second.")
    elif difference < 0:
        content.append(clock(-difference) + " /mi faster than the reference.")
    else:
        content.append(clock(difference) + " /mi slower than the reference.")
    content.append("Reference: " + clock(state.reference_pace) + " /mi. "
                   + "Faster does not always mean a better run; consider effort and conditions.")
    content.append(Header("Halfway analysis", level=2))
    content += split_feedback(run)
    content += [Header("Notes", level=2), run.notes or "No notes entered.",
                Button("Delete this run", delete_run)]
    return Page(state, content + navigation())


@route
def delete_run(state: State) -> Page:
    """Remove only the selected run and return to the log."""
    remaining = []
    removed = False
    for run in state.runs:
        if run.run_id != state.selected_id:
            remaining.append(run)
        else:
            removed = True
    state.runs = remaining
    state.selected_id = 0
    state.status = "Run deleted."
    if not removed:
        state.status = "No run was selected to delete."
    return run_log(state)


@route
def settings(state: State) -> Page:
    """Show editable runner name and comparison pace settings."""
    return Page(state, [
        Header("Settings"), state.status,
        Label("Your name", "runner_name"),
        TextBox("runner_name", state.runner_name),
        Label("Reference pace (minutes:seconds per mile)", "reference"),
        TextBox("reference", clock(state.reference_pace)),
        "Choose a pace to compare against, such as your planned pace for a run.",
        Button("Save settings", save_settings),
    ] + navigation())


@route
def save_settings(state: State, runner_name: str, reference: str) -> Page:
    """Save settings only when both the name and reference pace are valid."""
    pace = read_time(reference)
    if not runner_name.strip():
        state.status = "Enter your name."
        return settings(state)
    if pace <= 0:
        state.status = "Enter a positive reference pace as minutes:seconds."
        return settings(state)
    state.runner_name = runner_name.strip()
    state.reference_pace = pace
    state.status = "Settings saved."
    return settings(state)


@route
def help_page(state: State) -> Page:
    """Explain inputs, calculations, and the limits of this simple log."""
    return Page(state, [
        Header("How to use Run Review"),
        "1. Set your name and reference pace in Settings.",
        "2. Add a run using miles and minutes:seconds. For 1 hour, use 60:00.",
        "3. Optionally enter elapsed time at halfway DISTANCE, plus notes.",
        "4. View analysis or revisit any saved run in the Run log.",
        "Average pace = total seconds / total miles.",
        "Overall pace = all runs' total seconds / all runs' total miles.",
        "A negative split means the second half took less time over equal distance.",
        "Effort is your own description; it is not calculated from pace.",
        "Use consistent moving time or elapsed time for meaningful comparisons.",
        "Weather, terrain, stops, and effort affect pace. This app does not measure fitness.",
        "Runs live in the app's current state, without an account or database. ",
        "Deleting a run removes it immediately.",
    ] + navigation())




# This standard Python guard starts the app when run directly, but prevents
# starting a web server when tests import the functions from this file.
if __name__ == "__main__":
    start_server(initial_state(), site_title="Run Review", theme="skeleton")

