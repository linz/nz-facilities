from pathlib import Path

import typer


def output_file_callback(ctx: typer.Context, value: Path) -> Path:
    if not value.suffix == ".gpkg":
        raise typer.BadParameter(f"Specified output file does not end in .gpkg.")
    if value.exists() and ctx.params["overwrite"] is False:
        raise typer.BadParameter("Specified output file already exists. To overwrite, rerun with --overwrite.")
    return value
