import os
import sys
import pickle
import pandas as pd
import numpy as np

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
SRC_DIR = os.path.join(ROOT_DIR, "src")
DATA_DIR = os.path.join(ROOT_DIR, "data")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from creator_recommender import CreatorRecommender, INDEX_FILE, PROFILES_CSV, get_follower_tier, clean_text
import database

NEW_CREATORS = [
    # -------------------------------------------------------------
    # TECHNOLOGY (15 creators)
    # -------------------------------------------------------------
    {
        "username": "mkbhd",
        "fullName": "Marques Brownlee",
        "category": "Technology",
        "bio": "Quality Tech Videos | Smartphones, electric vehicles, consumer tech reviews and gadgets. Host of Waveform podcast.",
        "followers": 4700000,
        "avg_likes": 165000,
        "avg_comments": 4500,
        "engagement_rate": 0.038,
        "is_verified": True
    },
    {
        "username": "mrwhosetheboss",
        "fullName": "Arun Maini",
        "category": "Technology",
        "bio": "Exploring the future of tech. Smartphone camera shootouts, futuristic consumer gadgets, tech teardowns and reviews.",
        "followers": 3200000,
        "avg_likes": 120000,
        "avg_comments": 3800,
        "engagement_rate": 0.041,
        "is_verified": True
    },
    {
        "username": "linustech",
        "fullName": "Linus Tech Tips",
        "category": "Technology",
        "bio": "We make entertaining videos about technology, PC building, custom gaming rigs, computer hardware, servers and tech experiments.",
        "followers": 1550000,
        "avg_likes": 75000,
        "avg_comments": 2200,
        "engagement_rate": 0.052,
        "is_verified": True
    },
    {
        "username": "lexfridman",
        "fullName": "Lex Fridman",
        "category": "Technology",
        "bio": "Research scientist at MIT working on artificial intelligence, autonomous vehicles, robotics and deep learning. Host of Lex Fridman Podcast.",
        "followers": 2900000,
        "avg_likes": 95000,
        "avg_comments": 3100,
        "engagement_rate": 0.035,
        "is_verified": True
    },
    {
        "username": "ijustine",
        "fullName": "Justine Ezarik",
        "category": "Technology",
        "bio": "Tech, gaming, gadgets, Apple ecosystem reviews, iPhone, unboxings and tech lifestyle. Video creator and author.",
        "followers": 1600000,
        "avg_likes": 38000,
        "avg_comments": 1200,
        "engagement_rate": 0.026,
        "is_verified": True
    },
    {
        "username": "austintech",
        "fullName": "Austin Evans",
        "category": "Technology",
        "bio": "Tech reviews, mystery gadgets, budget gaming setups, futuristic smartphones and consumer electronics testing.",
        "followers": 520000,
        "avg_likes": 22000,
        "avg_comments": 800,
        "engagement_rate": 0.045,
        "is_verified": True
    },
    {
        "username": "dave2d",
        "fullName": "Dave Lee",
        "category": "Technology",
        "bio": "Minimalist, honest tech reviews. Laptops, GPUs, smartphones, mechanical keyboards and portable gaming gear.",
        "followers": 480000,
        "avg_likes": 25000,
        "avg_comments": 950,
        "engagement_rate": 0.055,
        "is_verified": True
    },
    {
        "username": "sama",
        "fullName": "Sam Altman",
        "category": "Technology",
        "bio": "CEO of OpenAI. Building safe artificial general intelligence (AGI), neural networks, ChatGPT, and transformative frontier technologies.",
        "followers": 1200000,
        "avg_likes": 68000,
        "avg_comments": 2600,
        "engagement_rate": 0.060,
        "is_verified": True
    },
    {
        "username": "sundarpichai",
        "fullName": "Sundar Pichai",
        "category": "Technology",
        "bio": "CEO of Google and Alphabet. Working on AI breakthroughs, Android, Google Search, Gemini models, Quantum computing and cloud infrastructure.",
        "followers": 3100000,
        "avg_likes": 140000,
        "avg_comments": 4200,
        "engagement_rate": 0.048,
        "is_verified": True
    },
    {
        "username": "tim_cook",
        "fullName": "Tim Cook",
        "category": "Technology",
        "bio": "CEO of Apple. Innovation in consumer hardware, Apple Silicon, iPhone, Mac, iOS software, Vision Pro spatial computing and environmental sustainability.",
        "followers": 1800000,
        "avg_likes": 90000,
        "avg_comments": 3000,
        "engagement_rate": 0.051,
        "is_verified": True
    },
    {
        "username": "saradietschy",
        "fullName": "Sara Dietschy",
        "category": "Technology",
        "bio": "Creative tech, camera gear, video production, tech lifestyle and podcast host of That's Creative.",
        "followers": 195000,
        "avg_likes": 8500,
        "avg_comments": 350,
        "engagement_rate": 0.046,
        "is_verified": True
    },
    {
        "username": "unboxtherapy",
        "fullName": "Lewis Hilsenteger",
        "category": "Technology",
        "bio": "Where products get naked. Unboxing the craziest gadgets, newest smartphones, weird tech inventions and futuristic electronics.",
        "followers": 2400000,
        "avg_likes": 65000,
        "avg_comments": 1900,
        "engagement_rate": 0.029,
        "is_verified": True
    },
    {
        "username": "supercarblondie",
        "fullName": "Alex Hirschi",
        "category": "Technology",
        "bio": "Showcasing the world's coolest tech, concept hypercars, autonomous futuristic vehicles, robotics and luxury transport technology.",
        "followers": 16800000,
        "avg_likes": 350000,
        "avg_comments": 8000,
        "engagement_rate": 0.022,
        "is_verified": True
    },
    {
        "username": "cleoabram",
        "fullName": "Cleo Abram",
        "category": "Technology",
        "bio": "Huge If True. Video journalist exploring big questions in science and technology: AI, nuclear fusion, quantum computers and space.",
        "followers": 850000,
        "avg_likes": 48000,
        "avg_comments": 1500,
        "engagement_rate": 0.059,
        "is_verified": True
    },
    {
        "username": "theverge",
        "fullName": "The Verge",
        "category": "Technology",
        "bio": "Covering the intersection of technology, science, art, and culture. Tech news, smartphone reviews, computing and gadgets.",
        "followers": 1450000,
        "avg_likes": 32000,
        "avg_comments": 1100,
        "engagement_rate": 0.024,
        "is_verified": True
    },

    # -------------------------------------------------------------
    # FITNESS (15 creators)
    # -------------------------------------------------------------
    {
        "username": "cbum",
        "fullName": "Chris Bumstead",
        "category": "Fitness",
        "bio": "5x Classic Physique Mr. Olympia Champion. Bodybuilding motivation, heavy compound lifts, bodybuilding training and Raw Nutrition.",
        "followers": 24500000,
        "avg_likes": 920000,
        "avg_comments": 18000,
        "engagement_rate": 0.040,
        "is_verified": True
    },
    {
        "username": "kayla_itsines",
        "fullName": "Kayla Itsines",
        "category": "Fitness",
        "bio": "Co-founder of Sweat. Helping millions of women get fit with high-intensity HIIT workouts, strength training, core guides and healthy habits.",
        "followers": 16200000,
        "avg_likes": 85000,
        "avg_comments": 2200,
        "engagement_rate": 0.012,
        "is_verified": True
    },
    {
        "username": "pamela_rf",
        "fullName": "Pamela Reif",
        "category": "Fitness",
        "bio": "Fitness creator & cookbook author. Intense home workouts, booty burn, abs routines, dance cardio and clean nutritional snacks.",
        "followers": 9300000,
        "avg_likes": 180000,
        "avg_comments": 4500,
        "engagement_rate": 0.021,
        "is_verified": True
    },
    {
        "username": "simeonpanda",
        "fullName": "Simeon Panda",
        "category": "Fitness",
        "bio": "Fitness entrepreneur, bodybuilder and owner of Just Lift. Dedicated to intense weight training, aesthetic muscle building and discipline.",
        "followers": 8200000,
        "avg_likes": 75000,
        "avg_comments": 1900,
        "engagement_rate": 0.011,
        "is_verified": True
    },
    {
        "username": "jeffnippard",
        "fullName": "Jeff Nippard",
        "category": "Fitness",
        "bio": "Natural bodybuilder and science communicator. Evidence-based workout routines, hypertrophy biomechanics, squat and bench press technique.",
        "followers": 2100000,
        "avg_likes": 110000,
        "avg_comments": 3500,
        "engagement_rate": 0.055,
        "is_verified": True
    },
    {
        "username": "noeldeyzel_bodybuilder",
        "fullName": "Noel Deyzel",
        "category": "Fitness",
        "bio": "IFBB bodybuilder, gym motivation, fitness advice, wholesome gym culture, lifting heavy, form correction and personal growth.",
        "followers": 4600000,
        "avg_likes": 290000,
        "avg_comments": 8500,
        "engagement_rate": 0.066,
        "is_verified": True
    },
    {
        "username": "chloe_t",
        "fullName": "Chloe Ting",
        "category": "Fitness",
        "bio": "Home fitness challenges, 2-week shred, abs workout programs, full body cardio and healthy meal prep inspiration.",
        "followers": 2800000,
        "avg_likes": 65000,
        "avg_comments": 1800,
        "engagement_rate": 0.025,
        "is_verified": True
    },
    {
        "username": "bradleymartyn",
        "fullName": "Bradley Martyn",
        "category": "Fitness",
        "bio": "Owner of Zoo Culture Gym and Raw Gear. Heavy weightlifting, gym pranks, fitness podcast host and bodybuilding athlete.",
        "followers": 4400000,
        "avg_likes": 110000,
        "avg_comments": 3200,
        "engagement_rate": 0.027,
        "is_verified": True
    },
    {
        "username": "thebodycoach",
        "fullName": "Joe Wicks",
        "category": "Fitness",
        "bio": "The Body Coach. Lean in 15 creator, daily HIIT workouts, family fitness, home exercise routines and nutritious easy recipes.",
        "followers": 4700000,
        "avg_likes": 45000,
        "avg_comments": 1400,
        "engagement_rate": 0.012,
        "is_verified": True
    },
    {
        "username": "michelle_lewin",
        "fullName": "Michelle Lewin",
        "category": "Fitness",
        "bio": "Fitness model and workout athlete. Resistance training, gym apparel, glute exercises and active lifestyle motivation.",
        "followers": 15400000,
        "avg_likes": 60000,
        "avg_comments": 1500,
        "engagement_rate": 0.008,
        "is_verified": True
    },
    {
        "username": "gregdoucetteifbbpro",
        "fullName": "Greg Doucette",
        "category": "Fitness",
        "bio": "IFBB Pro bodybuilder, Guinness record holder, anabolic diet recipes, high-volume fat loss and harder than last time training.",
        "followers": 650000,
        "avg_likes": 28000,
        "avg_comments": 1100,
        "engagement_rate": 0.046,
        "is_verified": True
    },
    {
        "username": "calisthenicmovement",
        "fullName": "Calisthenics Movement",
        "category": "Fitness",
        "bio": "Bodyweight training specialists, muscle ups, gymnastics rings, handstands, calisthenics progression and core strength.",
        "followers": 1100000,
        "avg_likes": 50000,
        "avg_comments": 1200,
        "engagement_rate": 0.048,
        "is_verified": True
    },
    {
        "username": "krissycela",
        "fullName": "Krissy Cela",
        "category": "Fitness",
        "bio": "Founder of Oner Active and EvolveYou app. Empowering women through heavy strength training, gym consistency and fitness form.",
        "followers": 3400000,
        "avg_likes": 95000,
        "avg_comments": 2800,
        "engagement_rate": 0.030,
        "is_verified": True
    },
    {
        "username": "athleanx",
        "fullName": "Jeff Cavaliere",
        "category": "Fitness",
        "bio": "Physical therapist and strength coach. Injury-free athletic training, biomechanically sound muscle building, rotator cuff health and core workouts.",
        "followers": 2300000,
        "avg_likes": 60000,
        "avg_comments": 1700,
        "engagement_rate": 0.028,
        "is_verified": True
    },
    {
        "username": "demibagby",
        "fullName": "Demi Bagby",
        "category": "Fitness",
        "bio": "CrossFit athlete, ninja warrior, calisthenics powerhouse, acrobatics, functional fitness and extreme workout motivation.",
        "followers": 2600000,
        "avg_likes": 75000,
        "avg_comments": 2100,
        "engagement_rate": 0.031,
        "is_verified": True
    },

    # -------------------------------------------------------------
    # BEAUTY (15 creators)
    # -------------------------------------------------------------
    {
        "username": "nikkietutorials",
        "fullName": "Nikkie de Jager",
        "category": "Beauty",
        "bio": "Professional makeup artist & founder of Nimya. Transformative glam tutorials, beauty product testing, vibrant eye artistry and glowing skin.",
        "followers": 19100000,
        "avg_likes": 320000,
        "avg_comments": 7000,
        "engagement_rate": 0.018,
        "is_verified": True
    },
    {
        "username": "jamescharles",
        "fullName": "James Charles",
        "category": "Beauty",
        "bio": "Makeup artist and creative director of Painted. High glam cosmetics, color theory, beauty transformations and makeup tutorials.",
        "followers": 20800000,
        "avg_likes": 280000,
        "avg_comments": 6500,
        "engagement_rate": 0.015,
        "is_verified": True
    },
    {
        "username": "bretmanrock",
        "fullName": "Bretman Rock",
        "category": "Beauty",
        "bio": "Beauty guru, author and makeup personality. Flawless contouring, brow styling, beauty humor, tropical glow and skincare rituals.",
        "followers": 18700000,
        "avg_likes": 550000,
        "avg_comments": 11000,
        "engagement_rate": 0.032,
        "is_verified": True
    },
    {
        "username": "jeffreestar",
        "fullName": "Jeffree Star",
        "category": "Beauty",
        "bio": "Founder and CEO of Jeffree Star Cosmetics. Brutally honest makeup reviews, iconic liquid lipsticks, vibrant eyeshadow palettes and luxury beauty.",
        "followers": 13500000,
        "avg_likes": 180000,
        "avg_comments": 4000,
        "engagement_rate": 0.015,
        "is_verified": True
    },
    {
        "username": "patrickstarrr",
        "fullName": "Patrick Starrr",
        "category": "Beauty",
        "bio": "Celebrity makeup artist & founder of ONE/SIZE Beauty. Makeup is a one-size-fits-all. Full glam tutorials, setting powder magic and inclusivity.",
        "followers": 4400000,
        "avg_likes": 90000,
        "avg_comments": 2500,
        "engagement_rate": 0.022,
        "is_verified": True
    },
    {
        "username": "jackieaina",
        "fullName": "Jackie Aina",
        "category": "Beauty",
        "bio": "Founder of FORVR Mood. Beauty activist for inclusive shades, rich skincare routines, luxury fragrances, makeup techniques and glowy skin.",
        "followers": 1900000,
        "avg_likes": 65000,
        "avg_comments": 1900,
        "engagement_rate": 0.036,
        "is_verified": True
    },
    {
        "username": "mannymua733",
        "fullName": "Manny Gutierrez",
        "category": "Beauty",
        "bio": "Founder of Lunar Beauty. Boys in makeup, cut crease tutorials, cosmetics honest reviews, glam looks and beauty product launches.",
        "followers": 3900000,
        "avg_likes": 70000,
        "avg_comments": 1800,
        "engagement_rate": 0.020,
        "is_verified": True
    },
    {
        "username": "skincarebyhyram",
        "fullName": "Hyram Yarbro",
        "category": "Beauty",
        "bio": "Skincare specialist & founder of Selfless by Hyram. Educating on sunscreen, barrier repair, salicylic acid, hydrating serums and clean beauty.",
        "followers": 1050000,
        "avg_likes": 45000,
        "avg_comments": 1300,
        "engagement_rate": 0.045,
        "is_verified": True
    },
    {
        "username": "mikaylanogueira",
        "fullName": "Mikayla Nogueira",
        "category": "Beauty",
        "bio": "Professional makeup artist. Viral product testing, drugstore foundation gems, acne-covering techniques, lipstick swatches and honest reviews.",
        "followers": 2700000,
        "avg_likes": 150000,
        "avg_comments": 4200,
        "engagement_rate": 0.058,
        "is_verified": True
    },
    {
        "username": "makeupbymario",
        "fullName": "Mario Dedivanovic",
        "category": "Beauty",
        "bio": "Master makeup artist & founder of MAKEUP BY MARIO. Creator of iconic sculpted contouring, soft sculpting and Master Mattes palettes.",
        "followers": 14200000,
        "avg_likes": 110000,
        "avg_comments": 2800,
        "engagement_rate": 0.010,
        "is_verified": True
    },
    {
        "username": "charlottetilbury",
        "fullName": "Charlotte Tilbury",
        "category": "Beauty",
        "bio": "British celebrity makeup artist & beauty entrepreneur. Pillow Talk, Magic Cream, Hollywood Flawless Filter and red carpet glow.",
        "followers": 6400000,
        "avg_likes": 85000,
        "avg_comments": 2100,
        "engagement_rate": 0.015,
        "is_verified": True
    },
    {
        "username": "nikki_makeup",
        "fullName": "Nikki Wolff",
        "category": "Beauty",
        "bio": "Celebrity and editorial makeup artist. Glass skin masterclasses, laminated brows, sultry eyeliner and modern backstage beauty.",
        "followers": 1850000,
        "avg_likes": 50000,
        "avg_comments": 1400,
        "engagement_rate": 0.029,
        "is_verified": True
    },
    {
        "username": "hindash",
        "fullName": "Mohammed Hindash",
        "category": "Beauty",
        "bio": "Painter turned beauty visionary & founder of Hindash Cosmetics. Gradient makeup art, Beautopsy palette, editorial face mapping and elegance.",
        "followers": 1350000,
        "avg_likes": 55000,
        "avg_comments": 1500,
        "engagement_rate": 0.043,
        "is_verified": True
    },
    {
        "username": "desiperkins",
        "fullName": "Desi Perkins",
        "category": "Beauty",
        "bio": "Founder of Dezi Skin and Dezi Eyewear. Vitamin C serum glow, everyday radiant makeup routines, beauty tutorials and luxury lifestyle.",
        "followers": 4300000,
        "avg_likes": 95000,
        "avg_comments": 2400,
        "engagement_rate": 0.024,
        "is_verified": True
    },
    {
        "username": "tatcha",
        "fullName": "Tatcha Beauty",
        "category": "Beauty",
        "bio": "Japanese rituals for radiant skin. Dewy Skin Cream, Rice Wash, Camellia Cleansing Oil and timeless skincare formulas for healthy glow.",
        "followers": 1500000,
        "avg_likes": 28000,
        "avg_comments": 900,
        "engagement_rate": 0.021,
        "is_verified": True
    },

    # -------------------------------------------------------------
    # FASHION (15 creators)
    # -------------------------------------------------------------
    {
        "username": "chiaraferragni",
        "fullName": "Chiara Ferragni",
        "category": "Fashion",
        "bio": "Founder of The Blonde Salad & Chiara Ferragni Brand. High fashion runway front row, Milan Fashion Week, luxury styling and accessories.",
        "followers": 28800000,
        "avg_likes": 310000,
        "avg_comments": 6800,
        "engagement_rate": 0.012,
        "is_verified": True
    },
    {
        "username": "camilacoelho",
        "fullName": "Camila Coelho",
        "category": "Fashion",
        "bio": "Fashion designer & founder of Camila Coelho Collection. Paris Fashion Week, haute couture gowns, street style trends and luxury travel.",
        "followers": 10100000,
        "avg_likes": 95000,
        "avg_comments": 2300,
        "engagement_rate": 0.011,
        "is_verified": True
    },
    {
        "username": "aimeesong",
        "fullName": "Aimee Song",
        "category": "Fashion",
        "bio": "Fashion blogger behind Song of Style, NYT bestselling author. Chic minimalist tailoring, effortless everyday outfits and designer styling.",
        "followers": 730000,
        "avg_likes": 65000,
        "avg_comments": 1600,
        "engagement_rate": 0.010,
        "is_verified": True
    },
    {
        "username": "leoniehanne",
        "fullName": "Leonie Hanne",
        "category": "Fashion",
        "bio": "Couture fashion creator. Jaw-dropping Cannes red carpet gowns, Valentino, Fendi, Schiaparelli runway styling and haute couture aesthetic.",
        "followers": 4700000,
        "avg_likes": 120000,
        "avg_comments": 3100,
        "engagement_rate": 0.028,
        "is_verified": True
    },
    {
        "username": "oliviapalermo",
        "fullName": "Olivia Palermo",
        "category": "Fashion",
        "bio": "Fashion entrepreneur, model and style icon. Timeless uptown elegance, bespoke tailoring, accessory layering and modern classic styling.",
        "followers": 8300000,
        "avg_likes": 40000,
        "avg_comments": 1100,
        "engagement_rate": 0.006,
        "is_verified": True
    },
    {
        "username": "wisdm",
        "fullName": "Wisdom Kaye",
        "category": "Fashion",
        "bio": "Vogue's best-dressed guy on TikTok. High fashion editorial modeling, Rick Owens, vintage archives, 70s aesthetics and avant-garde styling.",
        "followers": 3100000,
        "avg_likes": 240000,
        "avg_comments": 6500,
        "engagement_rate": 0.080,
        "is_verified": True
    },
    {
        "username": "weworewhat",
        "fullName": "Danielle Bernstein",
        "category": "Fashion",
        "bio": "Founder & CEO of WeWoreWhat. New York street style, seasonal denim, swimwear, capsule wardrobe curations and fashion business.",
        "followers": 3200000,
        "avg_likes": 45000,
        "avg_comments": 1200,
        "engagement_rate": 0.015,
        "is_verified": True
    },
    {
        "username": "marianodivaio",
        "fullName": "Mariano Di Vaio",
        "category": "Fashion",
        "bio": "Italian menswear icon, model and MDV style founder. Bespoke Italian suits, classic gentlemen tailoring, street style and fashion elegance.",
        "followers": 7000000,
        "avg_likes": 80000,
        "avg_comments": 1900,
        "engagement_rate": 0.013,
        "is_verified": True
    },
    {
        "username": "lukasabbat",
        "fullName": "Luka Sabbat",
        "category": "Fashion",
        "bio": "Model, creative director and style icon. High fashion streetwear, avant-garde Met Gala looks, vintage leather jackets and luxury designer campaigns.",
        "followers": 3800000,
        "avg_likes": 90000,
        "avg_comments": 2200,
        "engagement_rate": 0.026,
        "is_verified": True
    },
    {
        "username": "emmachamberlain",
        "fullName": "Emma Chamberlain",
        "category": "Fashion",
        "bio": "Fashion trendsetter, Met Gala red carpet host, Louis Vuitton & Cartier brand ambassador. Vintage thrift styling and runway chic.",
        "followers": 15300000,
        "avg_likes": 650000,
        "avg_comments": 12000,
        "engagement_rate": 0.045,
        "is_verified": True
    },
    {
        "username": "jeannedamas",
        "fullName": "Jeanne Damas",
        "category": "Fashion",
        "bio": "Founder and artistic director of Rouje. The epitome of Parisian chic, French girl wardrobe, floral wrap dresses and vintage Parisian style.",
        "followers": 1500000,
        "avg_likes": 35000,
        "avg_comments": 950,
        "engagement_rate": 0.025,
        "is_verified": True
    },
    {
        "username": "tesschristinexo",
        "fullName": "Tess Christine",
        "category": "Fashion",
        "bio": "New York city style lookbooks, seasonal autumn/winter coats, vintage flea market finds and wearable aesthetic outfit guides.",
        "followers": 710000,
        "avg_likes": 28000,
        "avg_comments": 800,
        "engagement_rate": 0.042,
        "is_verified": True
    },
    {
        "username": "tamara",
        "fullName": "Tamara Kalinic",
        "category": "Fashion",
        "bio": "The Glam & Glitter. International luxury fashion influencer, Hermès collector, front row at Chanel and Dior, fine jewelry styling.",
        "followers": 1700000,
        "avg_likes": 48000,
        "avg_comments": 1300,
        "engagement_rate": 0.030,
        "is_verified": True
    },
    {
        "username": "rowisingh",
        "fullName": "Rowi Singh",
        "category": "Fashion",
        "bio": "Maximalist fashion artist and stylist. Vibrant color blocking, Y2K accessories, high fashion streetwear and bold creative styling.",
        "followers": 420000,
        "avg_likes": 26000,
        "avg_comments": 900,
        "engagement_rate": 0.065,
        "is_verified": True
    },
    {
        "username": "rickeythompson",
        "fullName": "Rickey Thompson",
        "category": "Fashion",
        "bio": "Runway model, fashion icon and performer. High fashion catwalks, Alexander Wang, luxury street outfits, flamboyant style and vibrant energy.",
        "followers": 5100000,
        "avg_likes": 180000,
        "avg_comments": 4500,
        "engagement_rate": 0.037,
        "is_verified": True
    }
]

