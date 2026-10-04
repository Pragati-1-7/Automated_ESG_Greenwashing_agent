"""
data_gen/world_refs.py

Static reference tables used by build_world.py: Indian states, district
centroids, sector profiles, facility templates, name banks.
ALL COMPANIES ARE FICTIONAL.
"""

from __future__ import annotations

# state -> CIN code, SPCB abbreviation, NGT zone
STATES = {
    "Odisha":           {"cin": "OR", "board": "OSPCB",  "zone": "EZ"},
    "Maharashtra":      {"cin": "MH", "board": "MPCB",   "zone": "WZ"},
    "Tamil Nadu":       {"cin": "TN", "board": "TNPCB",  "zone": "SZ"},
    "Gujarat":          {"cin": "GJ", "board": "GPCB",   "zone": "WZ"},
    "Karnataka":        {"cin": "KA", "board": "KSPCB",  "zone": "SZ"},
    "Delhi":            {"cin": "DL", "board": "DPCC",   "zone": "PB"},
    "West Bengal":      {"cin": "WB", "board": "WBPCB",  "zone": "EZ"},
    "Jharkhand":        {"cin": "JH", "board": "JSPCB",  "zone": "EZ"},
    "Chhattisgarh":     {"cin": "CT", "board": "CECB",   "zone": "CZ"},
    "Madhya Pradesh":   {"cin": "MP", "board": "MPPCB",  "zone": "CZ"},
    "Uttar Pradesh":    {"cin": "UP", "board": "UPPCB",  "zone": "PB"},
    "Telangana":        {"cin": "TG", "board": "TSPCB",  "zone": "SZ"},
    "Andhra Pradesh":   {"cin": "AP", "board": "APPCB",  "zone": "SZ"},
    "Rajasthan":        {"cin": "RJ", "board": "RSPCB",  "zone": "WZ"},
    "Haryana":          {"cin": "HR", "board": "HSPCB",  "zone": "PB"},
    "Punjab":           {"cin": "PB", "board": "PPCB",   "zone": "PB"},
    "Uttarakhand":      {"cin": "UT", "board": "UKPCB",  "zone": "PB"},
    "Himachal Pradesh": {"cin": "HP", "board": "HPSPCB", "zone": "PB"},
    "Goa":              {"cin": "GA", "board": "GSPCB",  "zone": "WZ"},
}

