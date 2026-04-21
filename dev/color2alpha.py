import numpy as np
from PIL import Image


def gimp_color_to_alpha_exact(image_path, target_color=(0, 0, 0), output_path=None):
    """
    Exact replication of GIMP's Color to Alpha algorithm

    Args:
        image_path: Path to input image
        target_color: RGB tuple of color to remove (default: black)
        output_path: Optional output path

    GIMP Settings replicated:
    - Transparency threshold: 0
    - Opacity threshold: 1
    - Mode: replace
    - Opacity: 100%
    """
    img = Image.open(image_path).convert("RGBA")
    data = np.array(img, dtype=np.float64)

    # Normalize to 0-1 range for calculations
    data = data / 255.0
    target = np.array(target_color, dtype=np.float64) / 255.0

    height, width = data.shape[:2]

    for y in range(height):
        for x in range(width):
            pixel = data[y, x]
            red, green, blue, alpha = pixel[0], pixel[1], pixel[2], pixel[3]

            # GIMP's Color to Alpha algorithm
            target_red, target_green, target_blue = target[0], target[1], target[2]

            # Calculate the alpha based on how much of the target color is present
            if target_red == 0.0 and target_green == 0.0 and target_blue == 0.0:
                # Special case for pure black target
                # Alpha is the maximum of the RGB components
                new_alpha = max(red, green, blue)

                if new_alpha > 0:
                    # Remove the black component, scale remaining color
                    data[y, x, 0] = red / new_alpha if new_alpha > 0 else 0
                    data[y, x, 1] = green / new_alpha if new_alpha > 0 else 0
                    data[y, x, 2] = blue / new_alpha if new_alpha > 0 else 0
                else:
                    # Pure black becomes transparent
                    data[y, x, 0] = 0
                    data[y, x, 1] = 0
                    data[y, x, 2] = 0
                    new_alpha = 0

                # Replace mode: completely replace the alpha
                data[y, x, 3] = new_alpha * alpha

            else:
                # General case for non-black target colors
                # Calculate alpha as minimum ratio needed to remove target color
                alpha_r = (red - target_red) / (1.0 - target_red) if target_red < 1.0 else 0
                alpha_g = (green - target_green) / (1.0 - target_green) if target_green < 1.0 else 0
                alpha_b = (blue - target_blue) / (1.0 - target_blue) if target_blue < 1.0 else 0

                new_alpha = max(0, max(alpha_r, alpha_g, alpha_b))

                if new_alpha > 0:
                    # Calculate new RGB values
                    data[y, x, 0] = (red - target_red) / new_alpha + target_red if new_alpha > 0 else target_red
                    data[y, x, 1] = (green - target_green) / new_alpha + target_green if new_alpha > 0 else target_green
                    data[y, x, 2] = (blue - target_blue) / new_alpha + target_blue if new_alpha > 0 else target_blue
                else:
                    data[y, x, 0] = target_red
                    data[y, x, 1] = target_green
                    data[y, x, 2] = target_blue

                # Replace mode: completely replace the alpha
                data[y, x, 3] = new_alpha * alpha

    # Convert back to 0-255 range and uint8
    data = np.clip(data * 255.0, 0, 255).astype(np.uint8)
    result = Image.fromarray(data)

    if output_path:
        result.save(output_path)
    return result


def gimp_color_to_alpha_vectorized(image_path, target_color=(0, 0, 0), output_path=None):
    """
    Vectorized version of GIMP's Color to Alpha algorithm for better performance
    """
    img = Image.open(image_path).convert("RGBA")
    data = np.array(img, dtype=np.float64) / 255.0

    target = np.array(target_color, dtype=np.float64) / 255.0
    target_red, target_green, target_blue = target[0], target[1], target[2]

    red, green, blue, alpha = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]

    if target_red == 0.0 and target_green == 0.0 and target_blue == 0.0:
        # Special case for black target - vectorized
        new_alpha = np.maximum(np.maximum(red, green), blue)

        # Avoid division by zero
        safe_alpha = np.where(new_alpha > 0, new_alpha, 1)

        # Scale RGB values
        new_r = np.where(new_alpha > 0, red / safe_alpha, 0)
        new_g = np.where(new_alpha > 0, green / safe_alpha, 0)
        new_b = np.where(new_alpha > 0, blue / safe_alpha, 0)

        # Apply new values
        data[:, :, 0] = new_r
        data[:, :, 1] = new_g
        data[:, :, 2] = new_b
        data[:, :, 3] = new_alpha * alpha

    else:
        # General case for non-black colors - vectorized
        alpha_r = np.where(target_red < 1.0, (red - target_red) / (1.0 - target_red), 0)
        alpha_g = np.where(target_green < 1.0, (green - target_green) / (1.0 - target_green), 0)
        alpha_b = np.where(target_blue < 1.0, (blue - target_blue) / (1.0 - target_blue), 0)

        new_alpha = np.maximum(0, np.maximum(np.maximum(alpha_r, alpha_g), alpha_b))

        # Calculate new RGB
        safe_alpha = np.where(new_alpha > 0, new_alpha, 1)
        new_r = np.where(new_alpha > 0, (red - target_red) / safe_alpha + target_red, target_red)
        new_g = np.where(new_alpha > 0, (green - target_green) / safe_alpha + target_green, target_green)
        new_b = np.where(new_alpha > 0, (blue - target_blue) / safe_alpha + target_blue, target_blue)

        data[:, :, 0] = new_r
        data[:, :, 1] = new_g
        data[:, :, 2] = new_b
        data[:, :, 3] = new_alpha * alpha

    # Convert back to uint8
    data = np.clip(data * 255.0, 0, 255).astype(np.uint8)
    result = Image.fromarray(data)

    if output_path:
        result.save(output_path)
    return result


# Usage examples
if __name__ == "__main__":
    # Basic usage - convert black to alpha
    gimp_color_to_alpha_exact("gradient_clear.png", output_path="gradient_clear.png")

    print("Color to Alpha processing complete!")
