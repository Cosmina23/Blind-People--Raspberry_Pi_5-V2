
import folium

def salveaza_harta(graf, ruta, extra_points=None):
    noduri = [(graf.nodes[n]['y'], graf.nodes[n]['x']) for n in ruta]
    m = folium.Map(location=noduri[0], zoom_start=15)
    folium.PolyLine(noduri, color='blue', weight=5).add_to(m)
    folium.Marker(noduri[0], tooltip='Start').add_to(m)
    folium.Marker(noduri[-1], tooltip='Finish').add_to(m)
    if extra_points:
        for idx, pt in enumerate(extra_points):
            folium.Marker(pt, tooltip=f'Oprire {idx+1}', icon=folium.Icon(color='green')).add_to(m)
    m.save('maps.html')