# state -> [(district, lat, lon, forested)]
DISTRICTS = {
    "Odisha": [("Jharsuguda", 21.86, 84.01, False), ("Angul", 20.84, 85.10, True), ("Keonjhar", 21.63, 85.58, True),
               ("Sundargarh", 22.12, 84.04, True), ("Rourkela", 22.26, 84.85, False), ("Koraput", 18.81, 82.71, True),
               ("Jajpur", 20.85, 86.33, False), ("Khordha", 20.18, 85.62, False), ("Ganjam", 19.39, 85.05, False),
               ("Kalahandi", 19.91, 83.17, True), ("Dhenkanal", 20.66, 85.60, True)],
    "Jharkhand": [("Ranchi", 23.34, 85.31, False), ("Bokaro", 23.67, 86.15, False), ("West Singhbhum", 22.55, 85.80, True),
                  ("East Singhbhum", 22.80, 86.20, False), ("Dhanbad", 23.80, 86.43, False), ("Hazaribagh", 23.99, 85.36, True),
                  ("Ramgarh", 23.63, 85.52, False), ("Giridih", 24.19, 86.30, True), ("Latehar", 23.74, 84.50, True)],
    "Chhattisgarh": [("Raipur", 21.25, 81.63, False), ("Bilaspur", 22.08, 82.15, False), ("Korba", 22.35, 82.68, True),
                     ("Raigarh", 21.90, 83.40, True), ("Durg", 21.19, 81.28, False), ("Bastar", 19.10, 81.95, True),
                     ("Surguja", 23.12, 83.20, True), ("Dantewada", 18.90, 81.35, True)],
    "Madhya Pradesh": [("Bhopal", 23.26, 77.41, False), ("Indore", 22.72, 75.86, False), ("Satna", 24.60, 80.83, False),
                       ("Singrauli", 24.20, 82.67, True), ("Katni", 23.83, 80.40, False), ("Jabalpur", 23.18, 79.99, False),
                       ("Sagar", 23.84, 78.74, False), ("Neemuch", 24.47, 74.87, False), ("Dhar", 22.60, 75.30, False),
                       ("Balaghat", 21.81, 80.19, True)],
    "Maharashtra": [("Pune", 18.52, 73.86, False), ("Chandrapur", 19.96, 79.30, True), ("Nagpur", 21.15, 79.09, False),
                    ("Raigad", 18.52, 73.18, False), ("Nashik", 20.00, 73.79, False), ("Aurangabad", 19.88, 75.34, False),
                    ("Thane", 19.20, 72.97, False), ("Kolhapur", 16.70, 74.24, False), ("Ratnagiri", 16.99, 73.30, False),
                    ("Solapur", 17.66, 75.91, False)],
    "Karnataka": [("Bengaluru Urban", 12.97, 77.59, False), ("Ballari", 15.14, 76.92, True), ("Kalaburagi", 17.33, 76.83, False),
                  ("Mysuru", 12.30, 76.64, False), ("Tumakuru", 13.34, 77.10, False), ("Belagavi", 15.85, 74.50, False),
                  ("Dakshina Kannada", 12.87, 74.88, False), ("Raichur", 16.20, 77.36, False), ("Koppal", 15.35, 76.15, False)],
    "Tamil Nadu": [("Coimbatore", 11.02, 76.96, False), ("Tiruppur", 11.11, 77.34, False), ("Chennai", 13.08, 80.27, False),
                   ("Salem", 11.66, 78.15, False), ("Erode", 11.34, 77.72, False), ("Madurai", 9.93, 78.12, False),
                   ("Tirunelveli", 8.71, 77.76, False), ("Karur", 10.96, 78.08, False), ("Ariyalur", 11.14, 79.08, False),
                   ("Krishnagiri", 12.74, 77.83, False), ("Thoothukudi", 8.76, 78.13, False), ("Namakkal", 11.22, 78.17, False)],
    "Gujarat": [("Ahmedabad", 23.02, 72.57, False), ("Surat", 21.17, 72.83, False), ("Vadodara", 22.31, 73.18, False),
                ("Bharuch", 21.71, 72.99, False), ("Rajkot", 22.30, 70.80, False), ("Amreli", 21.60, 71.22, False),
                ("Morbi", 22.82, 70.84, False), ("Jamnagar", 22.47, 70.07, False), ("Bhavnagar", 21.76, 72.15, False),
                ("Valsad", 20.60, 72.93, False)],
    "Rajasthan": [("Jaipur", 26.91, 75.79, False), ("Chittorgarh", 24.88, 74.63, False), ("Udaipur", 24.59, 73.71, False),
                  ("Bhilwara", 25.35, 74.64, False), ("Nagaur", 27.20, 73.73, False), ("Jodhpur", 26.24, 73.02, False),
                  ("Sirohi", 24.89, 72.86, False), ("Kota", 25.21, 75.86, False), ("Jhalawar", 24.60, 76.16, False)],
    "Uttar Pradesh": [("Lucknow", 26.85, 80.95, False), ("Kanpur Nagar", 26.45, 80.35, False), ("Sonbhadra", 24.69, 83.07, True),
                      ("Ghaziabad", 28.67, 77.45, False), ("Gautam Buddha Nagar", 28.54, 77.39, False),
                      ("Mirzapur", 25.15, 82.57, False), ("Meerut", 28.98, 77.71, False), ("Agra", 27.18, 78.02, False),
                      ("Lalitpur", 24.69, 78.41, False)],
    "Haryana": [("Gurugram", 28.46, 77.03, False), ("Faridabad", 28.41, 77.31, False), ("Panipat", 29.39, 76.97, False),
                ("Sonipat", 28.99, 77.02, False), ("Hisar", 29.15, 75.72, False)],
    "West Bengal": [("Kolkata", 22.57, 88.36, False), ("Paschim Bardhaman", 23.55, 87.31, False), ("Howrah", 22.59, 88.26, False),
                    ("Purba Medinipur", 22.06, 88.07, False), ("Bankura", 23.23, 87.07, True),
                    ("Paschim Medinipur", 22.43, 87.32, True)],
    "Telangana": [("Hyderabad", 17.39, 78.49, False), ("Rangareddy", 17.25, 78.30, False), ("Sangareddy", 17.62, 78.08, False),
                  ("Nalgonda", 17.05, 79.27, False), ("Khammam", 17.25, 80.15, False),
                  ("Bhadradri Kothagudem", 17.55, 80.62, True), ("Peddapalli", 18.75, 79.51, False)],
    "Andhra Pradesh": [("Visakhapatnam", 17.69, 83.22, False), ("Krishna", 16.17, 81.13, False), ("Guntur", 16.31, 80.44, False),
                       ("Kadapa", 14.47, 78.82, False), ("Anantapur", 14.68, 77.60, False), ("Nellore", 14.44, 79.99, False),
                       ("Srikakulam", 18.30, 83.90, False)],
    "Punjab": [("Ludhiana", 30.90, 75.86, False), ("Mohali", 30.70, 76.72, False), ("Bathinda", 30.21, 74.95, False)],
    "Delhi": [("New Delhi", 28.61, 77.21, False)],
    "Uttarakhand": [("Haridwar", 29.95, 78.16, False), ("Udham Singh Nagar", 28.98, 79.40, False), ("Dehradun", 30.32, 78.03, False)],
    "Himachal Pradesh": [("Solan", 30.91, 77.10, False), ("Sirmaur", 30.56, 77.46, False)],
    "Goa": [("North Goa", 15.50, 73.83, False), ("South Goa", 15.27, 74.00, True)],
}

