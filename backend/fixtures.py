"""
Deterministic HTML & JSON fixtures representing Shopify, Myntra, and AJIO product pages
for automated unit tests and authentic offline/WAF-resilient verification.
"""

from __future__ import annotations
from typing import Any, Dict

IMG_OXFORD_FRONT = "/src/assets/images/myntra_oxford_shirt_front_1794577925898.jpg"
IMG_OXFORD_DETAIL = "/src/assets/images/myntra_oxford_shirt_detail_1794577928205.jpg"
IMG_BLAZER_FRONT = "/src/assets/images/ajio_linen_blazer_front_1794577929144.jpg"
IMG_TROUSERS_FRONT = "/src/assets/images/ajio_pleated_trousers_front_1794577929936.jpg"

SHOPIFY_TAYLOR_STITCH_STOREFRONT_JSON: Dict[str, Any] = {
    "product": {
        "id": 8910234567890,
        "title": "The Glacier Shirt in Topsoil Corded Denim",
        "handle": "glacier-shirt-in-topsoil-corded-denim-2610",
        "vendor": "Taylor Stitch",
        "product_type": "Wovens",
        "tags": "Category: Long Sleeves, Color:Brown, Construction: Denim, Fit: Tailored",
        "body_html": "<p>Crafted from 8-oz 100% organic corded cotton denim with double needle felled construction and vintage brass snaps.</p>",
        "images": [
            {"src": "https://www.taylorstitch.com/cdn/shop/files/glacier_shirt_01.jpg"},
            {"src": "https://www.taylorstitch.com/cdn/shop/files/glacier_shirt_02.jpg"},
        ],
        "variants": [
            {"id": 40101, "title": "XS - 36", "option1": "XS - 36", "price": "168.00", "compare_at_price": "198.00", "sku": "2610GSTCD36", "available": True},
            {"id": 40102, "title": "S - 38", "option1": "S - 38", "price": "168.00", "compare_at_price": "198.00", "sku": "2610GSTCD38", "available": True},
            {"id": 40103, "title": "M - 40", "option1": "M - 40", "price": "168.00", "compare_at_price": "198.00", "sku": "2610GSTCD40", "available": True},
            {"id": 40104, "title": "L - 42", "option1": "L - 42", "price": "168.00", "compare_at_price": "198.00", "sku": "2610GSTCD42", "available": True},
            {"id": 40105, "title": "XL - 44", "option1": "XL - 44", "price": "168.00", "compare_at_price": "198.00", "sku": "2610GSTCD44", "available": False},
        ],
    }
}

SHOPIFY_TAYLOR_STITCH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>The Glacier Shirt in Topsoil Corded Denim | Taylor Stitch</title>
  <meta property="og:title" content="The Glacier Shirt in Topsoil Corded Denim" />
  <meta property="og:description" content="Crafted from 8-oz 100% organic corded cotton denim with double needle felled construction and custom YKK western snaps." />
  <meta property="og:image" content="https://www.taylorstitch.com/cdn/shop/files/glacier_shirt_01.jpg" />
  <meta property="og:price:amount" content="168.00" />
  <meta property="og:price:currency" content="USD" />
  <script type="application/ld+json">
  {
    "@context": "http://schema.org",
    "@type": "ProductGroup",
    "name": "The Glacier Shirt in Topsoil Corded Denim",
    "description": "Crafted from 8-oz 100% organic corded cotton denim with double needle felled construction and custom YKK western snaps.",
    "brand": "Taylor Stitch",
    "image": "https://www.taylorstitch.com/cdn/shop/files/glacier_shirt_01.jpg",
    "hasVariant": [
      {
        "@type": "Product",
        "sku": "2610GSTCD38",
        "size": "S - 38",
        "offers": {
          "@type": "Offer",
          "price": "168.00",
          "priceCurrency": "USD",
          "availability": "http://schema.org/InStock"
        }
      }
    ]
  }
  </script>
