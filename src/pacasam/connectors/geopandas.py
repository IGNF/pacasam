import logging
from pathlib import Path
import geopandas as gpd
from geopandas import GeoDataFrame

from pacasam.connectors.connector import Connector
from pacasam.samplers.sampler import SAMPLER_COLNAME, SPLIT_COLNAME, SPLIT_POSSIBLE_VALUES

TEST_COLNAME_IN_LIPAC = "test"


class GeopandasConnector(Connector):
    def __init__(self, log: logging.Logger, gpd_database_path: Path, split: SPLIT_POSSIBLE_VALUES):
        """Connector to interface with any geopandas-compatible file.

        Args:
            log (logging.Logger): shared logger
            gpd_database_path (Path): path to file to connect to (e.g. geopackage file).
            split (str): Unused. For compatibility with other samplers only.

        """

        super().__init__(log=log)
        self.gpd_database_path = Path(gpd_database_path).resolve()
        self._db = None
        self._db = self.filter_lipac_patches_on_split(
            db=self.db,
            test_colname=TEST_COLNAME_IN_LIPAC,
            desired_split=split,
        )

    @property
    def db(self):
        if self._db is None:
            self._db = gpd.read_file(self.gpd_database_path)
            # Those two columns are present if we read from a sampling (in particular: from the output of CopySampler).
            # We need to drop them to avoid conflicts when sampling again.
            
            self._db = self._db.drop(columns=[SPLIT_COLNAME, SAMPLER_COLNAME], errors="ignore")
        return self._db

    def filter_lipac_patches_on_split(self, db: GeoDataFrame, test_colname: str, desired_split: SPLIT_POSSIBLE_VALUES):
        """Filter patches based on the desired split.

        Parameters
        ----------
        db : GeoDataFrame
            The input GeoDataFrame containing the patches to filter.
        split_colname : str
            The name of the column containing the split information.
            It contains True for test patches, and False or None for other patches.
        desired_split : SPLIT_TYPE
            The desired split type to filter patches. Valid options are 'train', 'test', or 'any'.

        Returns
        -------
        GeoDataFrame
            The filtered GeoDataFrame containing the patches matching the desired split.

        Raises
        ------
        ValueError
            If an invalid desired split is provided.

        Notes
        -----
        Following the Lipac design, this function assumes that NaN values in the split column correspond
        to non-test (and therefore train) samples.

        """
        if desired_split == "any":
            return db
        if desired_split == "test":
            return db[db[test_colname] == True]  # noqa
        if desired_split == "train":
            return db[db[test_colname].isna() | (db[test_colname] == False)]  # noqa
        else:
            raise ValueError(f"Invalid desired split: `{desired_split}`. Choose among `train`, `test`, or `any`.")
