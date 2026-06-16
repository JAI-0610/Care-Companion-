"""
Go Farm Work - Seed data for Karnataka.
Covers all 31 districts of Karnataka with representative taluks & villages.
Idempotent — safe to re-run.
"""
from datetime import datetime, timezone

# All 31 Karnataka districts (Bengaluru Urban + Rural + 29 others)
KARNATAKA_DISTRICTS = [
    {"name": "Bengaluru Urban", "taluks": [
        {"name": "Bengaluru North", "villages": ["Yelahanka", "Hebbal", "Jakkur"]},
        {"name": "Bengaluru South", "villages": ["Kanakapura Road", "Jayanagar", "JP Nagar"]},
        {"name": "Bengaluru East", "villages": ["Whitefield", "KR Puram", "Mahadevapura"]},
        {"name": "Anekal", "villages": ["Anekal", "Jigani", "Attibele"]},
    ]},
    {"name": "Bengaluru Rural", "taluks": [
        {"name": "Devanahalli", "villages": ["Devanahalli", "Vijayapura", "Bettakote"]},
        {"name": "Doddaballapura", "villages": ["Doddaballapura", "Rajaghatta", "Hadonahalli"]},
        {"name": "Hosakote", "villages": ["Hosakote", "Sulibele", "Nandagudi"]},
        {"name": "Nelamangala", "villages": ["Nelamangala", "Tyamagondlu", "Soladevanahalli"]},
    ]},
    {"name": "Mysuru", "taluks": [
        {"name": "Mysuru", "villages": ["Srirangapatna", "Nanjangud", "Bogadi"]},
        {"name": "Hunsur", "villages": ["Bilikere", "Hanagodu", "Ravandur"]},
        {"name": "K.R. Nagar", "villages": ["Saligrama", "Mirle", "Hosahalli"]},
        {"name": "H.D. Kote", "villages": ["Antharasanthe", "Hampapura", "Beechanahalli"]},
        {"name": "Periyapatna", "villages": ["Bettadapura", "Kampalapura", "Halegunda"]},
    ]},
    {"name": "Mandya", "taluks": [
        {"name": "Mandya", "villages": ["Keragodu", "Duddagere", "Halagur"]},
        {"name": "Maddur", "villages": ["Shivapura", "Koppa", "Basaralu"]},
        {"name": "Malavalli", "villages": ["Kirugavalu", "Halaguru", "Shivanasamudra"]},
        {"name": "Pandavapura", "villages": ["Pandavapura", "Melukote", "Chinakurali"]},
        {"name": "Srirangapatna", "villages": ["Srirangapatna", "Belagola", "Karighatta"]},
    ]},
    {"name": "Tumakuru", "taluks": [
        {"name": "Tumakuru", "villages": ["Gubbi", "Hebbur", "Kora"]},
        {"name": "Tiptur", "villages": ["Nonavinakere", "Banasandra", "Maralahalli"]},
        {"name": "Sira", "villages": ["Kallambella", "Hulikunte", "Madalur"]},
        {"name": "Chiknayakanahalli", "villages": ["Hosadurga", "Kandikere", "Nidaghatta"]},
        {"name": "Pavagada", "villages": ["Pavagada", "Y N Hosakote", "Nagalamadike"]},
    ]},
    {"name": "Hassan", "taluks": [
        {"name": "Hassan", "villages": ["Shantigrama", "Kattaya", "Dudda"]},
        {"name": "Channarayapatna", "villages": ["Shravanabelagola", "Nuggehalli", "Hirisave"]},
        {"name": "Arsikere", "villages": ["Banavara", "Javagallu", "Gandasi"]},
        {"name": "Belur", "villages": ["Belur", "Halebid", "Arehalli"]},
        {"name": "Sakleshpur", "villages": ["Sakleshpur", "Hanbal", "Hettur"]},
    ]},
    {"name": "Kodagu", "taluks": [
        {"name": "Madikeri", "villages": ["Madikeri", "Bhagamandala", "Talacauvery"]},
        {"name": "Virajpet", "villages": ["Virajpet", "Gonikoppal", "Ammathi"]},
        {"name": "Somwarpet", "villages": ["Somwarpet", "Kushalnagar", "Suntikoppa"]},
    ]},
    {"name": "Chamarajanagar", "taluks": [
        {"name": "Chamarajanagar", "villages": ["Chamarajanagar", "Haradanahalli", "Bagali"]},
        {"name": "Gundlupet", "villages": ["Gundlupet", "Bargi", "Hangala"]},
        {"name": "Kollegal", "villages": ["Kollegal", "Hanur", "Yelandur"]},
        {"name": "Yelandur", "villages": ["Yelandur", "Honnur", "Madapura"]},
    ]},
    {"name": "Chikkamagaluru", "taluks": [
        {"name": "Chikkamagaluru", "villages": ["Aldur", "Mudigere", "Balehonnur"]},
        {"name": "Tarikere", "villages": ["Tarikere", "Lingadahalli", "Ajjampura"]},
        {"name": "Kadur", "villages": ["Kadur", "Birur", "Hiriyur"]},
        {"name": "Koppa", "villages": ["Koppa", "Shringeri", "Sringeri"]},
        {"name": "N R Pura", "villages": ["Narasimharajapura", "Megaravalli", "Halasulige"]},
    ]},
    {"name": "Shivamogga", "taluks": [
        {"name": "Shivamogga", "villages": ["Ayanur", "Kumsi", "Holalur"]},
        {"name": "Bhadravathi", "villages": ["Holehonnur", "Arasalu", "Nidige"]},
        {"name": "Sagar", "villages": ["Sagar", "Talaguppa", "Hosanagar"]},
        {"name": "Soraba", "villages": ["Soraba", "Anavatti", "Yelagi"]},
        {"name": "Tirthahalli", "villages": ["Tirthahalli", "Megaravalli", "Mandagadde"]},
    ]},
    {"name": "Davanagere", "taluks": [
        {"name": "Davanagere", "villages": ["Anaji", "Kakkaragolla", "Kundwad"]},
        {"name": "Harihara", "villages": ["Banuvalli", "Kondajji", "Malebennur"]},
        {"name": "Honnali", "villages": ["Honnali", "Nyamati", "Belaguru"]},
        {"name": "Jagalur", "villages": ["Jagalur", "Bilichodu", "Asagodu"]},
        {"name": "Channagiri", "villages": ["Channagiri", "Basavapatna", "Doddagatta"]},
    ]},
    {"name": "Chitradurga", "taluks": [
        {"name": "Chitradurga", "villages": ["Bhanavasi", "Turuvanur", "Hosadurga"]},
        {"name": "Hosadurga", "villages": ["Hosadurga", "Sreerampura", "Lingadahalli"]},
        {"name": "Hiriyur", "villages": ["Hiriyur", "Aimangala", "Vani Vilas Sagara"]},
        {"name": "Challakere", "villages": ["Challakere", "Parashurampura", "Talak"]},
        {"name": "Molakalmuru", "villages": ["Molakalmuru", "Rampura", "Devasamudra"]},
    ]},
    {"name": "Ballari", "taluks": [
        {"name": "Ballari", "villages": ["Moka", "Kurugodu", "Sanapura"]},
        {"name": "Hospet", "villages": ["Kamalapur", "Mariyammanahalli", "Mundargi"]},
        {"name": "Hagaribommanahalli", "villages": ["HB Halli", "Hampasagar", "Tambrahalli"]},
        {"name": "Sandur", "villages": ["Sandur", "Yeshwanthnagar", "Toranagallu"]},
        {"name": "Siruguppa", "villages": ["Siruguppa", "Tekkalakote", "Karur"]},
    ]},
    {"name": "Koppal", "taluks": [
        {"name": "Koppal", "villages": ["Koppal", "Munirabad", "Anegundi"]},
        {"name": "Gangavathi", "villages": ["Gangavathi", "Kanakagiri", "Hanumanahalli"]},
        {"name": "Yelburga", "villages": ["Yelburga", "Kukanoor", "Maradi"]},
        {"name": "Kushtagi", "villages": ["Kushtagi", "Hanamasagar", "Tavargera"]},
    ]},
    {"name": "Raichur", "taluks": [
        {"name": "Raichur", "villages": ["Raichur", "Yermarus", "Chandrabanda"]},
        {"name": "Manvi", "villages": ["Manvi", "Kavital", "Sirwar"]},
        {"name": "Lingsugur", "villages": ["Lingsugur", "Mudgal", "Hatti"]},
        {"name": "Sindhanur", "villages": ["Sindhanur", "Maski", "Turvihal"]},
        {"name": "Devadurga", "villages": ["Devadurga", "Gabbur", "Jalahalli"]},
    ]},
    {"name": "Yadgir", "taluks": [
        {"name": "Yadgir", "villages": ["Yadgir", "Hattikuni", "Saidapur"]},
        {"name": "Shahapur", "villages": ["Shahapur", "Wadagera", "Kembavi"]},
        {"name": "Shorapur", "villages": ["Shorapur", "Hunasagi", "Kakkera"]},
    ]},
    {"name": "Kalaburagi", "taluks": [
        {"name": "Kalaburagi", "villages": ["Kalaburagi", "Aland", "Afzalpur"]},
        {"name": "Aland", "villages": ["Aland", "Bhusnoor", "Madanahipparga"]},
        {"name": "Afzalpur", "villages": ["Afzalpur", "Atnoor", "Karjagi"]},
        {"name": "Chincholi", "villages": ["Chincholi", "Chitapur", "Kodli"]},
        {"name": "Sedam", "villages": ["Sedam", "Madana Hipparga", "Chitapur"]},
        {"name": "Jewargi", "villages": ["Jewargi", "Yadrami", "Andola"]},
    ]},
    {"name": "Bidar", "taluks": [
        {"name": "Bidar", "villages": ["Bidar", "Kamthana", "Hallikhed"]},
        {"name": "Bhalki", "villages": ["Bhalki", "Hulsoor", "Mehkar"]},
        {"name": "Aurad", "villages": ["Aurad", "Santpur", "Kamalanagar"]},
        {"name": "Humnabad", "villages": ["Humnabad", "Chitaguppa", "Mannaekhelli"]},
        {"name": "Basavakalyan", "villages": ["Basavakalyan", "Mantal", "Kohinoor"]},
    ]},
    {"name": "Vijayapura", "taluks": [
        {"name": "Vijayapura", "villages": ["Vijayapura", "Babaleshwar", "Tikota"]},
        {"name": "Indi", "villages": ["Indi", "Chadachan", "Hingani"]},
        {"name": "Sindgi", "villages": ["Sindgi", "Devar Hipparagi", "Almel"]},
        {"name": "Basavana Bagewadi", "villages": ["Basavana Bagewadi", "Hunsagi", "Kolhar"]},
        {"name": "Muddebihal", "villages": ["Muddebihal", "Talikoti", "Nidagundi"]},
    ]},
    {"name": "Bagalkot", "taluks": [
        {"name": "Bagalkot", "villages": ["Bagalkot", "Banahatti", "Kerur"]},
        {"name": "Badami", "villages": ["Badami", "Pattadakal", "Aihole"]},
        {"name": "Jamkhandi", "villages": ["Jamkhandi", "Rabkavi", "Banahatti"]},
        {"name": "Bilgi", "villages": ["Bilgi", "Galgali", "Anagawadi"]},
        {"name": "Hungund", "villages": ["Hungund", "Ilkal", "Amingad"]},
        {"name": "Mudhol", "villages": ["Mudhol", "Lokapur", "Rampur"]},
    ]},
    {"name": "Belagavi", "taluks": [
        {"name": "Belagavi", "villages": ["Hudli", "Kakati", "Uchagaon"]},
        {"name": "Bailhongal", "villages": ["Sampagaon", "Rayabag", "Amatur"]},
        {"name": "Saundatti", "villages": ["Yaragatti", "Munvalli", "Navalgund"]},
        {"name": "Chikodi", "villages": ["Chikodi", "Nipani", "Yamkanmardi"]},
        {"name": "Athani", "villages": ["Athani", "Kagwad", "Aigali"]},
        {"name": "Khanapur", "villages": ["Khanapur", "Kittur", "Beedi"]},
    ]},
    {"name": "Dharwad", "taluks": [
        {"name": "Dharwad", "villages": ["Garag", "Narendra", "Kalaghatagi"]},
        {"name": "Hubli", "villages": ["Adaragunchi", "Kusugal", "Nulavi"]},
        {"name": "Navalgund", "villages": ["Navalgund", "Annigeri", "Yaravattigi"]},
        {"name": "Kundgol", "villages": ["Kundgol", "Saunshi", "Garag"]},
        {"name": "Kalghatgi", "villages": ["Kalaghatagi", "Tabakad Honnalli", "Devikoppa"]},
    ]},
    {"name": "Gadag", "taluks": [
        {"name": "Gadag", "villages": ["Gadag", "Hulkoti", "Mulgund"]},
        {"name": "Mundargi", "villages": ["Mundargi", "Dambal", "Shirahatti"]},
        {"name": "Ron", "villages": ["Ron", "Naregal", "Holealur"]},
        {"name": "Shirhatti", "villages": ["Shirhatti", "Lakshmeshwar", "Bellatti"]},
        {"name": "Nargund", "villages": ["Nargund", "Bhairanahatti", "Konnur"]},
    ]},
    {"name": "Haveri", "taluks": [
        {"name": "Haveri", "villages": ["Haveri", "Tilavalli", "Hosaritti"]},
        {"name": "Ranebennur", "villages": ["Ranebennur", "Magod", "Yadalli"]},
        {"name": "Byadgi", "villages": ["Byadgi", "Kaginele", "Motebennur"]},
        {"name": "Hangal", "villages": ["Hangal", "Bommanahalli", "Akkialur"]},
        {"name": "Hirekerur", "villages": ["Hirekerur", "Hanagal", "Rattihalli"]},
        {"name": "Savanur", "villages": ["Savanur", "Karadagi", "Hosaritti"]},
        {"name": "Shiggaon", "villages": ["Shiggaon", "Bankapur", "Tadas"]},
    ]},
    {"name": "Uttara Kannada", "taluks": [
        {"name": "Karwar", "villages": ["Karwar", "Sadashivgad", "Chendia"]},
        {"name": "Sirsi", "villages": ["Sirsi", "Banavasi", "Bisgod"]},
        {"name": "Yellapur", "villages": ["Yellapur", "Mundgod", "Manchikeri"]},
        {"name": "Honnavar", "villages": ["Honnavar", "Gerusoppa", "Mavinkurva"]},
        {"name": "Bhatkal", "villages": ["Bhatkal", "Murudeshwar", "Mavinkurva"]},
        {"name": "Kumta", "villages": ["Kumta", "Gokarna", "Dhareshwar"]},
        {"name": "Mundgod", "villages": ["Mundgod", "Banavasi", "Yedoga"]},
        {"name": "Ankola", "villages": ["Ankola", "Belekeri", "Bhetkuli"]},
        {"name": "Joida", "villages": ["Joida", "Karjagi", "Anshi"]},
        {"name": "Haliyal", "villages": ["Haliyal", "Dandeli", "Tinaighat"]},
        {"name": "Siddapur", "villages": ["Siddapur", "Bilgi", "Heggarni"]},
    ]},
    {"name": "Udupi", "taluks": [
        {"name": "Udupi", "villages": ["Udupi", "Manipal", "Malpe"]},
        {"name": "Karkala", "villages": ["Karkala", "Hebri", "Bajagoli"]},
        {"name": "Kundapura", "villages": ["Kundapura", "Byndoor", "Maravanthe"]},
        {"name": "Brahmavar", "villages": ["Brahmavar", "Saligrama", "Belman"]},
    ]},
    {"name": "Dakshina Kannada", "taluks": [
        {"name": "Mangaluru", "villages": ["Mangaluru", "Surathkal", "Mulki"]},
        {"name": "Bantwal", "villages": ["Bantwal", "Vittal", "Panemangalore"]},
        {"name": "Puttur", "villages": ["Puttur", "Uppinangadi", "Kabaka"]},
        {"name": "Belthangady", "villages": ["Belthangady", "Dharmasthala", "Ujire"]},
        {"name": "Sullia", "villages": ["Sullia", "Subramanya", "Aranthodu"]},
        {"name": "Moodabidri", "villages": ["Moodabidri", "Karkala", "Padangadi"]},
    ]},
    {"name": "Chikkaballapur", "taluks": [
        {"name": "Chikkaballapur", "villages": ["Chikkaballapur", "Maluru", "Lakkur"]},
        {"name": "Sidlaghatta", "villages": ["Sidlaghatta", "Yellampalli", "Melur"]},
        {"name": "Chintamani", "villages": ["Chintamani", "Murugamalla", "Kaivara"]},
        {"name": "Gauribidanur", "villages": ["Gauribidanur", "Manchenahalli", "Vidurashwatha"]},
        {"name": "Bagepalli", "villages": ["Bagepalli", "Chelur", "Mittemari"]},
    ]},
    {"name": "Kolar", "taluks": [
        {"name": "Kolar", "villages": ["Kolar", "Vemagal", "Holur"]},
        {"name": "Mulbagal", "villages": ["Mulbagal", "Kurudi", "N Vaddahalli"]},
        {"name": "Bangarpet", "villages": ["Bangarpet", "Bethamangala", "Kamasamudra"]},
        {"name": "Srinivaspur", "villages": ["Srinivaspur", "Nelvagilu", "Rayalpad"]},
        {"name": "Malur", "villages": ["Malur", "Masthi", "Lakkur"]},
    ]},
    {"name": "Ramanagara", "taluks": [
        {"name": "Ramanagara", "villages": ["Ramanagara", "Bidadi", "Closepet"]},
        {"name": "Channapatna", "villages": ["Channapatna", "Hejjala", "Konanakunte"]},
        {"name": "Kanakapura", "villages": ["Kanakapura", "Sangama", "Harohalli"]},
        {"name": "Magadi", "villages": ["Magadi", "Solur", "Kudur"]},
    ]},
    {"name": "Vijayanagara", "taluks": [
        {"name": "Hosapete", "villages": ["Hosapete", "Hampi", "Kamalapur"]},
        {"name": "Hagaribommanahalli", "villages": ["HB Halli", "Hampasagar", "Karur"]},
        {"name": "Kottur", "villages": ["Kottur", "Ujjini", "Hadagali"]},
        {"name": "Harpanahalli", "villages": ["Harpanahalli", "Halavagalu", "Telegi"]},
        {"name": "Hoovina Hadagali", "villages": ["Hoovinahadagali", "Holalu", "Itigi"]},
    ]},
]

