# BlockAssist Structure Catalog

This directory contains the structures that are selected from. They are grouped into `train` and `test` subsets and are selected automatically at runtime. Difficulty is an informal guide to relative effort/size.

## Train set (16 incl. legacy)
| Name | Difficulty | Size (H×W×D) | Style / Notes |
| --- | --- | --- | --- |
| arch_bridge | Easy | 4×5×13 | Small wooden walkway with a gentle arch. |
| lakeside_pier | Easy | 5×4×12 | Narrow dock on log supports. |
| market_stall | Easy | 5×7×5 | Tiny booth with striped wool canopy. |
| treehouse_platform | Easy | 9×9×9 | Log trunk with a raised plank deck and railing. |
| river_hut | Easy | 6×7×7 | Compact stilted hut with simple glazing. |
| garden_gazebo | Medium | 6×9×9 | Open log columns, wool floor, layered roof. |
| hill_bunker | Medium | 5×9×7 | Low-profile stonebrick shell with endstone cap. |
| glass_greenhouse | Medium | 6×10×8 | Log-framed glass walls and roof. |
| oak_cottage | Medium | 7×9×9 | Cozy plank-and-log box with windows. |
| library_pavilion | Medium | 7×11×7 | Stonebrick frame with glass frontage. |
| cliffside_base | Medium-Hard | 8×8×10 | Tiered stone walls with plank roof layers. |
| desert_shrine | Medium-Hard | 7×9×9 | Endstone shell with yellow accents. |
| spruce_longhouse | Medium-Hard | 6×6×14 | Long beam-supported hall with clerestory glass. |
| stone_watchtower | Medium-Hard | 10×7×7 | Tall stonebrick tower with battlements. |
| frost_keep | Hard | 9×9×9 | Stonebrick keep with blue banding and roof slab. |
| workdir.2018-08-10-20:57:24.ip-172-31-0-48 | Legacy | 7×15×15 | Original bundled structure. |

## Test set (6 incl. legacy)
| Name | Difficulty | Size (H×W×D) | Style / Notes |
| --- | --- | --- | --- |
| observatory_dome | Medium | 9×11×11 | Stone base with a glass dome. |
| spiral_tower | Hard | 12×7×7 | Stone tower with interior spiral path. |
| orchard_yard | Hard | 6×14×14 | Planter grid with small “trees”. |
| harbor_warehouse | Hard | 7×8×16 | Long timber storage bay with beam supports. |
| modern_loft | Hard | 8×12×10 | Glass-heavy loft with plank top. |
| workdir.2018-08-18-01:46:43.ip-172-31-12-95 | Legacy | 14×11×14 | Original bundled structure. |

To lock to a specific build, set `house_id` in the goal generator config; otherwise selection is randomized within the subset.
