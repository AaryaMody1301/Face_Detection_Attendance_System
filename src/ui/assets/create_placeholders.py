"""Generate simple development placeholder images beside this script."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ASSET_DIR = Path(__file__).resolve().parent


def create_placeholders(output_dir: str | Path = ASSET_DIR) -> tuple[Path, Path]:
    """Create portable logo/login placeholder images for development use."""
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    logo_path = destination / "logo.png"
    logo_image = Image.new("RGB", (100, 100), "white")
    logo_draw = ImageDraw.Draw(logo_image)
    logo_draw.ellipse((25, 25, 75, 75), fill="blue", outline="black")
    logo_image.save(logo_path)

    login_path = destination / "login_illustration.png"
    login_image = Image.new("RGB", (350, 350), "white")
    login_draw = ImageDraw.Draw(login_image)
    login_draw.rectangle((50, 50, 300, 300), fill="green", outline="black")
    login_image.save(login_path)

    return logo_path, login_path


if __name__ == "__main__":
    logo, login = create_placeholders()
    print(f"Created {logo}")
    print(f"Created {login}")