JOB_CATEGORIES = [
    {"id": "land_preparation", "name": "Land Preparation", "icon": "tractor"},
    {"id": "sowing", "name": "Sowing", "icon": "sprout"},
    {"id": "transplanting", "name": "Transplanting", "icon": "sprout"},
    {"id": "harvesting", "name": "Harvesting", "icon": "wheat"},
    {"id": "sugarcane_cutting", "name": "Sugarcane Cutting", "icon": "scissors"},
    {"id": "coconut_climbing", "name": "Coconut Climbing", "icon": "tree-palm"},
    {"id": "weeding", "name": "Weeding", "icon": "leaf"},
    {"id": "pruning", "name": "Pruning", "icon": "scissors"},
    {"id": "fencing", "name": "Fencing", "icon": "fence"},
    {"id": "irrigation_setup", "name": "Irrigation Setup", "icon": "droplets"},
    {"id": "drip_maintenance", "name": "Drip Maintenance", "icon": "droplet"},
    {"id": "borewell_support", "name": "Borewell Support", "icon": "waves"},
    {"id": "pesticide_spraying", "name": "Pesticide Spraying", "icon": "spray-can"},
    {"id": "fertilizer_application", "name": "Fertilizer Application", "icon": "flask-conical"},
    {"id": "drone_spraying", "name": "Drone Spraying", "icon": "plane"},
    {"id": "tractor_services", "name": "Tractor Services", "icon": "tractor"},
    {"id": "rotavator_services", "name": "Rotavator/Tiller", "icon": "cog"},
    {"id": "harvester_services", "name": "Harvester Services", "icon": "truck"},
    {"id": "orchard_work", "name": "Orchard Work", "icon": "apple"},
    {"id": "plantation_maintenance", "name": "Plantation Maintenance", "icon": "trees"},
    {"id": "dairy_support", "name": "Dairy Support", "icon": "milk"},
    {"id": "poultry_support", "name": "Poultry Support", "icon": "bird"},
    {"id": "warehouse_loading", "name": "Warehouse/Loading", "icon": "package"},
    {"id": "farm_transport", "name": "Farm Transport", "icon": "truck"},
    {"id": "soil_testing", "name": "Soil Testing", "icon": "test-tube"},
    {"id": "agri_advisory", "name": "Agri Advisory", "icon": "book-open"},
    {"id": "organic_farming", "name": "Organic Farming", "icon": "leaf"},
    {"id": "nursery_work", "name": "Nursery Work", "icon": "flower"},
    {"id": "machinery_maintenance", "name": "Machinery Maintenance", "icon": "wrench"},
]

