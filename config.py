# ================================================================
#  config.py — All settings and stock definitions
# ================================================================

# ── Data inclusion flags ──────────────────────────────────────────
# Flip to True once the corresponding cache file has been fetched.
# False = completely ignored, no file dependency whatsoever.

USE_SUPPLEMENTAL = True    # trends_cache_supplemental.pkl  (~20 stocks)
USE_EXPANSION    = True   # trends_cache_expansion.pkl     (~80 stocks)
                           # Run fetch_expansion.py first, then flip to True.

# ── Optimization universe (19 stocks — used for walk-forward) ─────
STOCKS_OPTIMIZE = {
    "LULU": {"trends_keyword": "lululemon",           "name": "Lululemon",           "ibes_ticker": "LULU"},
    "NKE":  {"trends_keyword": "nike shoes",          "name": "Nike",                "ibes_ticker": "NKE"},
    "GOOS": {"trends_keyword": "canada goose jacket", "name": "Canada Goose",        "ibes_ticker": "GOOS"},
    "ONON": {"trends_keyword": "on running shoes",    "name": "On Running",          "ibes_ticker": "ONON"},
    "DECK": {"trends_keyword": "hoka shoes",          "name": "Deckers (Hoka/UGG)",  "ibes_ticker": "DECK"},
    "COLM": {"trends_keyword": "columbia sportswear", "name": "Columbia Sportswear", "ibes_ticker": "COLM"},
    "UAA":  {"trends_keyword": "under armour",        "name": "Under Armour",        "ibes_ticker": "UAA"},
    "CROX": {"trends_keyword": "crocs shoes",         "name": "Crocs",               "ibes_ticker": "CROX"},
    "RL":   {"trends_keyword": "ralph lauren",        "name": "Ralph Lauren",        "ibes_ticker": "RL"},
    "TPR":  {"trends_keyword": "coach bags",          "name": "Tapestry (Coach)",    "ibes_ticker": "TPR"},
    "CPRI": {"trends_keyword": "michael kors",        "name": "Capri (Kors/Versace)","ibes_ticker": "CPRI"},
    "PVH":  {"trends_keyword": "calvin klein",        "name": "PVH (CK/Tommy)",      "ibes_ticker": "PVH"},
    "ANF":  {"trends_keyword": "abercrombie fitch",   "name": "Abercrombie & Fitch", "ibes_ticker": "ANF"},
    "AEO":  {"trends_keyword": "american eagle",      "name": "American Eagle",      "ibes_ticker": "AEO"},
    "URBN": {"trends_keyword": "urban outfitters",    "name": "Urban Outfitters",    "ibes_ticker": "URBN"},
    "VFC":  {"trends_keyword": "north face",          "name": "VF Corp (North Face)","ibes_ticker": "VFC"},
    "SKX":  {"trends_keyword": "skechers shoes",      "name": "Skechers",            "ibes_ticker": "SKX"},
    "GPS":  {"trends_keyword": "gap clothing",        "name": "Gap",                 "ibes_ticker": "GPS"},
}

