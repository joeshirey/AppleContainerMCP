import sys

from d2c.executor import dry_run, execute
from d2c.global_flags import GLOBAL_FLAGS, prompt_continue, strip_global_flags
from d2c.registry import translate
from d2c.unsupported import UNSUPPORTED


def main() -> None:
    args = sys.argv[1:]

    is_dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]

    if not args:
        print("Usage: d2c [--dry-run] <docker-command> [args...]")
        print("       d2c --dry-run ps -a")
        print("       d2c run --rm -it ubuntu bash")
        sys.exit(1)

    args, warned_flags, prepend_flags = strip_global_flags(args)

    for flag in warned_flags:
        gf = GLOBAL_FLAGS[flag]
        if not prompt_continue(flag, gf.hint):
            sys.exit(1)

    if not args:
        print("d2c: no command provided after flags")
        sys.exit(1)

    # Peek at the effective command name (accounting for management namespace)
    effective_cmd = args[1] if args[0] == "container" and len(args) > 1 else args[0]

    if effective_cmd in UNSUPPORTED:
        unsupported = UNSUPPORTED[effective_cmd]
        print(f"✗  'docker {effective_cmd}' is not supported by Apple Container.")
        print(f"   Hint: {unsupported.hint}")
        sys.exit(1)

    try:
        container_args, note = translate(args)
    except KeyError:
        print(f"d2c: unknown command '{args[0]}'")
        sys.exit(1)

    # Insert translated global flags (e.g. --debug) after 'container'
    if prepend_flags:
        container_args = [container_args[0]] + prepend_flags + container_args[1:]

    if is_dry_run:
        dry_run(args, container_args, note)
        sys.exit(0)

    sys.exit(execute(container_args))
