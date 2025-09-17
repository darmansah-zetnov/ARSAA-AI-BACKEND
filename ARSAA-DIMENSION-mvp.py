#!/usr/bin/env python3
"""
ARSAA-DIMENSION-mvp.py
ARSAA Dimension MVP - Property Analysis Platform
Version: 1.0 MVP - Production Ready
Focus: Jabodetabek Property Intelligence
"""

import os
import sys
import time
import json
import requests
import feedparser
from datetime import datetime

# ===============================
# ARSAA AI CONFIGURATION
# ===============================
class ARSAAConfig:
    # API Configuration
    GEMINI_KEY = os.environ.get("GEMINI_KEY") or os.environ.get("GEMINI_API_KEY")
    NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY") or os.environ.get("NEWS_API_KEY")
    
    # AI Model Configuration - Updated for stability
    MODEL = "gemini-2.0-flash"  # More stable than experimental
    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    
    # Geolocation Configuration
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "ARSAA-Dimension-AI/2.0 (+https://arsaa.ai)"
    
    # Jabodetabek Bounding Box (West, North, East, South)
    JABODETABEK_BBOX = "106.5,-6.0,107.2,-7.1"
    
    # News Sources
    RSS_FEEDS = [
        "https://www.kompas.com/properti/rss",
        "https://finance.detik.com/properti/rss", 
        "https://www.kontan.co.id/rss/properti",
        "https://ekonomi.bisnis.com/rss"
    ]
    
    # Risk Assessment Parameters
    RISK_WEIGHTS = {
        'flood': 0.25,
        'earthquake': 0.15,
        'legal': 0.30,
        'crime': 0.15,
        'double_listing': 0.10,
        'accessibility': 0.05
    }

# ===============================
# DEPENDENCY & SYSTEM CHECKS
# ===============================
class SystemChecker:
    @staticmethod
    def check_dependencies():
        """Check if all required packages are available"""
        required_packages = ['requests', 'feedparser']
        missing = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)
        
        if missing:
            print(f"❌ Missing packages: {', '.join(missing)}")
            print(f"🔧 Install with: pip install {' '.join(missing)}")
            return False
        
        print("✅ All dependencies satisfied")
        return True
    
    @staticmethod
    def validate_api_keys():
        """Validate API keys format and availability"""
        print("\n🔑 API KEY VALIDATION")
        print("=" * 40)
        
        # Gemini API Validation (Required)
        if ARSAAConfig.GEMINI_KEY:
            if len(ARSAAConfig.GEMINI_KEY) > 30 and ARSAAConfig.GEMINI_KEY.startswith('AIzaSy'):
                print("✅ Gemini API: Valid format")
                gemini_status = True
            else:
                print("❌ Gemini API: Invalid format")
                gemini_status = False
        else:
            print("❌ Gemini API: Missing")
            gemini_status = False
        
        # NewsAPI Validation (Optional)
        if ARSAAConfig.NEWSAPI_KEY:
            if len(ARSAAConfig.NEWSAPI_KEY) == 32:
                print("✅ NewsAPI: Valid format")
            else:
                print("⚠️  NewsAPI: Invalid format")
        else:
            print("⚠️  NewsAPI: Missing (will use RSS fallback)")
        
        return gemini_status