# ── Full backtest universe ────────────────────────────────────────
STOCKS = {

    # ── Original 19 ──────────────────────────────────────────────
    "LULU": {"trends_keyword": "lululemon",             "name": "Lululemon",              "ibes_ticker": "LULU"},
    "NKE":  {"trends_keyword": "nike shoes",            "name": "Nike",                   "ibes_ticker": "NKE"},
    "GOOS": {"trends_keyword": "canada goose jacket",   "name": "Canada Goose",           "ibes_ticker": "GOOS"},
    "ONON": {"trends_keyword": "on running shoes",      "name": "On Running",             "ibes_ticker": "ONON"},
    "DECK": {"trends_keyword": "hoka shoes",            "name": "Deckers (Hoka/UGG)",     "ibes_ticker": "DECK"},
    "COLM": {"trends_keyword": "columbia sportswear",   "name": "Columbia Sportswear",    "ibes_ticker": "COLM"},
    "UAA":  {"trends_keyword": "under armour",          "name": "Under Armour",           "ibes_ticker": "UAA"},
    "CROX": {"trends_keyword": "crocs shoes",           "name": "Crocs",                  "ibes_ticker": "CROX"},
    "RL":   {"trends_keyword": "ralph lauren",          "name": "Ralph Lauren",           "ibes_ticker": "RL"},
    "TPR":  {"trends_keyword": "coach bags",            "name": "Tapestry (Coach)",       "ibes_ticker": "TPR"},
    "CPRI": {"trends_keyword": "michael kors",          "name": "Capri (Kors/Versace)",   "ibes_ticker": "CPRI"},
    "PVH":  {"trends_keyword": "calvin klein",          "name": "PVH (CK/Tommy)",         "ibes_ticker": "PVH"},
    "ANF":  {"trends_keyword": "abercrombie fitch",     "name": "Abercrombie & Fitch",    "ibes_ticker": "ANF"},
    "AEO":  {"trends_keyword": "american eagle",        "name": "American Eagle",         "ibes_ticker": "AEO"},
    "URBN": {"trends_keyword": "urban outfitters",      "name": "Urban Outfitters",       "ibes_ticker": "URBN"},
    "VFC":  {"trends_keyword": "north face",            "name": "VF Corp (North Face)",   "ibes_ticker": "VFC"},
    "SKX":  {"trends_keyword": "skechers shoes",        "name": "Skechers",               "ibes_ticker": "SKX"},
    "GPS":  {"trends_keyword": "gap clothing",          "name": "Gap",                    "ibes_ticker": "GPS"},

    # ── Luxury ───────────────────────────────────────────────────
    "TIF":  {"trends_keyword": "tiffany jewelry",       "name": "Tiffany (LVMH)",         "ibes_ticker": "TIF"},
    "MOV":  {"trends_keyword": "movado watch",          "name": "Movado",                 "ibes_ticker": "MOV"},
    "SIG":  {"trends_keyword": "kay jewelers",          "name": "Signet Jewelers",        "ibes_ticker": "SIG"},
    "FOSL": {"trends_keyword": "fossil watch",          "name": "Fossil Group",           "ibes_ticker": "FOSL"},

    # ── Department Stores ─────────────────────────────────────────
    "JWN":  {"trends_keyword": "nordstrom",             "name": "Nordstrom",              "ibes_ticker": "JWN"},
    "M":    {"trends_keyword": "macys",                 "name": "Macy's",                 "ibes_ticker": "M"},
    "KSS":  {"trends_keyword": "kohls",                 "name": "Kohl's",                 "ibes_ticker": "KSS"},
    "DDS":  {"trends_keyword": "dillards",              "name": "Dillard's",              "ibes_ticker": "DDS"},

    # ── Footwear ──────────────────────────────────────────────────
    "BIRK": {"trends_keyword": "birkenstock sandals",   "name": "Birkenstock",            "ibes_ticker": "BIRK"},
    "WWW":  {"trends_keyword": "wolverine boots",       "name": "Wolverine World Wide",   "ibes_ticker": "WWW"},
    "SHOO": {"trends_keyword": "steve madden shoes",    "name": "Steve Madden",           "ibes_ticker": "SHOO"},
    "CAL":  {"trends_keyword": "caleres shoes",         "name": "Caleres",                "ibes_ticker": "CAL"},
    "BOOT": {"trends_keyword": "boot barn",             "name": "Boot Barn",              "ibes_ticker": "BOOT"},

    # ── Off-price / Value ─────────────────────────────────────────
    "TJX":  {"trends_keyword": "tj maxx",               "name": "TJX Companies",          "ibes_ticker": "TJX"},
    "ROST": {"trends_keyword": "ross dress for less",   "name": "Ross Stores",            "ibes_ticker": "ROST"},
    "BURL": {"trends_keyword": "burlington coat factory","name": "Burlington",             "ibes_ticker": "BURL"},
    "PSMT": {"trends_keyword": "primark",               "name": "Primark (ABF)",          "ibes_ticker": "PSMT"},

    # ── Sportswear ────────────────────────────────────────────────
    "ADDYY":{"trends_keyword": "adidas shoes",          "name": "Adidas",                 "ibes_ticker": "ADDYY"},
    "ASO":  {"trends_keyword": "academy sports",        "name": "Academy Sports",         "ibes_ticker": "ASO"},
    "DKS":  {"trends_keyword": "dicks sporting goods",  "name": "Dick's Sporting Goods",  "ibes_ticker": "DKS"},
    "HIBB": {"trends_keyword": "hibbett sports",        "name": "Hibbett Sports",         "ibes_ticker": "HIBB"},

    # ── Kids / Teen / Specialty ───────────────────────────────────
    "CRI":  {"trends_keyword": "carters baby clothes",  "name": "Carter's",               "ibes_ticker": "CRI"},
    "PLCE": {"trends_keyword": "childrens place",       "name": "Children's Place",       "ibes_ticker": "PLCE"},
    "GES":  {"trends_keyword": "guess clothing",        "name": "Guess",                  "ibes_ticker": "GES"},
    "OXM":  {"trends_keyword": "tommy hilfiger",        "name": "Oxford Industries",      "ibes_ticker": "OXM"},
    "VNCE": {"trends_keyword": "vince clothing",        "name": "Vince",                  "ibes_ticker": "VNCE"},
    "TLYS": {"trends_keyword": "tillys clothing",       "name": "Tilly's",                "ibes_ticker": "TLYS"},
    "ZUMZ": {"trends_keyword": "zumiez",                "name": "Zumiez",                 "ibes_ticker": "ZUMZ"},
    "HOFT": {"trends_keyword": "hooker furniture",      "name": "Hooker Furnishings",     "ibes_ticker": "HOFT"},

    # ── Supplemental: Single-Brand Apparel ───────────────────────
    "LEVI":  {"trends_keyword": "levis jeans",          "name": "Levi Strauss",           "ibes_ticker": "LEVI"},
    "EXPR":  {"trends_keyword": "express clothing",     "name": "Express",                "ibes_ticker": "EXPR"},
    "CURV":  {"trends_keyword": "torrid plus size",     "name": "Torrid",                 "ibes_ticker": "CURV"},

    # ── Supplemental: Outdoor / Lifestyle ────────────────────────
    "YETI":  {"trends_keyword": "yeti tumbler",         "name": "YETI Holdings",          "ibes_ticker": "YETI"},
    "HELE":  {"trends_keyword": "hydro flask",          "name": "Helen of Troy",          "ibes_ticker": "HELE"},
    "SFIX":  {"trends_keyword": "stitch fix",           "name": "Stitch Fix",             "ibes_ticker": "SFIX"},
    "REAL":  {"trends_keyword": "the realreal luxury",  "name": "The RealReal",           "ibes_ticker": "REAL"},

    # ── Supplemental: Beauty / Personal Care ─────────────────────
    "ELF":   {"trends_keyword": "elf cosmetics",        "name": "e.l.f. Beauty",          "ibes_ticker": "ELF"},
    "ULTA":  {"trends_keyword": "ulta beauty",          "name": "Ulta Beauty",            "ibes_ticker": "ULTA"},
    "COTY":  {"trends_keyword": "coty perfume",         "name": "Coty",                   "ibes_ticker": "COTY"},

    # ── Expansion: Restaurants / QSR ─────────────────────────────
    # Only included when USE_EXPANSION = True (loaded dynamically
    # in code.py via the expansion cache). Listed here for reference
    # so the full intended universe is visible in one place.
    #
    # CMG, WING, TXRH, SHAK, BROS, DNUT, JACK, PTLO, DINE, EAT,
    # CAKE, BJRI, RRGB, BLMN, DRI, NDLS, FWRG, CAVA, SG
    #
    # ── Expansion: Pets ──────────────────────────────────────────
    # CHWY, WOOF, FRPT, BARK
    #
    # ── Expansion: Specialty Retail ──────────────────────────────
    # FIVE, PLAY, BOWL, VSCO, BBWI, GME, LESL, BGFV, SPWH
    #
    # ── Expansion: Online / Resale ───────────────────────────────
    # RVLV, TDUP, OSTK, RENT
    #
    # ── Expansion: Beauty / Wellness ─────────────────────────────
    # OLPX, IPAR, HIMS, PTON, PLNT, XPOF
    #
    # ── Expansion: Home Goods ─────────────────────────────────────
    # WSM, RH, ARHS, LOVE, SNBR, TPX, PRPL
    #
    # ── Expansion: Auto Retail ────────────────────────────────────
    # KMX, CVNA, ORLY, AAP
    #
    # ── Expansion: Travel / Delivery ─────────────────────────────
    # ABNB, EXPE, DASH, UBER, LYFT
    #
    # ── Expansion: Consumer Electronics ──────────────────────────
    # BBY, SONO, FNKO, BIRD
}

