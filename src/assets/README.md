# Dashboard assets

Crop photos are bundled locally so the dashboard makes no image requests at
runtime. Each is a real photograph of that crop, cropped to a 320 × 320 square
with the crop centred, so every zone card and directory tile is framed the same way.

| File | Zone | Source | Author | Licence |
|---|---|---|---|---|
| `tomato.jpg` | Tomatoes | [Unsplash photo-1592841200221](https://images.unsplash.com/photo-1592841200221-a6898f307baa) | Unsplash contributor | Unsplash License |
| `lettuce.jpg` | Lettuce | [Unsplash photo-1622206151226](https://images.unsplash.com/photo-1622206151226-18ca2c9ab4a1) | Unsplash contributor | Unsplash License |
| `seedling.jpg` | Seedlings | [CeRDI AgReFed](https://www.cerdi.edu.au/cb_pages/images/StockSnap_FSKMJDOOMB-8MB-927x400.jpg) (StockSnap) | StockSnap contributor | CC0 (StockSnap) |
| `cucumber.jpg` | Cucumber | [Wikimedia Commons: Greek yoghurt cucumbers garlic.jpg](https://commons.wikimedia.org/wiki/File:Greek_yoghurt_cucumbers_garlic.jpg) | Nikodem Nijaki | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| `carrot.jpg` | Carrot | [Wikimedia Commons: Organic Carrots (Unsplash).jpg](https://commons.wikimedia.org/wiki/File:Organic_Carrots_(Unsplash).jpg) | Harshal Hirve | CC0 |
| `corn.jpg` | Corn | [Wikimedia Commons: CORN HARVEST close up of ear](https://commons.wikimedia.org/wiki/File:CORN_HARVEST_close_up_of_ear_(48980552538).jpg) | Alabama Extension | CC0 |
| `onion.jpg` | Onions | [Wikimedia Commons: Red Onion on White.JPG](https://commons.wikimedia.org/wiki/File:Red_Onion_on_White.JPG) | Colin | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| `watermelon.jpg` | Watermelon | [Wikimedia Commons: Sliced Watermelon.jpg](https://commons.wikimedia.org/wiki/File:Sliced_Watermelon.jpg) | Harsha K R | [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/) |
| `cabbage.jpg` | Cabbage | [Wikimedia Commons: Cabbage in a stack.jpg](https://commons.wikimedia.org/wiki/File:Cabbage_in_a_stack.jpg) | Jeffery Martin | CC0 |
| `sensor.jpg` | Sensor devices (e.g. Device GH-SENSOR-01) | [Wikimedia Commons: Worms and larvae next to a soil sensor.jpg](https://commons.wikimedia.org/wiki/File:Worms_and_larvae_next_to_a_soil_sensor.jpg) | Neb | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| `generic.jpg` | Unconfigured sources | [Unsplash photo-1416879595882](https://images.unsplash.com/photo-1416879595882-3373a0480b5b) | Unsplash contributor | Unsplash License |

The only change to each photo is a square crop and resize. The CC BY-SA crops are
shared under the same licence as their originals.

Icons and sparklines are generated as SVG data images by `dashboard_ui.py`.
`dashboard.css` adds the reference styling and responsive breakpoints.
