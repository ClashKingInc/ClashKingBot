from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps


# Configuration
background_path = 'warbkpng.png'  # Path to your background image
output_path = 'clash_image.png'
font_path = 'SCmagic.ttf'  # Path to your font file
font_size = 20
overlay_opacity = 128  # 0 (transparent) to 255 (opaque)

# Load background image
background = Image.open(background_path).convert('RGBA')
background = background.resize((1920, 1080))

# Create overlay
overlay = Image.new('RGBA', background.size, (0, 0, 0, overlay_opacity))

# Combine background and overlay
combined = Image.alpha_composite(background, overlay)

# Draw sections
draw = ImageDraw.Draw(combined)
font = ImageFont.truetype(font_path, font_size)

sections = ['Troops', 'Spells', 'Sieges', 'Heroes']
section_height = 200
padding = 20
start_y = 50

for i, section in enumerate(sections):
    y = start_y + i * (section_height + padding)
    draw.rectangle([padding, y, 1920 - padding, y + section_height], outline='white', width=2)
    draw.text((padding + 10, y + 10), section, fill='white', font=font)

# Memory cache for images
image_cache = {}


# Function to fetch and cache images
def fetch_image(url):
    if url not in image_cache:
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            img = Image.open(BytesIO(response.content))
            image_cache[url] = img
        except (requests.RequestException, Image.UnidentifiedImageError) as e:
            print(f'Error fetching image from {url}: {e}')
            img = Image.new('RGBA', (100, 100), (255, 0, 0, 0))  # Placeholder image in case of error
    else:
        img = image_cache[url]
    return img


# Function to draw items
def draw_item(draw, x, y, url, item_name, item_level, item_state, item_cost, font):
    item_image = fetch_image(url).resize((100, 100))

    if item_state == 'max_th':
        border_color = 'silver'
    elif item_state == 'max_game':
        border_color = 'gold'
    elif item_state == 'rushed':
        border_color = 'red'
    else:
        border_color = None

    if border_color:
        border = ImageOps.expand(item_image, border=5, fill=border_color)
    else:
        border = item_image

    combined.paste(border, (x, y), border)

    draw.text((x, y + 110), item_name, fill='white', font=font)
    draw.text((x + 70, y), str(item_level), fill='white', font=font)

    if item_cost:
        cost_image = fetch_image(item_cost['image']).resize((20, 20))
        combined.paste(cost_image, (x, y - 25), cost_image)
        draw.text((x + 25, y - 25), f"{item_cost['amount']}M", fill='white', font=font)


# Example usage
item_data = [
    {
        'url': 'https://static.wikia.nocookie.net/clashofclans/images/8/87/Avatar_Barbarian.png/revision/latest?cb=20170525070200',  # Replace with actual URL
        'name': 'Barbarian',
        'level': 5,
        'state': 'upgradeable',  # Options: 'max_th', 'max_game', 'rushed', 'upgradeable'
        'cost': {
            'image': 'https://static.wikia.nocookie.net/clashofclans/images/4/43/Elixir.png',
            'amount': 1.5,
        },  # Replace with actual URL
    },
    # Add more items as needed
]

# Draw items for the first section as an example
x, y = padding + 10, start_y + section_height + padding + 10
for item in item_data:
    draw_item(draw, x, y, item['url'], item['name'], item['level'], item['state'], item['cost'], font)
    x += 120  # Adjust spacing as needed

# Save the final image
combined.save(output_path)

print(f'Image saved as {output_path}')
