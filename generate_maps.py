import geopandas as gpd
import matplotlib as plt
import numpy as np
import pandas as pd
from matplotlib import pyplot
from shapely.geometry import Polygon
import matplotlib.pyplot
import geoplot


def get_data(n):
    data = pd.read_csv('Predicted_densities.csv')
    data = data.drop(['estimated_mass', 'estimated_pop'], axis=1)
    data = data[data.binomial != 'Sus scrofa']
    data = data[data.binomial != 'Ursus maritimus']
    data = data.assign(total_mass=data.AdultBodyMassG * data.pop_density * data.Range)
    data = data.sort_values(by='total_mass', ascending=False)
    data = data.iloc[0:n - 1]
    geo_data = gpd.read_file('TERRESTRIAL_MAMMALS/TERRESTRIAL_MAMMALS.shp')
    geo_data = geo_data[geo_data.category != 'EX']
    geo_data = geo_data[geo_data.binomial != 'Sus scrofa']
    range_polygons = geo_data.loc[(geo_data['legend'] == 'Extant & Introduced (resident)') |
                                  (geo_data['legend'] == 'Extant & Origin Uncertain (resident)') |
                                  (geo_data['legend'] == 'Extant & Reintroduced (resident)') |
                                  (geo_data['legend'] == 'Extant & Vagrant (seasonality uncertain)') |
                                  (geo_data['legend'] == 'Extant (non breeding)') |
                                  (geo_data['legend'] == 'Extant (resident)') |
                                  (geo_data['legend'] == 'Probably Extant & Origin Uncertain (resident)') |
                                  (geo_data['legend'] == 'Probably Extant (resident)') |
                                  (geo_data['legend'] == 'Reintroduced')]
    range_polygons = range_polygons.merge(data, on='binomial')
    range_polygons = range_polygons.to_crs("EPSG:6933")
    return range_polygons


def get_continent_data():
    world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
    continents = world.dissolve(by='continent').drop('Antarctica', axis=0)
    continents = continents.to_crs("EPSG:6933")
    return continents


def gen_grid(delta):
    outline = get_continent_data()
    xmin, ymin, xmax, ymax = outline.total_bounds
    dx, dy = delta
    xgrid, ygrid = np.meshgrid(np.arange(xmin, xmax, dx), np.arange(ymin, ymax, dy))
    xgrid, ygrid = xgrid.flatten(), ygrid.flatten()
    grid = gpd.GeoDataFrame(geometry=([Polygon([
        [x - dx, y - dy],
        [x - dx, y],
        [x, y],
        [x, y - dy]]) for x, y in zip(xgrid, ygrid)
    ]), crs=outline.crs)

    grid_clip = gpd.clip(grid, outline).reset_index(drop=True)
    grid_clip = grid_clip[grid_clip.geom_type != 'LineString']
    grid_clip = grid_clip[grid_clip.geom_type != 'Point']
    grid_clip = grid_clip[grid_clip.geom_type != 'MultiLineString']
    grid_clip['grid_index'] = grid_clip.index
    grid_clip.grid_index = grid_clip['grid_index'].apply(str)
    return grid_clip


def overlay_and_sum(num_of_species, delta=(300000, 300000)):
    geo_data = get_data(num_of_species)
    grid = gen_grid(delta)
    inter = gpd.overlay(geo_data, grid, how='union')
    inter = inter.assign(area_km_2=inter.geometry.area * 10 ** (-6))
    inter = inter.assign(population=inter.pop_density * inter.area_km_2)
    inter = inter.assign(total_mass=inter.population * inter.AdultBodyMassG)
    inter_grouped = inter.groupby(['grid_index']).sum()
    inter_grouped = inter_grouped.merge(grid, on='grid_index')
    inter_grouped = gpd.GeoDataFrame(inter_grouped)
    inter_grouped = inter_grouped.assign(total_mass_Mt=inter_grouped.total_mass * 10 ** (-12))
    return inter_grouped


def gen_grid_plot(gridded_data):
    continents_polygon = gpd.GeoDataFrame(get_continent_data().unary_union).rename(columns={0: "geometry"})
    plt.rcParams["figure.figsize"] = (30, 10)
    font = {'weight': 'normal',
            'size': 22}
    plt.rc('font', **font)
    fig, ax = pyplot.subplots(1, 1)
    ax.set_title('Mammal mass [Mt]')
    ax.axis('off')
    base = gridded_data.plot(column='total_mass_Mt', ax=ax, legend=True, cmap='magma')
    continents_polygon.plot(ax=base, fc='none', ec='indigo', linewidth=0.3)

    return type(base)
#
# fig.savefig("inter_2pt5_indigo.jpg")
# inter_grouped[['pop_density','area_km_2','geometry','total_mass_Mt']].to_file("inter_2pt5.shp")
