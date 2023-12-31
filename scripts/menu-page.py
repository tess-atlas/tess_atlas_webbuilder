#!/usr/bin/env python

import sys
import argparse
import itables
from pathlib import Path

import pandas as pd
import numpy as np
from jinja2 import Environment, FileSystemLoader

EXOFOP = "https://exofop.ipac.caltech.edu/tess/"
TIC_DATASOURCE = EXOFOP + "download_toi.php?sort=toi&output=csv"


# Uses itables to generate html for a fancy table
def generate_table_html(src_dir, csv_path):
    tois = []
    toi_links = []
    thumbnails = []

    # find phaseplots for each notebook
    for d in (src_dir / "objects").glob("toi_*_files"):
        i_toi = int(str(d.name).removeprefix("toi_").removesuffix("_files"))
        tois.append(i_toi)
        href = f"'/objects/toi_{i_toi}/'"
        toi_html = f"<a href={href}> {i_toi}</a>"
        thumbnail = f"<a href={href}/'> <img src='/toi_data/toi_{i_toi}_files/thumbnail.png'></a>"
        thumbnails.append(thumbnail)
        toi_links.append(toi_html)

    df = pd.read_csv(csv_path)[["TOI", "Status", "Category", "Classification"]]
    df = df.dropna()
    df = df.astype({"TOI": "int"})
    df = df.loc[df["TOI"].isin(tois)]
    df = df.reset_index(drop=True)

    # Add empty row for anything not found in summary file
    for toi in tois:
        if toi not in df["TOI"].values:
            print(f"WARNING: did not find TOI {toi} in summary file", file=sys.stderr)
            df.loc[-1] = [toi, "", "", ""]
            df = df.reset_index(drop=True)

    df["TOI"] = toi_links
    df.insert(1, "Phase Plot", thumbnails)

    html = itables.to_html_datatable(
        df,
        caption="TESS Atlas Catalog Summary",
        scrollX=True,
        lengthMenu=[5, 10, 20, 50],
        classes="compact",
        maxBytes=0,
        connected=True,
        style="table-layout:auto;width:100%;float:none",
    )

    return html


if __name__ == "__main__":
    cwd = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("source_directory", type=Path)
    parser.add_argument("-s", "--summary-file", type=Path)
    args = parser.parse_args()
    src_dir = args.source_directory.resolve()

    if args.summary_file:
        csv_path = args.summary_file.resolve()
    else:
        # assume summary file is in sourced directory
        csv_path = src_dir / "analysis_summary.csv"

    assert csv_path.is_file()

    # Get analysis counts
    df = pd.read_csv(csv_path)
    counts = df["Status"].value_counts().to_dict()
    num_tois = len(
        np.unique(pd.read_csv(TIC_DATASOURCE)["TOI"].values.astype(np.int64))
    )

    html_table = generate_table_html(src_dir, csv_path)

    # Set up jinja2 env
    environment = Environment(
        loader=FileSystemLoader(cwd / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.get_template("menu_page.j2")

    # Render menu_page.myst and print to stdout
    content = template.render(
        N_TESS_ATLAS=len(df["Status"].dropna()),
        N_EXOFOP=num_tois,
        N_PASS=counts.get("completed", 0),
        N_FAIL=counts.get("failed", 0),
        N_NOT_STARTED=counts.get("not_started", 0),
        html_table=html_table,
    )
    print(content)
