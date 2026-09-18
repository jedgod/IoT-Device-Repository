# Dashboard assets

Crop thumbnails are bundled locally so the dashboard does not make image requests
at runtime. Source: Unsplash image service, downloaded for the reference design.

- Tomato: https://images.unsplash.com/photo-1592841200221-a6898f307baa
- Lettuce: https://images.unsplash.com/photo-1622206151226-18ca2c9ab4a1
- Seedling / gardening: https://images.unsplash.com/photo-1416879595882-3373a0480b5b

Icons and sparklines are generated as SVG data images by `dashboard_ui.py`.
`dashboard.css` adds the requested reference styling and responsive breakpoints.
