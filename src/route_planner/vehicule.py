from dataclasses import dataclass


@dataclass
class Vehicule:
    type_transport: str
    consommation_l_km: float = 0
    cout_energie: float = 0
    co2_kg_par_litre: float = 2.31
    co2_kg_par_km_bike: float = 0.0
    co2_kg_par_km_walk: float = 0.0

    def __post_init__(self):
        if self.type_transport not in {"drive", "bike", "walk"}:
            raise ValueError(f"Mode de transport invalide: {self.type_transport}")
        if self.consommation_l_km < 0:
            raise ValueError("La consommation ne peut pas etre negative")
        if self.cout_energie < 0:
            raise ValueError("Le cout de l'energie ne peut pas etre negatif")
        if self.co2_kg_par_litre < 0:
            raise ValueError("Le facteur CO2 ne peut pas etre negatif")
