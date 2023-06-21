import geopandas as gpd
from pacasam.samplers.sampler import Sampler


class CopySampler(Sampler):
    """Copier - a sampler to make a full copy of the database."""

    def get_patches(self) -> gpd.GeoDataFrame:
        patches = self.connector.request_all_patches()
        patches["sampler"] = self.name
        patches["split"] = None
        return patches[self.sampling_schema]