def main():
    print(f"[*] Starting creator expansion for 4 key categories...")
    print(f"[*] Total new creators to index: {len(NEW_CREATORS)}")

    recommender = CreatorRecommender()
    if not recommender.load_index(INDEX_FILE):
        print(f"[*] Index not found, building from catalog...")
        recommender.build_creator_catalog()

    curr_df = recommender.creators_df
    print(f"[*] Initial creators in index: {len(curr_df)}")

    # Prepare rows for creators_df
    new_rows = []
    for c in NEW_CREATORS:
        uname = c["username"].strip().lower()
        full_name = c["fullName"]
        cat = c["category"]
        bio = c["bio"]
        followers = float(c["followers"])
        tier = get_follower_tier(followers)
        eng_rate = float(c["engagement_rate"])
        avg_likes = float(c["avg_likes"])
        avg_comments = float(c["avg_comments"])

        doc_parts = [
            f"Creator @{uname}",
            clean_text(full_name),
            f"Category: {cat}",
            clean_text(bio)
        ]
        content_doc = " ".join([p for p in doc_parts if p])

        row_dict = {
            "username": uname,
            "fullName": full_name,
            "biography": bio,
            "bio": bio,
            "category": cat,
            "businessCategoryName": cat,
            "followers": followers,
            "followersCount": followers,
            "followsCount": 250.0,
            "following": 250.0,
            "posts_count": 350.0,
            "postsCount": 350.0,
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "engagement_rate": eng_rate,
            "follower_tier": tier,
            "content_document": content_doc,
            "is_verified": bool(c.get("is_verified", True)),
            "verified": bool(c.get("is_verified", True)),
            "is_business": True,
            "isBusinessAccount": True,
            "profilePicUrl": "",
            "profilePicUrlHD": "",
            "aggregated_captions": "",
            "aggregated_hashtags": "",
            "tracked_posts_count": 0
        }
        new_rows.append(row_dict)

    new_df = pd.DataFrame(new_rows)

    # Merge and deduplicate by username
    combined_df = pd.concat([curr_df, new_df], ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=["username"], keep="last").reset_index(drop=True)

    recommender.creators_df = combined_df
    recommender.fit()
    recommender.save_index(INDEX_FILE)
    print(f"[✓] Updated vector index saved with {len(recommender.creators_df)} creators!")

    # Also append to creator_profiles.csv
    if os.path.exists(PROFILES_CSV):
        existing_profiles = pd.read_csv(PROFILES_CSV)
        profiles_to_append = []
        for c in NEW_CREATORS:
            uname = c["username"].strip().lower()
            if "username" in existing_profiles.columns and (existing_profiles["username"].astype(str).str.lower() == uname).any():
                continue
            profiles_to_append.append({
                "username": uname,
                "fullName": c["fullName"],
                "biography": c["bio"],
                "businessCategoryName": c["category"],
                "followersCount": float(c["followers"]),
                "followsCount": 250.0,
                "postsCount": 350.0,
                "verified": bool(c.get("is_verified", True))
            })
        if profiles_to_append:
            merged_profiles = pd.concat([existing_profiles, pd.DataFrame(profiles_to_append)], ignore_index=True)
            merged_profiles.to_csv(PROFILES_CSV, index=False)
            print(f"[✓] Appended {len(profiles_to_append)} profiles to {PROFILES_CSV}")

    # Check breakdown
    print("\n--- NEW CATALOG CATEGORY DISTRIBUTION ---")
    for category_name in ["Fashion", "Beauty", "Technology", "Fitness"]:
        matched = combined_df[combined_df["category"].astype(str).str.contains(category_name, case=False, na=False)]
        print(f"  • {category_name}: {len(matched)} creators")
    print(f"Total Creators in Catalog: {len(combined_df)}\n")

    # Sync to Supabase table if active
    try:
        creators_payload = combined_df.to_dict(orient="records")
        synced = database.sync_creators_from_catalog(creators_payload)
        print(f"[✓] Successfully synced {synced} creators to database table.")
    except Exception as e:
        print(f"[!] Database sync note: {e}")

if __name__ == "__main__":
    main()