# Boxes (lat0, lat1, lon0, lon1, weight) where background forest-loss alerts are scattered.
FOREST_BOXES = [
    ("Odisha", 19.2, 22.2, 83.2, 86.2, 5), ("Jharkhand", 22.5, 24.3, 84.2, 86.8, 4),
    ("Chhattisgarh", 18.8, 23.0, 80.8, 83.6, 5), ("Madhya Pradesh", 21.6, 24.4, 76.8, 81.4, 4),
    ("Assam", 25.6, 27.4, 91.2, 94.8, 2), ("Meghalaya", 25.3, 25.9, 90.6, 92.4, 1),
    ("Arunachal Pradesh", 27.0, 28.4, 93.6, 96.4, 1.5), ("Mizoram", 22.6, 23.9, 92.6, 93.2, 1),
    ("Nagaland", 25.5, 26.4, 94.1, 94.9, 0.8), ("Manipur", 24.4, 25.4, 93.6, 94.4, 0.8),
]

# ---------------------------------------------------------------------------
# Sector profiles
# ---------------------------------------------------------------------------
# rev: FY2025 turnover range (Rs cr); s1_int: scope1 tCO2e per Rs cr; s2_ratio: scope2/scope1
# en_int: GJ per Rs cr; wat_int: kL per Rs cr; disch: discharge/withdrawal; waste_int: t per Rs cr
# recov: recovered/generated; elec_share: share of energy that is electricity
SECTOR_PROFILE = {
    "Steel": dict(rev=(4000, 60000), s1_int=(250, 480), s2_ratio=(0.08, 0.18), en_int=(3200, 4200), wat_int=(1400, 2200),
                  disch=(0.08, 0.18), waste_int=(140, 220), recov=(0.82, 0.95), elec_share=0.22, ltifr=(0.35, 0.8),
                  fat_rate=1.5, women=(2, 6), msme=(8, 25), re0=(3, 12), re_gain=(0.5, 3.0),
                  hq=[("Kolkata", "West Bengal"), ("Bhubaneswar", "Odisha"), ("Ranchi", "Jharkhand"), ("Raipur", "Chhattisgarh"),
                      ("Jamshedpur", "Jharkhand"), ("Mumbai", "Maharashtra"), ("Nagpur", "Maharashtra"), ("Hyderabad", "Telangana"),
                      ("Rourkela", "Odisha"), ("Bengaluru", "Karnataka")],
                  states=["Odisha", "Jharkhand", "Chhattisgarh", "West Bengal", "Karnataka", "Maharashtra", "Andhra Pradesh", "Gujarat"],
                  nic=["27100", "27104", "27106"], n_fac=(3, 4), reg_w=1.6),
    "Cement": dict(rev=(2500, 25000), s1_int=(380, 700), s2_ratio=(0.05, 0.10), en_int=(2300, 3200), wat_int=(180, 320),
                   disch=(0.01, 0.05), waste_int=(10, 24), recov=(0.65, 0.9), elec_share=0.15, ltifr=(0.2, 0.6),
                   fat_rate=0.7, women=(1, 4), msme=(12, 30), re0=(4, 14), re_gain=(1.0, 4.0),
                   hq=[("Mumbai", "Maharashtra"), ("Pune", "Maharashtra"), ("Hyderabad", "Telangana"), ("Jaipur", "Rajasthan"),
                       ("Chennai", "Tamil Nadu"), ("Ahmedabad", "Gujarat"), ("Bhopal", "Madhya Pradesh"), ("Raipur", "Chhattisgarh"),
                       ("Bengaluru", "Karnataka"), ("New Delhi", "Delhi")],
                   states=["Rajasthan", "Madhya Pradesh", "Maharashtra", "Andhra Pradesh", "Telangana", "Karnataka", "Gujarat",
                           "Chhattisgarh", "Tamil Nadu", "Himachal Pradesh"],
                   nic=["26941", "26942", "26943"], n_fac=(3, 4), reg_w=1.0),
    "Power": dict(rev=(3000, 45000), s1_int=(150, 2400), s2_ratio=(0.004, 0.03), en_int=None, wat_int=(1500, 3200),
                  disch=(0.15, 0.4), waste_int=(180, 520), recov=(0.55, 0.95), elec_share=0.03, ltifr=(0.15, 0.5),
                  fat_rate=0.7, women=(2, 7), msme=(5, 18), re0=(2, 30), re_gain=(0.5, 5.0),
                  hq=[("New Delhi", "Delhi"), ("Mumbai", "Maharashtra"), ("Hyderabad", "Telangana"), ("Raipur", "Chhattisgarh"),
                      ("Ahmedabad", "Gujarat"), ("Chennai", "Tamil Nadu"), ("Kolkata", "West Bengal"), ("Bengaluru", "Karnataka"),
                      ("Gurugram", "Haryana"), ("Lucknow", "Uttar Pradesh")],
                  states=["Chhattisgarh", "Uttar Pradesh", "Odisha", "Madhya Pradesh", "Maharashtra", "Tamil Nadu", "Gujarat",
                          "Rajasthan", "Karnataka", "Telangana", "Andhra Pradesh", "Jharkhand"],
                  nic=["35101", "35102", "40101"], n_fac=(2, 4), reg_w=1.8),
    "Textiles": dict(rev=(800, 9000), s1_int=(18, 60), s2_ratio=(0.9, 1.8), en_int=(450, 800), wat_int=(240, 420),
                     disch=(0.15, 0.45), waste_int=(1.2, 3.5), recov=(0.7, 0.9), elec_share=0.5, ltifr=(0.08, 0.4),
                     fat_rate=0.1, women=(25, 45), msme=(25, 55), re0=(10, 35), re_gain=(1.5, 5.0),
                     hq=[("Coimbatore", "Tamil Nadu"), ("Tiruppur", "Tamil Nadu"), ("Ludhiana", "Punjab"), ("Ahmedabad", "Gujarat"),
                         ("Mumbai", "Maharashtra"), ("Surat", "Gujarat"), ("Panipat", "Haryana"), ("Bengaluru", "Karnataka"),
                         ("Madurai", "Tamil Nadu"), ("Kanpur", "Uttar Pradesh")],
                     states=["Tamil Nadu", "Gujarat", "Maharashtra", "Punjab", "Haryana", "Uttar Pradesh", "Rajasthan", "Karnataka"],
                     nic=["17111", "13111", "13121", "13131"], n_fac=(2, 3), reg_w=0.8),
    "FMCG": dict(rev=(1500, 30000), s1_int=(4, 14), s2_ratio=(0.7, 1.3), en_int=(110, 220), wat_int=(250, 600),
                 disch=(0.35, 0.65), waste_int=(1.5, 5), recov=(0.6, 0.92), elec_share=0.4, ltifr=(0.08, 0.35),
                 fat_rate=0.12, women=(8, 20), msme=(15, 45), re0=(5, 25), re_gain=(2.0, 5.0),
                 hq=[("Mumbai", "Maharashtra"), ("Pune", "Maharashtra"), ("Bengaluru", "Karnataka"), ("Kolkata", "West Bengal"),
                     ("Gurugram", "Haryana"), ("Chennai", "Tamil Nadu"), ("Ahmedabad", "Gujarat"), ("Lucknow", "Uttar Pradesh"),
                     ("Noida", "Uttar Pradesh"), ("Indore", "Madhya Pradesh")],
                 states=["Maharashtra", "Gujarat", "Uttar Pradesh", "Karnataka", "Tamil Nadu", "Haryana", "West Bengal",
                         "Punjab", "Uttarakhand", "Himachal Pradesh"],
                 nic=["10799", "10501", "15499", "20231", "10611"], n_fac=(2, 3), reg_w=0.3),
    "Chemicals": dict(rev=(1500, 25000), s1_int=(70, 190), s2_ratio=(0.25, 0.6), en_int=(700, 1200), wat_int=(500, 1100),
                      disch=(0.25, 0.55), waste_int=(12, 30), recov=(0.45, 0.8), elec_share=0.3, ltifr=(0.15, 0.55),
                      fat_rate=0.35, women=(4, 12), msme=(10, 35), re0=(3, 20), re_gain=(1.0, 4.0),
                      hq=[("Mumbai", "Maharashtra"), ("Vadodara", "Gujarat"), ("Ahmedabad", "Gujarat"), ("Hyderabad", "Telangana"),
                          ("Chennai", "Tamil Nadu"), ("Pune", "Maharashtra"), ("Kolkata", "West Bengal"), ("Bharuch", "Gujarat"),
                          ("Visakhapatnam", "Andhra Pradesh"), ("Lucknow", "Uttar Pradesh")],
                      states=["Gujarat", "Maharashtra", "Andhra Pradesh", "Telangana", "Tamil Nadu", "Uttar Pradesh", "West Bengal"],
                      nic=["24119", "20119", "20211", "20121", "24129"], n_fac=(2, 3), reg_w=1.6),
    "Automotive": dict(rev=(2000, 40000), s1_int=(3, 9), s2_ratio=(1.2, 2.2), en_int=(100, 210), wat_int=(60, 170),
                       disch=(0.4, 0.65), waste_int=(2.5, 8), recov=(0.8, 0.97), elec_share=0.45, ltifr=(0.1, 0.45),
                       fat_rate=0.2, women=(6, 14), msme=(18, 40), re0=(8, 30), re_gain=(2.0, 6.0),
                       hq=[("Pune", "Maharashtra"), ("Chennai", "Tamil Nadu"), ("Gurugram", "Haryana"), ("Bengaluru", "Karnataka"),
                           ("Coimbatore", "Tamil Nadu"), ("Mumbai", "Maharashtra"), ("Aurangabad", "Maharashtra"),
                           ("Faridabad", "Haryana"), ("Rajkot", "Gujarat"), ("Noida", "Uttar Pradesh")],
                       states=["Maharashtra", "Tamil Nadu", "Haryana", "Karnataka", "Gujarat", "Uttar Pradesh", "Uttarakhand"],
                       nic=["29301", "29104", "29107", "29302"], n_fac=(2, 3), reg_w=0.3),
    "Pharmaceuticals": dict(rev=(1500, 30000), s1_int=(8, 24), s2_ratio=(0.9, 1.6), en_int=(180, 340), wat_int=(380, 650),
                            disch=(0.3, 0.55), waste_int=(5, 12), recov=(0.35, 0.7), elec_share=0.45, ltifr=(0.05, 0.3),
                            fat_rate=0.05, women=(12, 25), msme=(10, 30), re0=(6, 28), re_gain=(1.5, 5.0),
                            hq=[("Hyderabad", "Telangana"), ("Ahmedabad", "Gujarat"), ("Mumbai", "Maharashtra"), ("Pune", "Maharashtra"),
                                ("Bengaluru", "Karnataka"), ("Vadodara", "Gujarat"), ("Visakhapatnam", "Andhra Pradesh"),
                                ("Mohali", "Punjab"), ("Dehradun", "Uttarakhand"), ("Baddi", "Himachal Pradesh")],
                            states=["Telangana", "Gujarat", "Himachal Pradesh", "Maharashtra", "Andhra Pradesh", "Karnataka", "Uttarakhand"],
                            nic=["21001", "21002", "21003"], n_fac=(2, 3), reg_w=0.8),
    "Mining": dict(rev=(1500, 25000), s1_int=(40, 120), s2_ratio=(0.3, 0.7), en_int=(300, 520), wat_int=(400, 800),
                   disch=(0.2, 0.45), waste_int=(180, 420), recov=(0.3, 0.7), elec_share=0.3, ltifr=(0.4, 1.1),
                   fat_rate=2.0, women=(2, 6), msme=(10, 30), re0=(2, 15), re_gain=(0.5, 3.0),
                   hq=[("Kolkata", "West Bengal"), ("Bhubaneswar", "Odisha"), ("Ranchi", "Jharkhand"), ("Raipur", "Chhattisgarh"),
                       ("Nagpur", "Maharashtra"), ("Hyderabad", "Telangana"), ("Panaji", "Goa"), ("Bengaluru", "Karnataka"),
                       ("Jaipur", "Rajasthan"), ("Bhopal", "Madhya Pradesh")],
                   states=["Odisha", "Jharkhand", "Chhattisgarh", "Madhya Pradesh", "Rajasthan", "Karnataka", "Goa", "Telangana"],
                   nic=["07100", "07210", "05101", "08101", "07291"], n_fac=(2, 4), reg_w=1.6),
    "IT Services": dict(rev=(3000, 90000), s1_int=(0.15, 0.5), s2_ratio=(8, 20), en_int=(25, 60), wat_int=(20, 70),
                        disch=(0.5, 0.8), waste_int=(0.03, 0.09), recov=(0.5, 0.9), elec_share=0.95, ltifr=(0.05, 0.12),
                        fat_rate=0.01, women=(25, 40), msme=(5, 18), re0=(25, 55), re_gain=(3.0, 8.0),
                        hq=[("Bengaluru", "Karnataka"), ("Hyderabad", "Telangana"), ("Pune", "Maharashtra"), ("Chennai", "Tamil Nadu"),
                            ("Noida", "Uttar Pradesh"), ("Gurugram", "Haryana"), ("Mumbai", "Maharashtra"), ("Kolkata", "West Bengal")],
                        states=["Karnataka", "Telangana", "Maharashtra", "Tamil Nadu", "Uttar Pradesh", "Haryana"],
                        nic=["62013", "62011", "72200", "62020"], n_fac=(2, 3), reg_w=0.03),
}