</head>
<body>
  <span class="product-vendor">Taylor Stitch</span>
  <h1 class="product-title">The Glacier Shirt in Topsoil Corded Denim</h1>
  <span class="product-price">$168</span>
  <div class="product-description">
    Crafted from 8-oz 100% organic corded cotton denim with double needle felled construction and custom YKK western snaps.
  </div>
  <dialog id="size-guide-dialog" class="dialog dialog--size-guide">
    <div id="size-chart">
      <table class="wovens-sizing">
        <tr><th colspan="6">Garment Size Chart</th></tr>
        <tr>
          <th>Size</th>
          <th>Chest</th>
          <th>Neck</th>
          <th>Shoulder</th>
          <th>Sleeve*</th>
          <th>Length**</th>
        </tr>
        <tr><td>36&thinsp;&ndash;&thinsp;XS</td><td>40</td><td>15&frac12;</td><td>17&frac14;</td><td>33</td><td>28&frac18;</td></tr>
        <tr><td>38&thinsp;&ndash;&thinsp;S</td><td>42</td><td>16</td><td>18</td><td>33&frac34;</td><td>28&frac78;</td></tr>
        <tr><td>40&thinsp;&ndash;&thinsp;M</td><td>44</td><td>16&frac12;</td><td>18&frac34;</td><td>34&frac12;</td><td>29&frac58;</td></tr>
        <tr><td>42&thinsp;&ndash;&thinsp;L</td><td>46</td><td>17</td><td>19&frac12;</td><td>35&frac12;</td><td>30&frac38;</td></tr>
        <tr><td>44&thinsp;&ndash;&thinsp;XL</td><td>49</td><td>17&frac12;</td><td>20&frac12;</td><td>36&frac58;</td><td>31&frac18;</td></tr>
      </table>
    </div>
  </dialog>