# ── Expansion stocks (loaded dynamically when USE_EXPANSION=True) ─
# Defined separately so STOCKS stays clean and the flag is a true
# on/off switch with zero side effects when False.
STOCKS_EXPANSION = {

    # ── Restaurants / QSR ────────────────────────────────────────
    "CMG":   {"trends_keyword": "chipotle mexican grill",     "name": "Chipotle",              "ibes_ticker": "CMG"},
    "WING":  {"trends_keyword": "wingstop chicken wings",     "name": "Wingstop",              "ibes_ticker": "WING"},
    "TXRH":  {"trends_keyword": "texas roadhouse restaurant", "name": "Texas Roadhouse",       "ibes_ticker": "TXRH"},
    "SHAK":  {"trends_keyword": "shake shack burger",         "name": "Shake Shack",           "ibes_ticker": "SHAK"},
    "BROS":  {"trends_keyword": "dutch bros coffee",          "name": "Dutch Bros Coffee",     "ibes_ticker": "BROS"},
    "DNUT":  {"trends_keyword": "krispy kreme donuts",        "name": "Krispy Kreme",          "ibes_ticker": "DNUT"},
    "JACK":  {"trends_keyword": "jack in the box burger",     "name": "Jack in the Box",       "ibes_ticker": "JACK"},
    "PTLO":  {"trends_keyword": "portillos hot dogs",         "name": "Portillo's",            "ibes_ticker": "PTLO"},
    "DINE":  {"trends_keyword": "applebees restaurant",       "name": "Dine Brands (Applebee's)","ibes_ticker": "DINE"},
    "EAT":   {"trends_keyword": "chilis restaurant",          "name": "Brinker (Chili's)",     "ibes_ticker": "EAT"},
    "CAKE":  {"trends_keyword": "cheesecake factory menu",    "name": "Cheesecake Factory",    "ibes_ticker": "CAKE"},
    "BJRI":  {"trends_keyword": "bj's restaurant brewhouse",  "name": "BJ's Restaurants",      "ibes_ticker": "BJRI"},
    "RRGB":  {"trends_keyword": "red robin burger",           "name": "Red Robin",             "ibes_ticker": "RRGB"},
    "BLMN":  {"trends_keyword": "outback steakhouse",         "name": "Bloomin' Brands",       "ibes_ticker": "BLMN"},
    "DRI":   {"trends_keyword": "olive garden restaurant",    "name": "Darden (Olive Garden)", "ibes_ticker": "DRI"},
    "NDLS":  {"trends_keyword": "noodles and company",        "name": "Noodles & Company",     "ibes_ticker": "NDLS"},
    "FWRG":  {"trends_keyword": "first watch restaurant",     "name": "First Watch",           "ibes_ticker": "FWRG"},
    "CAVA":  {"trends_keyword": "cava mediterranean food",    "name": "CAVA Group",            "ibes_ticker": "CAVA"},
    "SG":    {"trends_keyword": "sweetgreen salad",           "name": "Sweetgreen",            "ibes_ticker": "SG"},

    # ── Pets ─────────────────────────────────────────────────────
    "CHWY":  {"trends_keyword": "chewy pet food",             "name": "Chewy",                 "ibes_ticker": "CHWY"},
    "WOOF":  {"trends_keyword": "petco pet store",            "name": "Petco",                 "ibes_ticker": "WOOF"},
    "FRPT":  {"trends_keyword": "freshpet dog food",          "name": "Freshpet",              "ibes_ticker": "FRPT"},
    "BARK":  {"trends_keyword": "barkbox dog subscription",   "name": "BarkBox",               "ibes_ticker": "BARK"},

    # ── Specialty Retail ─────────────────────────────────────────
    "FIVE":  {"trends_keyword": "five below store",           "name": "Five Below",            "ibes_ticker": "FIVE"},
    "PLAY":  {"trends_keyword": "dave and busters",           "name": "Dave & Buster's",       "ibes_ticker": "PLAY"},
    "BOWL":  {"trends_keyword": "bowlero bowling",            "name": "Bowlero",               "ibes_ticker": "BOWL"},
    "VSCO":  {"trends_keyword": "victoria secret pink",       "name": "Victoria's Secret",     "ibes_ticker": "VSCO"},
    "BBWI":  {"trends_keyword": "bath body works",            "name": "Bath & Body Works",     "ibes_ticker": "BBWI"},
    "GME":   {"trends_keyword": "gamestop video games",       "name": "GameStop",              "ibes_ticker": "GME"},
    "LESL":  {"trends_keyword": "leslies pool supply",        "name": "Leslie's Pool",         "ibes_ticker": "LESL"},
    "BGFV":  {"trends_keyword": "big 5 sporting goods",       "name": "Big 5 Sporting Goods",  "ibes_ticker": "BGFV"},
    "SPWH":  {"trends_keyword": "sportsmans warehouse",       "name": "Sportsman's Warehouse", "ibes_ticker": "SPWH"},
    "XPOF":  {"trends_keyword": "xponential fitness",         "name": "Xponential Fitness",    "ibes_ticker": "XPOF"},

    # ── Online / Resale ───────────────────────────────────────────
    "RVLV":  {"trends_keyword": "revolve clothing",           "name": "Revolve Group",         "ibes_ticker": "RVLV"},
    "TDUP":  {"trends_keyword": "thredup online thrift",      "name": "ThredUp",               "ibes_ticker": "TDUP"},
    "OSTK":  {"trends_keyword": "overstock furniture",        "name": "Overstock.com",         "ibes_ticker": "OSTK"},
    "RENT":  {"trends_keyword": "rent the runway dresses",    "name": "Rent the Runway",       "ibes_ticker": "RENT"},

    # ── Beauty / Wellness ─────────────────────────────────────────
    "OLPX":  {"trends_keyword": "olaplex hair treatment",     "name": "Olaplex",               "ibes_ticker": "OLPX"},
    "IPAR":  {"trends_keyword": "jimmy choo perfume",         "name": "Inter Parfums",         "ibes_ticker": "IPAR"},
    "HIMS":  {"trends_keyword": "hims hair loss",             "name": "Hims & Hers Health",    "ibes_ticker": "HIMS"},
    "PTON":  {"trends_keyword": "peloton bike",               "name": "Peloton",               "ibes_ticker": "PTON"},
    "PLNT":  {"trends_keyword": "planet fitness gym",         "name": "Planet Fitness",        "ibes_ticker": "PLNT"},

    # ── Home Goods ────────────────────────────────────────────────
    "WSM":   {"trends_keyword": "williams sonoma",            "name": "Williams-Sonoma",       "ibes_ticker": "WSM"},
    "RH":    {"trends_keyword": "restoration hardware",       "name": "RH",                    "ibes_ticker": "RH"},
    "ARHS":  {"trends_keyword": "arhaus furniture",           "name": "Arhaus",                "ibes_ticker": "ARHS"},
    "LOVE":  {"trends_keyword": "lovesac couch",              "name": "Lovesac",               "ibes_ticker": "LOVE"},
    "SNBR":  {"trends_keyword": "sleep number mattress",      "name": "Sleep Number",          "ibes_ticker": "SNBR"},
    "TPX":   {"trends_keyword": "tempur pedic mattress",      "name": "Tempur Sealy",          "ibes_ticker": "TPX"},
    "PRPL":  {"trends_keyword": "purple mattress",            "name": "Purple Innovation",     "ibes_ticker": "PRPL"},

    # ── Auto Retail ───────────────────────────────────────────────
    "KMX":   {"trends_keyword": "carmax used cars",           "name": "CarMax",                "ibes_ticker": "KMX"},
    "CVNA":  {"trends_keyword": "carvana buy car online",     "name": "Carvana",               "ibes_ticker": "CVNA"},
    "ORLY":  {"trends_keyword": "oreilly auto parts",         "name": "O'Reilly Auto Parts",   "ibes_ticker": "ORLY"},
    "AAP":   {"trends_keyword": "advance auto parts store",   "name": "Advance Auto Parts",    "ibes_ticker": "AAP"},

    # ── Travel / Delivery ─────────────────────────────────────────
    "ABNB":  {"trends_keyword": "airbnb vacation rental",     "name": "Airbnb",                "ibes_ticker": "ABNB"},
    "EXPE":  {"trends_keyword": "expedia flights hotels",     "name": "Expedia",               "ibes_ticker": "EXPE"},
    "DASH":  {"trends_keyword": "doordash food delivery",     "name": "DoorDash",              "ibes_ticker": "DASH"},
    "LYFT":  {"trends_keyword": "lyft ride share",            "name": "Lyft",                  "ibes_ticker": "LYFT"},

    # ── Consumer Electronics ──────────────────────────────────────
    "BBY":   {"trends_keyword": "best buy electronics store", "name": "Best Buy",              "ibes_ticker": "BBY"},
    "SONO":  {"trends_keyword": "sonos speaker",              "name": "Sonos",                 "ibes_ticker": "SONO"},
    "FNKO":  {"trends_keyword": "funko pop figure",           "name": "Funko",                 "ibes_ticker": "FNKO"},
    "BIRD":  {"trends_keyword": "allbirds shoes",             "name": "Allbirds",              "ibes_ticker": "BIRD"},
}

# ── Shared trade settings ─────────────────────────────────────────
SIGNAL_THRESHOLD  = 0.5
STARTING_CASH     = 10_000
POSITION_MIN      = 0.10
POSITION_MAX      = 0.90

# ── Benchmark ─────────────────────────────────────────────────────
N_SIMULATIONS = 1000

# ── Cache paths ───────────────────────────────────────────────────
TRENDS_CACHE              = "trends_cache.pkl"
TRENDS_CACHE_EXTENDED     = "trends_cache_extended.pkl"
TRENDS_CACHE_SUPPLEMENTAL = "trends_cache_supplemental.pkl"
TRENDS_CACHE_EXPANSION    = "trends_cache_expansion.pkl"