# ---------------------------------------------------------------------------
# Facility templates per sector
# (type, capacity_unit, (lo, hi), scope1 weight, method, ocems kind, anchor?, short label, forest-eligible)
# ---------------------------------------------------------------------------
FAC_TEMPLATES = {
    "Steel": [
        ("Integrated steel plant", "MTPA crude steel", (0.5, 6.0), 0.62, "mass balance", "air", True, "Integrated Steel Plant", True),
        ("Coal-fired captive power plant", "MW", (60, 900), 0.24, "CEMS", "air", False, "Captive Power Plant", True),
        ("Pellet plant", "MTPA pellets", (1.0, 8.0), 0.06, "emission factor", "air", False, "Pellet Plant", False),
        ("Sponge iron plant", "tpd DRI", (500, 3000), 0.06, "mass balance", "air", False, "Sponge Iron Plant", False),
        ("Open-cast iron ore mine", "MTPA ore", (2.0, 15.0), 0.02, "emission factor", None, False, "Iron Ore Mine", True),
        ("Rolling mill", "MTPA", (0.3, 2.0), 0.03, "emission factor", None, False, "Rolling Mill", False),
    ],
    "Cement": [
        ("Integrated cement plant", "MTPA cement", (1.5, 7.0), 0.62, "mass balance", "air", True, "Integrated Cement Plant", False),
        ("Integrated cement plant", "MTPA cement", (1.5, 7.0), 0.62, "mass balance", "air", False, "Cement Works", False),
        ("Grinding unit", "MTPA cement", (1.0, 3.0), 0.08, "emission factor", "air", False, "Grinding Unit", False),
        ("Limestone mine", "MTPA limestone", (3.0, 10.0), 0.05, "emission factor", None, False, "Limestone Mine", False),
        ("Captive power plant", "MW", (20, 120), 0.17, "CEMS", "air", False, "Captive Power Plant", True),
    ],
    "Power": [
        ("Coal-fired thermal power plant", "MW", (500, 3960), 0.92, "CEMS", "air", True, "Thermal Power Station", True),
        ("Gas-based power plant", "MW", (300, 1500), 0.45, "CEMS", "air", False, "Gas Power Plant", False),
        ("Solar park", "MWp", (100, 1000), 0.001, "emission factor", None, False, "Solar Park", False),
        ("Wind farm", "MW", (50, 600), 0.001, "emission factor", None, False, "Wind Farm", False),
        ("Hydro power station", "MW", (100, 900), 0.01, "emission factor", None, False, "Hydro Power Station", True),
        ("Biomass power plant", "MW", (10, 60), 0.02, "emission factor", "air", False, "Biomass Power Plant", False),
    ],
    "Textiles": [
        ("Spinning mill", "spindles", (50000, 300000), 0.28, "emission factor", None, True, "Spinning Mill", False),
        ("Dyeing and processing unit", "tonnes fabric/day", (20, 120), 0.65, "emission factor", "water", False, "Processing Unit", False),
        ("Weaving unit", "looms", (200, 1500), 0.05, "emission factor", None, False, "Weaving Unit", False),
        ("Garment manufacturing unit", "mn pieces/yr", (2, 15), 0.03, "emission factor", None, False, "Garment Unit", False),
        ("Captive wind farm", "MW", (10, 80), 0.01, "emission factor", None, False, "Captive Wind Farm", False),
    ],
    "FMCG": [
        ("Food processing plant", "tpd", (200, 3000), 0.45, "emission factor", "water", True, "Food Processing Plant", False),
        ("Edible oil refinery", "tpd", (300, 2000), 0.25, "emission factor", "water", False, "Oil Refinery Unit", False),
        ("Dairy plant", "klpd", (200, 2000), 0.2, "emission factor", "water", False, "Dairy Plant", False),
        ("Personal care manufacturing plant", "tpa", (20000, 150000), 0.1, "emission factor", None, False, "Personal Care Plant", False),
        ("Distribution and packaging centre", "tpa", (10000, 90000), 0.05, "emission factor", None, False, "Packaging Centre", False),
    ],
    "Chemicals": [
        ("Chemical complex", "tpa", (50000, 1200000), 0.6, "mass balance", "water", True, "Chemical Complex", False),
        ("Specialty chemicals plant", "tpa", (20000, 300000), 0.25, "emission factor", "water", False, "Specialty Chemicals Plant", False),
        ("Fertiliser plant", "tpa urea", (200000, 1300000), 0.4, "mass balance", "air", False, "Fertiliser Plant", False),
        ("Dyes and pigments unit", "tpd", (20, 200), 0.1, "emission factor", "water", False, "Dyes Unit", False),
        ("Captive power plant", "MW", (20, 150), 0.15, "CEMS", "air", False, "Captive Power Plant", False),
    ],
    "Automotive": [
        ("Auto components plant", "mn units/yr", (2, 40), 0.35, "emission factor", None, True, "Components Plant", False),
        ("Foundry and forging unit", "tpa castings", (20000, 150000), 0.45, "emission factor", "air", False, "Foundry", False),
        ("Vehicle assembly plant", "k vehicles/yr", (50, 400), 0.1, "emission factor", None, False, "Assembly Plant", False),
        ("Machining and axle unit", "mn units/yr", (1, 20), 0.1, "emission factor", None, False, "Axle Unit", False),
    ],
    "Pharmaceuticals": [
        ("API manufacturing plant", "tpa", (500, 6000), 0.45, "emission factor", "water", True, "API Plant", False),
        ("Formulation plant", "mn tablets/yr", (500, 8000), 0.25, "emission factor", None, False, "Formulation Plant", False),
        ("Biologics facility", "kL fermentation", (20, 400), 0.15, "emission factor", None, False, "Biologics Facility", False),
        ("R&D and pilot plant", "sq m", (5000, 40000), 0.15, "emission factor", None, False, "R&D Centre", False),
    ],
    "Mining": [
        ("Open-cast coal mine", "MTPA coal", (2.0, 20.0), 0.5, "emission factor", None, True, "Coal Mine", True),
        ("Open-cast iron ore mine", "MTPA ore", (2.0, 15.0), 0.3, "emission factor", None, False, "Iron Ore Mine", True),
        ("Bauxite mine", "MTPA ore", (1.0, 8.0), 0.2, "emission factor", None, False, "Bauxite Mine", True),
        ("Manganese mine", "MTPA ore", (0.3, 2.0), 0.1, "emission factor", None, False, "Manganese Mine", True),
        ("Beneficiation plant", "MTPA ore", (2.0, 12.0), 0.2, "emission factor", "air", False, "Beneficiation Plant", False),
        ("Coal washery", "MTPA", (2.0, 10.0), 0.15, "emission factor", "water", False, "Coal Washery", False),
    ],
    "IT Services": [
        ("IT campus", "seats", (3000, 25000), 0.5, "emission factor", None, True, "Technology Campus", False),
        ("Delivery centre", "seats", (1000, 8000), 0.3, "emission factor", None, False, "Delivery Centre", False),
        ("Data centre", "MW IT load", (5, 60), 0.2, "emission factor", None, False, "Data Centre", False),
    ],
}