</body>
</html>
"""

MYNTRA_OXFORD_SHIRT_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Buy Ralph Lauren Men Navy Blue Tailored Fit Pure Cotton Oxford Shirt - Shirts for Men 24891024 | Myntra</title>
  <meta property="og:title" content="Buy Ralph Lauren Men Navy Blue Tailored Fit Pure Cotton Oxford Shirt | Myntra" />
  <meta property="og:description" content="Navy blue solid opaque casual Oxford shirt, has a button-down collar, button placket, 1 patch pocket, long regular sleeves, curved hem." />
  <meta property="og:image" content="{IMG_OXFORD_FRONT}" />
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Men Navy Blue Tailored Fit Pure Cotton Oxford Shirt",
    "sku": "24891024",
    "brand": {{ "@type": "Brand", "name": "Polo Ralph Lauren" }},
    "description": "Navy blue solid opaque casual Oxford shirt crafted from 2-ply long-staple combed cotton, featuring a classic button-down collar, mother-of-pearl buttons, single chest patch pocket, and tailored back box pleat.",
    "image": ["{IMG_OXFORD_FRONT}", "{IMG_OXFORD_DETAIL}"],
    "offers": {{
      "@type": "Offer",
      "priceCurrency": "INR",
      "price": "8799",
      "availability": "https://schema.org/InStock"
    }}
  }}
  </script>
  <script>
  window.__myx = {{
    "pdpData": {{
      "id": 24891024,
      "name": "Men Navy Blue Tailored Fit Pure Cotton Oxford Shirt",
      "mrp": 10999,
      "price": {{
        "mrp": 10999,
        "discounted": 8799
      }},
      "discount": {{
        "label": "(20% OFF)",
        "displayLabel": "20% OFF"
      }},
      "brand": {{
        "name": "Polo Ralph Lauren"
      }},
      "gender": "Men",
      "articleType": {{
        "typeName": "Shirts"
      }},
      "analytics": {{
        "masterCategory": "Apparel",
        "subCategory": "Topwear",
        "articleType": "Shirts",
        "gender": "Men"
      }},
      "flags": {{
        "outOfStock": false
      }},
      "offers": [
        {{ "title": "10% Instant Discount on HDFC Bank Credit Cards" }},
        {{ "title": "Complimentary alteration available at select boutiques" }}
      ],
      "productDetails": [
        {{
          "title": "Product Details",
          "description": "Navy blue solid opaque casual Oxford shirt crafted from 2-ply long-staple combed cotton. Features a structured button-down collar, full mother-of-pearl button placket, single chest patch pocket, long sleeves with barrel cuffs, and curved shirttail hem."
        }},
        {{
          "title": "Material & Care",
          "description": "100% Pure Combed Oxford Cotton (165 GSM) · Machine wash cold gentle cycle, warm iron"
        }}
      ],
      "articleAttributes": {{
        "Fit": "Tailored Fit",
        "Collar": "Button-Down Collar",
        "Fabric": "Pure Cotton",
        "Sleeve Length": "Long Sleeves",
        "Pattern": "Solid",
        "Occasion": "Smart Casual",
        "Weave Pattern": "Oxford Basketweave"
      }},
      "media": {{
        "albums": [
          {{
            "name": "default",
            "images": [
              {{ "imageURL": "{IMG_OXFORD_FRONT}", "src": "{IMG_OXFORD_FRONT}" }},
              {{ "imageURL": "{IMG_OXFORD_DETAIL}", "src": "{IMG_OXFORD_DETAIL}" }}
            ]
          }}
        ]
      }},
      "sizes": [
        {{
          "skuId": 880101,
          "label": "38",
          "available": true,
          "sizeSellerData": [{{ "availableCount": 6 }}],
          "measurements": [
            {{ "type": "Chest", "value": "39.5", "unit": "in" }},
            {{ "type": "Shoulder", "value": "17.2", "unit": "in" }},
            {{ "type": "Sleeve Length", "value": "25.0", "unit": "in" }},
            {{ "type": "Front Length", "value": "29.0", "unit": "in" }},
            {{ "type": "Neck", "value": "15.0", "unit": "in" }}
          ]
        }},
        {{
          "skuId": 880102,
          "label": "40",
          "available": true,
          "sizeSellerData": [{{ "availableCount": 14 }}],
          "measurements": [
            {{ "type": "Chest", "value": "41.5", "unit": "in" }},
            {{ "type": "Shoulder", "value": "18.0", "unit": "in" }},
            {{ "type": "Sleeve Length", "value": "25.5", "unit": "in" }},
            {{ "type": "Front Length", "value": "29.8", "unit": "in" }},
            {{ "type": "Neck", "value": "15.75", "unit": "in" }}
          ]
        }},
        {{
          "skuId": 880103,
          "label": "42",
          "available": true,
          "sizeSellerData": [{{ "availableCount": 9 }}],
          "measurements": [
            {{ "type": "Chest", "value": "44.0", "unit": "in" }},
            {{ "type": "Shoulder", "value": "18.8", "unit": "in" }},
            {{ "type": "Sleeve Length", "value": "26.0", "unit": "in" }},
            {{ "type": "Front Length", "value": "30.5", "unit": "in" }},
            {{ "type": "Neck", "value": "16.5", "unit": "in" }}
          ]
        }},
        {{
          "skuId": 880104,
          "label": "44",
          "available": true,
          "sizeSellerData": [{{ "availableCount": 3 }}],
          "measurements": [
            {{ "type": "Chest", "value": "46.5", "unit": "in" }},
            {{ "type": "Shoulder", "value": "19.5", "unit": "in" }},
            {{ "type": "Sleeve Length", "value": "26.5", "unit": "in" }},
            {{ "type": "Front Length", "value": "31.2", "unit": "in" }},
            {{ "type": "Neck", "value": "17.25", "unit": "in" }}
          ]
        }},
        {{
          "skuId": 880105,
          "label": "46",
          "available": false,
          "sizeSellerData": [{{ "availableCount": 0 }}],
          "measurements": [
            {{ "type": "Chest", "value": "49.0", "unit": "in" }},
            {{ "type": "Shoulder", "value": "20.2", "unit": "in" }},
            {{ "type": "Sleeve Length", "value": "27.0", "unit": "in" }},
            {{ "type": "Front Length", "value": "32.0", "unit": "in" }},
            {{ "type": "Neck", "value": "18.0", "unit": "in" }}
          ]
        }}
      ]
    }}
  }};
  </script>
</head>
<body>
  <h1 class="pdp-title">Polo Ralph Lauren</h1>
  <h1 class="pdp-name">Men Navy Blue Tailored Fit Pure Cotton Oxford Shirt</h1>
  <span class="pdp-price">Rs. 8799</span>
</body>
</html>
"""

