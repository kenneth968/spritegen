"""Mycomed TD Tower Evolution Chains.

This module defines the tower evolution chains for Mycomed TD,
providing the sprite generation prompts for each evolution stage.

Tower Types and Evolution Chains:
- Puffball: Spore cloud area damage
- Cordyceps: Mind control / slow effect
- Amanita: Poison damage over time
- Chanterelle: Economy boost
- Mycelium: Buffs neighboring towers
"""

from dataclasses import dataclass
from typing import Literal

from .style import StyleManager
from .generator import create_mycomed_style


EVOLUTION_STAGES = {
    "slime_enemy": [
        {
            "name": "Slime Larva",
            "prompt": "tiny slime creature, translucent green blob, single eye, simple game enemy sprite, pixel art style",
            "count": 4,
        },
        {
            "name": "Slime Juvenile",
            "prompt": "young slime monster, larger translucent green body, two eyes, slightly more defined shape, game enemy sprite",
            "count": 4,
        },
        {
            "name": "Slime Mature",
            "prompt": "mature slime creature, big translucent green body, multiple eyes, jiggly appearance, slime trail, game enemy sprite",
            "count": 4,
        },
        {
            "name": "Slime Alpha",
            "prompt": "massive alpha slime, enormous translucent green body, glowing eyes, corrosive aura, slime pool underneath, boss enemy sprite",
            "count": 4,
        },
    ],
    "puffball": [
        {
            "name": "Puffball Sprout",
            "prompt": "tiny mushroom sprout, pale white cap, single small puffball, early growth stage, small and delicate, game sprite",
            "count": 4,
        },
        {
            "name": "Puffball Juvenile",
            "prompt": "young puffball mushroom, larger white spherical cap, slight spore clouds forming, game sprite, RPG element",
            "count": 4,
        },
        {
            "name": "Puffball Mature",
            "prompt": "mature puffball mushroom, full white spherical cap with visible spores, mushroom cloud forming above, powerful, game sprite",
            "count": 4,
        },
        {
            "name": "Puffball Ultimate",
            "prompt": "massive cosmic puffball mushroom, glowing ethereal cap, large spore cloud explosion, bioluminescent, ultimate evolution, game sprite, tower defense",
            "count": 4,
        },
    ],
    "cordyceps": [
        {
            "name": "Cordyceps Spore",
            "prompt": "tiny cordyceps spore, just germinated, small orange glow, parasitic mushroom start, game sprite",
            "count": 4,
        },
        {
            "name": "Cordyceps Growth",
            "prompt": "young cordyceps, orange fungal tendrils spreading, mind control energy aura visible, insect host visible, game sprite",
            "count": 4,
        },
        {
            "name": "Cordyceps Mature",
            "prompt": "mature cordyceps, fully developed orange parasitic mushroom, glowing mind control waves, insect host consumed, powerful ability effects, game sprite",
            "count": 4,
        },
        {
            "name": "Cordyceps Ultimate",
            "prompt": "cosmic cordyceps, massive ethereal fungal network, universal mind control aura, glowing orange and purple, ultimate parasitic power, game sprite",
            "count": 4,
        },
    ],
    "amanita": [
        {
            "name": "Amanita Sprout",
            "prompt": "tiny amanita mushroom sprout, red cap with white spots emerging, toxic appearance beginning, delicate, game sprite",
            "count": 4,
        },
        {
            "name": "Amanita Juvenile",
            "prompt": "young amanita mushroom, bright red cap with white warts, poison droplets forming, toxic aura beginning, game sprite",
            "count": 4,
        },
        {
            "name": "Amanita Mature",
            "prompt": "mature amanita muscaria, iconic red and white spotted cap, poison cloud effect, toxic aura strong, dangerous looking, game sprite",
            "count": 4,
        },
        {
            "name": "Amanita Ultimate",
            "prompt": "mega amanita, massive glowing red and gold cap, poison explosion effect, toxic death aura, ultimate poison tower, epic game sprite",
            "count": 4,
        },
    ],
    "chanterelle": [
        {
            "name": "Chanterelle Sprout",
            "prompt": "tiny chanterelle mushroom sprout, small yellow-orange funnel shape emerging from soil, delicate frilly edges, game sprite",
            "count": 4,
        },
        {
            "name": "Chanterelle Juvenile",
            "prompt": "young chanterelle, golden-yellow funnel mushroom, wavy cap edges, faint golden glow, economic boost aura beginning, game sprite",
            "count": 4,
        },
        {
            "name": "Chanterelle Mature",
            "prompt": "mature chanterelle, iconic golden-yellow funnel shape, pronounced wavy frilly edges, golden coin generation aura visible, game sprite",
            "count": 4,
        },
        {
            "name": "Chanterelle Ultimate",
            "prompt": "cosmic chanterelle, massive glowing golden mushroom, golden coin explosion effect, ultimate economic power, wealth aura radiating, legendary game sprite",
            "count": 4,
        },
    ],
}


@dataclass
class EvolutionChain:
    tower_id: str
    name: str
    species: str
    stages: list[dict]


def get_evolution_chain(tower_id: str) -> EvolutionChain | None:
    if tower_id not in EVOLUTION_STAGES:
        return None

    stage_data = EVOLUTION_STAGES[tower_id]
    return EvolutionChain(
        tower_id=tower_id,
        name=stage_data[0]["name"].split()[0],
        species=tower_id,
        stages=stage_data,
    )


def get_all_tower_ids() -> list[str]:
    return list(EVOLUTION_STAGES.keys())


def setup_mycomed_style(style_dir: str | None = None) -> None:
    manager = StyleManager(style_dir=style_dir)
    if not manager.exists("mycomed_towers"):
        create_mycomed_style(manager)
        print("Created mycomed_towers style")
    else:
        print("mycomed_towers style already exists")


if __name__ == "__main__":
    print("Available tower evolution chains:")
    for tower_id in get_all_tower_ids():
        chain = get_evolution_chain(tower_id)
        print(f"  - {tower_id}: {len(chain.stages)} stages")
