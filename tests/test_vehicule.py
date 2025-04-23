from route_planner.vehicule import Vehicule

def test_creation_vehicule():
    v = Vehicule(type_transport='drive', consommation_l_km=0.05, cout_energie=1.9)
    assert v.type_transport == 'drive'
    assert v.consommation_l_km == 0.05
    assert v.cout_energie == 1.9
