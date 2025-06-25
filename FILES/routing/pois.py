from pyrosm import OSM
from geopy.distance import geodesic
import osmnx as ox

def scor_calitate(row):
    scor = 0
    if isinstance(row.get("name"), str) and len(row["name"]) > 2:
        scor += 1
    if isinstance(row.get("tags"), dict) and "brand" in row["tags"]:
        scor += 1
    return scor


#POI = PUNCTE DE INTERES DIN TRASEU                 
async def cauta_poi(traseu_coord, categorie_poi):
    try:
        lat_min = min(p[0] for p in traseu_coord)
        lng_min = min(p[1] for p in traseu_coord)
        lat_max = max(p[0] for p in traseu_coord)
        lng_max = max(p[1] for p in traseu_coord)

        g = ox.graph_from_bbox(lat_max, lat_min, lng_max, lng_min, network_type='walk')
        pois = ox.features_from_bbox(lat_max, lat_min, lng_max, lng_min, tags={"amenity": categorie_poi})

        if pois.empty:
            return None 
        
        #gasire cel mai apropiat poi de traseu 
        ruta_points = [(lat,lng) for lat,lng in traseu_coord]
        min_dist = float("inf")
        clossest = None 

        for _, row in pois.iterrows():
            poi_point = (row.geometry.y, row.geometry.x)
            for coord in ruta_points:
                dist = ox.distance.great_circle_vec(coord[0], coord[1], poi_point[0], poi_point[1])
                if dist < min_dist:
                    min_dist = dist
                    clossest = poi_point
        return clossest
    
    except Exception as e:
        print(f'[POI] Eroare la cautare poi: {e}')
        return None 


def dist_minim_fata_de_traseu(start, end, coordonate_traseu, row):
    loc = (row["lat"], row["lon"])
    if coordonate_traseu:
        return min(geodesic(loc, start).meters for punct in coordonate_traseu)
    else:
        return min(geodesic(loc, start).meters, geodesic(loc, end).meters)

def gaseste_puncte_pe_traseu(start, end, nume_pbf, categorie="pharmacy", max_rezultate=3, coordonate_traseu = None):
    try:
        osm = OSM(nume_pbf)
        if categorie == "supermarket":
            pois = osm.get_pois(custom_filter={
                "amenity": ["supermarket"],
                "shop": ["supermarket", "convenience"]
            })
        elif categorie == "pharmacy":
            pois = osm.get_pois(custom_filter={
                "amenity": ["pharmacy"],
                "healthcare": ["pharmacy"]
            })
        elif categorie == "cafe":
            pois = osm.get_pois(custom_filter={
                "amenity": ["cafe"]
            })
        elif categorie == "restaurant":
            pois = osm.get_pois(custom_filter={
                "amenity": ["restaurant"]
            })
        elif categorie == "fuel":
            pois = osm.get_pois(custom_filter={
                "amenity": ["fuel"]
            })
        else:
            pois = osm.get_pois(custom_filter={"amenity": [categorie]})



        if pois is None or pois.empty:
            print(f"[INFO] Nu am găsit POI-uri pentru categoria: {categorie}")
            return []

        pois_valid = pois.dropna(subset=["geometry"])

        
        if "name" in pois_valid.columns:
            pois_valid = pois_valid[~pois_valid["name"].str.lower().str.contains("spital", na=False)]
        if "tags" in pois_valid.columns:
            pois_valid = pois_valid[~pois_valid["tags"].astype(str).str.contains("hospital", case=False, na=False)]

        
        pois_valid = pois_valid.to_crs(epsg=3857)

        
        pois_valid["geometry"] = pois_valid["geometry"].centroid

        
        pois_valid = pois_valid.to_crs(epsg=4326)
        
        pois_valid["lat"] = pois_valid.geometry.y
        pois_valid["lon"] = pois_valid.geometry.x

        # pois_valid["scor"] = pois_valid.apply(scor_calitate, axis=1)


        pois_valid["dist_traseu"] = pois_valid.apply( lambda row: dist_minim_fata_de_traseu(start, end, coordonate_traseu, row), axis=1)

        
        pois_valid = pois_valid.sort_values(by=["dist_traseu"], ascending=[True])

        coord_pois = pois_valid[["lat", "lon"]].values.tolist()
        return coord_pois[:max_rezultate]

    except Exception as e:
        print(f"[EROARE] {e}")
        return []

# if __name__ == "__main__":
#     start = (45.7575, 21.2294)
#     end = (45.7489, 21.2087)
#     categorie = "pharmacy"
#     pbf_file = "/home/cosmina/Documente/Proiect1/timisoara.osm.pbf"

#     rezultate = gaseste_puncte_pe_traseu(start, end, pbf_file, categorie)
#     for idx, (lat, lon) in enumerate(rezultate, 1):
#         print(f"{idx}. POI {categorie} la coordonate: {lat}, {lon}")
