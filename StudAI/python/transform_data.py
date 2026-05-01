import json
import requests
from datetime import datetime
from pathlib import Path


def get_residences_from_studyrama():
    """Fetch residence data from Studyrama API"""
    url = "https://logement.studyrama.com/api/annuaire?center=1&distance=30&surfacemin=9&loyermax=2000&typeslogement=&meuble=&type=&tri=prix&lat=48.8588897&lng=2.3200410217200766"
    headers = {
        "accept": "*/*",
        "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin"
    }
    
    response = requests.get(url, headers=headers, allow_redirects=True)
    data = response.json()
    
    return data


def transform_residence(residence):
    """Transform Studyrama residence data to our Housing format"""
    # Extract provider from logo or title
    provider = None
    if residence.get('logo_annonceur') and residence['logo_annonceur'].get('alt'):
        provider = residence['logo_annonceur']['alt'].replace('Logo ', '').strip()
    
    # Build full URL
    base_url = "https://logement.studyrama.com"
    full_url = base_url + residence.get('url', '') if residence.get('url') else None
    
    # Get image URL
    image_url = None
    if residence.get('image') and residence['image'].get('image'):
        image_url = residence['image']['image']
    
    # Convert string numbers to actual numbers
    rent = None
    if residence.get('loyer'):
        try:
            rent = int(residence['loyer'])
        except (ValueError, TypeError):
            pass
    
    surface = None
    if residence.get('surface'):
        try:
            surface = int(residence['surface'])
        except (ValueError, TypeError):
            pass
    
    # Create transformed object
    transformed = {
        "id": f"studyrama-{residence.get('id', '')}",
        "name": residence.get('titre', 'Unknown'),
        "provider": provider,
        "lat": residence.get('lat'),
        "lng": residence.get('lng'),
        "rent": rent,
        "surface": surface,
        "type": residence.get('type'),
        "distance": residence.get('distance'),
        "url": full_url,
        "imageUrl": image_url,
        "lastUpdated": datetime.now().strftime("%Y-%m-%d")
    }
    
    return transformed


def save_housing_data():
    """Fetch, transform, and save housing data to JSON file"""
    print("Fetching data from Studyrama API...")
    residences = get_residences_from_studyrama()
    
    print(f"Found {len(residences)} residences")
    
    print("Transforming data...")
    transformed_data = [transform_residence(r) for r in residences]
    
    # Filter out any residences without valid coordinates
    valid_data = [r for r in transformed_data if r['lat'] and r['lng']]
    print(f"Valid residences with coordinates: {len(valid_data)}")
    
    # Save to JSON file
    output_path = Path(__file__).parent.parent / "App" / "public" / "data" / "housing.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Saving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(valid_data, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully saved {len(valid_data)} residences to housing.json")
    
    # Print some stats
    providers = {}
    for r in valid_data:
        provider = r.get('provider', 'Unknown')
        providers[provider] = providers.get(provider, 0) + 1
    
    print("\nResidences by provider:")
    for provider, count in sorted(providers.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {provider}: {count}")
    
    return valid_data


if __name__ == "__main__":
    save_housing_data()
