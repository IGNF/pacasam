import argparse
from pathlib import Path
from typing import List
import geopandas as gpd
import pandas as pd
import plotly.express as px
import numpy as np

from sklearn.preprocessing import QuantileTransformer

from pacasam.connectors.synthetic import NB_POINTS_COLNAMES

PREFIX_BOOL_DESCRIPTOR = "presence"

HTML_PLOTS_PLACEHOLDER = "{{PLACEHOLDER_TO_ADD_GRAPHS_ITERATIVELY}}"
REPORT_HTML_TEMPLATE_PATH = "./src/pacasam/describe/sampling_dataviz_template.html"


def make_class_histogram(df):
    df_bool = df.copy()
    nb_point_col_bool = [nb_point_col.replace("nb_points_", "") for nb_point_col in NB_POINTS_COLNAMES]
    df_bool[nb_point_col_bool] = df_bool[NB_POINTS_COLNAMES] > 0
    df_bool = df_bool.groupby("split")[nb_point_col_bool].sum().transpose()
    fig = px.bar(df_bool, color="split", barmode="stack", text_auto=True, title="Nombres de patches avec classe présente.")
    return fig


def make_boolean_descriptor_histogram(df: pd.DataFrame):
    bool_descriptors_cols = df.select_dtypes(include=bool).columns.tolist()
    df_bool = df[["split"] + bool_descriptors_cols].copy()
    df_bool["all"] = 1
    df_bool = df_bool.groupby("split")[["all"] + bool_descriptors_cols].sum().transpose()
    fig = px.bar(
        df_bool,
        color="split",
        barmode="relative",
        text_auto=True,
        title=f"Nombres de patches concernées - TOTAL={len(df)}",
        orientation="h",
    )
    return fig


def make_class_histograms(df):
    # Passer à zéro, concernera les classes rares, permet distribution interprétable.
    df_no_zero = df[["split"] + NB_POINTS_COLNAMES].copy()
    df_no_zero[NB_POINTS_COLNAMES] = df_no_zero[NB_POINTS_COLNAMES].replace({0: np.nan})
    figs = []
    for c in NB_POINTS_COLNAMES:
        fig = px.histogram(
            df_no_zero,
            x=c,
            color="split",
            marginal="box",
            hover_data=df_no_zero.columns,
            opacity=0.5,
            labels={c: f"Nombre de points {c.replace('nb_points_','')} (valeurs nulles ignorées)"},
            barmode="overlay",
            title=f"Histogramme du nombres de points : {c.replace('nb_points_','')}",
        )
        figs += [fig]
    return figs


def make_scatter_matrix_classes(df, norm=None, hide_zeros=True):
    df_norm = df.copy()

    if hide_zeros:
        df_norm = df_norm.replace(to_replace=0, value=np.nan)

    if norm == "Standardization":
        # Quantilization enables to make classes "more" comparable in Farthest point Sampling,
        # and respects distribution within each class.
        df_norm.loc[:, NB_POINTS_COLNAMES] = (df_norm.loc[:, NB_POINTS_COLNAMES] - df.loc[:, NB_POINTS_COLNAMES].mean()) / df_norm.loc[
            :, NB_POINTS_COLNAMES
        ].std()
    elif norm == "Quantilization":
        # Quantilization enables to fully explore each X vs Y relationship.
        qt = QuantileTransformer(n_quantiles=50, random_state=0, subsample=100_000)
        df_norm.loc[:, NB_POINTS_COLNAMES] = qt.fit_transform(df_norm.loc[:, NB_POINTS_COLNAMES].values)

    if hide_zeros:
        # put zeros back
        df_norm.loc[:, NB_POINTS_COLNAMES] = df_norm.loc[:, NB_POINTS_COLNAMES].fillna(0)

    fig = px.scatter_matrix(
        df_norm,
        dimensions=NB_POINTS_COLNAMES,
        color="split",
        symbol="split",
        opacity=0.9,
        labels={col: col.replace("nb_points_", "").replace("vegetation", "veg") for col in df.columns},
        width=1500,
        height=1500,
        title="Nombres de points" + (f" ({norm})" if norm else "") + (" (zéros ignorés)" if hide_zeros else ""),
    )  # remove underscore
    fig.update_traces(diagonal_visible=False)

    return fig


def add_viz_to_template(template: str, viz_name: str, output_path):
    # TODO: simplify by giving the figure directly and getting its html without saving it first.
    with open(output_path / f"{viz_name}.html", "r") as f:
        plot_html = f.read()
    html_and_some_spacing = plot_html + "\n" + HTML_PLOTS_PLACEHOLDER
    template = template.replace(HTML_PLOTS_PLACEHOLDER, html_and_some_spacing)
    return template


def save_report(html_report: str, output_path: Path):
    html_report = html_report.replace(HTML_PLOTS_PLACEHOLDER, "")
    with open(output_path / "pacasam-sampling-dataviz.html", "w") as f:
        f.write(html_report)

def make_all_graphs_and_a_report(gpkg_path: Path, output_path: Path):
    df: pd.DataFrame = gpd.read_file(gpkg_path)

    # Load the HTML template
    with open(REPORT_HTML_TEMPLATE_PATH, "r") as f:
        report: str = f.read()

    output_path.mkdir(parents=True, exist_ok=True)

    viz_name = "classes_histogram"
    fig = make_class_histogram(df)
    fig.write_html(output_path / f"{viz_name}.html")
    fig.write_image(output_path / f"{viz_name}.svg")
    report = add_viz_to_template(report, viz_name, output_path)

    viz_name = "descriptors_histogram"
    fig = make_boolean_descriptor_histogram(df)
    fig.write_html(output_path / f"{viz_name}.html")
    fig.write_image(output_path / f"{viz_name}.svg")
    report = add_viz_to_template(report, viz_name, output_path)

    fig_class_hist_nb_points = make_class_histograms(df)
    for colname, fig in zip(NB_POINTS_COLNAMES, fig_class_hist_nb_points):
        viz_name = f"distribution-{colname}"
        fig.write_html(output_path / f"{viz_name}.html")
        fig.write_image(output_path / f"{viz_name}.svg")
        report = add_viz_to_template(report, viz_name, output_path)

    viz_name = "scatter_matrix-nonorm"
    fig = make_scatter_matrix_classes(df, norm=None)
    fig.write_html(output_path / f"{viz_name}.html")
    fig.write_image(output_path / f"{viz_name}.svg")
    report = add_viz_to_template(report, viz_name, output_path)

    viz_name = "scatter_matrix-standardnorm"
    fig = make_scatter_matrix_classes(df, norm="Standardization")
    fig.write_html(output_path / f"{viz_name}.html")
    fig.write_image(output_path / f"{viz_name}.svg")
    report = add_viz_to_template(report, viz_name, output_path)

    viz_name = "scatter_matrix-quantilenorm"
    fig = make_scatter_matrix_classes(df, norm="Quantilization")
    fig.write_html(output_path / f"{viz_name}.html")
    fig.write_image(output_path / f"{viz_name}.svg")
    report = add_viz_to_template(report, viz_name, output_path)

    save_report(report, output_path)




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpkg_path", type=Path)
    parser.add_argument("--output_path", type=Path)
    args = parser.parse_args()

    make_all_graphs_and_a_report(gpkg_path=args.gpkg_path, output_path=args.output_path)