# ===============================
# GEOCODING SERVICE
# ===============================
class GeocodingService:
    @staticmethod
    def geocode_address(address):
        """Geocode address using Nominatim with Jabodetabek focus"""
        params = {
            "q": address + ", Indonesia",
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 3,
            "viewbox": ARSAAConfig.JABODETABEK_BBOX,
            "bounded": 1
        }
        
        headers = {"User-Agent": ARSAAConfig.USER_AGENT}
        
        try:
            response = requests.get(
                ARSAAConfig.NOMINATIM_URL, 
                params=params, 
                headers=headers, 
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return None
            
            # Get the best match
            best_match = data[0]
            
            return {
                "display_name": best_match.get("display_name", ""),
                "latitude": float(best_match.get("lat", 0)),
                "longitude": float(best_match.get("lon", 0)),
                "address_components": best_match.get("address", {}),
                "osm_id": best_match.get("osm_id", ""),
                "confidence": len(data)  # More results = lower confidence
            }
            
        except Exception as e:
            print(f"⚠️ Geocoding error: {e}")
            return None

# ===============================
# NEWS INTELLIGENCE SERVICE  
# ===============================
class NewsService:
    @staticmethod
    def fetch_newsapi_data(city="Jakarta", limit=5):
        """Fetch property news from NewsAPI"""
        if not ARSAAConfig.NEWSAPI_KEY:
            return []
        
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": f"properti {city} OR real estate {city} OR perumahan {city}",
            "language": "id",
            "sortBy": "publishedAt",
            "pageSize": limit,
            "apiKey": ARSAAConfig.NEWSAPI_KEY
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "error":
                print(f"❌ NewsAPI Error: {data.get('message')}")
                return []
            
            articles = []
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "published": article.get("publishedAt", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "description": article.get("description", "")[:200]
                })
            
            return articles
            
        except Exception as e:
            print(f"⚠️ NewsAPI error: {e}")
            return []
    
    @staticmethod
    def fetch_rss_feeds(limit_per_feed=3):
        """Fetch property news from RSS feeds"""
        all_articles = []
        
        for feed_url in ARSAAConfig.RSS_FEEDS:
            try:
                print(f"📡 Fetching: {feed_url.split('/')[2]}")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:limit_per_feed]:
                    all_articles.append({
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "source": feed.feed.get("title", "RSS Feed"),
                        "description": (entry.get("summary", "") or "")[:200]
                    })
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"⚠️ RSS error for {feed_url}: {e}")
                continue
        
        return all_articles

# ===============================
# GEMINI AI SERVICE
# ===============================
class GeminiAI:
    @staticmethod
    def create_analysis_prompt(property_data, geo_data, news_data):
        """Create structured prompt for Gemini AI analysis"""
        
        # Prepare news context
        news_context = ""
        for article in news_data[:5]:
            title = article.get('title', 'Unknown')
            source = article.get('source', '')
            news_context += f"• {title} - {source}\n"
        
        # Determine city context
        location_name = geo_data.get('display_name', property_data['address'])
        city_context = GeminiAI._extract_city_context(location_name)
        
        prompt = f"""
Anda adalah ARSAA AI, sistem analisis properti terdepan untuk kawasan Jabodetabek.

=== DATA PROPERTI ===
Alamat: {property_data['address']}
Lokasi Terverifikasi: {location_name}
Koordinat: {geo_data.get('latitude', 'N/A')}, {geo_data.get('longitude', 'N/A')}
Konteks Wilayah: {city_context}

=== PENILAIAN RISIKO USER ===
• Risiko Banjir: {property_data.get('flood_risk', 'tidak diketahui')}
• Risiko Gempa: {property_data.get('earthquake_risk', 'tidak diketahui')}
• Status Legal: {property_data.get('legal_status', 'tidak diketahui')}
• Double Listing: {property_data.get('double_listing', 'tidak diketahui')}
• Tingkat Kriminalitas: {property_data.get('crime_level', 'tidak diketahui')}

=== FASILITAS & AKSES ===
Fasilitas: {property_data.get('facilities', 'Tidak disebutkan')}
Akses Transportasi: {property_data.get('transport_access', 'Tidak disebutkan')}

=== INTELIGENS BERITA TERKINI ===
{news_context if news_context else 'Tidak ada berita relevan ditemukan.'}

=== INSTRUKSI ANALISIS ===
Sebagai ARSAA AI, berikan analisis komprehensif dalam format JSON yang valid (tanpa markdown):

{{
  "trust_score": [integer 0-100, skor kepercayaan investasi],
  "risk_analysis": {{
    "flood": [integer 0-100, 0=aman, 100=sangat berisiko],
    "earthquake": [integer 0-100],
    "legal": [integer 0-100], 
    "crime": [integer 0-100],
    "double_listing": [integer 0-100],
    "accessibility": [integer 0-100]
  }},
  "market_insights": {{
    "price_trend": "[naik/stabil/turun]",
    "demand_level": "[tinggi/sedang/rendah]", 
    "investment_grade": "[A/B/C/D]"
  }},
  "executive_summary": "[Ringkasan eksekutif 6-8 kalimat untuk investor property, gunakan konteks berita dan lokasi spesifik]",
  "recommendations": [
    "[Rekomendasi aksi 1]",
    "[Rekomendasi aksi 2]", 
    "[Rekomendasi aksi 3]",
    "[Rekomendasi aksi 4]"
  ],
  "risk_factors": [
    "[Faktor risiko utama 1]",
    "[Faktor risiko utama 2]",
    "[Faktor risiko utama 3]"
  ],
  "competitive_advantages": [
    "[Keunggulan kompetitif 1]",
    "[Keunggulan kompetitif 2]"
  ]
}}

Gunakan pengetahuan mendalam tentang pasar properti Jabodetabek, tren infrastruktur, dan analisis risiko profesional.
"""
        return prompt
    
    @staticmethod
    def _extract_city_context(location_name):
        """Extract city context from location name"""
        location_lower = location_name.lower()
        
        city_mapping = {
            "jakarta": "DKI Jakarta - Pusat bisnis dan pemerintahan",
            "tangerang selatan": "Tangerang Selatan - Area berkembang dengan infrastruktur modern", 
            "tangerang": "Tangerang - Kawasan industri dan residential",
            "bekasi": "Bekasi - Buffer zone Jakarta dengan pertumbuhan pesat",
            "bogor": "Bogor - Area sejuk dengan akses ke Jakarta",
            "depok": "Depok - Kota satelit dengan banyak universitas"
        }
        
        for city, context in city_mapping.items():
            if city in location_lower:
                return context
        
        return "Area Jabodetabek - Kawasan metropolitan Jakarta"
    
    @staticmethod
    def call_gemini_api(prompt):
        """Call Gemini API with error handling"""
        if not ARSAAConfig.GEMINI_KEY:
            raise RuntimeError("❌ Gemini API key not configured")
        
        url = f"{ARSAAConfig.GEMINI_URL}/{ARSAAConfig.MODEL}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": ARSAAConfig.GEMINI_KEY
        }
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 4096,
                "topP": 0.8,
                "topK": 40
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                print(f"❌ Gemini API Error: {data['error']}")
                return None
            
            # Extract response text
            return data["candidates"][0]["content"]["parts"][0]["text"]
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"❌ Response parsing error: {e}")
            return None