# ---------------------------------------------------------------------------
# Name banks
# ---------------------------------------------------------------------------
PREFIXES = """Narmada Trikuta Brahmani Subarnarekha Tungabhadra Vaigai Sabarmati Indravati Rushikulya Vamsadhara Betwa Hirakud
Koyna Bhima Pinaka Vindhya Satpura Aravalli Nilgiri Anamalai Purvaghat Malwa Marwar Mewar Bundela Kalinga Utkal Vidarbha Konkan
Khandesh Kongu Chola Pandya Chera Hoysala Kakatiya Satavahana Maurya Himagiri Barak Dhauli Konark Hampi Ajanta Ellora Rajgir Nalanda
Pushkar Girnar Saurashtra Kathiawar Panchmahal Bastar Kosala Magadh Anga Mithila Doab Rohilkhand Awadh Braj Terai Sundarban Chilika
Loktak Zanskar Spiti Kangra Kumaon Garhwal Agni Vayu Varuna Pavan Prithvi Akash Meru Kailash Arjuna Karna Drona Garuda Mandovi Zuari
Tapti Wardha Wainganga Penganga Manjira Musi Kolleru Pulicat Bhavani Noyyal Amaravati Palar Cheyyar Vellar Gundar Hemavati
Sharavathi Netravati Malaprabha Ghataprabha Kabini Arkavathi Tunga Beas Ravi Chenab Giri Pabbar Parvati Tons Alaknanda Mandakini
Bhagirathi Kosi Gandak Rapti Ghaghara Sharda Hindon Gomti Ramganga Sindh Luni Banas Mahi Sabri Dhadhar Damanganga Purna Kim Orsang
Himavan Nagarjuna Ashwamedh Vikramaditya Aryavarta Dandaka Gondwana Kishkindha Pataliputra Takshashila Vijaya Ujjain Avanti Vatsa
Chedi Kuru Panchala Surasena Matsya Gandhara Kamboja Vidisha Mahakoshal Baghelkhand Rewa Jhelum Tawi Teesta Mahananda Dibang
Subansiri Barapani Jorhat Karbi Garo Jaintia Khasi Mishmi Apatani Naga Zeliang Kuki Ao Lotha Sema Angami""".split()

