# BlockAssist Structure Catalog

This directory contains the structures that are selected from. They are grouped into `train` and `test` subsets and are selected automatically at runtime. Difficulty is an informal guide to relative effort/size.

## Train set (12 incl. legacy)
| Name | Difficulty | Size (H×W×D) | Description |
| --- | --- | --- | --- |
| treehouse_platform | Easy | 9×9×9 | Log trunk with a raised plank deck and railing. |
| river_hut | Easy | 6×7×7 | Compact stilted hut with simple glazing. |
| hill_bunker | Medium | 5×9×7 | Low-profile stonebrick shell with endstone cap. |
| glass_greenhouse | Medium | 6×10×8 | Log-framed glass walls and roof. |
| oak_cottage | Medium | 7×9×9 | Cozy plank-and-log box with windows. |
| library_pavilion | Medium | 7×11×7 | Stonebrick frame with glass frontage. |
| cliffside_base | Medium-Hard | 8×8×10 | Tiered stone walls with plank roof layers. |
| desert_shrine | Medium-Hard | 7×9×9 | Endstone shell with yellow accents. |
| stone_watchtower | Medium-Hard | 10×7×7 | Tall stonebrick tower with battlements. |
| frost_keep | Hard | 9×9×9 | Stonebrick keep with blue banding and roof slab. |
| modern_loft | Hard | 8×12×10 | Glass-heavy loft with plank top. |
| workdir.2018-08-10-20:57:24.ip-172-31-0-48 | Legacy | 7×15×15 | Original bundled structure. |

## Test set (4 incl. legacy)
| Name | Difficulty | Size (H×W×D) | Description |
| --- | --- | --- | --- |
| observatory_dome | Medium | 9×11×11 | Stone base with a glass dome. |
| orchard_yard | Hard | 6×14×14 | Planter grid with small “trees”. |
| harbor_warehouse | Hard | 7×8×16 | Long timber storage bay with beam supports. |
| workdir.2018-08-18-01:46:43.ip-172-31-12-95 | Legacy | 14×11×14 | Original bundled structure. |

To lock to a specific build, set a local environment variable called `BA_HOUSE_ID` to the name of the structure you'd like to build; otherwise selection is randomized within the subset.
