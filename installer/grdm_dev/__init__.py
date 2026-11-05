"""grdm-dev: one-command installer for the GakuNin RDM developer environment 2027 (SPEC-02).

Standard library only. Every subcommand lives in its own module and follows one contract:

    def register(subparsers) -> None      # add its argparse sub-parser(s)
    def run(ctx: Context, args) -> int    # do the work, return an exit code from exit_codes

Reports are produced through `grdm_dev.report.emit(ctx, name, data)`, which prints TOON by
default or JSON with --json and keeps a copy under runtime/reports/.
"""
__version__ = "0.1.0"
