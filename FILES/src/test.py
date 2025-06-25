from navigator_maps import obtine_ruta_standard
from geopy.distance import geodesic
import folium

def salveaza_harta_din_coord(coordonate, nume_fisier="timisoara.html"):
    if not coordonate:
        print("Lista de coordonate e goală.")
        return

    m = folium.Map(location=coordonate[0], zoom_start=15)
    folium.PolyLine(coordonate, color='blue', weight=5).add_to(m)
    folium.Marker(coordonate[0], tooltip="Start", icon=folium.Icon(color='green')).add_to(m)
    folium.Marker(coordonate[-1], tooltip="Finish", icon=folium.Icon(color='red')).add_to(m)
    m.save(nume_fisier)
    print(f"Harta salvată în fișierul: {nume_fisier}")


start = (45.71891, 21.25856)  
end = (45.7246, 21.256)  
ruta, durata = obtine_ruta_standard(start, end)

# Calculează distanța totală în km
dist_km = sum(
    geodesic(ruta[i], ruta[i + 1]).kilometers
    for i in range(len(ruta) - 1)
)

print("\n=== Informații traseu ===")
print(f"Număr noduri: {len(ruta)}")
print(f"Distanță totală: {dist_km:.2f} km")
print(f"Durată estimată: {durata} minute")

# Opțional: afisează nodurile
# for lat, lon in ruta:
#     print(f" - {lat}, {lon}")

salveaza_harta_din_coord(ruta, "timisoara_b.html")