CROPS = [
    "Rice/Paddy", "Ragi", "Jowar", "Maize", "Wheat", "Pulses (Toor/Chana)",
    "Sugarcane", "Cotton", "Groundnut", "Sunflower", "Soybean",
    "Coconut", "Arecanut", "Coffee", "Tea", "Cardamom", "Pepper",
    "Banana", "Mango", "Pomegranate", "Grapes", "Tomato", "Onion",
    "Potato", "Chilli", "Turmeric", "Ginger", "Mulberry (Silk)",
]

SKILLS = [
    "Plowing", "Sowing by hand", "Tractor driving", "Harvester operation",
    "Sugarcane cutting", "Coconut climbing", "Tree pruning", "Drip system setup",
    "Borewell/pump repair", "Pesticide spraying", "Drone piloting",
    "Cattle handling", "Milking", "Poultry feeding", "Fencing",
    "Loading/unloading", "Truck driving", "Organic composting", "Nursery care",
]


def seed_database(db):
    """Idempotent seed. Creates reference data if missing.

    Re-seeds geography if the count is less than expected (so adding districts is automatic).
    """
    # Districts/taluks/villages
    current_districts = db.districts.count_documents({})
    if current_districts < len(KARNATAKA_DISTRICTS):
        # Wipe and reseed (only geography ref data — no user data)
        if current_districts > 0:
            db.districts.delete_many({})
            db.taluks.delete_many({})
            db.villages.delete_many({})
        for d_idx, d in enumerate(KARNATAKA_DISTRICTS):
            district_id = f"dist_{d_idx+1:02d}"
            db.districts.insert_one({"district_id": district_id, "name": d["name"], "state": "Karnataka"})
            for t_idx, t in enumerate(d["taluks"]):
                taluk_id = f"{district_id}_tal_{t_idx+1:02d}"
                db.taluks.insert_one({
                    "taluk_id": taluk_id, "district_id": district_id, "name": t["name"],
                })
                for v_idx, v in enumerate(t["villages"]):
                    village_id = f"{taluk_id}_vil_{v_idx+1:02d}"
                    db.villages.insert_one({
                        "village_id": village_id, "taluk_id": taluk_id,
                        "district_id": district_id, "name": v,
                    })
    # Categories
    if db.job_categories.count_documents({}) == 0:
        for c in JOB_CATEGORIES:
            db.job_categories.insert_one(c)
    # Crops
    if db.crops.count_documents({}) == 0:
        for i, crop in enumerate(CROPS):
            db.crops.insert_one({"crop_id": f"crop_{i+1:03d}", "name": crop})
    # Skills
    if db.skills.count_documents({}) == 0:
        for i, skill in enumerate(SKILLS):
            db.skills.insert_one({"skill_id": f"skill_{i+1:03d}", "name": skill})

    # Indexes (idempotent)
    db.users.create_index("user_id", unique=True)
    db.users.create_index("email", sparse=True)
    db.users.create_index("phone", sparse=True)
    db.user_sessions.create_index("session_token", unique=True)
    db.user_sessions.create_index("user_id")
    db.jobs.create_index("job_id", unique=True)
    db.jobs.create_index("owner_user_id")
    db.jobs.create_index("status")
    db.jobs.create_index("district")
    db.jobs.create_index("category_id")
    db.proposals.create_index("proposal_id", unique=True)
    db.proposals.create_index("job_id")
    db.proposals.create_index("partner_user_id")
    db.contracts.create_index("contract_id", unique=True)
    db.messages.create_index([("thread_id", 1), ("created_at", 1)])
    db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    db.audit_log.create_index([("user_id", 1), ("created_at", -1)])
    db.live_location_sessions.create_index([("status", 1), ("expires_at", 1)])
    db.live_location_pings.create_index([("session_id", 1), ("at", -1)])
    db.otp_tokens.create_index([("identifier", 1), ("channel", 1), ("created_at", -1)])
    db.step_up_tokens.create_index("token", unique=True)
    db.idempotency_keys.create_index([("key", 1), ("user_id", 1)], unique=True)
    db.push_tokens.create_index([("user_id", 1), ("device_token", 1)], unique=True)
    db.webhook_events.create_index([("provider", 1), ("received_at", -1)])
    db.shortlists.create_index([("owner_user_id", 1), ("created_at", -1)])

    # Seed a demo admin account
    admin_email = "admin@gofarmwork.in"
    existing_admin = db.users.find_one({"email": admin_email}, {"_id": 0})
    if not existing_admin:
        from auth import hash_password, new_user_id
        db.users.insert_one({
            "user_id": new_user_id(),
            "email": admin_email,
            "password_hash": hash_password("Admin@123"),
            "full_name": "Go Farm Work Admin",
            "role": "admin",
            "auth_provider": "email",
            "preferred_language": "en",
            "onboarded": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
