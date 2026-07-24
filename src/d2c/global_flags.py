from dataclasses import dataclass


@dataclass(frozen=True)
class GlobalFlag:
    hint: str
    takes_value: bool = False


GLOBAL_FLAGS: dict[str, GlobalFlag] = {
    "--host": GlobalFlag(
        hint="Apple Container connects to the local system service only — no remote daemon.",
        takes_value=True,
    ),
    "-H": GlobalFlag(
        hint="Apple Container connects to the local system service only — no remote daemon.",
        takes_value=True,
    ),
    "--context": GlobalFlag(
        hint="Apple Container has no context switching.",
        takes_value=True,
    ),
    "-c": GlobalFlag(
        hint="Apple Container has no context switching.",
        takes_value=True,
    ),
    "--tls": GlobalFlag(
        hint="Apple Container manages its own security — no TLS flags needed.",
    ),
    "--tlscacert": GlobalFlag(
        hint="Apple Container manages its own security — no TLS flags needed.",
        takes_value=True,
    ),
    "--tlscert": GlobalFlag(
        hint="Apple Container manages its own security — no TLS flags needed.",
        takes_value=True,
    ),
    "--tlskey": GlobalFlag(
        hint="Apple Container manages its own security — no TLS flags needed.",
        takes_value=True,
    ),
    "--tlsverify": GlobalFlag(
        hint="Apple Container manages its own security — no TLS flags needed.",
    ),
    "--config": GlobalFlag(
        hint="No equivalent config directory.",
        takes_value=True,
    ),
    "--log-level": GlobalFlag(
        hint="Use 'container --debug' for verbose output.",
        takes_value=True,
    ),
    "-l": GlobalFlag(
        hint="Use 'container --debug' for verbose output.",
        takes_value=True,
    ),
}

# Flags that translate directly to container CLI flags (no warning)
TRANSLATABLE_GLOBAL_FLAGS: dict[str, list[str]] = {
    "--debug": ["--debug"],
    "-D": ["--debug"],
}


def strip_global_flags(args: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Separate Docker global flags from command args.

    Returns (remaining_args, warned_flags, prepend_flags) where:
    - remaining_args: args with Docker global flags removed
    - warned_flags: flag names that need user confirmation
    - prepend_flags: flags to insert after 'container' in the translated command
    """
    remaining: list[str] = []
    warned: list[str] = []
    prepend: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        bare = arg.split("=")[0]

        if bare in GLOBAL_FLAGS:
            gf = GLOBAL_FLAGS[bare]
            warned.append(bare)
            i += 1
            # Consume the value if the flag takes one and it wasn't in --flag=value form
            if gf.takes_value and "=" not in arg and i < len(args):
                i += 1
        elif arg in TRANSLATABLE_GLOBAL_FLAGS:
            prepend.extend(TRANSLATABLE_GLOBAL_FLAGS[arg])
            i += 1
        else:
            remaining.append(arg)
            i += 1

    return remaining, warned, prepend


def prompt_continue(flag: str, hint: str) -> bool:
    """Warn about an unsupported Docker global flag and ask whether to proceed.

    Returns True if the user chooses to continue, False otherwise.
    Defaults to False (safe for non-interactive scripts).
    """
    print(f"⚠  '{flag}' is not supported by Apple Container.")
    print(f"   {hint}")
    answer = input("   Continue anyway? [y/N] ").strip().lower()
    return answer == "y"