SECTOR_NOUNS = {
    "Steel": ["Steel & Alloys", "Ispat Ltd", "Steels", "Iron & Steel Works", "Special Steels", "Metallics", "Rolling Mills", "Sponge & Steel"],
    "Cement": ["Cement", "Cements", "Cement Industries", "Cement Works", "Concrete & Cement"],
    "Power": ["Power", "Thermal Energy", "Power Generation", "Energy", "Hydro & Power", "Renewable Power", "Green Power", "Powergen"],
    "Textiles": ["Spinning Mills", "Textiles", "Fabrics", "Weaves", "Cotton Mills", "Denim", "Processors", "Knitwear"],
    "FMCG": ["Foods", "Consumer Products", "Agro Foods", "Dairy", "Personal Care", "Beverages", "Edible Oils", "Home Care", "Biscuits & Snacks"],
    "Chemicals": ["Polymers", "Chemicals", "Specialty Chemicals", "Agrochem", "Fertilisers", "Petrochemicals", "Dyes & Pigments", "Industrial Gases"],
    "Automotive": ["Auto Components", "Forgings", "Motors", "Castings", "Autotech", "Tyres", "Axles & Drivetrains", "Auto Ancillaries"],
    "Pharmaceuticals": ["Pharma", "Lifesciences", "Laboratories", "Drugs & Pharmaceuticals", "Biopharma", "Formulations", "API Industries"],
    "Mining": ["Minerals", "Mining & Minerals", "Coal & Minerals", "Resources", "Bauxite Mines", "Mining Industries", "Manganese & Minerals", "Ores"],
    "IT Services": ["Infotech", "Technologies", "Digital Services", "Software", "Systems", "Datacom", "Cloud Solutions", "InfoSystems"],
}