AJIO_LINEN_BLAZER_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Buy Massimo Dutti Women Sand Beige Single-Breasted Linen Blend Blazer | AJIO</title>
  <meta property="og:title" content="Massimo Dutti Women Sand Beige Single-Breasted Linen Blend Blazer | AJIO" />
  <meta property="og:description" content="Structured single-breasted blazer tailored in European flax linen and viscose blend with notched lapels, horn button closure, and welt pockets." />
  <meta property="og:image" content="{IMG_BLAZER_FRONT}" />
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Women Sand Beige Single-Breasted Linen Blend Tailored Blazer",
    "sku": "469482190_sand",
    "brand": {{ "@type": "Brand", "name": "Massimo Dutti" }},
    "description": "Structured single-breasted blazer tailored in European flax linen and viscose blend with notched lapels, horn button closure, and flap welt pockets.",
    "image": ["{IMG_BLAZER_FRONT}"],
    "offers": {{
      "@type": "Offer",
      "priceCurrency": "INR",
      "price": "9490",
      "highPrice": "12990",
      "availability": "https://schema.org/InStock"
    }}
  }}
  </script>
  <script>
  window.__PRELOADED_STATE__ = {{
    "product": {{
      "productDetails": {{
        "code": "469482190_sand",
        "name": "Women Sand Beige Single-Breasted Linen Blend Tailored Blazer",
        "brandName": "Massimo Dutti",
        "brickName": "Blazers & Waistcoats",
        "brickSubCategory": "Outerwear",
        "brickCategory": "Women",
        "description": "Structured single-breasted blazer tailored from a breathable European flax linen and viscose weave. Designed with classic notched lapels, single horn button fastening, two front flap pockets, and a vented back hem.",
        "discountPercent": 27,
        "price": {{
          "currencyIso": "INR",
          "value": 9490,
          "formattedValue": "Rs. 9,490"
        }},
        "wasPriceData": {{
          "currencyIso": "INR",
          "value": 12990,
          "formattedValue": "Rs. 12,990"
        }},
        "images": [
          {{ "format": "superZoom", "url": "{IMG_BLAZER_FRONT}" }},
          {{ "format": "thumbnail", "url": "{IMG_BLAZER_FRONT}" }}
        ],
        "featureData": [
          {{ "name": "Fabric Composition", "featureValues": [{{ "value": "68% European Linen, 32% Viscose" }}] }},
          {{ "name": "Lining", "featureValues": [{{ "value": "100% Acetate Half-Lined" }}] }},
          {{ "name": "Wash Care", "featureValues": [{{ "value": "Dry clean only" }}] }},
          {{ "name": "Fit", "featureValues": [{{ "value": "Structured Tailored Fit" }}] }}
        ],
        "variantOptions": [
          {{
            "code": "469482190_xs",
            "scDisplaySize": "XS",
            "stock": {{ "stockLevelStatus": "inStock", "stockLevel": 4 }}
          }},
          {{
            "code": "469482190_s",
            "scDisplaySize": "S",
            "stock": {{ "stockLevelStatus": "inStock", "stockLevel": 11 }}
          }},
          {{
            "code": "469482190_m",
            "scDisplaySize": "M",
            "stock": {{ "stockLevelStatus": "inStock", "stockLevel": 8 }}
          }},
          {{
            "code": "469482190_l",
            "scDisplaySize": "L",
            "stock": {{ "stockLevelStatus": "inStock", "stockLevel": 5 }}
          }},
          {{
            "code": "469482190_xl",
            "scDisplaySize": "XL",
            "stock": {{ "stockLevelStatus": "outOfStock", "stockLevel": 0 }}
          }}
        ],
        "sizeGuide": {{
          "unit": "in",
          "measurements": [
            {{ "size": "XS", "chest": 35.0, "shoulder": 14.8, "waist": 31.5, "sleeve": 23.2, "length": 26.5 }},
            {{ "size": "S", "chest": 36.8, "shoulder": 15.3, "waist": 33.0, "sleeve": 23.6, "length": 27.0 }},
            {{ "size": "M", "chest": 38.6, "shoulder": 15.8, "waist": 34.8, "sleeve": 24.0, "length": 27.5 }},
            {{ "size": "L", "chest": 40.8, "shoulder": 16.4, "waist": 37.0, "sleeve": 24.4, "length": 28.0 }},
            {{ "size": "XL", "chest": 43.0, "shoulder": 17.0, "waist": 39.2, "sleeve": 24.8, "length": 28.5 }}
          ]
        }}
      }}
    }}
  }};
  </script>
