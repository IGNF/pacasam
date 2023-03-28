from pathlib import Path
from typing import List
import geopandas as gpd
import pandas as pd
import plotly.express as px
import numpy as np

import plotly.express as px
from sklearn.preprocessing import QuantileTransformer

PREFIX_BOOL_DESCRIPTOR = "presence"
NB_POINTS_COLNAMES = [
    "nb_points_total",
    "nb_points_sol",
    "nb_points_bati",
    "nb_points_vegetation_basse",
    "nb_points_vegetation_moyenne",
    "nb_points_vegetation_haute",
    "nb_points_pont",
    "nb_points_eau",
    "nb_points_sursol_perenne",
    "nb_points_non_classes",
]

BOOLEAN_DESCRIPTORS = [""]


def make_class_histogram(df):
    df_bool = df.copy()
    nb_point_col_bool = [nb_point_col.replace("nb_points_", "") for nb_point_col in NB_POINTS_COLNAMES]
    df_bool[nb_point_col_bool] = df_bool[NB_POINTS_COLNAMES] > 0
    df_bool = df_bool.groupby("Split")[nb_point_col_bool].sum().transpose().sort_values(by="Train", ascending=False)
    fig = px.bar(df_bool, color="Split", barmode="stack", text_auto=True, title="Nombres de patches avec classe présente.")
    return fig, df_bool


def make_boolean_descriptor_histogram(df, bool_descriptors_cols: List[str]):
    df_bool = df[["Split"] + bool_descriptors_cols].copy()
    df_bool["all"] = 1
    df_bool = df_bool.groupby("Split")[["all"] + bool_descriptors_cols].sum().transpose().sort_values(by="Train", ascending=True)
    fig = px.bar(
        df_bool,
        color="Split",
        barmode="relative",
        text_auto=True,
        title=f"Nombres de patches concernées - TOTAL={len(df)}",
        orientation="h",
    )
    return fig, df_bool


def make_class_histograms(df):
    # Passer à zéro, concernera les classes rares, permet distribution interprétable.
    df_no_zero = df[["Split"] + NB_POINTS_COLNAMES].copy()
    df_no_zero[NB_POINTS_COLNAMES] = df_no_zero[NB_POINTS_COLNAMES].replace({0: np.nan})
    figs = []
    for c in NB_POINTS_COLNAMES:
        fig = px.histogram(
            df_no_zero,
            x=c,
            color="Split",
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
        color="Split",
        symbol="Split",
        opacity=0.9,
        labels={col: col.replace("nb_points_", "").replace("vegetation", "veg") for col in df.columns},
        width=1500,
        height=1500,
        title="Nombres de points" + (f" ({norm})" if norm else "") + (" (zéros ignorés)" if hide_zeros else ""),
    )  # remove underscore
    fig.update_traces(diagonal_visible=False)

    return fig


HTML_PLOTS_PLACEHOLDER = "{{next_div}}"


def make_all_graphs_and_a_report(gpkg_path: Path, output_path: Path):
    # Load the HTML template
    with open("./src/pacasam/dataviz/sampling_dataviz_template.html", "r") as f:
        template = f.read()
    template = template.replace("{{sampling_gpkg_path}}", str(gpkg_path))

    def add_viz(template: str, viz_name: str):
        with open(output_path / f"{viz_name}.html", "r") as f:
            plot_html = f.read()
        template = template.replace(HTML_PLOTS_PLACEHOLDER, plot_html + "\n" + HTML_PLOTS_PLACEHOLDER)
        return template

    df: pd.DataFrame = gpd.read_file(gpkg_path)

    # TODO: change is_test_set to be a str from its creation on.
    df["Split"] = df["is_test_set"].apply(lambda flag: "Test" if flag else "Train")

    viz_name = "classes_histogram"
    fig_class_hist, df_bool_classes = make_class_histogram(df)
    fig_class_hist.write_html(output_path / f"{viz_name}.html")
    fig_class_hist.write_image(output_path / f"{viz_name}.svg")
    template = add_viz(template, viz_name)
    # TODO: consolidation could be done at extract time to have a cleaner output

    viz_name = "descriptors_histogram"
    df["nb_points_eau_heq_500"] = df["nb_points_eau"] > 500
    df["nb_points_bati_heq_500"] = df["nb_points_bati"] > 500
    bool_desc_cols = ["nb_points_eau_heq_500", "nb_points_bati_heq_500"]
    # Make sure that the column is considered
    bool_desc_cols += [column for column in df if column.startswith(PREFIX_BOOL_DESCRIPTOR)]
    fig_bool_desc, df_bool_descriptors = make_boolean_descriptor_histogram(df, bool_desc_cols)
    fig_bool_desc.write_html(output_path / f"{viz_name}.html")
    fig_bool_desc.write_image(output_path / f"{viz_name}.svg")
    template = add_viz(template, viz_name)

    fig_class_hist_nb_points = make_class_histograms(df)
    for colname, fig in zip(NB_POINTS_COLNAMES, fig_class_hist_nb_points):
        viz_name = f"distribution-{colname}"
        fig.write_html(output_path / f"{viz_name}.html")
        fig.write_image(output_path / f"{viz_name}.svg")
        template = add_viz(template, viz_name)

    viz_name = "scatter_matrix-nonorm"
    fig_scatter_matrix = make_scatter_matrix_classes(df, norm=None)
    fig_scatter_matrix.write_html(output_path / f"{viz_name}.html")
    fig_scatter_matrix.write_image(output_path / f"{viz_name}.svg")
    template = add_viz(template, viz_name)

    viz_name = "scatter_matrix-standardnorm"
    fig_scatter_matrix_standard = make_scatter_matrix_classes(df, norm="Standardization")
    fig_scatter_matrix_standard.write_html(output_path / f"{viz_name}.html")
    fig_scatter_matrix_standard.write_image(output_path / f"{viz_name}.svg")
    template = add_viz(template, viz_name)

    viz_name = "scatter_matrix-quantilenorm"
    fig_scatter_matrix_quantile = make_scatter_matrix_classes(df, norm="Quantilization")
    fig_scatter_matrix_quantile.write_html(output_path / f"{viz_name}.html")
    fig_scatter_matrix_quantile.write_image(output_path / f"{viz_name}.svg")
    template = add_viz(template, viz_name)

    # cf. https://medium.com/analytics-vidhya/how-to-export-a-plotly-chart-as-html-3b5df568df4a

    # Fill in

    # Write the final report to a file
    # TODO: add a timestamp.
    template = template.replace(HTML_PLOTS_PLACEHOLDER, "")
    with open(output_path / "pacasam-sampling-dataviz.html", "w") as f:
        f.write(template)