SECTOR_TAG = {"Steel": "STL", "Cement": "CEM", "Power": "PWR", "Textiles": "TEX", "FMCG": "FMC",
              "Chemicals": "CHM", "Automotive": "AUT", "Pharmaceuticals": "PHR", "Mining": "MIN", "IT Services": "ITS"}

ASSURERS = [
    "Bhargava Menon & Associates", "Sundaram Krishnan LLP", "Gupta Deshpande & Co", "Iyengar Ranganathan Assurance LLP",
    "Chowdhury Sen & Partners", "Patel Joshi Sustainability Advisors LLP", "Nair Varghese & Co", "Bose Mukherjee Assurance",
    "Reddy Prasad & Associates", "Singhania Kapoor Assurance LLP", "Deshmukh Apte & Co", "Verma Saxena Assurance Services",
    "Pillai Menon Sustainability LLP", "Malhotra Bedi & Co", "Acharya Mohanty Assurance LLP", "Thakkar Shah & Associates",
]

OUTLETS = [
    "The Eastern Ledger", "Business Mint India", "Deccan Industry Times", "Western Markets Daily", "Kongu Business Review",
    "Odisha Field Report", "Bharat Commerce Weekly", "The Gangetic Business Chronicle", "Southern Industrial Gazette",
    "Capital Pulse India", "Konkan Trade Journal", "The Mahanadi Post", "Rajdhani Financial Standard",
    "Northern Industry Observer", "Telangana Economic Bulletin", "Green Ledger India", "ESG Watch India",
]