</head>
<body>
  <h2 class="brand-name">Massimo Dutti</h2>
  <h1 class="prod-name">Women Sand Beige Single-Breasted Linen Blend Tailored Blazer</h1>
  <div class="prod-sp">9490</div>
  <div class="prod-cp">12990</div>
</body>
</html>
"""

AJIO_PLEATED_TROUSERS_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Buy COS Women Charcoal Slate High-Waisted Wide-Leg Pleated Wool Blend Trousers | AJIO</title>
  <meta property="og:title" content="COS Women Charcoal Slate High-Waisted Wide-Leg Pleated Wool Blend Trousers | AJIO" />
  <meta property="og:image" content="{IMG_TROUSERS_FRONT}" />
  <script>
  window.__PRELOADED_STATE__ = {{
    "product": {{
      "productDetails": {{
        "code": "469710338_charcoal",
        "name": "Women Charcoal Slate High-Waisted Wide-Leg Pleated Wool Blend Trousers",
        "brandName": "COS",
        "brickName": "Trousers & Pants",
        "brickSubCategory": "Bottomwear",
        "brickCategory": "Women",
        "description": "Architectural wide-leg tailored trousers crafted from an RWS-certified merino wool blend. Cut with a high-rise waist, double front knife pleats, concealed hook-and-bar closure, and full-length fluid drape.",
        "discountPercent": 15,
        "price": {{
          "currencyIso": "INR",
          "value": 6790
        }},
        "wasPriceData": {{
          "currencyIso": "INR",
          "value": 7990
        }},
        "images": [
          {{ "format": "superZoom", "url": "{IMG_TROUSERS_FRONT}" }}
        ],
        "featureData": [
          {{ "name": "Material", "featureValues": [{{ "value": "54% RWS Merino Wool, 44% Recycled Polyester, 2% Elastane" }}] }},
          {{ "name": "Waist Rise", "featureValues": [{{ "value": "High-Rise" }}] }},
          {{ "name": "Fit", "featureValues": [{{ "value": "Relaxed Wide-Leg Fit" }}] }}
        ],
        "variantOptions": [
          {{ "code": "469710338_28", "scDisplaySize": "28", "stock": {{ "stockLevelStatus": "inStock", "stockLevel": 7 }} }},
          {{ "code": "469710338_30", "scDisplaySize": "30", "stock": {{ "stockLevelStatus": "inStock", "stockLevel": 12 }} }},
          {{ "code": "469710338_32", "scDisplaySize": "32", "stock": {{ "stockLevelStatus": "inStock", "stockLevel": 6 }} }},
          {{ "code": "469710338_34", "scDisplaySize": "34", "stock": {{ "stockLevelStatus": "outOfStock", "stockLevel": 0 }} }}
        ],
        "sizeGuide": {{
          "unit": "in",
          "measurements": [
            {{ "size": "28", "waist": 28.0, "hip": 38.5, "inseam": 30.5, "rise": 11.5, "length": 41.5 }},
            {{ "size": "30", "waist": 30.0, "hip": 40.5, "inseam": 30.8, "rise": 11.8, "length": 42.0 }},
            {{ "size": "32", "waist": 32.0, "hip": 42.5, "inseam": 31.0, "rise": 12.2, "length": 42.5 }},
            {{ "size": "34", "waist": 34.0, "hip": 44.5, "inseam": 31.2, "rise": 12.5, "length": 43.0 }}
          ]
        }}
      }}
    }}
  }};
  </script>
</head>
<body>
  <h2 class="brand-name">COS</h2>
  <h1 class="prod-name">Women Charcoal Slate High-Waisted Wide-Leg Pleated Wool Blend Trousers</h1>
</body>
</html>
"""