# ===============================
# JSON PROCESSING SERVICE
# ===============================
class JSONProcessor:
    @staticmethod
    def extract_and_parse_json(text):
        """Extract and parse JSON from AI response"""
        if not text or "{" not in text:
            return None
        
        # Find JSON boundaries
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        
        if start_idx == -1 or end_idx == -1:
            return None
        
        json_candidate = text[start_idx:end_idx + 1]
        
        # Try direct parsing first
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            pass
        
        # Clean up common JSON issues
        import re
        
        # Remove trailing commas
        json_candidate = re.sub(r',\s*}', '}', json_candidate)
        json_candidate = re.sub(r',\s*]', ']', json_candidate)
        
        # Fix line breaks in strings
        json_candidate = re.sub(r'"\s*\n\s*"', '" "', json_candidate)
        
        # Try parsing again
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing failed: {e}")
            return None

# ===============================
# MAIN APPLICATION CLASS
# ===============================
class ARSAADimension:
    def __init__(self):
        self.version = "1.0 MVP"
        self.session_id = int(time.time())
        
    def display_welcome(self):
        """Display welcome screen"""
        print("🏢" + "=" * 55 + "🏢")
        print("      ARSAA DIMENSION MVP - PROPERTY INTELLIGENCE")
        print(f"                 Version {self.version}")
        print("🎯" + "=" * 55 + "🎯")
        print("📍 Focus Area: JABODETABEK (Jakarta, Bogor, Depok, Tangerang, Bekasi)")
        print("🤖 Powered by: Gemini AI + Real-time News Intelligence")
        print("📊 Features: Risk Analysis | Market Insights | Investment Recommendations")
        print("=" * 64)
    
    def collect_user_input(self):
        """Collect property data from user"""
        print("\n📝 INPUT DATA PROPERTI")
        print("-" * 30)
        
        # Basic property info
        address = input("🏠 Alamat properti (contoh: 'BSD City, Tangerang Selatan'):\n> ").strip()
        if not address:
            print("❌ Alamat tidak boleh kosong")
            sys.exit(1)
        
        print("\n⚠️  PENILAIAN RISIKO (tekan Enter untuk default)")
        print("-" * 45)
        
        # Risk assessments
        flood_risk = input("🌊 Risiko Banjir [rendah/sedang/tinggi] (default: sedang): ").strip() or "sedang"
        earthquake_risk = input("🌍 Risiko Gempa [rendah/sedang/tinggi] (default: sedang): ").strip() or "sedang"
        legal_status = input("📜 Status Legal [lengkap/tidak lengkap] (default: lengkap): ").strip() or "lengkap"
        double_listing = input("🔄 Double Listing [ya/tidak] (default: tidak): ").strip() or "tidak"
        crime_level = input("🚨 Tingkat Kriminalitas [rendah/sedang/tinggi] (default: sedang): ").strip() or "sedang"
        
        print("\n🏗️  INFO TAMBAHAN (opsional)")
        print("-" * 30)
        
        facilities = input("🏪 Fasilitas sekitar: ").strip() or ""
        transport_access = input("🚌 Akses transportasi: ").strip() or ""
        
        return {
            "address": address,
            "flood_risk": flood_risk,
            "earthquake_risk": earthquake_risk,
            "legal_status": legal_status,
            "double_listing": double_listing,
            "crime_level": crime_level,
            "facilities": facilities,
            "transport_access": transport_access,
            "timestamp": datetime.now().isoformat()
        }
    
    def process_geolocation(self, address):
        """Process geolocation for the address"""
        print(f"\n🗺️  GEOCODING ANALYSIS")
        print("-" * 25)
        print(f"📍 Mencari lokasi: {address}")
        
        geo_data = GeocodingService.geocode_address(address)
        
        if geo_data:
            print(f"✅ Lokasi ditemukan: {geo_data['display_name']}")
            print(f"📌 Koordinat: {geo_data['latitude']:.4f}, {geo_data['longitude']:.4f}")
            return geo_data
        else:
            print("⚠️ Lokasi tidak ditemukan di Jabodetabek, menggunakan estimasi")
            return {
                "display_name": f"Area {address} (estimasi)",
                "latitude": -6.2,
                "longitude": 106.8,
                "confidence": 0
            }
    
    def gather_market_intelligence(self, geo_data):
        """Gather news and market intelligence"""
        print(f"\n📰 MARKET INTELLIGENCE GATHERING")
        print("-" * 35)
        
        # Extract city for news search
        city = "Jakarta"  # default
        location_name = geo_data.get('display_name', '').lower()
        
        city_keywords = {
            'tangerang selatan': 'Tangerang Selatan',
            'tangerang': 'Tangerang', 
            'bekasi': 'Bekasi',
            'bogor': 'Bogor',
            'depok': 'Depok'
        }
        
        for keyword, city_name in city_keywords.items():
            if keyword in location_name:
                city = city_name
                break
        
        print(f"🔍 Target pencarian: {city}")
        
        news_data = []
        
        # Try NewsAPI first
        if ARSAAConfig.NEWSAPI_KEY:
            print("📡 Mengakses NewsAPI...")
            news_data = NewsService.fetch_newsapi_data(city)
        
        # Fallback to RSS feeds
        if not news_data:
            print("📡 Menggunakan RSS feeds...")
            news_data = NewsService.fetch_rss_feeds()
        
        print(f"✅ Berhasil mengumpulkan {len(news_data)} berita properti")
        return news_data
    
    def run_ai_analysis(self, property_data, geo_data, news_data):
        """Run AI analysis using Gemini"""
        print(f"\n🤖 ARSAA AI ANALYSIS ENGINE")
        print("-" * 32)
        print("⚙️  Memproses data dengan Gemini AI...")
        
        # Create analysis prompt
        prompt = GeminiAI.create_analysis_prompt(property_data, geo_data, news_data)
        
        # Call Gemini API
        ai_response = GeminiAI.call_gemini_api(prompt)
        
        if not ai_response:
            print("❌ Gagal mendapatkan respons dari AI")
            return None
        
        # Parse JSON response
        analysis_result = JSONProcessor.extract_and_parse_json(ai_response)
        
        if analysis_result:
            print("✅ Analisis AI berhasil diproses")
            return analysis_result, ai_response
        else:
            print("⚠️ Gagal memparse hasil AI, menyimpan raw response")
            return None, ai_response
    
    def display_analysis_results(self, analysis_result):
        """Display formatted analysis results"""
        print("\n" + "🎯" * 25)
        print("   ARSAA DIMENSION - HASIL ANALISIS PROPERTI")
        print("🎯" * 25)
        
        # Trust Score
        trust_score = analysis_result.get('trust_score', 0)
        print(f"\n🏆 TRUST SCORE: {trust_score}/100")
        
        if trust_score >= 80:
            print("   Status: 🟢 SANGAT DIREKOMENDASIKAN")
        elif trust_score >= 60:
            print("   Status: 🟡 DIREKOMENDASIKAN DENGAN CATATAN")
        else: print("   Status: 🔴 PERLU PERTIMBANGAN MENDALAM")
        
        # Risk Analysis
        risk_analysis = analysis_result.get('risk_analysis', {})
        print(f"\n📊 ANALISIS RISIKO:")
        for risk_type, score in risk_analysis.items():
            risk_name = risk_type.replace('_', ' ').title()
            if score <= 30:
                status = "🟢 Rendah"
            elif score <= 60:
                status = "🟡 Sedang" 
            else:
                status = "🔴 Tinggi"
            print(f"   {risk_name}: {score}/100 {status}")
        
        # Market Insights
        market_insights = analysis_result.get('market_insights', {})
        if market_insights:
            print(f"\n📈 MARKET INSIGHTS:")
            print(f"   Tren Harga: {market_insights.get('price_trend', 'N/A').upper()}")
            print(f"   Level Demand: {market_insights.get('demand_level', 'N/A').upper()}")
            print(f"   Investment Grade: {market_insights.get('investment_grade', 'N/A')}")
        
        # Executive Summary
        summary = analysis_result.get('executive_summary', '')
        if summary:
            print(f"\n📋 RINGKASAN EKSEKUTIF:")
            print(f"   {summary}")
        
        # Recommendations
        recommendations = analysis_result.get('recommendations', [])
        if recommendations:
            print(f"\n💡 REKOMENDASI STRATEGIS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        # Risk Factors
        risk_factors = analysis_result.get('risk_factors', [])
        if risk_factors:
            print(f"\n⚠️  FAKTOR RISIKO UTAMA:")
            for factor in risk_factors:
                print(f"   • {factor}")
        
        # Competitive Advantages
        advantages = analysis_result.get('competitive_advantages', [])
        if advantages:
            print(f"\n✨ KEUNGGULAN KOMPETITIF:")
            for advantage in advantages:
                print(f"   • {advantage}")
    
    def save_analysis_report(self, property_data, geo_data, news_data, analysis_result, raw_response):
        """Save comprehensive analysis report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"arsaa_mvp_analysis_{timestamp}.json"
        
        report = {
            "arsaa_version": self.version,
            "session_id": self.session_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "property_input": property_data,
            "geolocation_data": geo_data,
            "news_intelligence": {
                "total_articles": len(news_data),
                "articles": news_data[:10]  # Save top 10 articles
            },
            "ai_analysis": analysis_result,
            "raw_ai_response": raw_response,
            "system_info": {
                "model": ARSAAConfig.MODEL,
                "user_agent": ARSAAConfig.USER_AGENT
            }
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 LAPORAN TERSIMPAN: {filename}")
            print(f"📁 Lokasi: {os.path.abspath(filename)}")
            return filename
        
        except Exception as e:
            print(f"⚠️ Gagal menyimpan laporan: {e}")
            return None
    
    def run(self):
        """Main application runner"""
        # Display welcome
        self.display_welcome()
        
        # System checks
        print("\n🔧 SYSTEM INITIALIZATION")
        print("-" * 25)
        
        if not SystemChecker.check_dependencies():
            sys.exit(1)
        
        if not SystemChecker.validate_api_keys():
            print("\n❌ API configuration required:")
            print("   export GEMINI_KEY='your-gemini-api-key'")
            print("   export NEWSAPI_KEY='your-newsapi-key'  # optional")
            sys.exit(1)
        
        print("✅ System ready for analysis")
        
        try:
            # Collect user input
            property_data = self.collect_user_input()
            
            # Process geolocation
            geo_data = self.process_geolocation(property_data['address'])
            
            # Gather market intelligence
            news_data = self.gather_market_intelligence(geo_data)
            
            # Run AI analysis
            result = self.run_ai_analysis(property_data, geo_data, news_data)
            
            if result:
                analysis_result, raw_response = result
                
                if analysis_result:
                    # Display results
                    self.display_analysis_results(analysis_result)
                    
                    # Save report
                    self.save_analysis_report(
                        property_data, geo_data, news_data, 
                        analysis_result, raw_response
                    )
                else:
                    # Save raw response if parsing failed
                    filename = f"ARSAA_Raw_{int(time.time())}.txt"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(raw_response)
                    print(f"💾 Raw response saved: {filename}")
            else:
                print("❌ Analysis failed - please check your API configuration")
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Analysis interrupted by user")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n🏢 Terima kasih telah menggunakan ARSAA Dimension AI!")

# ===============================
# MAIN ENTRY POINT
# ===============================
if __name__ == "__main__":
    app = ARSAADimension()
    app.run()
