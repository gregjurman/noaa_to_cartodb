from qgis.core import *
import requests
from uuid import uuid4
from sh import unzip, rm
from shapely.wkb import loads as wkb_loads
from shapely.wkt import dumps as wkt_dumps

from cartodb import CartoDBAPIKey, CartoDBException
from config import API_KEY, cartodb_domain


layer_map = {
        "TOR": "Tornado Warning",
        "SVR": "Severe Thunderstorm Warning",
        "FFW": "Flash Flood Warning",
        "SMW": "Special Marine Warning",
        }


def incr_gen():
    i = 1
    while True:
        yield i
        i = i + 1

layer_index = incr_gen()


def get_shapefiles():
    print "Getting new NOAA shapefiles..."
    r = requests.get("http://www.nws.noaa.gov/regsci/gis/shapefiles/current_warnings.zip")
    file_name = str(uuid4())
    with open("/tmp/%s.zip" %file_name, "wb") as out_file:
        out_file.write(r.content)

    return file_name


def cstor_qgis():
    print "Initializing QGIS..."
    QgsApplication.setPrefixPath("/usr", True)
    QgsApplication.initQgis()


def dstor_qgis():
    print "Stopping QGIS..."
    QgsApplication.exitQgis()


def extract_shapefiles(in_file):
    print "Extracting shapefiles..."
    unzip( "-d", "/tmp/%s" % in_file, "/tmp/%s.zip" % in_file)

    return "/tmp/%s" % in_file


def import_shapefile(in_dir, file_name):
    print "Importing %s (%s)..." % (k, "%s/%s" % (in_dir, file_name))
    layer = QgsVectorLayer("%s/%s" % (in_dir, file_name), "layer_%i" % layer_index.next(), "ogr")
    if not layer.isValid:
        raise Exception("Layer is not valid for file %s" % file_name)
    QgsMapLayerRegistry.instance().addMapLayer(layer)

    return layer


def remove_temp(in_dir):
    print "Deleting temp files.."
    rm("-rf", in_dir)
    rm("%s.zip" % in_dir)


def flush_and_transmit(features):
    print "Connecting to CartoDB..."
    cl = CartoDBAPIKey(API_KEY, cartodb_domain)

    try:
        print "Clearing old feature set..."
        cl.sql("TRUNCATE TABLE warning_geom;")

        print "Inserting new features..."
        for feat in features:
            cl.sql("INSERT INTO warning_geom (name, description, the_geom) VALUES ('%s','%s', ST_SetSRID(ST_GeometryFromText('%s'), 4326))" % (feat['key'], feat['desc'], feat['wkt']))
    except CartoDBException as e:
        print ("some error ocurred", e)


if __name__ == "__main__":
    file_id = get_shapefiles()
    cstor_qgis()

    dir_out = extract_shapefiles(file_id)

    layers = []

    for k in layer_map.keys():
        layers.append(import_shapefile(dir_out, "%s.shp" % k))

    features = []

    for layer, key in zip(layers, layer_map.keys()):
        print "    Features: %i" % layer.featureCount()
        provider = layer.dataProvider()
        allAttrs = provider.attributeIndexes()

        # start data retreival: fetch geometry and all attributes for each feature
        provider.select(allAttrs)

        feat = QgsFeature()

        while provider.nextFeature(feat):

              # fetch geometry
                geom = feat.geometry()
                print "        Feature ID: %s" % feat.id()
                features.append(
                    dict(
                        wkt=wkt_dumps(wkb_loads(geom.asWkb())),
                        key=key,
                        desc=layer_map[key]
                    )
                )


    print "Total features: %i" % len(features)

    flush_and_transmit(features)

    dstor_qgis()
    remove_temp(dir_out)