JSON_LD_ONLY_MYNTRA_HTML = f"""<!DOCTYPE html>
<html>
<head>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Unisex Classic Heavyweight Cotton Tee",
    "sku": "19002100",
    "brand": {{ "@type": "Brand", "name": "H&M" }},
    "description": "Heavyweight 240 GSM organic cotton jersey t-shirt with dropped shoulders.",
    "image": ["{IMG_OXFORD_FRONT}"],
    "offers": {{
      "@type": "Offer",
      "priceCurrency": "INR",
      "price": "1299",
      "highPrice": "1499",
      "availability": "https://schema.org/InStock"
    }}
  }}
  </script>
</head>
<body></body>
</html>
"""

MISSING_IMAGES_AND_CHART_AJIO_HTML = """<!DOCTYPE html>
<html>
<head>
  <script>
  window.__PRELOADED_STATE__ = {
    "product": {
      "productDetails": {
        "code": "460009999_black",
        "name": "Minimalist Cotton Overshirt",
        "brandName": "MARKS & SPENCER",
        "brickName": "Shirts",
        "brickCategory": "Men",
        "price": { "value": 2499 },
        "wasPriceData": { "value": 3499 },
        "images": [],
        "variantOptions": [
          { "code": "sku_s", "scDisplaySize": "S", "stock": { "stockLevelStatus": "inStock", "stockLevel": 3 } },
          { "code": "sku_m", "scDisplaySize": "M", "stock": { "stockLevelStatus": "inStock", "stockLevel": 5 } }
        ]
      }
    }
  };
  </script>
</head>
<body></body>
</html>
"""

WAF_BLOCKED_HTML = """<!DOCTYPE html>
<html>
<head><title>Access Denied</title></head>
<body>
  <h1>Access Denied</h1>
  <p>You don't have permission to access "http://www.myntra.com/shirts/..." on this server.</p>
  <p>Reference #18.2d341202.1794577920.a810ef2 (edgesuite.net)</p>
</body>
</html>
"""

KNOWN_FIXTURE_BY_ID = {
    "24891024": (
        "Myntra",
        "https://www.myntra.com/shirts/polo-ralph-lauren/polo-ralph-lauren-men-navy-blue-tailored-fit-pure-cotton-oxford-shirt/24891024/buy",
        MYNTRA_OXFORD_SHIRT_HTML,
    ),
    "469482190_sand": (
        "AJIO",
        "https://www.ajio.com/massimo-dutti-women-sand-beige-single-breasted-linen-blend-tailored-blazer/p/469482190_sand",
        AJIO_LINEN_BLAZER_HTML,
    ),
    "469710338_charcoal": (
        "AJIO",
        "https://www.ajio.com/cos-women-charcoal-slate-high-waisted-wide-leg-pleated-wool-blend-trousers/p/469710338_charcoal",
        AJIO_PLEATED_TROUSERS_HTML,
    ),
}
